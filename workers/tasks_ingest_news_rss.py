import feedparser
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import time
import re
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import hashlib

logger = structlog.get_logger()

# Database setup
DATABASE_URL = "postgresql://credtech:credtech_pass@postgres:5432/credtech"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class NewsRSSIngestion:
    """Real-time news ingestion using Google News RSS feeds"""
    
    def __init__(self):
        self.session = SessionLocal()
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        
        # Google News RSS URLs for different search terms
        self.rss_urls = {
            "earnings": "https://news.google.com/rss/search?q=earnings+report&hl=en-US&gl=US&ceid=US:en",
            "bankruptcy": "https://news.google.com/rss/search?q=bankruptcy+filing&hl=en-US&gl=US&ceid=US:en",
            "restructuring": "https://news.google.com/rss/search?q=debt+restructuring&hl=en-US&gl=US&ceid=US:en",
            "downgrade": "https://news.google.com/rss/search?q=credit+downgrade&hl=en-US&gl=US&ceid=US:en",
            "acquisition": "https://news.google.com/rss/search?q=acquisition+merger&hl=en-US&gl=US&ceid=US:en",
            "management": "https://news.google.com/rss/search?q=CEO+resignation+management+change&hl=en-US&gl=US&ceid=US:en",
            "regulatory": "https://news.google.com/rss/search?q=regulatory+investigation+SEC&hl=en-US&gl=US&ceid=US:en",
            "dividend": "https://news.google.com/rss/search?q=dividend+cut+suspension&hl=en-US&gl=US&ceid=US:en"
        }
    
    def fetch_rss_feed(self, url: str) -> List[Dict]:
        """Fetch and parse RSS feed"""
        try:
            feed = feedparser.parse(url)
            articles = []
            
            for entry in feed.entries[:20]:  # Limit to 20 most recent articles
                article = {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "summary": entry.get("summary", ""),
                    "source": entry.get("source", {}).get("title", "Unknown")
                }
                articles.append(article)
            
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching RSS feed {url}: {e}")
            return []
    
    def extract_company_name(self, title: str, summary: str) -> Optional[str]:
        """Extract company name from news title/summary"""
        # Common company name patterns
        company_patterns = [
            r'\b(Apple|AAPL)\b',
            r'\b(Microsoft|MSFT)\b',
            r'\b(Google|Alphabet|GOOGL)\b',
            r'\b(Amazon|AMZN)\b',
            r'\b(Tesla|TSLA)\b',
            r'\b(Meta|Facebook|FB)\b',
            r'\b(Netflix|NFLX)\b',
            r'\b(Walmart|WMT)\b',
            r'\b(Johnson & Johnson|JNJ)\b',
            r'\b(Procter & Gamble|PG)\b',
            r'\b(JPMorgan|JPM)\b',
            r'\b(Bank of America|BAC)\b',
            r'\b(Wells Fargo|WFC)\b',
            r'\b(Goldman Sachs|GS)\b',
            r'\b(Morgan Stanley|MS)\b',
            r'\b(Coca-Cola|KO)\b',
            r'\b(PepsiCo|PEP)\b',
            r'\b(Disney|DIS)\b',
            r'\b(Nike|NKE)\b',
            r'\b(Home Depot|HD)\b'
        ]
        
        text = f"{title} {summary}".lower()
        
        for pattern in company_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def classify_event_type(self, title: str, summary: str) -> str:
        """Classify the type of event based on content"""
        text = f"{title} {summary}".lower()
        
        if any(word in text for word in ["bankruptcy", "chapter 11", "chapter 7"]):
            return "bankruptcy"
        elif any(word in text for word in ["restructuring", "debt restructuring", "financial restructuring"]):
            return "restructuring"
        elif any(word in text for word in ["downgrade", "credit downgrade", "rating downgrade"]):
            return "downgrade"
        elif any(word in text for word in ["earnings miss", "missed earnings", "earnings disappointment"]):
            return "earnings_miss"
        elif any(word in text for word in ["guidance cut", "lowered guidance", "reduced guidance"]):
            return "guidance_cut"
        elif any(word in text for word in ["ceo resign", "management change", "executive departure"]):
            return "management_change"
        elif any(word in text for word in ["acquisition", "merger", "buyout"]):
            return "acquisition"
        elif any(word in text for word in ["earnings beat", "strong earnings", "earnings surprise"]):
            return "positive_earnings_beat"
        elif any(word in text for word in ["dividend cut", "dividend suspension", "dividend reduction"]):
            return "dividend_cut"
        elif any(word in text for word in ["sec investigation", "regulatory probe", "regulatory investigation"]):
            return "regulatory_investigation"
        else:
            return "general"
    
    def calculate_sentiment(self, title: str, summary: str) -> float:
        """Calculate sentiment score using VADER"""
        text = f"{title} {summary}"
        sentiment_scores = self.sentiment_analyzer.polarity_scores(text)
        return sentiment_scores['compound']  # Returns value between -1 and 1
    
    def calculate_event_weight(self, event_type: str, sentiment: float) -> float:
        """Calculate event weight based on type and sentiment"""
        base_weights = {
            "bankruptcy": -9.0,
            "restructuring": -4.0,
            "downgrade": -5.0,
            "earnings_miss": -2.5,
            "guidance_cut": -3.0,
            "management_change": -2.0,
            "acquisition": 1.0,
            "positive_earnings_beat": 2.0,
            "dividend_cut": -2.5,
            "regulatory_investigation": -3.5,
            "general": -1.0
        }
        
        base_weight = base_weights.get(event_type, -1.0)
        
        # Adjust weight based on sentiment
        if sentiment > 0.3:
            base_weight *= 0.5  # Reduce negative impact for positive sentiment
        elif sentiment < -0.3:
            base_weight *= 1.5  # Increase negative impact for negative sentiment
        
        return base_weight
    
    def get_issuer_id_by_name(self, company_name: str) -> Optional[int]:
        """Get issuer ID by company name"""
        try:
            # Map company names to tickers
            name_to_ticker = {
                "Apple": "AAPL",
                "Microsoft": "MSFT",
                "Google": "GOOGL",
                "Alphabet": "GOOGL",
                "Amazon": "AMZN",
                "Tesla": "TSLA",
                "Meta": "META",
                "Facebook": "META",
                "Netflix": "NFLX",
                "Walmart": "WMT",
                "Johnson & Johnson": "JNJ",
                "Procter & Gamble": "PG",
                "JPMorgan": "JPM",
                "Bank of America": "BAC",
                "Wells Fargo": "WFC",
                "Goldman Sachs": "GS",
                "Morgan Stanley": "MS",
                "Coca-Cola": "KO",
                "PepsiCo": "PEP",
                "Disney": "DIS",
                "Nike": "NKE",
                "Home Depot": "HD"
            }
            
            ticker = name_to_ticker.get(company_name)
            if not ticker:
                return None
            
            result = self.session.execute(
                text("SELECT id FROM issuer WHERE ticker = :ticker"),
                {"ticker": ticker}
            )
            issuer = result.fetchone()
            
            return issuer[0] if issuer else None
            
        except Exception as e:
            logger.error(f"Error getting issuer ID for {company_name}: {e}")
            return None
    
    def store_news_event(self, issuer_id: int, article: Dict, event_type: str, sentiment: float, weight: float):
        """Store news event in database"""
        try:
            # Create hash for deduplication
            content_hash = hashlib.md5(f"{article['title']}{article['link']}".encode()).hexdigest()
            
            # Check if event already exists
            existing = self.session.execute(
                text("SELECT id FROM event WHERE raw_hash = :hash"),
                {"hash": content_hash}
            ).fetchone()
            
            if existing:
                return False  # Event already exists
            
            # Parse published date
            try:
                published_date = datetime.strptime(article['published'], '%a, %d %b %Y %H:%M:%S %Z')
            except:
                published_date = datetime.utcnow()
            
            # Insert event
            self.session.execute(
                text("""
                    INSERT INTO event (issuer_id, ts, type, headline, url, sentiment, weight, raw_hash, source)
                    VALUES (:issuer_id, :ts, :event_type, :headline, :url, :sentiment, :weight, :raw_hash, :source)
                """),
                {
                    "issuer_id": issuer_id,
                    "ts": published_date,
                    "event_type": event_type,
                    "headline": article['title'],
                    "url": article['link'],
                    "sentiment": sentiment,
                    "weight": weight,
                    "raw_hash": content_hash,
                    "source": "google_news_rss"
                }
            )
            
            self.session.commit()
            logger.info(f"Stored news event for issuer {issuer_id}: {article['title'][:50]}...")
            return True
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error storing news event: {e}")
            return False
    
    def update_credit_score_from_news(self, issuer_id: int, event_weight: float):
        """Update credit score based on news event"""
        try:
            # Get current score
            result = self.session.execute(
                text("SELECT score FROM score WHERE issuer_id = :issuer_id ORDER BY ts DESC LIMIT 1"),
                {"issuer_id": issuer_id}
            )
            current_score = result.fetchone()
            
            if not current_score:
                return
            
            # Calculate impact (limit to reasonable bounds)
            impact = max(-15, min(15, event_weight))
            new_score = max(0, min(100, current_score.score + impact))
            
            # Determine bucket
            if new_score >= 85: bucket = "AA"
            elif new_score >= 75: bucket = "A"
            elif new_score >= 65: bucket = "BBB"
            elif new_score >= 55: bucket = "BB"
            elif new_score >= 45: bucket = "B"
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
                    "score": new_score,
                    "bucket": bucket,
                    "base": current_score.score,
                    "market": 0.0,
                    "event_delta": impact,
                    "macro_adj": 0.0,
                    "model_version": "v2.0-real-news",
                    "explanation": f'{{"source": "google_news_rss", "impact": {impact:.2f}}}'
                }
            )
            
            self.session.commit()
            logger.info(f"Updated credit score for issuer {issuer_id} by {impact:.2f} points")
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating credit score from news: {e}")

def ingest_news_from_rss():
    """Main function to ingest news from RSS feeds"""
    try:
        logger.info("Starting RSS news ingestion")
        
        ingestion = NewsRSSIngestion()
        
        for category, url in ingestion.rss_urls.items():
            logger.info(f"Fetching news for category: {category}")
            
            # Fetch articles
            articles = ingestion.fetch_rss_feed(url)
            
            for article in articles:
                # Extract company name
                company_name = ingestion.extract_company_name(article['title'], article['summary'])
                if not company_name:
                    continue
                
                # Get issuer ID
                issuer_id = ingestion.get_issuer_id_by_name(company_name)
                if not issuer_id:
                    continue
                
                # Classify event
                event_type = ingestion.classify_event_type(article['title'], article['summary'])
                
                # Calculate sentiment
                sentiment = ingestion.calculate_sentiment(article['title'], article['summary'])
                
                # Calculate weight
                weight = ingestion.calculate_event_weight(event_type, sentiment)
                
                # Store event
                if ingestion.store_news_event(issuer_id, article, event_type, sentiment, weight):
                    # Update credit score
                    ingestion.update_credit_score_from_news(issuer_id, weight)
                
                # Rate limiting
                time.sleep(0.5)
        
        logger.info("Completed RSS news ingestion")
        return True
        
    except Exception as e:
        logger.error(f"Error in RSS news ingestion: {e}")
        return False

if __name__ == "__main__":
    ingest_news_from_rss()
