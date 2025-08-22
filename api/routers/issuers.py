from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func, text
from typing import List, Optional
import structlog

from services.db import get_db
from models.issuer import Issuer
from models.score import Score
from models.event import Event
from schemas.issuer import IssuerResponse, IssuerDetailResponse, IssuerListResponse

logger = structlog.get_logger()
router = APIRouter()

@router.get("/issuers", response_model=IssuerListResponse)
async def list_issuers(
    sector: Optional[str] = Query(None, description="Filter by sector"),
    country: Optional[str] = Query(None, description="Filter by country"),
    limit: int = Query(100, le=1000, description="Maximum number of issuers to return"),
    offset: int = Query(0, ge=0, description="Number of issuers to skip"),
    db: Session = Depends(get_db)
):
    """
    List all issuers with their latest scores and changes.
    
    Returns issuers with their current credit scores, 24h changes, and rating buckets.
    """
    try:
        # Build base query
        query = select(Issuer)
        
        # Apply filters
        if sector:
            query = query.where(Issuer.sector == sector)
        if country:
            query = query.where(Issuer.country == country)
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        # Execute query
        result = await db.execute(query)
        issuers = result.scalars().all()
        
        # Get score changes for each issuer
        issuer_responses = []
        for issuer in issuers:
            # Get latest score for this issuer
            latest_score_query = select(Score).where(Score.issuer_id == issuer.id).order_by(Score.ts.desc()).limit(1)
            latest_score_result = await db.execute(latest_score_query)
            latest_score = latest_score_result.scalar_one_or_none()
            
            # Calculate recent score change (for demo purposes)
            score_change_24h = 0.0
            if latest_score:
                # Get the previous score (for demo, we'll use the 2nd most recent)
                
                # Find the previous score
                previous_score_result = await db.execute(
                    text("""
                        SELECT score 
                        FROM score 
                        WHERE issuer_id = :issuer_id 
                        AND ts < :latest_ts
                        ORDER BY ts DESC 
                        LIMIT 1
                    """),
                    {
                        "issuer_id": issuer.id,
                        "latest_ts": latest_score.ts
                    }
                )
                previous_score_row = previous_score_result.fetchone()
                
                if previous_score_row:
                    previous_score = previous_score_row[0]
                    score_change_24h = latest_score.score - previous_score
            
            issuer_response = IssuerResponse(
                id=issuer.id,
                name=issuer.name,
                ticker=issuer.ticker,
                sector=issuer.sector,
                country=issuer.country,
                score=latest_score.score if latest_score else None,
                bucket=latest_score.bucket if latest_score else None,
                delta_24h=round(score_change_24h, 2) if score_change_24h else 0.0,
                score_ts=latest_score.ts if latest_score else None
            )
            issuer_responses.append(issuer_response)
        
        return IssuerListResponse(
            issuers=issuer_responses,
            total=len(issuer_responses),
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error("Failed to list issuers", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/issuer/{issuer_id}", response_model=IssuerDetailResponse)
async def get_issuer_detail(
    issuer_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific issuer.
    
    Returns issuer details, latest score with explanation, and recent events.
    """
    try:
        # Get issuer with latest score and recent events
        issuer_query = select(Issuer).where(Issuer.id == issuer_id)
        issuer_result = await db.execute(issuer_query)
        issuer = issuer_result.scalar_one_or_none()
        if not issuer:
            raise HTTPException(status_code=404, detail="Issuer not found")
        
        # Get latest score
        latest_score_query = select(Score).where(Score.issuer_id == issuer_id).order_by(Score.ts.desc()).limit(1)
        latest_score_result = await db.execute(latest_score_query)
        latest_score = latest_score_result.scalar_one_or_none()
        
        # Get recent events (last 7 days)
        from datetime import datetime, timedelta
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_events_query = select(Event).where(
            Event.issuer_id == issuer_id,
            Event.ts >= seven_days_ago
        ).order_by(Event.ts.desc()).limit(10)
        recent_events_result = await db.execute(recent_events_query)
        recent_events = recent_events_result.scalars().all()
        
        # Calculate 24h score change
        score_change_24h = 0.0
        if latest_score:
            # Get score from 24 hours ago
            from datetime import datetime, timedelta
            
            twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
            
            # Find the most recent score before 24 hours ago
            previous_score_result = await db.execute(
                text("""
                    SELECT score 
                    FROM score 
                    WHERE issuer_id = :issuer_id 
                    AND ts < :twenty_four_hours_ago
                    ORDER BY ts DESC 
                    LIMIT 1
                """),
                {
                    "issuer_id": issuer_id,
                    "twenty_four_hours_ago": twenty_four_hours_ago
                }
            )
            previous_score_row = previous_score_result.fetchone()
            
            if previous_score_row:
                previous_score = previous_score_row[0]
                score_change_24h = latest_score.score - previous_score
        
        return IssuerDetailResponse(
            id=issuer.id,
            name=issuer.name,
            ticker=issuer.ticker,
            sector=issuer.sector,
            country=issuer.country,
            score=latest_score.score if latest_score else None,
            bucket=latest_score.bucket if latest_score else None,
            delta_24h=round(score_change_24h, 2) if score_change_24h else 0.0,
            components={
                "base": latest_score.base if latest_score else 0.0,
                "market": latest_score.market if latest_score else 0.0,
                "event_delta": latest_score.event_delta if latest_score else 0.0,
                "macro_adj": latest_score.macro_adj if latest_score else 0.0
            } if latest_score else None,
            top_features=[
                {"name": "Base Fundamentals", "impact": latest_score.base if latest_score else 0.0},
                {"name": "Market Risk", "impact": latest_score.market if latest_score else 0.0},
                {"name": "Event Impact", "impact": latest_score.event_delta if latest_score else 0.0},
                {"name": "Macro Adjustment", "impact": latest_score.macro_adj if latest_score else 0.0}
            ] if latest_score else [],
            events=[event.to_dict() for event in recent_events],
            score_ts=latest_score.ts if latest_score else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get issuer detail", error=str(e), issuer_id=issuer_id)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/issuer/{issuer_id}/timeline")
async def get_issuer_timeline(
    issuer_id: int,
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(100, le=1000, description="Maximum number of data points"),
    db: Session = Depends(get_db)
):
    """
    Get historical timeline for an issuer.
    
    Returns scores and events over time for the specified period.
    """
    try:
        # Verify issuer exists
        issuer = db.query(Issuer).filter(Issuer.id == issuer_id).first()
        if not issuer:
            raise HTTPException(status_code=404, detail="Issuer not found")
        
        # Build score query
        score_query = db.query(Score).filter(Score.issuer_id == issuer_id)
        
        # Apply date filters
        if from_date:
            score_query = score_query.filter(Score.ts >= from_date)
        if to_date:
            score_query = score_query.filter(Score.ts <= to_date)
        
        scores = score_query.order_by(Score.ts.desc()).limit(limit).all()
        
        # Build event query
        event_query = db.query(Event).filter(Event.issuer_id == issuer_id)
        
        if from_date:
            event_query = event_query.filter(Event.ts >= from_date)
        if to_date:
            event_query = event_query.filter(Event.ts <= to_date)
        
        events = event_query.order_by(Event.ts.desc()).limit(limit).all()
        
        # Combine and sort by timestamp
        timeline = []
        
        for score in scores:
            timeline.append({
                "ts": score.ts.isoformat(),
                "type": "score",
                "data": score.to_dict()
            })
        
        for event in events:
            timeline.append({
                "ts": event.ts.isoformat(),
                "type": "event",
                "data": event.to_dict()
            })
        
        # Sort by timestamp (newest first)
        timeline.sort(key=lambda x: x["ts"], reverse=True)
        
        return {
            "issuer_id": issuer_id,
            "timeline": timeline[:limit],
            "total_scores": len(scores),
            "total_events": len(events)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get issuer timeline", error=str(e), issuer_id=issuer_id)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{issuer_id}/history")
async def get_issuer_score_history(issuer_id: int, db: Session = Depends(get_db)):
    """Get score history for an issuer (for charts)"""
    try:
        # Get score history
        result = await db.execute(
            text("""
                SELECT 
                    ts,
                    score,
                    bucket,
                    base,
                    market,
                    event_delta,
                    macro_adj
                FROM score 
                WHERE issuer_id = :issuer_id 
                ORDER BY ts DESC 
                LIMIT 50
            """),
            {"issuer_id": issuer_id}
        )
        
        scores = result.fetchall()
        
        # Convert to list of dicts
        score_history = []
        for score in scores:
            score_history.append({
                "ts": score.ts.isoformat() if score.ts else None,
                "score": float(score.score) if score.score else 0.0,
                "bucket": score.bucket,
                "base": float(score.base) if score.base else 0.0,
                "market": float(score.market) if score.market else 0.0,
                "event_delta": float(score.event_delta) if score.event_delta else 0.0,
                "macro_adj": float(score.macro_adj) if score.macro_adj else 0.0
            })
        
        return score_history
        
    except Exception as e:
        logger.error(f"Error fetching issuer score history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/sectors")
async def list_sectors(db: Session = Depends(get_db)):
    """
    Get list of all sectors in the database.
    """
    try:
        sectors = db.query(Issuer.sector).distinct().filter(Issuer.sector.isnot(None)).all()
        return {"sectors": [sector[0] for sector in sectors]}
    except Exception as e:
        logger.error("Failed to list sectors", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/countries")
async def list_countries(db: Session = Depends(get_db)):
    """
    Get list of all countries in the database.
    """
    try:
        countries = db.query(Issuer.country).distinct().filter(Issuer.country.isnot(None)).all()
        return {"countries": [country[0] for country in countries]}
    except Exception as e:
        logger.error("Failed to list countries", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")
