import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import structlog
from celery import current_task
import os
from dotenv import load_dotenv
import json

from celery_app import celery_app

# Load environment variables
load_dotenv()

logger = structlog.get_logger()

# Database connection
def get_db_session():
    """Get database session"""
    database_url = f"postgresql://{os.getenv('POSTGRES_USER', 'credtech')}:{os.getenv('POSTGRES_PASSWORD', 'credtech_pass')}@{os.getenv('POSTGRES_HOST', 'postgres')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'credtech')}"
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

# Scoring weights (from settings)
SCORING_WEIGHTS = {
    "base": 0.55,
    "market": 0.25,
    "event": 0.12,
    "macro": 0.08
}

def sigmoid(x):
    """Sigmoid function for score normalization"""
    return 1 / (1 + np.exp(-x))

def get_score_bucket(score: float) -> str:
    """Map score to rating bucket"""
    if score >= 90:
        return "AAA"
    elif score >= 80:
        return "AA"
    elif score >= 70:
        return "BBB"
    elif score >= 60:
        return "BB"
    elif score >= 50:
        return "B"
    elif score >= 30:
        return "CCC"
    else:
        return "CC"

def normalize_feature(value: float, feature_name: str) -> float:
    """Normalize feature values to [-1, 1] range"""
    if value is None or np.isnan(value):
        return 0.0
    
    # Feature-specific normalization
    if feature_name == "icr":
        # Interest Coverage Ratio: clip [-10, 50], then logistic mapping
        clipped = np.clip(value, -10, 50)
        return 1 / (1 + np.exp(-0.2 * (clipped - 2)))
    
    elif feature_name == "debt_to_ebitda":
        # Debt/EBITDA: clip [0, 50], monotonic decreasing
        clipped = np.clip(value, 0, 50)
        return 1 - np.tanh(clipped / 10)
    
    elif feature_name == "current_ratio":
        # Current Ratio: clip [0, 10], linear scale
        clipped = np.clip(value, 0, 10)
        return clipped / 10
    
    elif feature_name == "vol_30d":
        # Volatility: log transform
        return np.log1p(value)
    
    elif feature_name == "max_drawdown_30d":
        # Max Drawdown: sqrt transform
        return np.sqrt(value)
    
    else:
        # Default: clip to [-3, 3] and scale
        clipped = np.clip(value, -3, 3)
        return clipped / 3

def calculate_base_score(issuer_id: int, db) -> tuple:
    """Calculate base score from fundamental features"""
    try:
        # Get latest fundamental features
        features = db.execute(
            text("""
                SELECT feature_name, value 
                FROM feature_snapshot 
                WHERE issuer_id = :issuer_id 
                AND feature_name IN ('icr', 'debt_to_ebitda', 'current_ratio', 'rev_yoy', 'altman_z')
                AND ts = (
                    SELECT MAX(ts) 
                    FROM feature_snapshot 
                    WHERE issuer_id = :issuer_id 
                    AND feature_name = feature_snapshot.feature_name
                )
            """),
            {"issuer_id": issuer_id}
        ).fetchall()
        
        if not features:
            return 0.0, []
        
        # Calculate weighted base score
        base_score = 0.0
        feature_contributions = []
        
        feature_weights = {
            "icr": 0.3,
            "debt_to_ebitda": 0.25,
            "current_ratio": 0.2,
            "rev_yoy": 0.15,
            "altman_z": 0.1
        }
        
        for feature_name, value in features:
            if feature_name in feature_weights:
                normalized_value = normalize_feature(value, feature_name)
                weight = feature_weights[feature_name]
                contribution = normalized_value * weight
                base_score += contribution
                
                feature_contributions.append({
                    "name": feature_name,
                    "value": value,
                    "normalized": normalized_value,
                    "weight": weight,
                    "contribution": contribution
                })
        
        return base_score, feature_contributions
        
    except Exception as e:
        logger.error("Failed to calculate base score", error=str(e), issuer_id=issuer_id)
        return 0.0, []

def calculate_market_score(issuer_id: int, db) -> tuple:
    """Calculate market risk score"""
    try:
        # Get latest market features
        features = db.execute(
            text("""
                SELECT feature_name, value 
                FROM feature_snapshot 
                WHERE issuer_id = :issuer_id 
                AND feature_name IN ('vol_30d', 'max_drawdown_30d', 'beta_180d')
                AND ts = (
                    SELECT MAX(ts) 
                    FROM feature_snapshot 
                    WHERE issuer_id = :issuer_id 
                    AND feature_name = feature_snapshot.feature_name
                )
            """),
            {"issuer_id": issuer_id}
        ).fetchall()
        
        if not features:
            return 0.0, []
        
        # Calculate negative market risk score
        market_score = 0.0
        feature_contributions = []
        
        feature_weights = {
            "vol_30d": 0.5,
            "max_drawdown_30d": 0.3,
            "beta_180d": 0.2
        }
        
        for feature_name, value in features:
            if feature_name in feature_weights:
                normalized_value = normalize_feature(value, feature_name)
                weight = feature_weights[feature_name]
                contribution = -normalized_value * weight  # Negative for risk
                market_score += contribution
                
                feature_contributions.append({
                    "name": feature_name,
                    "value": value,
                    "normalized": normalized_value,
                    "weight": weight,
                    "contribution": contribution
                })
        
        return market_score, feature_contributions
        
    except Exception as e:
        logger.error("Failed to calculate market score", error=str(e), issuer_id=issuer_id)
        return 0.0, []

def calculate_event_score(issuer_id: int, db) -> tuple:
    """Calculate event impact score"""
    try:
        # Get active events (last 7 days with significant impact)
        events = db.execute(
            text("""
                SELECT type, sentiment, weight, decay_factor, headline, url, ts
                FROM event 
                WHERE issuer_id = :issuer_id 
                AND ts >= NOW() - INTERVAL '7 days'
                AND decay_factor > 0.1
                ORDER BY ts DESC
            """),
            {"issuer_id": issuer_id}
        ).fetchall()
        
        if not events:
            return 0.0, []
        
        # Calculate total event impact
        event_score = 0.0
        event_contributions = []
        
        for event in events:
            event_type, sentiment, weight, decay_factor, headline, url, ts = event
            
            # Calculate effective impact
            effective_weight = weight * decay_factor
            event_score += effective_weight
            
            event_contributions.append({
                "type": event_type,
                "sentiment": sentiment,
                "weight": weight,
                "decay_factor": decay_factor,
                "effective_weight": effective_weight,
                "headline": headline,
                "url": url,
                "ts": ts.isoformat() if ts else None
            })
        
        # Scale to [-1, 1] range
        event_score = np.clip(event_score / 10, -1.5, 1.0)
        
        return event_score, event_contributions
        
    except Exception as e:
        logger.error("Failed to calculate event score", error=str(e), issuer_id=issuer_id)
        return 0.0, []

def calculate_macro_score(issuer_id: int, db) -> tuple:
    """Calculate macro adjustment score"""
    try:
        # Get latest macro indicators
        macro_data = db.execute(
            text("""
                SELECT key, value 
                FROM macro 
                WHERE key IN ('cpi_yoy', 'pmi', 'policy_rate', 'gdp_growth')
                AND ts = (
                    SELECT MAX(ts) 
                    FROM macro 
                    WHERE key = macro.key
                )
            """)
        ).fetchall()
        
        if not macro_data:
            return 0.0, []
        
        # Simple macro adjustment (placeholder implementation)
        macro_score = 0.0
        macro_contributions = []
        
        for key, value in macro_data:
            # Simplified macro adjustments
            if key == "cpi_yoy":
                # High CPI is negative for credit
                adjustment = -0.1 if value > 3.0 else 0.0
            elif key == "pmi":
                # PMI > 50 is positive
                adjustment = 0.1 if value > 50 else -0.1
            elif key == "policy_rate":
                # High rates are negative
                adjustment = -0.05 if value > 5.0 else 0.0
            elif key == "gdp_growth":
                # High growth is positive
                adjustment = 0.1 if value > 2.0 else -0.1
            else:
                adjustment = 0.0
            
            macro_score += adjustment
            macro_contributions.append({
                "indicator": key,
                "value": value,
                "adjustment": adjustment
            })
        
        # Clip to [-0.3, 0.3] range
        macro_score = np.clip(macro_score, -0.3, 0.3)
        
        return macro_score, macro_contributions
        
    except Exception as e:
        logger.error("Failed to calculate macro score", error=str(e), issuer_id=issuer_id)
        return 0.0, []

def generate_explanation(base_contributions, market_contributions, event_contributions, macro_contributions) -> dict:
    """Generate explanation for score components"""
    try:
        # Top features (combine base and market)
        all_features = []
        for contrib in base_contributions + market_contributions:
            all_features.append({
                "name": contrib["name"],
                "impact": round(contrib["contribution"] * 100, 1)  # Scale to percentage points
            })
        
        # Sort by absolute impact
        all_features.sort(key=lambda x: abs(x["impact"]), reverse=True)
        top_features = all_features[:5]
        
        # Recent events
        events = []
        for event in event_contributions:
            events.append({
                "type": event["type"],
                "headline": event["headline"],
                "impact": round(event["effective_weight"], 1),
                "url": event["url"],
                "ts": event["ts"]
            })
        
        # Generate summary
        total_impact = sum(f["impact"] for f in top_features)
        direction = "increased" if total_impact > 0 else "decreased"
        
        summary = f"Score {direction} by {abs(total_impact):.1f} points. "
        if top_features:
            main_driver = top_features[0]
            summary += f"Primary driver: {main_driver['name']} ({main_driver['impact']:+.1f}). "
        if events:
            summary += f"Recent events: {len(events)} significant news items."
        
        return {
            "top_features": top_features,
            "events": events,
            "summary": summary
        }
        
    except Exception as e:
        logger.error("Failed to generate explanation", error=str(e))
        return {
            "top_features": [],
            "events": [],
            "summary": "Explanation generation failed"
        }

@celery_app.task(bind=True, name="compute_issuer_score")
def compute_issuer_score(self, issuer_id: int):
    """
    Compute credit score for a specific issuer.
    """
    try:
        logger.info("Starting score computation", issuer_id=issuer_id)
        
        db = get_db_session()
        
        # Verify issuer exists
        issuer = db.execute(
            text("SELECT name, ticker FROM issuer WHERE id = :id"),
            {"id": issuer_id}
        ).fetchone()
        
        if not issuer:
            logger.error("Issuer not found", issuer_id=issuer_id)
            return {"status": "error", "message": "Issuer not found"}
        
        # Calculate score components
        base_score, base_contributions = calculate_base_score(issuer_id, db)
        market_score, market_contributions = calculate_market_score(issuer_id, db)
        event_score, event_contributions = calculate_event_score(issuer_id, db)
        macro_score, macro_contributions = calculate_macro_score(issuer_id, db)
        
        # Calculate final score
        final_score_raw = (
            SCORING_WEIGHTS["base"] * base_score +
            SCORING_WEIGHTS["market"] * market_score +
            SCORING_WEIGHTS["event"] * event_score +
            SCORING_WEIGHTS["macro"] * macro_score
        )
        
        # Apply sigmoid and scale to 0-100
        final_score = 100 * sigmoid(final_score_raw)
        final_score = np.clip(final_score, 0, 100)
        
        # Get rating bucket
        bucket = get_score_bucket(final_score)
        
        # Generate explanation
        explanation = generate_explanation(
            base_contributions, market_contributions, 
            event_contributions, macro_contributions
        )
        
        # Store score
        current_time = datetime.now()
        db.execute(
            text("""
                INSERT INTO score (issuer_id, ts, score, bucket, base, market, event_delta, macro_adj, model_version, explanation)
                VALUES (:issuer_id, :ts, :score, :bucket, :base, :market, :event_delta, :macro_adj, :model_version, :explanation)
            """),
            {
                "issuer_id": issuer_id,
                "ts": current_time,
                "score": float(final_score),
                "bucket": bucket,
                "base": float(base_score),
                "market": float(market_score),
                "event_delta": float(event_score),
                "macro_adj": float(macro_score),
                "model_version": "v1.0",
                "explanation": json.dumps(explanation)
            }
        )
        
        db.commit()
        db.close()
        
        logger.info("Score computation completed", 
                   issuer_id=issuer_id, 
                   score=final_score, 
                   bucket=bucket)
        
        return {
            "status": "success",
            "issuer_id": issuer_id,
            "score": final_score,
            "bucket": bucket,
            "components": {
                "base": base_score,
                "market": market_score,
                "event_delta": event_score,
                "macro_adj": macro_score
            },
            "explanation": explanation
        }
        
    except Exception as e:
        logger.error("Score computation failed", error=str(e), issuer_id=issuer_id)
        if 'db' in locals():
            db.rollback()
            db.close()
        raise

@celery_app.task(bind=True, name="compute_all_scores")
def compute_all_scores(self):
    """
    Compute scores for all issuers.
    """
    try:
        logger.info("Starting score computation for all issuers")
        
        db = get_db_session()
        
        # Get all issuers
        issuers = db.execute(
            text("SELECT id FROM issuer")
        ).fetchall()
        
        results = []
        for issuer in issuers:
            try:
                result = compute_issuer_score.delay(issuer[0])
                results.append({"issuer_id": issuer[0], "task_id": result.id})
            except Exception as e:
                logger.error("Failed to queue score computation", error=str(e), issuer_id=issuer[0])
        
        db.close()
        
        logger.info("Queued score computation tasks", count=len(results))
        return {"status": "success", "tasks_queued": len(results), "results": results}
        
    except Exception as e:
        logger.error("Failed to queue score computations", error=str(e))
        raise

@celery_app.task(bind=True, name="schedule_score_computation")
def schedule_score_computation(self):
    """
    Schedule score computation tasks.
    """
    try:
        logger.info("Scheduling score computation")
        
        # Compute scores for all issuers
        compute_all_scores.delay()
        
        logger.info("Score computation scheduled")
        return {"status": "success", "message": "Tasks scheduled"}
        
    except Exception as e:
        logger.error("Failed to schedule score computation", error=str(e))
        raise





