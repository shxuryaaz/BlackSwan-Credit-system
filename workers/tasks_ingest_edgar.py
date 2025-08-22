import requests
import time
import hashlib
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

class EDGARIngestion:
    """SEC EDGAR data ingestion for financial filings"""
    
    def __init__(self):
        self.base_url = "https://data.sec.gov"
        self.headers = {
            'User-Agent': 'BlackSwan Credit Intelligence Platform (your-email@domain.com)',
            'Accept': 'application/json'
        }
    
    def get_company_facts(self, cik: str) -> Optional[Dict]:
        """Get company facts from SEC EDGAR"""
        try:
            # Pad CIK to 10 digits
            cik_padded = cik.zfill(10)
            url = f"{self.base_url}/api/xbrl/companyfacts/CIK{cik_padded}.json"
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error("Failed to fetch company facts", error=str(e), cik=cik)
            return None
    
    def extract_financial_ratios(self, facts_data: Dict) -> Dict[str, float]:
        """Extract key financial ratios from SEC data"""
        ratios = {}
        
        try:
            # Extract from concepts
            concepts = facts_data.get('facts', {})
            
            # Interest Coverage Ratio (ICR)
            icr_data = concepts.get('us-gaap:InterestExpense', {}).get('units', {}).get('USD', [])
            if icr_data:
                # Calculate ICR = EBIT / Interest Expense
                latest_icr = self._calculate_icr(concepts)
                if latest_icr:
                    ratios['icr'] = latest_icr
            
            # Debt to EBITDA
            debt_ebitda = self._calculate_debt_to_ebitda(concepts)
            if debt_ebitda:
                ratios['debt_to_ebitda'] = debt_ebitda
            
            # Current Ratio
            current_ratio = self._calculate_current_ratio(concepts)
            if current_ratio:
                ratios['current_ratio'] = current_ratio
            
            # Revenue Growth
            revenue_growth = self._calculate_revenue_growth(concepts)
            if revenue_growth:
                ratios['revenue_growth'] = revenue_growth
            
            # Altman Z-Score components
            altman_z = self._calculate_altman_z_score(concepts)
            if altman_z:
                ratios['altman_z'] = altman_z
            
        except Exception as e:
            logger.error("Failed to extract financial ratios", error=str(e))
        
        return ratios
    
    def _calculate_icr(self, concepts: Dict) -> Optional[float]:
        """Calculate Interest Coverage Ratio"""
        try:
            # Get EBIT (Earnings Before Interest and Taxes)
            ebit_data = concepts.get('us-gaap:EarningsBeforeInterestAndTaxes', {}).get('units', {}).get('USD', [])
            interest_data = concepts.get('us-gaap:InterestExpense', {}).get('units', {}).get('USD', [])
            
            if ebit_data and interest_data:
                # Get latest values
                latest_ebit = max(ebit_data, key=lambda x: x.get('end', ''))
                latest_interest = max(interest_data, key=lambda x: x.get('end', ''))
                
                if latest_interest.get('val', 0) != 0:
                    return latest_ebit.get('val', 0) / latest_interest.get('val', 0)
            
        except Exception as e:
            logger.error("Failed to calculate ICR", error=str(e))
        
        return None
    
    def _calculate_debt_to_ebitda(self, concepts: Dict) -> Optional[float]:
        """Calculate Debt to EBITDA ratio"""
        try:
            # Get Total Debt
            debt_data = concepts.get('us-gaap:LongTermDebt', {}).get('units', {}).get('USD', [])
            ebitda_data = concepts.get('us-gaap:EarningsBeforeInterestTaxesDepreciationAndAmortization', {}).get('units', {}).get('USD', [])
            
            if debt_data and ebitda_data:
                latest_debt = max(debt_data, key=lambda x: x.get('end', ''))
                latest_ebitda = max(ebitda_data, key=lambda x: x.get('end', ''))
                
                if latest_ebitda.get('val', 0) != 0:
                    return latest_debt.get('val', 0) / latest_ebitda.get('val', 0)
            
        except Exception as e:
            logger.error("Failed to calculate Debt/EBITDA", error=str(e))
        
        return None
    
    def _calculate_current_ratio(self, concepts: Dict) -> Optional[float]:
        """Calculate Current Ratio"""
        try:
            current_assets = concepts.get('us-gaap:AssetsCurrent', {}).get('units', {}).get('USD', [])
            current_liabilities = concepts.get('us-gaap:LiabilitiesCurrent', {}).get('units', {}).get('USD', [])
            
            if current_assets and current_liabilities:
                latest_assets = max(current_assets, key=lambda x: x.get('end', ''))
                latest_liabilities = max(current_liabilities, key=lambda x: x.get('end', ''))
                
                if latest_liabilities.get('val', 0) != 0:
                    return latest_assets.get('val', 0) / latest_liabilities.get('val', 0)
            
        except Exception as e:
            logger.error("Failed to calculate Current Ratio", error=str(e))
        
        return None
    
    def _calculate_revenue_growth(self, concepts: Dict) -> Optional[float]:
        """Calculate Revenue Growth (YoY)"""
        try:
            revenue_data = concepts.get('us-gaap:Revenues', {}).get('units', {}).get('USD', [])
            
            if len(revenue_data) >= 2:
                # Sort by end date and get last two periods
                sorted_revenue = sorted(revenue_data, key=lambda x: x.get('end', ''))
                current = sorted_revenue[-1].get('val', 0)
                previous = sorted_revenue[-2].get('val', 0)
                
                if previous != 0:
                    return ((current - previous) / previous) * 100
            
        except Exception as e:
            logger.error("Failed to calculate Revenue Growth", error=str(e))
        
        return None
    
    def _calculate_altman_z_score(self, concepts: Dict) -> Optional[float]:
        """Calculate Altman Z-Score"""
        try:
            # Get required components
            working_capital = concepts.get('us-gaap:WorkingCapital', {}).get('units', {}).get('USD', [])
            total_assets = concepts.get('us-gaap:Assets', {}).get('units', {}).get('USD', [])
            retained_earnings = concepts.get('us-gaap:RetainedEarningsAccumulatedDeficit', {}).get('units', {}).get('USD', [])
            ebit = concepts.get('us-gaap:EarningsBeforeInterestAndTaxes', {}).get('units', {}).get('USD', [])
            total_liabilities = concepts.get('us-gaap:Liabilities', {}).get('units', {}).get('USD', [])
            sales = concepts.get('us-gaap:Revenues', {}).get('units', {}).get('USD', [])
            
            if all([working_capital, total_assets, retained_earnings, ebit, total_liabilities, sales]):
                # Get latest values
                wc = max(working_capital, key=lambda x: x.get('end', '')).get('val', 0)
                ta = max(total_assets, key=lambda x: x.get('end', '')).get('val', 0)
                re = max(retained_earnings, key=lambda x: x.get('end', '')).get('val', 0)
                ebit_val = max(ebit, key=lambda x: x.get('end', '')).get('val', 0)
                tl = max(total_liabilities, key=lambda x: x.get('end', '')).get('val', 0)
                sales_val = max(sales, key=lambda x: x.get('end', '')).get('val', 0)
                
                if ta != 0 and tl != 0 and sales_val != 0:
                    # Altman Z-Score formula
                    z_score = (1.2 * (wc / ta)) + (1.4 * (re / ta)) + (3.3 * (ebit_val / ta)) + (0.6 * (sales_val / tl))
                    return z_score
            
        except Exception as e:
            logger.error("Failed to calculate Altman Z-Score", error=str(e))
        
        return None
    
    def store_financial_data(self, issuer_id: int, ratios: Dict[str, float]):
        """Store financial ratios in database"""
        try:
            with SessionLocal() as session:
                current_time = datetime.utcnow()
                
                for ratio_name, value in ratios.items():
                    # Store in feature_snapshot table
                    session.execute(
                        text("""
                            INSERT INTO feature_snapshot (issuer_id, ts, feature_name, value, source)
                            VALUES (:issuer_id, :ts, :feature_name, :value, :source)
                            ON CONFLICT (issuer_id, ts, feature_name) DO UPDATE SET
                            value = EXCLUDED.value,
                            source = EXCLUDED.source
                        """),
                        {
                            "issuer_id": issuer_id,
                            "ts": current_time,
                            "feature_name": ratio_name,
                            "value": value,
                            "source": "sec_edgar"
                        }
                    )
                
                session.commit()
                logger.info("Stored financial ratios", issuer_id=issuer_id, ratios=list(ratios.keys()))
                
        except Exception as e:
            logger.error("Failed to store financial data", error=str(e), issuer_id=issuer_id)

def ingest_edgar_data_for_issuer(issuer_ticker: str, issuer_id: int):
    """Main function to ingest EDGAR data for an issuer"""
    try:
        # CIK mapping for major companies (in production, you'd have a database)
        cik_mapping = {
            'AAPL': '0000320193',
            'MSFT': '0000789019',
            'GOOGL': '0001652044',
            'AMZN': '0001018724',
            'TSLA': '0001318605',
            'JPM': '0000019617',
            'BAC': '0000070858',
            'WFC': '0000072971',
            'XOM': '0000034088',
            'CVX': '0000093410',
            'JNJ': '0000200406',
            'PFE': '0000078003',
            'PG': '0000080424',
            'KO': '0000021344',
            'WMT': '0000104169'
        }
        
        cik = cik_mapping.get(issuer_ticker)
        if not cik:
            logger.warning("No CIK found for ticker", ticker=issuer_ticker)
            return
        
        # Initialize EDGAR ingestion
        edgar = EDGARIngestion()
        
        # Get company facts
        facts_data = edgar.get_company_facts(cik)
        if not facts_data:
            logger.warning("No facts data found", ticker=issuer_ticker, cik=cik)
            return
        
        # Extract financial ratios
        ratios = edgar.extract_financial_ratios(facts_data)
        if ratios:
            # Store in database
            edgar.store_financial_data(issuer_id, ratios)
            logger.info("Successfully ingested EDGAR data", ticker=issuer_ticker, ratios=len(ratios))
        else:
            logger.warning("No ratios extracted", ticker=issuer_ticker)
        
        # Rate limiting - SEC requires delays
        time.sleep(0.1)
        
    except Exception as e:
        logger.error("Failed to ingest EDGAR data", error=str(e), ticker=issuer_ticker)

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        ticker = sys.argv[1]
        issuer_id = int(sys.argv[2])
        ingest_edgar_data_for_issuer(ticker, issuer_id)
    else:
        print("Usage: python tasks_ingest_edgar.py <TICKER> <ISSUER_ID>")
