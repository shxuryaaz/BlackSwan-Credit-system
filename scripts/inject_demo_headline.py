#!/usr/bin/env python3
"""
Demo headline injection script for BlackSwan Credit Intelligence Platform.
Simulates real-time news events and shows score changes.
"""

import sys
import os
import argparse
import hashlib
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from workers.tasks_ingest_unstructured import classify_event, calculate_sentiment, calculate_event_weight
from workers.tasks_score_compute import compute_issuer_score

# Load environment variables
load_dotenv()

# Database connection
def get_db_session():
    """Get database session"""
    database_url = f"postgresql://{os.getenv('POSTGRES_USER', 'credtech')}:{os.getenv('POSTGRES_PASSWORD', 'credtech_pass')}@{os.getenv('POSTGRES_HOST', 'postgres')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'credtech')}"
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def get_issuer_by_ticker(db, ticker):
    """Get issuer by ticker symbol"""
    issuer = db.execute(
        text("SELECT id, name, ticker FROM issuer WHERE ticker = :ticker"),
        {"ticker": ticker.upper()}
    ).fetchone()
    return issuer

def get_latest_score(db, issuer_id):
    """Get latest score for an issuer"""
    score = db.execute(
        text("""
            SELECT score, bucket, ts, base, market, event_delta, macro_adj, explanation
            FROM score 
            WHERE issuer_id = :issuer_id 
            ORDER BY ts DESC 
            LIMIT 1
        """),
        {"issuer_id": issuer_id}
    ).fetchone()
    return score

def inject_event(db, issuer_id, headline, event_type, sentiment):
    """Inject a new event into the database"""
    try:
        # Calculate event weight
        weight = calculate_event_weight(event_type, sentiment)
        
        # Create hash for deduplication
        content_hash = hashlib.sha256(f"{headline}{datetime.now().isoformat()}".encode()).hexdigest()
        
        # Insert event
        db.execute(
            text("""
                INSERT INTO event (issuer_id, ts, type, sentiment, weight, headline, url, raw_hash, source)
                VALUES (:issuer_id, :ts, :type, :sentiment, :weight, :headline, :url, :hash, :source)
            """),
            {
                "issuer_id": issuer_id,
                "ts": datetime.now(),
                "type": event_type,
                "sentiment": sentiment,
                "weight": weight,
                "headline": headline,
                "url": "https://demo.blackswan.com/news",
                "hash": content_hash,
                "source": "demo_injection"
            }
        )
        
        db.commit()
        return True
        
    except Exception as e:
        print(f"Error injecting event: {e}")
        db.rollback()
        return False

def compute_new_score(issuer_id):
    """Compute new score for the issuer"""
    try:
        # Import the task function
        from workers.tasks_score_compute import compute_issuer_score
        
        # Run the task directly (not as Celery task for demo)
        result = compute_issuer_score(issuer_id)
        return result
        
    except Exception as e:
        print(f"Error computing new score: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Inject demo headline and show score change")
    parser.add_argument("--issuer", required=True, help="Ticker symbol (e.g., AAPL)")
    parser.add_argument("--headline", required=True, help="News headline")
    parser.add_argument("--type", required=True, 
                       choices=["restructuring", "bankruptcy", "downgrade", "earnings_miss", 
                               "guidance_cut", "management_change", "acquisition", 
                               "positive_earnings_beat", "dividend_cut", "regulatory_investigation"],
                       help="Event type")
    parser.add_argument("--sentiment", type=float, default=0.0, 
                       help="Sentiment score (-1 to 1, default: auto-calculate)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("BLACKSWAN CREDIT INTELLIGENCE - DEMO HEADLINE INJECTION")
    print("=" * 60)
    
    try:
        db = get_db_session()
        
        # Get issuer
        issuer = get_issuer_by_ticker(db, args.issuer)
        if not issuer:
            print(f"❌ Issuer not found: {args.issuer}")
            sys.exit(1)
        
        issuer_id, issuer_name, ticker = issuer
        print(f"📊 Issuer: {issuer_name} ({ticker})")
        
        # Get current score
        current_score = get_latest_score(db, issuer_id)
        if not current_score:
            print(f"❌ No current score found for {ticker}")
            sys.exit(1)
        
        current_score_val, current_bucket, score_ts, base, market, event_delta, macro_adj, explanation = current_score
        
        print(f"\n📈 CURRENT SCORE:")
        print(f"   Score: {current_score_val:.1f}")
        print(f"   Bucket: {current_bucket}")
        print(f"   Components: Base={base:.2f}, Market={market:.2f}, Events={event_delta:.2f}, Macro={macro_adj:.2f}")
        
        # Auto-calculate sentiment if not provided
        sentiment = args.sentiment
        if sentiment == 0.0:
            sentiment = calculate_sentiment(args.headline)
            print(f"\n🧠 Auto-calculated sentiment: {sentiment:.2f}")
        
        # Classify event
        detected_type, confidence = classify_event(args.headline)
        if detected_type != args.type:
            print(f"⚠️  Warning: Detected event type '{detected_type}' differs from specified '{args.type}'")
        
        # Calculate event weight
        weight = calculate_event_weight(args.type, sentiment)
        
        print(f"\n📰 INJECTING EVENT:")
        print(f"   Headline: {args.headline}")
        print(f"   Type: {args.type}")
        print(f"   Sentiment: {sentiment:.2f}")
        print(f"   Weight: {weight:.2f}")
        
        # Inject event
        if inject_event(db, issuer_id, args.headline, args.type, sentiment):
            print("✅ Event injected successfully")
        else:
            print("❌ Failed to inject event")
            sys.exit(1)
        
        # Compute new score
        print(f"\n🔄 Computing new score...")
        new_score_result = compute_new_score(issuer_id)
        
        if new_score_result and new_score_result.get("status") == "success":
            new_score = new_score_result["score"]
            new_bucket = new_score_result["bucket"]
            new_components = new_score_result["components"]
            
            score_change = new_score - current_score_val
            
            print(f"\n📊 NEW SCORE:")
            print(f"   Score: {new_score:.1f} ({score_change:+.1f})")
            print(f"   Bucket: {new_bucket}")
            print(f"   Components: Base={new_components['base']:.2f}, Market={new_components['market']:.2f}, Events={new_components['event_delta']:.2f}, Macro={new_components['macro_adj']:.2f}")
            
            # Show explanation
            if "explanation" in new_score_result:
                explanation = new_score_result["explanation"]
                print(f"\n💡 EXPLANATION:")
                print(f"   Summary: {explanation.get('summary', 'No summary available')}")
                
                if explanation.get("top_features"):
                    print(f"   Top Features:")
                    for feature in explanation["top_features"][:3]:
                        print(f"     • {feature['name']}: {feature['impact']:+.1f}")
                
                if explanation.get("events"):
                    print(f"   Recent Events:")
                    for event in explanation["events"][:2]:
                        print(f"     • {event['headline'][:50]}... ({event['impact']:+.1f})")
            
            # Show impact analysis
            print(f"\n📊 IMPACT ANALYSIS:")
            if abs(score_change) >= 5:
                print(f"   🚨 SIGNIFICANT CHANGE: Score changed by {abs(score_change):.1f} points")
                if score_change < 0:
                    print(f"   📉 Credit risk increased")
                else:
                    print(f"   📈 Credit risk decreased")
            else:
                print(f"   📊 Moderate change: Score changed by {abs(score_change):.1f} points")
            
            # Bucket change
            if new_bucket != current_bucket:
                print(f"   🏷️  Rating bucket changed: {current_bucket} → {new_bucket}")
            else:
                print(f"   🏷️  Rating bucket unchanged: {current_bucket}")
        
        else:
            print("❌ Failed to compute new score")
            sys.exit(1)
        
        print(f"\n✅ Demo completed successfully!")
        print(f"   Event: {args.headline}")
        print(f"   Score change: {current_score_val:.1f} → {new_score:.1f} ({score_change:+.1f})")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    main()





