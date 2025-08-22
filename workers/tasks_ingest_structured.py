import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import structlog
from celery import current_task
import os
from dotenv import load_dotenv

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

@celery_app.task(bind=True, name="ingest_yahoo_finance")
def ingest_yahoo_finance(self, ticker: str):
    """
    Ingest Yahoo Finance data for a specific ticker.
    """
    try:
        logger.info("Starting Yahoo Finance ingestion", ticker=ticker)
        
        # Get database session
        db = get_db_session()
        
        # Get issuer ID
        issuer = db.execute(text("SELECT id FROM issuer WHERE ticker = :ticker"), {"ticker": ticker}).fetchone()
        if not issuer:
            logger.error("Issuer not found", ticker=ticker)
            return {"status": "error", "message": "Issuer not found"}
        
        issuer_id = issuer[0]
        
        # Get latest price data from database
        latest_price = db.execute(
            text("SELECT ts FROM price WHERE issuer_id = :issuer_id ORDER BY ts DESC LIMIT 1"),
            {"issuer_id": issuer_id}
        ).fetchone()
        
        # Download data from Yahoo Finance
        stock = yf.Ticker(ticker)
        
        # Get historical data (last 365 days if no existing data, otherwise from last price)
        if latest_price:
            start_date = latest_price[0] + timedelta(days=1)
        else:
            start_date = datetime.now() - timedelta(days=365)
        
        end_date = datetime.now()
        
        # Download data
        data = stock.history(start=start_date, end=end_date, interval="1d")
        
        if data.empty:
            logger.warning("No new data available", ticker=ticker)
            return {"status": "success", "message": "No new data available"}
        
        # Insert price data
        for date, row in data.iterrows():
            db.execute(
                text("""
                    INSERT INTO price (issuer_id, ts, open, high, low, close, volume, adj_close)
                    VALUES (:issuer_id, :ts, :open, :high, :low, :close, :volume, :adj_close)
                    ON CONFLICT (issuer_id, ts) DO NOTHING
                """),
                {
                    "issuer_id": issuer_id,
                    "ts": date,
                    "open": float(row['Open']),
                    "high": float(row['High']),
                    "low": float(row['Low']),
                    "close": float(row['Close']),
                    "volume": int(row['Volume']),
                    "adj_close": float(row['Close'])  # Using Close as Adj Close for simplicity
                }
            )
        
        # Calculate and store market features
        calculate_market_features(issuer_id, db)
        
        db.commit()
        db.close()
        
        logger.info("Yahoo Finance ingestion completed", ticker=ticker, records=len(data))
        return {"status": "success", "records": len(data)}
        
    except Exception as e:
        logger.error("Yahoo Finance ingestion failed", error=str(e), ticker=ticker)
        if 'db' in locals():
            db.rollback()
            db.close()
        raise

def calculate_market_features(issuer_id: int, db):
    """Calculate market features from price data"""
    try:
        # Get price data for calculations
        prices = db.execute(
            text("""
                SELECT ts, close, volume 
                FROM price 
                WHERE issuer_id = :issuer_id 
                ORDER BY ts DESC 
                LIMIT 252
            """),
            {"issuer_id": issuer_id}
        ).fetchall()
        
        if len(prices) < 30:
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(prices, columns=['ts', 'close', 'volume'])
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        
        # Calculate returns
        df['returns'] = df['close'].pct_change()
        
        # Calculate features
        features = {}
        
        # 30-day volatility
        if len(df) >= 30:
            vol_30d = df['returns'].tail(30).std() * np.sqrt(252)
            features['vol_30d'] = vol_30d
        
        # 90-day volatility
        if len(df) >= 90:
            vol_90d = df['returns'].tail(90).std() * np.sqrt(252)
            features['vol_90d'] = vol_90d
        
        # Max drawdown (30 days)
        if len(df) >= 30:
            rolling_max = df['close'].tail(30).expanding().max()
            drawdown = (df['close'].tail(30) - rolling_max) / rolling_max
            max_drawdown = drawdown.min()
            features['max_drawdown_30d'] = abs(max_drawdown)
        
        # Beta (180 days, simplified - would need market data for proper calculation)
        if len(df) >= 180:
            # Simplified beta calculation
            returns_180d = df['returns'].tail(180)
            beta = returns_180d.std() * np.sqrt(252)
            features['beta_180d'] = beta
        
        # Liquidity (average daily volume)
        if len(df) >= 30:
            avg_volume = df['volume'].tail(30).mean()
            features['avg_daily_volume'] = avg_volume
        
        # Store features
        current_time = datetime.now()
        for feature_name, value in features.items():
            db.execute(
                text("""
                    INSERT INTO feature_snapshot (issuer_id, ts, feature_name, value, source)
                    VALUES (:issuer_id, :ts, :feature_name, :value, 'yfinance')
                    ON CONFLICT (issuer_id, ts, feature_name) DO UPDATE SET
                    value = EXCLUDED.value, source = EXCLUDED.source
                """),
                {
                    "issuer_id": issuer_id,
                    "ts": current_time,
                    "feature_name": feature_name,
                    "value": float(value)
                }
            )
        
    except Exception as e:
        logger.error("Failed to calculate market features", error=str(e), issuer_id=issuer_id)
        raise

@celery_app.task(bind=True, name="ingest_all_yahoo_finance")
def ingest_all_yahoo_finance(self):
    """
    Ingest Yahoo Finance data for all tracked issuers.
    """
    try:
        logger.info("Starting Yahoo Finance ingestion for all issuers")
        
        db = get_db_session()
        
        # Get all issuers with tickers
        issuers = db.execute(
            text("SELECT id, ticker FROM issuer WHERE ticker IS NOT NULL")
        ).fetchall()
        
        results = []
        for issuer in issuers:
            try:
                result = ingest_yahoo_finance.delay(issuer[1])
                results.append({"issuer_id": issuer[0], "ticker": issuer[1], "task_id": result.id})
            except Exception as e:
                logger.error("Failed to queue Yahoo Finance task", error=str(e), ticker=issuer[1])
        
        db.close()
        
        logger.info("Queued Yahoo Finance ingestion tasks", count=len(results))
        return {"status": "success", "tasks_queued": len(results), "results": results}
        
    except Exception as e:
        logger.error("Failed to queue Yahoo Finance ingestion", error=str(e))
        raise

@celery_app.task(bind=True, name="ingest_edgar_filings")
def ingest_edgar_filings(self, ticker: str):
    """
    Ingest SEC EDGAR filings for a specific ticker.
    Note: This is a simplified implementation. In production, you'd use a proper EDGAR API.
    """
    try:
        logger.info("Starting EDGAR filings ingestion", ticker=ticker)
        
        # This is a placeholder implementation
        # In a real implementation, you would:
        # 1. Use SEC EDGAR API or XBRL parser
        # 2. Download latest filings
        # 3. Extract financial ratios
        # 4. Store in feature_snapshot table
        
        logger.info("EDGAR filings ingestion completed (placeholder)", ticker=ticker)
        return {"status": "success", "message": "Placeholder implementation"}
        
    except Exception as e:
        logger.error("EDGAR filings ingestion failed", error=str(e), ticker=ticker)
        raise

@celery_app.task(bind=True, name="ingest_macro_data")
def ingest_macro_data(self):
    """
    Ingest macroeconomic data from FRED/World Bank.
    """
    try:
        logger.info("Starting macro data ingestion")
        
        # This is a placeholder implementation
        # In a real implementation, you would:
        # 1. Use FRED API to get CPI, PMI, policy rates
        # 2. Use World Bank API for GDP growth
        # 3. Store in macro table
        
        # Example macro indicators
        macro_indicators = {
            "cpi_yoy": 3.2,  # Placeholder
            "pmi": 50.1,     # Placeholder
            "policy_rate": 5.25,  # Placeholder
            "gdp_growth": 2.1  # Placeholder
        }
        
        db = get_db_session()
        current_time = datetime.now()
        
        for key, value in macro_indicators.items():
            db.execute(
                text("""
                    INSERT INTO macro (ts, key, value, source)
                    VALUES (:ts, :key, :value, 'fred')
                    ON CONFLICT (ts, key) DO UPDATE SET
                    value = EXCLUDED.value, source = EXCLUDED.source
                """),
                {
                    "ts": current_time,
                    "key": key,
                    "value": float(value)
                }
            )
        
        db.commit()
        db.close()
        
        logger.info("Macro data ingestion completed")
        return {"status": "success", "indicators": len(macro_indicators)}
        
    except Exception as e:
        logger.error("Macro data ingestion failed", error=str(e))
        if 'db' in locals():
            db.rollback()
            db.close()
        raise

@celery_app.task(bind=True, name="schedule_structured_ingestion")
def schedule_structured_ingestion(self):
    """
    Schedule all structured data ingestion tasks.
    """
    try:
        logger.info("Scheduling structured data ingestion")
        
        # Schedule Yahoo Finance ingestion
        ingest_all_yahoo_finance.delay()
        
        # Schedule macro data ingestion
        ingest_macro_data.delay()
        
        logger.info("Structured data ingestion scheduled")
        return {"status": "success", "message": "Tasks scheduled"}
        
    except Exception as e:
        logger.error("Failed to schedule structured ingestion", error=str(e))
        raise





