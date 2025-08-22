from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import structlog

from services.db import get_db
from models.score import Score
from models.issuer import Issuer

logger = structlog.get_logger()
router = APIRouter()

@router.get("/scores/latest")
async def get_latest_scores(
    limit: int = Query(50, le=1000, description="Maximum number of scores to return"),
    db: Session = Depends(get_db)
):
    """
    Get the latest scores for all issuers.
    """
    try:
        # Get latest score for each issuer
        latest_scores = db.query(Score).join(Issuer).filter(
            Score.ts == db.query(func.max(Score.ts)).filter(
                Score.issuer_id == Issuer.id
            ).scalar_subquery()
        ).limit(limit).all()
        
        return {
            "scores": [score.to_dict() for score in latest_scores],
            "total": len(latest_scores)
        }
    except Exception as e:
        logger.error("Failed to get latest scores", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/scores/{issuer_id}")
async def get_issuer_scores(
    issuer_id: int,
    limit: int = Query(100, le=1000, description="Maximum number of scores to return"),
    db: Session = Depends(get_db)
):
    """
    Get historical scores for a specific issuer.
    """
    try:
        # Verify issuer exists
        issuer = db.query(Issuer).filter(Issuer.id == issuer_id).first()
        if not issuer:
            raise HTTPException(status_code=404, detail="Issuer not found")
        
        # Get scores
        scores = db.query(Score).filter(
            Score.issuer_id == issuer_id
        ).order_by(Score.ts.desc()).limit(limit).all()
        
        return {
            "issuer_id": issuer_id,
            "issuer_name": issuer.name,
            "scores": [score.to_dict() for score in scores],
            "total": len(scores)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get issuer scores", error=str(e), issuer_id=issuer_id)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/scores/buckets")
async def get_score_buckets(db: Session = Depends(get_db)):
    """
    Get score distribution by rating buckets.
    """
    try:
        # Get latest scores and group by bucket
        latest_scores = db.query(Score.bucket, func.count(Score.id)).join(
            db.query(Score.issuer_id, func.max(Score.ts).label('max_ts')).group_by(Score.issuer_id).subquery()
        ).filter(
            Score.ts == func.max(Score.ts)
        ).group_by(Score.bucket).all()
        
        buckets = {}
        for bucket, count in latest_scores:
            if bucket:
                buckets[bucket] = count
        
        return {
            "buckets": buckets,
            "total_issuers": sum(buckets.values())
        }
    except Exception as e:
        logger.error("Failed to get score buckets", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/scores/sector/{sector}")
async def get_sector_scores(
    sector: str,
    db: Session = Depends(get_db)
):
    """
    Get latest scores for all issuers in a specific sector.
    """
    try:
        # Get latest scores for sector
        latest_scores = db.query(Score).join(Issuer).filter(
            Issuer.sector == sector,
            Score.ts == db.query(func.max(Score.ts)).filter(
                Score.issuer_id == Issuer.id
            ).scalar_subquery()
        ).all()
        
        return {
            "sector": sector,
            "scores": [score.to_dict() for score in latest_scores],
            "total": len(latest_scores)
        }
    except Exception as e:
        logger.error("Failed to get sector scores", error=str(e), sector=sector)
        raise HTTPException(status_code=500, detail="Internal server error")





