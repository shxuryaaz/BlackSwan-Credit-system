from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime
import json
import re
import os
from typing import List, Dict, Any
import openai
from services.db import get_db

router = APIRouter(prefix="/upload", tags=["upload"])

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-key-here")
openai.api_key = OPENAI_API_KEY

class NewsTextRequest(BaseModel):
    news_text: str
    issuer_id: int = None

async def analyze_news_with_openai(news_text: str) -> Dict[str, Any]:
    """
    Use OpenAI to analyze news text and determine credit score impact
    """
    try:
        # Create a structured prompt for credit analysis
        prompt = f"""
        Analyze the following news text and determine its impact on a company's credit score.
        
        News Text: "{news_text}"
        
        Please provide a JSON response with the following structure:
        {{
            "sentiment": float,  // -1.0 to 1.0 (negative to positive)
            "impact_weight": float,  // -10.0 to 10.0 (credit score change)
            "event_type": string,  // "earnings", "regulatory", "partnership", "product", "security", "leadership", "financial", "market"
            "confidence": float,  // 0.0 to 1.0
            "reasoning": string,  // Brief explanation of the analysis
            "keywords": [string],  // Key terms that influenced the analysis
            "risk_factors": [string]  // Any risk factors identified
        }}
        
        IMPORTANT GUIDELINES:
        - For negative news (stock drops, losses, scandals, etc.), use NEGATIVE sentiment (-1.0 to 0.0) and NEGATIVE impact_weight (-10.0 to 0.0)
        - For positive news (earnings beats, growth, partnerships, etc.), use POSITIVE sentiment (0.0 to 1.0) and POSITIVE impact_weight (0.0 to 10.0)
        - Stock price movements (tumbles, drops, crashes) should generally have negative impact
        - Financial losses, regulatory issues, and scandals should have significant negative impact
        - Earnings beats, revenue growth, and positive partnerships should have positive impact
        
        Consider:
        - Financial performance indicators (earnings, revenue, profit)
        - Regulatory issues or compliance
        - Strategic partnerships or acquisitions
        - Product launches or innovations
        - Security breaches or scandals
        - Leadership changes
        - Market position changes
        - Industry-specific factors
        - Stock price movements and market reactions
        
        Respond with ONLY the JSON object, no additional text.
        """
        
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a credit risk analyst. Analyze news text and provide structured credit impact assessment."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        # Extract JSON from response
        content = response.choices[0].message.content.strip()
        
        # Clean up the response to extract JSON
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        
        analysis = json.loads(content)
        
        return {
            "sentiment": analysis.get("sentiment", 0.0),
            "weight": analysis.get("impact_weight", 0.0),
            "type": analysis.get("event_type", "general"),
            "confidence": analysis.get("confidence", 0.5),
            "reasoning": analysis.get("reasoning", ""),
            "keywords": analysis.get("keywords", []),
            "risk_factors": analysis.get("risk_factors", [])
        }
        
    except Exception as e:
        # Fallback to keyword analysis if OpenAI fails
        print(f"OpenAI analysis failed: {e}, using fallback")
        return fallback_keyword_analysis(news_text)

def fallback_keyword_analysis(text: str) -> Dict[str, Any]:
    """
    Fallback keyword-based analysis if OpenAI is not available
    """
    text_lower = text.lower()
    
    # Positive keywords
    positive_keywords = {
        'earnings beat': 5.5, 'revenue growth': 4.8, 'profit increase': 4.2,
        'market share': 3.5, 'partnership': 3.2, 'product launch': 3.8,
        'expansion': 2.8, 'innovation': 2.5, 'strong': 2.0, 'record': 3.0,
        'successful': 2.2, 'growth': 2.5, 'positive': 1.8, 'upgrade': 2.8
    }
    
    # Negative keywords
    negative_keywords = {
        'earnings miss': -5.0, 'revenue decline': -4.5, 'loss': -4.0,
        'investigation': -4.2, 'breach': -5.5, 'scandal': -5.8,
        'resignation': -4.5, 'layoffs': -3.8, 'bankruptcy': -8.0,
        'regulatory': -3.2, 'fine': -3.5, 'penalty': -3.0, 'weak': -2.5,
        'tumbles': -4.0, 'tumble': -4.0, 'stock drop': -3.5, 'stock decline': -3.5,
        'stock fall': -3.5, 'stock crash': -5.0, 'market crash': -5.0,
        'plunge': -4.5, 'plunges': -4.5, 'drops': -3.0, 'drop': -3.0,
        'declines': -3.0, 'decline': -3.0, 'falls': -3.0, 'fall': -3.0,
        'sinks': -3.5, 'sink': -3.5, 'slumps': -3.0, 'slump': -3.0,
        'downturn': -3.5, 'bearish': -2.5, 'negative': -2.0, 'down': -2.0
    }
    
    positive_score = sum(weight for keyword, weight in positive_keywords.items() if keyword in text_lower)
    negative_score = sum(weight for keyword, weight in negative_keywords.items() if keyword in text_lower)
    total_score = positive_score + negative_score
    
    return {
        "sentiment": max(-1.0, min(1.0, total_score / 10.0)),
        "weight": round(total_score, 1),
        "type": "general",
        "confidence": 0.6,
        "reasoning": "Keyword-based analysis (OpenAI fallback)",
        "keywords": [k for k, v in positive_keywords.items() if k in text_lower] + 
                   [k for k, v in negative_keywords.items() if k in text_lower],
        "risk_factors": []
    }

async def update_issuer_score(conn: AsyncSession, issuer_id: int, news_text: str, analysis: Dict[str, Any]):
    """
    Update issuer score based on news analysis
    """
    # Insert the news event
    await conn.execute(text("""
        INSERT INTO event (issuer_id, ts, headline, type, sentiment, weight, source)
        VALUES (:issuer_id, :ts, :headline, :type, :sentiment, :weight, :source)
    """), {
        "issuer_id": issuer_id,
        "ts": datetime.now(),
        "headline": news_text[:200],  # Truncate if too long
        "type": analysis["type"],
        "sentiment": analysis["sentiment"],
        "weight": analysis["weight"],
        "source": "openai_upload"
    })
    
    # Get current score
    result = await conn.execute(text("""
        SELECT score, base, market, event_delta, macro_adj 
        FROM score 
        WHERE issuer_id = :issuer_id 
        ORDER BY ts DESC 
        LIMIT 1
    """), {"issuer_id": issuer_id})
    current = result.fetchone()
    
    if not current:
        raise HTTPException(status_code=404, detail=f"No current score found for issuer {issuer_id}")
    
    old_score, base, market, event_delta, macro_adj = current
    
    # Calculate new score - properly apply the weight
    new_event_delta = event_delta + analysis["weight"]
    new_score = base + market + new_event_delta + macro_adj
    
    # Ensure score stays within bounds
    new_score = max(0, min(100, new_score))
    
    # Debug logging
    print(f"🔍 Score calculation for issuer {issuer_id}:")
    print(f"   Old score: {old_score}")
    print(f"   Analysis weight: {analysis['weight']}")
    print(f"   New event delta: {new_event_delta}")
    print(f"   New score: {new_score}")
    print(f"   Sentiment: {analysis['sentiment']}")
    
    # Determine new bucket
    if new_score >= 90:
        bucket = "AAA"
    elif new_score >= 80:
        bucket = "AA"
    elif new_score >= 70:
        bucket = "A"
    elif new_score >= 60:
        bucket = "BBB"
    elif new_score >= 50:
        bucket = "BB"
    else:
        bucket = "B"
    
    # Insert new score
    await conn.execute(text("""
        INSERT INTO score (issuer_id, ts, score, bucket, base, market, event_delta, macro_adj, model_version, explanation)
        VALUES (:issuer_id, :ts, :score, :bucket, :base, :market, :event_delta, :macro_adj, :model_version, :explanation)
    """), {
        "issuer_id": issuer_id,
        "ts": datetime.now(),
        "score": round(new_score, 1),
        "bucket": bucket,
        "base": base,
        "market": market,
        "event_delta": round(new_event_delta, 1),
        "macro_adj": macro_adj,
        "model_version": "v4.0-openai-analysis",
        "explanation": json.dumps({
            "source": "openai_upload",
            "news_text": news_text,
            "analysis": analysis,
            "score_change": round(analysis["weight"], 1),
            "reason": f"OpenAI Analysis: {analysis['reasoning']}"
        })
    })
    
    await conn.commit()
    
    return {
        "issuer_id": issuer_id,
        "old_score": round(old_score, 1),
        "new_score": round(new_score, 1),
        "change": round(analysis["weight"], 1),
        "bucket": bucket,
        "analysis": analysis
    }

@router.post("/news-file")
async def upload_news_file(
    file: UploadFile = File(...),
    issuer_id: int = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a news text file and analyze it with OpenAI to update credit scores
    """
    try:
        # Validate file
        if not file.filename.endswith('.txt'):
            raise HTTPException(status_code=400, detail="Only .txt files are supported")
        
        # Read file content
        content = await file.read()
        news_text = content.decode('utf-8').strip()
        
        if not news_text:
            raise HTTPException(status_code=400, detail="File is empty")
        
        # If no issuer_id provided, use a random one (for demo purposes)
        if issuer_id is None:
            result = await db.execute(text("SELECT id FROM issuer ORDER BY RANDOM() LIMIT 1"))
            issuer_id = result.scalar_one()
        
        # Analyze with OpenAI
        print(f"🤖 Analyzing news with OpenAI for issuer {issuer_id}")
        analysis = await analyze_news_with_openai(news_text)
        
        print(f"📊 OpenAI Analysis Results:")
        print(f"   Sentiment: {analysis['sentiment']:.2f}")
        print(f"   Impact Weight: {analysis['weight']:.1f}")
        print(f"   Event Type: {analysis['type']}")
        print(f"   Confidence: {analysis['confidence']:.2f}")
        print(f"   Reasoning: {analysis['reasoning']}")
        
        # Update issuer score
        result = await update_issuer_score(db, issuer_id, news_text, analysis)
        
        return {
            "message": "News file analyzed and credit score updated successfully",
            "file_name": file.filename,
            "issuer_id": issuer_id,
            "analysis": analysis,
            "score_update": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@router.post("/news-text")
async def analyze_news_text(
    request: NewsTextRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze news text directly and update credit scores
    """
    try:
        if not request.news_text.strip():
            raise HTTPException(status_code=400, detail="News text cannot be empty")
        
        # If no issuer_id provided, use a random one
        if request.issuer_id is None:
            result = await db.execute(text("SELECT id FROM issuer ORDER BY RANDOM() LIMIT 1"))
            issuer_id = result.scalar_one()
        else:
            issuer_id = request.issuer_id
        
        # Analyze with OpenAI
        print(f"🤖 Analyzing news text with OpenAI for issuer {issuer_id}")
        analysis = await analyze_news_with_openai(request.news_text)
        
        # Update issuer score
        result = await update_issuer_score(db, issuer_id, request.news_text, analysis)
        
        return {
            "message": "News text analyzed and credit score updated successfully",
            "issuer_id": issuer_id,
            "analysis": analysis,
            "score_update": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing text: {str(e)}")

@router.get("/status")
async def get_upload_status():
    """
    Get upload system status
    """
    return {
        "status": "active",
        "features": [
            "OpenAI-powered news analysis",
            "File upload support (.txt)",
            "Real-time credit score updates",
            "Fallback keyword analysis"
        ],
        "openai_available": OPENAI_API_KEY != "your-openai-key-here",
        "endpoints": {
            "upload_file": "POST /api/v1/upload/news-file",
            "analyze_text": "POST /api/v1/upload/news-text",
            "status": "GET /api/v1/upload/status"
        }
    }
