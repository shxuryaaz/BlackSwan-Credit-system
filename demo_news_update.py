#!/usr/bin/env python3
"""
Demo script with AI news understanding to update credit scores in real-time
This demonstrates NLP analysis of news headlines to determine credit impact
"""

import psycopg2
import json
import random
from datetime import datetime
import time
import re

# Database connection
DB_CONFIG = {
    'host': 'postgres',  # Docker service name
    'port': 5432,
    'database': 'credtech',
    'user': 'credtech',
    'password': 'credtech_pass'
}

# AI News Analysis - Keyword-based sentiment and impact analysis
def analyze_news_ai(headline):
    """
    AI function to analyze news headlines and determine credit score impact
    This simulates NLP analysis of unstructured text
    """
    headline_lower = headline.lower()
    
    # Positive keywords and their impact weights
    positive_keywords = {
        'earnings beat': 5.5,
        'revenue growth': 4.8,
        'profit increase': 4.2,
        'market share': 3.5,
        'partnership': 3.2,
        'product launch': 3.8,
        'expansion': 2.8,
        'innovation': 2.5,
        'strong': 2.0,
        'record': 3.0,
        'successful': 2.2,
        'growth': 2.5,
        'positive': 1.8,
        'upgrade': 2.8,
        'approval': 2.0
    }
    
    # Negative keywords and their impact weights
    negative_keywords = {
        'earnings miss': -5.0,
        'revenue decline': -4.5,
        'loss': -4.0,
        'investigation': -4.2,
        'breach': -5.5,
        'scandal': -5.8,
        'resignation': -4.5,
        'layoffs': -3.8,
        'bankruptcy': -8.0,
        'default': -7.5,
        'regulatory': -3.2,
        'fine': -3.5,
        'penalty': -3.0,
        'weak': -2.5,
        'decline': -2.8,
        'negative': -2.0,
        'downgrade': -3.2
    }
    
    # Calculate sentiment score
    positive_score = 0
    negative_score = 0
    
    for keyword, weight in positive_keywords.items():
        if keyword in headline_lower:
            positive_score += weight
    
    for keyword, weight in negative_keywords.items():
        if keyword in headline_lower:
            negative_score += weight
    
    # Determine overall sentiment and weight
    total_score = positive_score + negative_score
    
    # Normalize sentiment to -1 to 1 range
    sentiment = max(-1.0, min(1.0, total_score / 10.0))
    
    # Determine event type based on keywords
    event_type = "general"
    if any(word in headline_lower for word in ['earnings', 'revenue', 'profit', 'financial']):
        event_type = "earnings"
    elif any(word in headline_lower for word in ['product', 'launch', 'innovation']):
        event_type = "product launch"
    elif any(word in headline_lower for word in ['partnership', 'acquisition', 'merger']):
        event_type = "partnership"
    elif any(word in headline_lower for word in ['investigation', 'regulatory', 'fine', 'penalty']):
        event_type = "regulatory"
    elif any(word in headline_lower for word in ['breach', 'security', 'hack']):
        event_type = "security"
    elif any(word in headline_lower for word in ['ceo', 'resignation', 'leadership']):
        event_type = "leadership"
    
    return {
        "sentiment": round(sentiment, 2),
        "weight": round(total_score, 1),
        "type": event_type,
        "analysis": {
            "positive_keywords": [k for k, v in positive_keywords.items() if k in headline_lower],
            "negative_keywords": [k for k, v in negative_keywords.items() if k in headline_lower],
            "confidence": min(0.95, abs(total_score) / 8.0 + 0.3)
        }
    }

# Realistic news headlines for demo
REALISTIC_NEWS = [
    "Apple Reports Record Q3 Earnings, Beats Expectations by 18%",
    "Microsoft Announces Strategic Partnership with OpenAI",
    "Tesla Faces Regulatory Investigation Over Safety Concerns",
    "Amazon Launches Revolutionary AI-Powered Product Line",
    "JPMorgan Reports Strong Revenue Growth in Q3",
    "Bank of America Faces Cybersecurity Breach",
    "Google Announces Major Market Expansion in Asia",
    "Meta Reports Weak Q3 Earnings, Misses Targets",
    "Netflix Shows Strong Subscriber Growth",
    "Disney Faces Leadership Changes Amid Controversy",
    "Nike Reports Record Breaking Sales Figures",
    "Coca-Cola Announces Global Partnership Deal",
    "Walmart Expands E-commerce Market Share",
    "Pfizer Receives Regulatory Approval for New Drug",
    "Exxon Mobil Reports Declining Oil Production"
]

def get_current_score(conn, issuer_id):
    """Get current score for an issuer"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT score, bucket, base, market, event_delta, macro_adj 
        FROM score 
        WHERE issuer_id = %s 
        ORDER BY ts DESC 
        LIMIT 1
    """, (issuer_id,))
    result = cursor.fetchone()
    cursor.close()
    return result

def add_ai_analyzed_news(conn, issuer_id, headline):
    """Add news event with AI analysis and update credit score"""
    cursor = conn.cursor()
    
    # AI analyzes the news headline
    print(f"🤖 AI analyzing: '{headline}'")
    ai_analysis = analyze_news_ai(headline)
    
    print(f"   📊 AI Analysis Results:")
    print(f"      Sentiment: {ai_analysis['sentiment']:.2f}")
    print(f"      Impact Weight: {ai_analysis['weight']:.1f}")
    print(f"      Event Type: {ai_analysis['type']}")
    print(f"      Confidence: {ai_analysis['analysis']['confidence']:.2f}")
    
    # Insert the news event
    cursor.execute("""
        INSERT INTO event (issuer_id, ts, headline, type, sentiment, weight, source)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        issuer_id,
        datetime.now(),
        headline,
        ai_analysis["type"],
        ai_analysis["sentiment"],
        ai_analysis["weight"],
        "ai_news_analysis"
    ))
    
    # Get current score
    current = get_current_score(conn, issuer_id)
    if not current:
        print(f"No current score found for issuer {issuer_id}")
        return
    
    old_score, old_bucket, base, market, event_delta, macro_adj = current
    
    # Calculate new score based on AI analysis
    new_event_delta = event_delta + ai_analysis["weight"]
    new_score = base + market + new_event_delta + macro_adj
    new_score = max(0, min(100, new_score))
    
    # Determine new bucket
    if new_score >= 90:
        new_bucket = "AAA"
    elif new_score >= 80:
        new_bucket = "AA"
    elif new_score >= 70:
        new_bucket = "A"
    elif new_score >= 60:
        new_bucket = "BBB"
    elif new_score >= 50:
        new_bucket = "BB"
    else:
        new_bucket = "B"
    
    # Insert new score with AI explanation
    cursor.execute("""
        INSERT INTO score (issuer_id, ts, score, bucket, base, market, event_delta, macro_adj, model_version, explanation)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        issuer_id,
        datetime.now(),
        round(new_score, 1),
        new_bucket,
        base,
        market,
        round(new_event_delta, 1),
        macro_adj,
        "v3.0-ai-news-analysis",
        json.dumps({
            "source": "ai_news_analysis",
            "headline": headline,
            "ai_analysis": ai_analysis,
            "score_change": round(ai_analysis["weight"], 1),
            "reason": f"AI Analysis: {headline}",
            "confidence": ai_analysis["analysis"]["confidence"],
            "keywords_found": {
                "positive": ai_analysis["analysis"]["positive_keywords"],
                "negative": ai_analysis["analysis"]["negative_keywords"]
            }
        })
    ))
    
    conn.commit()
    cursor.close()
    
    return {
        "issuer_id": issuer_id,
        "old_score": round(old_score, 1),
        "new_score": round(new_score, 1),
        "old_bucket": old_bucket,
        "new_bucket": new_bucket,
        "change": round(ai_analysis["weight"], 1),
        "ai_analysis": ai_analysis
    }

def show_current_scores(conn):
    """Show current scores for all issuers"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT i.name, s.score, s.bucket, s.delta_24h
        FROM issuer i
        JOIN (
            SELECT DISTINCT ON (issuer_id) 
                issuer_id, score, bucket, 
                score - LAG(score) OVER (PARTITION BY issuer_id ORDER BY ts) as delta_24h
            FROM score
            ORDER BY issuer_id, ts DESC
        ) s ON i.id = s.issuer_id
        ORDER BY i.id
        LIMIT 5
    """)
    
    results = cursor.fetchall()
    cursor.close()
    
    print("\n" + "="*70)
    print("CURRENT CREDIT SCORES")
    print("="*70)
    for name, score, bucket, delta in results:
        delta_str = f"+{delta:.1f}" if delta and delta > 0 else f"{delta:.1f}" if delta else "0.0"
        print(f"{name:<20} | {score:>6.1f} | {bucket:>3} | {delta_str:>6}")
    print("="*70)

def demo_ai_news_analysis():
    """Main demo function with AI news analysis"""
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connected to database")
        
        # Show initial state
        print("\n📊 INITIAL STATE:")
        show_current_scores(conn)
        
        # Demo issuers with realistic news
        demo_news = [
            (1, "Apple Reports Record Q3 Earnings, Beats Expectations by 18%"),
            (2, "Microsoft Announces Strategic Partnership with OpenAI"),
            (5, "Tesla Faces Regulatory Investigation Over Safety Concerns")
        ]
        
        print(f"\n🤖 AI NEWS ANALYSIS & CREDIT SCORE UPDATES")
        print("="*70)
        print("Demonstrating NLP analysis of unstructured news headlines")
        print("="*70)
        
        for i, (issuer_id, headline) in enumerate(demo_news, 1):
            print(f"\n📰 Event {i}: AI analyzing news for issuer {issuer_id}")
            print(f"   Headline: '{headline}'")
            
            # Add the event with AI analysis and update score
            result = add_ai_analyzed_news(conn, issuer_id, headline)
            
            if result:
                print(f"   📈 Score: {result['old_score']} → {result['new_score']} ({result['change']:+.1f})")
                print(f"   🏷️  Bucket: {result['old_bucket']} → {result['new_bucket']}")
                print(f"   🎯 AI Confidence: {result['ai_analysis']['analysis']['confidence']:.2f}")
            
            # Small delay for dramatic effect
            time.sleep(2)
        
        # Show final state
        print(f"\n📊 FINAL STATE (After AI News Analysis):")
        show_current_scores(conn)
        
        print(f"\n🎉 AI NEWS ANALYSIS DEMO COMPLETE!")
        print(f"   • AI analyzed {len(demo_news)} news headlines")
        print(f"   • Determined sentiment and impact automatically")
        print(f"   • Updated credit scores based on AI understanding")
        print(f"   • Check your dashboard to see the changes!")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🎯 CREDIT INTELLIGENCE PLATFORM - AI NEWS ANALYSIS DEMO")
    print("This script demonstrates AI understanding of news headlines")
    print("and real-time credit score updates based on NLP analysis")
    print("="*70)
    
    demo_ai_news_analysis()
