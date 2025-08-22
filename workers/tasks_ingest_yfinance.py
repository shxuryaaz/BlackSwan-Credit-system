import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import time
import os

logger = structlog.get_logger()

# Database setup
DATABASE_URL = "postgresql://credtech:credtech_pass@postgres:5432/credtech"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class YFinanceIngestion:
    """Real-time financial data ingestion using yfinance"""
    
    def __init__(self):
        self.session = SessionLocal()
    
    def get_stock_data(self, ticker: str, period: str = "1y") -> Optional[Dict]:
        """Get comprehensive stock data from Yahoo Finance"""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                stock = yf.Ticker(ticker)
                
                # Get basic info with retry
                info = {}
                try:
                    info = stock.info
                except Exception as e:
                    logger.warning(f"Could not fetch info for {ticker}: {e}")
                
                # Get historical data
                hist = stock.history(period=period)
                
                # Get financial statements (optional)
                balance_sheet = None
                income_stmt = None
                cash_flow = None
                
                try:
                    balance_sheet = stock.balance_sheet
                except:
                    pass
                
                try:
                    income_stmt = stock.income_stmt
                except:
                    pass
                
                try:
                    cash_flow = stock.cashflow
                except:
                    pass
                
                return {
                    "ticker": ticker,
                    "info": info,
                    "history": hist.to_dict('records') if not hist.empty else [],
                    "balance_sheet": balance_sheet.to_dict('records') if balance_sheet is not None and not balance_sheet.empty else [],
                    "income_stmt": income_stmt.to_dict('records') if income_stmt is not None and not income_stmt.empty else [],
                    "cash_flow": cash_flow.to_dict('records') if cash_flow is not None and not cash_flow.empty else []
                }
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {ticker}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"All attempts failed for {ticker}")
                    return None
        
        return None
    
    def calculate_financial_ratios(self, stock_data: Dict) -> Dict[str, float]:
        """Calculate key financial ratios for credit scoring"""
        ratios = {}
        
        try:
            info = stock_data.get("info", {})
            balance_sheet = stock_data.get("balance_sheet", [])
            income_stmt = stock_data.get("income_stmt", [])
            
            # Market-based ratios
            ratios["market_cap"] = info.get("marketCap", 0)
            ratios["enterprise_value"] = info.get("enterpriseValue", 0)
            ratios["pe_ratio"] = info.get("trailingPE", 0)
            ratios["pb_ratio"] = info.get("priceToBook", 0)
            ratios["debt_to_equity"] = info.get("debtToEquity", 0)
            
            # Financial ratios (if available)
            if balance_sheet and income_stmt:
                latest_bs = balance_sheet[0] if balance_sheet else {}
                latest_is = income_stmt[0] if income_stmt else {}
                
                # Current Ratio
                current_assets = latest_bs.get("Total Current Assets", 0)
                current_liabilities = latest_bs.get("Total Current Liabilities", 0)
                ratios["current_ratio"] = current_assets / current_liabilities if current_liabilities > 0 else 0
                
                # Debt/EBITDA
                total_debt = latest_bs.get("Total Debt", 0)
                ebitda = latest_is.get("EBITDA", 0)
                ratios["debt_to_ebitda"] = total_debt / ebitda if ebitda > 0 else 0
                
                # Interest Coverage Ratio
                ebit = latest_is.get("EBIT", 0)
                interest_expense = latest_is.get("Interest Expense", 0)
                ratios["interest_coverage"] = ebit / interest_expense if interest_expense > 0 else 0
                
                # Revenue Growth
                if len(income_stmt) > 1:
                    current_revenue = latest_is.get("Total Revenue", 0)
                    prev_revenue = income_stmt[1].get("Total Revenue", 0)
                    ratios["revenue_growth"] = ((current_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
                
                # Altman Z-Score components
                working_capital = current_assets - current_liabilities
                total_assets = latest_bs.get("Total Assets", 1)
                retained_earnings = latest_bs.get("Retained Earnings", 0)
                net_income = latest_is.get("Net Income", 0)
                
                ratios["working_capital_to_assets"] = working_capital / total_assets if total_assets > 0 else 0
                ratios["retained_earnings_to_assets"] = retained_earnings / total_assets if total_assets > 0 else 0
                ratios["ebit_to_assets"] = ebit / total_assets if total_assets > 0 else 0
                ratios["book_value_to_liabilities"] = info.get("bookValue", 0) / latest_bs.get("Total Liabilities", 1) if latest_bs.get("Total Liabilities", 0) > 0 else 0
                
                # Altman Z-Score
                z_score = (1.2 * ratios["working_capital_to_assets"] + 
                          1.4 * ratios["retained_earnings_to_assets"] + 
                          3.3 * ratios["ebit_to_assets"] + 
                          0.6 * ratios["book_value_to_liabilities"] + 
                          1.0 * (current_revenue / total_assets if total_assets > 0 else 0))
                ratios["altman_z_score"] = z_score
            
            # Price-based metrics
            if stock_data.get("history"):
                hist_data = stock_data["history"]
                if hist_data:
                    latest_price = hist_data[0].get("Close", 0)
                    ratios["current_price"] = latest_price
                    
                    # Volatility (30-day)
                    if len(hist_data) >= 30:
                        prices_30d = [d.get("Close", 0) for d in hist_data[:30]]
                        returns = pd.Series(prices_30d).pct_change().dropna()
                        ratios["volatility_30d"] = returns.std() * (252 ** 0.5)  # Annualized
            
        except Exception as e:
            logger.error(f"Error calculating ratios: {e}")
        
        return ratios
    
    def store_financial_data(self, issuer_id: int, ratios: Dict[str, float], stock_data: Dict):
        """Store financial data in the database"""
        try:
            # Store in feature_snapshot table
            for feature_name, value in ratios.items():
                if value is not None and not pd.isna(value):
                    self.session.execute(
                        text("""
                            INSERT INTO feature_snapshot (issuer_id, ts, feature_name, value, source)
                            VALUES (:issuer_id, :ts, :feature_name, :value, :source)
                        """),
                        {
                            "issuer_id": issuer_id,
                            "ts": datetime.utcnow(),
                            "feature_name": feature_name,
                            "value": float(value),
                            "source": "yfinance"
                        }
                    )
            
            # Store price data
            if stock_data.get("history"):
                latest_data = stock_data["history"][0]
                self.session.execute(
                    text("""
                        INSERT INTO price (issuer_id, ts, open, high, low, close, volume, source)
                        VALUES (:issuer_id, :ts, :open, :high, :low, :close, :volume, :source)
                    """),
                    {
                        "issuer_id": issuer_id,
                        "ts": datetime.utcnow(),
                        "open": float(latest_data.get("Open", 0)),
                        "high": float(latest_data.get("High", 0)),
                        "low": float(latest_data.get("Low", 0)),
                        "close": float(latest_data.get("Close", 0)),
                        "volume": int(latest_data.get("Volume", 0)),
                        "source": "yfinance"
                    }
                )
            
            self.session.commit()
            logger.info(f"Stored financial data for issuer {issuer_id}")
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error storing financial data: {e}")
    
    def update_credit_score_with_real_data(self, issuer_id: int, ratios: Dict[str, float]):
        """Update credit score based on real financial data"""
        try:
            # Get current score (optional - we'll create one if it doesn't exist)
            result = self.session.execute(
                text("SELECT score FROM score WHERE issuer_id = :issuer_id ORDER BY ts DESC LIMIT 1"),
                {"issuer_id": issuer_id}
            )
            current_score = result.fetchone()
            
            # Use current score if available, otherwise start with default
            base_score = current_score[0] if current_score else 50.0
            
            # Calculate new base score based on financial ratios
            # Start with the current score or default
            new_base_score = base_score
            
            # Adjust based on key ratios
            if ratios.get("altman_z_score"):
                z_score = ratios["altman_z_score"]
                if z_score > 3.0:
                    new_base_score += 20  # Very safe
                elif z_score > 2.7:
                    new_base_score += 15  # Safe
                elif z_score > 1.8:
                    new_base_score += 10  # Grey zone
                elif z_score > 1.2:
                    new_base_score += 5   # Distress zone
                else:
                    new_base_score -= 10  # High distress
            
            if ratios.get("current_ratio"):
                current_ratio = ratios["current_ratio"]
                if current_ratio > 2.0:
                    new_base_score += 10
                elif current_ratio > 1.5:
                    new_base_score += 5
                elif current_ratio < 1.0:
                    new_base_score -= 10
            
            if ratios.get("debt_to_ebitda"):
                debt_ebitda = ratios["debt_to_ebitda"]
                if debt_ebitda < 2.0:
                    new_base_score += 15
                elif debt_ebitda < 4.0:
                    new_base_score += 5
                elif debt_ebitda > 6.0:
                    new_base_score -= 15
            
            if ratios.get("interest_coverage"):
                icr = ratios["interest_coverage"]
                if icr > 5.0:
                    new_base_score += 10
                elif icr > 2.0:
                    new_base_score += 5
                elif icr < 1.0:
                    new_base_score -= 15
            
            # If we have no meaningful ratios (all zeros), use a default score
            if all(v == 0 for v in ratios.values()):
                new_base_score = 50.0  # Default score when no data available
                logger.info(f"No financial data available for issuer {issuer_id}, using default score")
            
            # Clamp score between 0 and 100
            new_base_score = max(0, min(100, new_base_score))
            
            # Determine bucket
            if new_base_score >= 85: bucket = "AA"
            elif new_base_score >= 75: bucket = "A"
            elif new_base_score >= 65: bucket = "BBB"
            elif new_base_score >= 55: bucket = "BB"
            elif new_base_score >= 45: bucket = "B"
            else: bucket = "CCC"
            
            # Insert new score
            self.session.execute(
                text("""
                    INSERT INTO score (issuer_id, ts, score, bucket, base, market, event_delta, macro_adj, model_version, explanation)
                    VALUES (:issuer_id, :ts, :score, :bucket, :base, :market, :event_delta, :macro_adj, :model_version, :explanation)
                """),
                {
                    "issuer_id": issuer_id,
                    "ts": datetime.utcnow(),
                    "score": new_base_score,
                    "bucket": bucket,
                    "base": new_base_score,
                    "market": 0.0,
                    "event_delta": 0.0,
                    "macro_adj": 0.0,
                    "model_version": "v2.0-real-data",
                    "explanation": f'{{"source": "yfinance", "ratios_analyzed": {list(ratios.keys())}}}'.replace("'", '"')
                }
            )
            
            self.session.commit()
            logger.info(f"Updated credit score for issuer {issuer_id} to {new_base_score:.2f} ({bucket})")
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating credit score: {e}")

def ingest_yfinance_data_for_issuer(issuer_ticker: str, issuer_id: int):
    """Main function to ingest yfinance data for a specific issuer"""
    try:
        logger.info(f"Starting yfinance data ingestion for {issuer_ticker}")
        
        # Add delay to respect rate limits
        time.sleep(3)
        
        ingestion = YFinanceIngestion()
        
        # Get stock data
        stock_data = ingestion.get_stock_data(issuer_ticker)
        logger.info(f"Stock data for {issuer_ticker}: {stock_data}")
        if not stock_data:
            logger.error(f"Failed to get stock data for {issuer_ticker}")
            return False
        
        # Calculate financial ratios
        try:
            ratios = ingestion.calculate_financial_ratios(stock_data)
            logger.info(f"Calculated ratios for {issuer_ticker}: {ratios}")
            if not ratios:
                logger.error(f"Failed to calculate ratios for {issuer_ticker}")
                return False
        except Exception as e:
            logger.error(f"Error calculating ratios: {e}")
            return False
        
        # Store data
        try:
            ingestion.store_financial_data(issuer_id, ratios, stock_data)
        except Exception as e:
            logger.error(f"Error storing data: {e}")
            return False
        
        # Update credit score
        try:
            logger.info(f"Updating credit score for issuer {issuer_id} with ratios: {ratios}")
            ingestion.update_credit_score_with_real_data(issuer_id, ratios)
        except Exception as e:
            logger.error(f"Error updating credit score: {e}")
            return False
        
        logger.info(f"Successfully ingested yfinance data for {issuer_ticker}")
        return True
        
    except Exception as e:
        logger.error(f"Error in yfinance ingestion for {issuer_ticker}: {e}")
        return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        ticker = sys.argv[1]
        issuer_id = int(sys.argv[2])
        ingest_yfinance_data_for_issuer(ticker, issuer_id)
    else:
        print("Usage: python tasks_ingest_yfinance.py <TICKER> <ISSUER_ID>")
