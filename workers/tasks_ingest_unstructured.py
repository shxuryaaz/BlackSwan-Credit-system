import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re

# Database setup
DATABASE_URL = "postgresql://credtech:credtech_pass@postgres:5432/credtech"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Sentiment analyzer
sentiment_analyzer = SentimentIntensityAnalyzer()

def classify_event(headline: str, content: str = "") -> Dict[str, Any]:
    """Classify event type based on keywords and content."""
    text = f"{headline} {content}".lower()
    
    # Event classification keywords
    event_types = {
        "earnings": ["earnings", "revenue", "profit", "quarterly", "financial results"],
        "merger": ["merger", "acquisition", "buyout", "takeover", "deal"],
        "product": ["product", "launch", "recall", "announcement", "release"],
        "regulatory": ["regulatory", "investigation", "lawsuit", "fine", "compliance"],
        "leadership": ["ceo", "executive", "resignation", "appointment", "leadership"],
        "market": ["market", "trading", "stock", "price", "volatility"],
        "default": ["default", "bankruptcy", "restructuring", "debt", "credit"]
    }
    
    # Find matching event type
    for event_type, keywords in event_types.items():
        if any(keyword in text for keyword in keywords):
            return {
                "type": event_type,
                "confidence": 0.8,
                "keywords_found": [k for k in keywords if k in text]
            }
    
    # Default to market event if no specific type found
    return {
        "type": "market",
        "confidence": 0.5,
        "keywords_found": []
    }

def calculate_sentiment(text: str) -> Dict[str, float]:
    """Calculate sentiment scores using VADER."""
    scores = sentiment_analyzer.polarity_scores(text)
    return {
        "compound": scores["compound"],
        "positive": scores["pos"],
        "negative": scores["neg"],
        "neutral": scores["neu"]
    }

def calculate_event_weight(event_type: str, sentiment: float, headline_length: int) -> float:
    """Calculate event weight based on type, sentiment, and headline characteristics."""
    # Base weights by event type
    type_weights = {
        "default": 0.9,
        "regulatory": 0.8,
        "earnings": 0.7,
        "merger": 0.6,
        "leadership": 0.5,
        "product": 0.4,
        "market": 0.3
    }
    
    base_weight = type_weights.get(event_type, 0.3)
    
    # Adjust for sentiment (negative events have higher impact)
    sentiment_multiplier = 1.0
    if sentiment < -0.3:
        sentiment_multiplier = 1.5  # Negative events have higher impact
    elif sentiment > 0.3:
        sentiment_multiplier = 0.8  # Positive events have lower impact
    
    # Adjust for headline length (longer headlines might be more significant)
    length_multiplier = min(1.5, max(0.5, headline_length / 50))
    
    return base_weight * sentiment_multiplier * length_multiplier

def process_news_event(issuer_ticker: str, headline: str, content: str = "") -> Dict[str, Any]:
    """Process a news event and return analysis results."""
    # Classify event
    event_classification = classify_event(headline, content)
    
    # Calculate sentiment
    sentiment_scores = calculate_sentiment(headline)
    
    # Calculate event weight
    event_weight = calculate_event_weight(
        event_classification["type"],
        sentiment_scores["compound"],
        len(headline)
    )
    
    # Generate raw hash for deduplication
    raw_hash = hashlib.md5(f"{issuer_ticker}:{headline}".encode()).hexdigest()
    
    return {
        "issuer_ticker": issuer_ticker,
        "headline": headline,
        "content": content,
        "event_type": event_classification["type"],
        "sentiment": sentiment_scores["compound"],
        "event_weight": event_weight,
        "raw_hash": raw_hash,
        "processed_at": datetime.utcnow()
    }

def store_event_and_update_score(event_data: Dict[str, Any]) -> bool:
    """Store event in database and trigger score update."""
    try:
        with SessionLocal() as session:
            # Get issuer ID
            result = session.execute(
                text("SELECT id FROM issuer WHERE ticker = :ticker"),
                {"ticker": event_data["issuer_ticker"]}
            )
            issuer_row = result.fetchone()
            
            if not issuer_row:
                print(f"Issuer {event_data['issuer_ticker']} not found")
                return False
            
            issuer_id = issuer_row[0]
            
            # Insert event
            session.execute(
                text("""
                    INSERT INTO event (issuer_id, ts, type, headline, url, 
                                     sentiment, weight, raw_hash, source)
                    VALUES (:issuer_id, :ts, :event_type, :headline, :url,
                           :sentiment, :event_weight, :raw_hash, :source)
                """),
                {
                    "issuer_id": issuer_id,
                    "ts": datetime.utcnow(),
                    "event_type": event_data["event_type"],
                    "headline": event_data["headline"],
                    "url": f"demo://{event_data['issuer_ticker']}",
                    "sentiment": event_data["sentiment"],
                    "event_weight": event_data["event_weight"],
                    "raw_hash": event_data["raw_hash"],
                    "source": "demo"
                }
            )
            
            # Update credit score based on event
            update_credit_score(session, issuer_id, event_data)
            
            session.commit()
            print(f"Event processed and score updated for {event_data['issuer_ticker']}")
            return True
            
    except Exception as e:
        print(f"Error processing event: {e}")
        return False

def update_credit_score(session, issuer_id: int, event_data: Dict[str, Any]):
    """Update credit score based on event impact."""
    # Get current score
    result = session.execute(
        text("""
            SELECT score
            FROM score 
            WHERE issuer_id = :issuer_id 
            ORDER BY ts DESC 
            LIMIT 1
        """),
        {"issuer_id": issuer_id}
    )
    current_score = result.fetchone()
    
    if not current_score:
        return
    
    # Calculate event impact (enhanced for demo visibility)
    event_impact = event_data["sentiment"] * event_data["event_weight"] * 15
    
    # Calculate new score
    new_score = current_score.score + event_impact
    
    # Ensure score stays within bounds
    new_score = max(0, min(100, new_score))
    
    # Calculate bucket based on score
    if new_score >= 85:
        bucket = "AA"
    elif new_score >= 75:
        bucket = "A"
    elif new_score >= 65:
        bucket = "BBB"
    elif new_score >= 55:
        bucket = "BB"
    elif new_score >= 45:
        bucket = "B"
    else:
        bucket = "CCC"
    
    # Insert new score
    session.execute(
        text("""
            INSERT INTO score (issuer_id, ts, score, bucket, base, market, event_delta, macro_adj, model_version, explanation)
            VALUES (:issuer_id, :ts, :score, :bucket, :base, :market, :event_delta, :macro_adj, :model_version, :explanation)
        """),
        {
            "issuer_id": issuer_id,
            "ts": datetime.utcnow(),
            "score": new_score,
            "bucket": bucket,
            "base": current_score.score,
            "market": 0.0,
            "event_delta": event_impact,
            "macro_adj": 0.0,
            "model_version": "v1.0",
            "explanation": f'{{"event_type": "{event_data["event_type"]}", "sentiment": {event_data["sentiment"]:.2f}, "impact": {event_impact:.2f}}}'
        }
    )

# Main function for processing events
def process_event(issuer_ticker: str, headline: str, content: str = "") -> bool:
    """Main function to process a news event."""
    event_data = process_news_event(issuer_ticker, headline, content)
    return store_event_and_update_score(event_data)

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        ticker = sys.argv[1]
        headline = sys.argv[2]
        content = sys.argv[3] if len(sys.argv) > 3 else ""
        
        success = process_event(ticker, headline, content)
        if success:
            print(f"✅ Event processed successfully for {ticker}")
        else:
            print(f"❌ Failed to process event for {ticker}")
    else:
        print("Usage: python tasks_ingest_unstructured.py <TICKER> <HEADLINE> [CONTENT]")





