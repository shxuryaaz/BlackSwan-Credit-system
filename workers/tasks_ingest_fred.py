import requests
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import structlog

logger = structlog.get_logger()

# Database setup
DATABASE_URL = "postgresql://credtech:credtech_pass@postgres:5432/credtech"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class FREDIngestion:
    """FRED (Federal Reserve Economic Data) ingestion for macroeconomic indicators"""
    
    def __init__(self, api_key: str = None):
        self.base_url = "https://api.stlouisfed.org/fred"
        self.api_key = api_key or os.getenv("FRED_API_KEY", "demo")
        self.headers = {
            'Accept': 'application/json'
        }
    
    def get_series_data(self, series_id: str, limit: int = 10) -> Optional[List[Dict]]:
        """Get time series data from FRED"""
        try:
            url = f"{self.base_url}/series/observations"
            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json',
                'limit': limit,
                'sort_order': 'desc'
            }
            
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            return data.get('observations', [])
            
        except Exception as e:
            logger.error("Failed to fetch FRED series", error=str(e), series_id=series_id)
            return None
    
    def get_multiple_series(self, series_ids: List[str]) -> Dict[str, List[Dict]]:
        """Get multiple FRED series"""
        results = {}
        
        for series_id in series_ids:
            data = self.get_series_data(series_id)
            if data:
                results[series_id] = data
            time.sleep(0.1)  # Rate limiting
        
        return results
    
    def extract_macro_indicators(self) -> Dict[str, float]:
        """Extract key macroeconomic indicators"""
        indicators = {}
        
        # Key FRED series for credit analysis
        series_mapping = {
            'GDP': 'GDP',  # Real GDP
            'UNRATE': 'UNRATE',  # Unemployment Rate
            'CPIAUCSL': 'CPIAUCSL',  # Consumer Price Index
            'FEDFUNDS': 'FEDFUNDS',  # Federal Funds Rate
            'DGS10': 'DGS10',  # 10-Year Treasury Rate
            'DGS2': 'DGS2',  # 2-Year Treasury Rate
            'VIXCLS': 'VIXCLS',  # VIX Volatility Index
            'DEXUSEU': 'DEXUSEU',  # US/Euro Exchange Rate
            'DCOILWTICO': 'DCOILWTICO',  # WTI Crude Oil Price
            'DEXCHUS': 'DEXCHUS'  # China/US Exchange Rate
        }
        
        try:
            # Get data for all series
            series_data = self.get_multiple_series(list(series_mapping.values()))
            
            for indicator_name, series_id in series_mapping.items():
                if series_id in series_data and series_data[series_id]:
                    # Get latest value
                    latest_observation = series_data[series_id][0]
                    value_str = latest_observation.get('value', '0')
                    
                    # Handle missing values
                    if value_str != '.':
                        try:
                            value = float(value_str)
                            indicators[indicator_name.lower()] = value
                        except ValueError:
                            logger.warning("Invalid value for indicator", indicator=indicator_name, value=value_str)
            
        except Exception as e:
            logger.error("Failed to extract macro indicators", error=str(e))
        
        return indicators
    
    def calculate_credit_impact_scores(self, indicators: Dict[str, float]) -> Dict[str, float]:
        """Calculate credit impact scores from macro indicators"""
        impact_scores = {}
        
        try:
            # GDP Growth Impact (positive for credit)
            if 'gdp' in indicators:
                # Normalize GDP growth (assume 2-3% is neutral)
                gdp_growth = indicators['gdp']
                impact_scores['gdp_impact'] = min(max((gdp_growth - 2.5) / 2.5, -1), 1)
            
            # Unemployment Impact (negative for credit)
            if 'unrate' in indicators:
                unemployment = indicators['unrate']
                # Normalize unemployment (assume 4-5% is neutral)
                impact_scores['unemployment_impact'] = min(max((4.5 - unemployment) / 2.5, -1), 1)
            
            # Inflation Impact (negative for credit)
            if 'cpiaucsl' in indicators:
                inflation = indicators['cpiaucsl']
                # Normalize inflation (assume 2-3% is neutral)
                impact_scores['inflation_impact'] = min(max((2.5 - inflation) / 2.5, -1), 1)
            
            # Interest Rate Impact (negative for credit)
            if 'fedfunds' in indicators:
                fed_rate = indicators['fedfunds']
                # Normalize Fed rate (assume 2-3% is neutral)
                impact_scores['interest_rate_impact'] = min(max((2.5 - fed_rate) / 2.5, -1), 1)
            
            # Yield Curve Impact (negative for credit when inverted)
            if 'dgs10' in indicators and 'dgs2' in indicators:
                yield_spread = indicators['dgs10'] - indicators['dgs2']
                # Normalize yield spread (positive is good, negative is bad)
                impact_scores['yield_curve_impact'] = min(max(yield_spread / 2, -1), 1)
            
            # Market Volatility Impact (negative for credit)
            if 'vixcls' in indicators:
                vix = indicators['vixcls']
                # Normalize VIX (assume 15-20 is neutral)
                impact_scores['volatility_impact'] = min(max((17.5 - vix) / 10, -1), 1)
            
            # Oil Price Impact (mixed - good for energy, bad for others)
            if 'dcoilwtico' in indicators:
                oil_price = indicators['dcoilwtico']
                # Normalize oil price (assume $60-80 is neutral)
                impact_scores['oil_price_impact'] = min(max((70 - oil_price) / 20, -1), 1)
            
        except Exception as e:
            logger.error("Failed to calculate credit impact scores", error=str(e))
        
        return impact_scores
    
    def store_macro_data(self, indicators: Dict[str, float], impact_scores: Dict[str, float]):
        """Store macroeconomic data in database"""
        try:
            with SessionLocal() as session:
                current_time = datetime.utcnow()
                
                # Store raw indicators
                for indicator_name, value in indicators.items():
                    session.execute(
                        text("""
                            INSERT INTO macro (ts, key, value, source)
                            VALUES (:ts, :key, :value, :source)
                            ON CONFLICT (ts, key) DO UPDATE SET
                            value = EXCLUDED.value,
                            source = EXCLUDED.source
                        """),
                        {
                            "ts": current_time,
                            "key": indicator_name,
                            "value": value,
                            "source": "fred"
                        }
                    )
                
                # Store impact scores
                for impact_name, score in impact_scores.items():
                    session.execute(
                        text("""
                            INSERT INTO macro (ts, key, value, source)
                            VALUES (:ts, :key, :value, :source)
                            ON CONFLICT (ts, key) DO UPDATE SET
                            value = EXCLUDED.value,
                            source = EXCLUDED.source
                        """),
                        {
                            "ts": current_time,
                            "key": f"impact_{impact_name}",
                            "value": score,
                            "source": "fred_calculated"
                        }
                    )
                
                session.commit()
                logger.info("Stored macro data", indicators=len(indicators), impacts=len(impact_scores))
                
        except Exception as e:
            logger.error("Failed to store macro data", error=str(e))

def ingest_fred_data():
    """Main function to ingest FRED macroeconomic data"""
    try:
        # Initialize FRED ingestion
        fred = FREDIngestion()
        
        # Extract macro indicators
        indicators = fred.extract_macro_indicators()
        if not indicators:
            logger.warning("No macro indicators extracted")
            return
        
        # Calculate credit impact scores
        impact_scores = fred.calculate_credit_impact_scores(indicators)
        
        # Store in database
        fred.store_macro_data(indicators, impact_scores)
        
        logger.info("Successfully ingested FRED data", indicators=len(indicators), impacts=len(impact_scores))
        
    except Exception as e:
        logger.error("Failed to ingest FRED data", error=str(e))

if __name__ == "__main__":
    ingest_fred_data()
