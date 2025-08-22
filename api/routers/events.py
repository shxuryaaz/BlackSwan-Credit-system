from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import structlog

from services.db import get_db
from models.event import Event
from models.issuer import Issuer

logger = structlog.get_logger()
router = APIRouter()

@router.get("/events/latest")
async def get_latest_events(
    limit: int = Query(50, le=1000, description="Maximum number of events to return"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    db: Session = Depends(get_db)
):
    """
    Get the latest events across all issuers.
    """
    try:
        query = db.query(Event).join(Issuer)
        
        if event_type:
            query = query.filter(Event.type == event_type)
        
        events = query.order_by(Event.ts.desc()).limit(limit).all()
        
        return {
            "events": [event.to_dict() for event in events],
            "total": len(events)
        }
    except Exception as e:
        logger.error("Failed to get latest events", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/events/{issuer_id}")
async def get_issuer_events(
    issuer_id: int,
    limit: int = Query(100, le=1000, description="Maximum number of events to return"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    db: Session = Depends(get_db)
):
    """
    Get events for a specific issuer.
    """
    try:
        # Verify issuer exists
        issuer = db.query(Issuer).filter(Issuer.id == issuer_id).first()
        if not issuer:
            raise HTTPException(status_code=404, detail="Issuer not found")
        
        query = db.query(Event).filter(Event.issuer_id == issuer_id)
        
        if event_type:
            query = query.filter(Event.type == event_type)
        
        events = query.order_by(Event.ts.desc()).limit(limit).all()
        
        return {
            "issuer_id": issuer_id,
            "issuer_name": issuer.name,
            "events": [event.to_dict() for event in events],
            "total": len(events)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get issuer events", error=str(e), issuer_id=issuer_id)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/events/types")
async def get_event_types(db: Session = Depends(get_db)):
    """
    Get list of all event types in the database.
    """
    try:
        event_types = db.query(Event.type).distinct().all()
        return {"event_types": [event_type[0] for event_type in event_types]}
    except Exception as e:
        logger.error("Failed to get event types", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/events/summary")
async def get_events_summary(
    days: int = Query(7, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """
    Get summary of events over the specified period.
    """
    try:
        # Get events in the specified period
        events = db.query(Event).filter(
            Event.ts >= func.now() - func.interval(f'{days} days')
        ).all()
        
        # Group by type
        event_summary = {}
        for event in events:
            if event.type not in event_summary:
                event_summary[event.type] = {
                    "count": 0,
                    "total_impact": 0.0,
                    "avg_sentiment": 0.0
                }
            
            event_summary[event.type]["count"] += 1
            event_summary[event.type]["total_impact"] += event.effective_weight
            event_summary[event.type]["avg_sentiment"] += event.sentiment or 0.0
        
        # Calculate averages
        for event_type, summary in event_summary.items():
            if summary["count"] > 0:
                summary["avg_sentiment"] /= summary["count"]
                summary["avg_impact"] = summary["total_impact"] / summary["count"]
        
        return {
            "period_days": days,
            "total_events": len(events),
            "event_types": event_summary
        }
    except Exception as e:
        logger.error("Failed to get events summary", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")





