#!/usr/bin/env python3
"""
Demo data seeding script for BlackSwan Credit Intelligence Platform.
Populates the database with sample issuers and historical data.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import random
import numpy as np
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
def get_db_session():
    """Get database session"""
    database_url = f"postgresql://{os.getenv('POSTGRES_USER', 'credtech')}:{os.getenv('POSTGRES_PASSWORD', 'credtech_pass')}@{os.getenv('POSTGRES_HOST', 'postgres')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'credtech')}"
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

# Sample issuers data
SAMPLE_ISSUERS = [
    {"name": "Apple Inc", "ticker": "AAPL", "cik": "0000320193", "sector": "Technology", "country": "US"},
    {"name": "Microsoft Corporation", "ticker": "MSFT", "cik": "0000789019", "sector": "Technology", "country": "US"},
    {"name": "Alphabet Inc", "ticker": "GOOGL", "cik": "0001652044", "sector": "Technology", "country": "US"},
    {"name": "Amazon.com Inc", "ticker": "AMZN", "cik": "0001018724", "sector": "Consumer Discretionary", "country": "US"},
    {"name": "Tesla Inc", "ticker": "TSLA", "cik": "0001318605", "sector": "Consumer Discretionary", "country": "US"},
    {"name": "JPMorgan Chase & Co", "ticker": "JPM", "cik": "0000019617", "sector": "Financial Services", "country": "US"},
    {"name": "Bank of America Corp", "ticker": "BAC", "cik": "0000070858", "sector": "Financial Services", "country": "US"},
    {"name": "Wells Fargo & Co", "ticker": "WFC", "cik": "0000072971", "sector": "Financial Services", "country": "US"},
    {"name": "Exxon Mobil Corporation", "ticker": "XOM", "cik": "0000034088", "sector": "Energy", "country": "US"},
    {"name": "Chevron Corporation", "ticker": "CVX", "cik": "0000093410", "sector": "Energy", "country": "US"},
    {"name": "Johnson & Johnson", "ticker": "JNJ", "cik": "0000200406", "sector": "Healthcare", "country": "US"},
    {"name": "Pfizer Inc", "ticker": "PFE", "cik": "0000078003", "sector": "Healthcare", "country": "US"},
    {"name": "Procter & Gamble Co", "ticker": "PG", "cik": "0000080424", "sector": "Consumer Staples", "country": "US"},
    {"name": "Coca-Cola Co", "ticker": "KO", "cik": "0000021344", "sector": "Consumer Staples", "country": "US"},
    {"name": "Walmart Inc", "ticker": "WMT", "cik": "0000104169", "sector": "Consumer Staples", "country": "US"}
]

def seed_issuers(db):
    """Seed issuers table"""
    print("Seeding issuers...")
    
    for issuer_data in SAMPLE_ISSUERS:
        # Check if issuer already exists
        existing = db.execute(
            text("SELECT id FROM issuer WHERE ticker = :ticker"),
            {"ticker": issuer_data["ticker"]}
        ).fetchone()
        
        if not existing:
            db.execute(
                text("""
                    INSERT INTO issuer (name, ticker, cik, sector, country)
                    VALUES (:name, :ticker, :cik, :sector, :country)
                """),
                issuer_data
            )
            print(f"  Added: {issuer_data['name']} ({issuer_data['ticker']})")
        else:
            print(f"  Exists: {issuer_data['name']} ({issuer_data['ticker']})")
    
    db.commit()

def generate_historical_prices(issuer_id, start_date, end_date, base_price, volatility):
    """Generate historical price data"""
    dates = []
    prices = []
    current_price = base_price
    
    current_date = start_date
    while current_date <= end_date:
        # Generate daily price movement
        daily_return = np.random.normal(0, volatility)
        current_price *= (1 + daily_return)
        
        # Add some noise
        current_price += np.random.normal(0, base_price * 0.01)
        
        # Ensure positive price
        current_price = max(current_price, base_price * 0.5)
        
        dates.append(current_date)
        prices.append(current_price)
        
        current_date += timedelta(days=1)
    
    return dates, prices

def seed_price_data(db):
    """Seed price data for all issuers"""
    print("Seeding price data...")
    
    issuers = db.execute(text("SELECT id, ticker FROM issuer")).fetchall()
    
    # Base prices for different sectors
    base_prices = {
        "Technology": 150.0,
        "Financial Services": 50.0,
        "Energy": 80.0,
        "Healthcare": 100.0,
        "Consumer Staples": 60.0,
        "Consumer Discretionary": 120.0
    }
    
    # Volatility by sector
    volatilities = {
        "Technology": 0.025,
        "Financial Services": 0.020,
        "Energy": 0.030,
        "Healthcare": 0.022,
        "Consumer Staples": 0.015,
        "Consumer Discretionary": 0.028
    }
    
    start_date = datetime.now() - timedelta(days=365)
    end_date = datetime.now()
    
    for issuer_id, ticker in issuers:
        # Get sector
        sector = db.execute(
            text("SELECT sector FROM issuer WHERE id = :id"),
            {"id": issuer_id}
        ).fetchone()[0]
        
        base_price = base_prices.get(sector, 100.0)
        volatility = volatilities.get(sector, 0.020)
        
        # Generate historical prices
        dates, prices = generate_historical_prices(issuer_id, start_date, end_date, base_price, volatility)
        
        # Insert price data
        for date, price in zip(dates, prices):
            db.execute(
                text("""
                    INSERT INTO price (issuer_id, ts, open, high, low, close, volume, adj_close)
                    VALUES (:issuer_id, :ts, :open, :high, :low, :close, :volume, :adj_close)
                    ON CONFLICT (id, ts) DO NOTHING
                """),
                {
                    "issuer_id": issuer_id,
                    "ts": date,
                    "open": price * (1 + np.random.normal(0, 0.01)),
                    "high": price * (1 + abs(np.random.normal(0, 0.02))),
                    "low": price * (1 - abs(np.random.normal(0, 0.02))),
                    "close": price,
                    "volume": int(np.random.uniform(1000000, 10000000)),
                    "adj_close": price
                }
            )
        
        print(f"  Added price data for {ticker}: {len(prices)} days")
    
    db.commit()

def seed_feature_data(db):
    """Seed feature data for all issuers"""
    print("Seeding feature data...")
    
    issuers = db.execute(text("SELECT id, ticker, sector FROM issuer")).fetchall()
    
    # Feature ranges by sector
    feature_ranges = {
        "Technology": {
            "icr": (5.0, 25.0),
            "debt_to_ebitda": (0.5, 3.0),
            "current_ratio": (1.2, 3.0),
            "rev_yoy": (0.05, 0.25),
            "altman_z": (2.5, 4.5)
        },
        "Financial Services": {
            "icr": (2.0, 8.0),
            "debt_to_ebitda": (2.0, 8.0),
            "current_ratio": (0.8, 1.5),
            "rev_yoy": (0.02, 0.15),
            "altman_z": (1.8, 3.2)
        },
        "Energy": {
            "icr": (3.0, 12.0),
            "debt_to_ebitda": (1.5, 6.0),
            "current_ratio": (1.0, 2.0),
            "rev_yoy": (-0.10, 0.20),
            "altman_z": (2.0, 3.8)
        },
        "Healthcare": {
            "icr": (4.0, 15.0),
            "debt_to_ebitda": (1.0, 4.0),
            "current_ratio": (1.1, 2.5),
            "rev_yoy": (0.03, 0.18),
            "altman_z": (2.2, 4.0)
        },
        "Consumer Staples": {
            "icr": (6.0, 20.0),
            "debt_to_ebitda": (0.8, 3.5),
            "current_ratio": (1.0, 2.2),
            "rev_yoy": (0.01, 0.12),
            "altman_z": (2.5, 4.2)
        },
        "Consumer Discretionary": {
            "icr": (3.0, 12.0),
            "debt_to_ebitda": (1.2, 5.0),
            "current_ratio": (1.1, 2.8),
            "rev_yoy": (0.02, 0.20),
            "altman_z": (2.0, 3.5)
        }
    }
    
    # Generate features for the last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    for issuer_id, ticker, sector in issuers:
        ranges = feature_ranges.get(sector, feature_ranges["Technology"])
        
        current_date = start_date
        while current_date <= end_date:
            # Generate features with some trend
            features = {}
            for feature_name, (min_val, max_val) in ranges.items():
                # Add some trend over time
                trend_factor = (current_date - start_date).days / 30.0
                base_value = min_val + (max_val - min_val) * 0.5
                trend = np.sin(trend_factor * np.pi) * 0.2  # Oscillating trend
                
                value = base_value + trend * (max_val - min_val) + np.random.normal(0, (max_val - min_val) * 0.1)
                value = np.clip(value, min_val, max_val)
                features[feature_name] = value
            
            # Add market features
            features["vol_30d"] = np.random.uniform(0.15, 0.35)
            features["max_drawdown_30d"] = np.random.uniform(0.05, 0.25)
            features["beta_180d"] = np.random.uniform(0.8, 1.4)
            features["avg_daily_volume"] = np.random.uniform(5000000, 50000000)
            
            # Insert features
            for feature_name, value in features.items():
                db.execute(
                    text("""
                        INSERT INTO feature_snapshot (issuer_id, ts, feature_name, value, source)
                        VALUES (:issuer_id, :ts, :feature_name, :value, 'demo')
                        ON CONFLICT (id, ts) DO UPDATE SET
                        value = EXCLUDED.value, source = EXCLUDED.source
                    """),
                    {
                        "issuer_id": issuer_id,
                        "ts": current_date,
                        "feature_name": feature_name,
                        "value": float(value)
                    }
                )
            
            current_date += timedelta(days=1)
        
        print(f"  Added feature data for {ticker}: 30 days")
    
    db.commit()

def seed_macro_data(db):
    """Seed macroeconomic data"""
    print("Seeding macro data...")
    
    # Generate macro data for the last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    macro_indicators = {
        "cpi_yoy": (2.5, 4.0),
        "pmi": (48.0, 52.0),
        "policy_rate": (5.0, 5.5),
        "gdp_growth": (1.5, 3.0)
    }
    
    current_date = start_date
    while current_date <= end_date:
        for indicator, (min_val, max_val) in macro_indicators.items():
            value = np.random.uniform(min_val, max_val)
            
            db.execute(
                text("""
                    INSERT INTO macro (ts, key, value, source)
                    VALUES (:ts, :key, :value, 'demo')
                    ON CONFLICT (id, ts) DO UPDATE SET
                    value = EXCLUDED.value, source = EXCLUDED.source
                """),
                {
                    "ts": current_date,
                    "key": indicator,
                    "value": float(value)
                }
            )
        
        current_date += timedelta(days=1)
    
    print("  Added macro data: 30 days")
    db.commit()

def seed_sample_events(db):
    """Seed sample events"""
    print("Seeding sample events...")
    
    issuers = db.execute(text("SELECT id, name, ticker FROM issuer")).fetchall()
    
    # Sample events
    sample_events = [
        {
            "type": "earnings_beat",
            "headline": "Company reports strong quarterly earnings, beats analyst expectations",
            "sentiment": 0.6,
            "weight": 2.0
        },
        {
            "type": "guidance_cut",
            "headline": "Company lowers full-year guidance due to economic uncertainty",
            "sentiment": -0.4,
            "weight": -3.0
        },
        {
            "type": "acquisition",
            "headline": "Company announces strategic acquisition to expand market presence",
            "sentiment": 0.3,
            "weight": 1.0
        },
        {
            "type": "management_change",
            "headline": "CEO announces retirement, successor named",
            "sentiment": -0.1,
            "weight": -2.0
        },
        {
            "type": "restructuring",
            "headline": "Company announces debt restructuring plan to improve financial position",
            "sentiment": -0.5,
            "weight": -4.0
        }
    ]
    
    # Add events for each issuer over the last 7 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    for issuer_id, name, ticker in issuers:
        # Add 1-3 random events per issuer
        num_events = np.random.randint(1, 4)
        
        for i in range(num_events):
            event = random.choice(sample_events)
            event_date = start_date + timedelta(
                days=np.random.randint(0, 7),
                hours=np.random.randint(0, 24)
            )
            
            # Customize headline
            headline = event["headline"].replace("Company", name)
            
            db.execute(
                text("""
                    INSERT INTO event (issuer_id, ts, type, sentiment, weight, headline, url, raw_hash, source)
                    VALUES (:issuer_id, :ts, :type, :sentiment, :weight, :headline, :url, :hash, :source)
                    ON CONFLICT (id, ts) DO NOTHING
                """),
                {
                    "issuer_id": issuer_id,
                    "ts": event_date,
                    "type": event["type"],
                    "sentiment": event["sentiment"],
                    "weight": event["weight"],
                    "headline": headline,
                    "url": f"https://example.com/news/{ticker.lower()}-{i}",
                    "hash": f"demo_event_{issuer_id}_{i}_{event_date.strftime('%Y%m%d')}",
                    "source": "demo"
                }
            )
        
        print(f"  Added {num_events} events for {ticker}")
    
    db.commit()

def seed_initial_scores(db):
    """Seed initial credit scores"""
    print("Seeding initial credit scores...")
    
    issuers = db.execute(text("SELECT id, ticker, sector FROM issuer")).fetchall()
    
    # Base scores by sector
    sector_base_scores = {
        "Technology": 75.0,
        "Financial Services": 65.0,
        "Energy": 60.0,
        "Healthcare": 70.0,
        "Consumer Staples": 80.0,
        "Consumer Discretionary": 68.0
    }
    
    for issuer_id, ticker, sector in issuers:
        base_score = sector_base_scores.get(sector, 70.0)
        
        # Add some variation
        score = base_score + np.random.normal(0, 10.0)
        score = np.clip(score, 30.0, 95.0)
        
        # Determine bucket
        if score >= 90:
            bucket = "AAA"
        elif score >= 80:
            bucket = "AA"
        elif score >= 70:
            bucket = "BBB"
        elif score >= 60:
            bucket = "BB"
        elif score >= 50:
            bucket = "B"
        elif score >= 30:
            bucket = "CCC"
        else:
            bucket = "CC"
        
        # Generate explanation
        explanation = {
            "top_features": [
                {"name": "icr", "impact": np.random.uniform(-5, 5)},
                {"name": "debt_to_ebitda", "impact": np.random.uniform(-3, 3)},
                {"name": "vol_30d", "impact": np.random.uniform(-2, 2)}
            ],
            "events": [],
            "summary": f"Initial score for {ticker} based on fundamental analysis."
        }
        
        db.execute(
            text("""
                INSERT INTO score (issuer_id, ts, score, bucket, base, market, event_delta, macro_adj, model_version, explanation)
                VALUES (:issuer_id, :ts, :score, :bucket, :base, :market, :event_delta, :macro_adj, :model_version, :explanation)
            """),
            {
                "issuer_id": issuer_id,
                "ts": datetime.now(),
                "score": float(score),
                "bucket": bucket,
                "base": float(score * 0.6),
                "market": float(score * 0.2),
                "event_delta": float(score * 0.1),
                "macro_adj": float(score * 0.1),
                "model_version": "v1.0",
                "explanation": json.dumps(explanation)
            }
        )
        
        print(f"  Added initial score for {ticker}: {score:.1f} ({bucket})")
    
    db.commit()

def main():
    """Main seeding function"""
    print("Starting demo data seeding...")
    
    try:
        db = get_db_session()
        
        # Seed data in order
        seed_issuers(db)
        seed_price_data(db)
        seed_feature_data(db)
        seed_macro_data(db)
        seed_sample_events(db)
        seed_initial_scores(db)
        
        print("\nDemo data seeding completed successfully!")
        print(f"Added {len(SAMPLE_ISSUERS)} issuers with historical data")
        
    except Exception as e:
        print(f"Error seeding demo data: {e}")
        if 'db' in locals():
            db.rollback()
        sys.exit(1)
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    main()
