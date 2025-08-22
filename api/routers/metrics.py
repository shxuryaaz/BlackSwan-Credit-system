from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, func
from typing import List, Dict, Any
from services.db import get_db

router = APIRouter()

@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Get dashboard metrics and analytics"""
    try:
        # Get total issuers
        result = await db.execute(text("SELECT COUNT(*) FROM issuer"))
        total_issuers = result.scalar_one()

        # Get last 2 scores per issuer to calculate deltas properly
        result = await db.execute(text("""
            WITH ranked_scores AS (
                SELECT 
                    issuer_id,
                    score,
                    bucket,
                    ts,
                    ROW_NUMBER() OVER (PARTITION BY issuer_id ORDER BY ts DESC) as rn
                FROM score
            )
            SELECT 
                current_scores.issuer_id,
                current_scores.score,
                current_scores.bucket,
                current_scores.ts,
                previous_scores.score as prev_score
            FROM (
                SELECT * FROM ranked_scores WHERE rn = 1
            ) current_scores
            LEFT JOIN (
                SELECT * FROM ranked_scores WHERE rn = 2
            ) previous_scores ON current_scores.issuer_id = previous_scores.issuer_id
            ORDER BY current_scores.issuer_id
        """))
        latest_scores = result.fetchall()

        # Calculate metrics
        improving = 0
        declining = 0
        alerts = 0
        total_score = 0
        valid_scores = 0

        for row in latest_scores:
            score = row.score
            prev_score = row.prev_score
            
            if score is not None:
                total_score += score
                valid_scores += 1
                
                if prev_score is not None:
                    delta = score - prev_score
                    if delta > 0:
                        improving += 1
                    elif delta < 0:
                        declining += 1
                    
                    # Alert if significant change (more than 5 points)
                    if abs(delta) >= 5:
                        alerts += 1

        avg_score = total_score / valid_scores if valid_scores > 0 else 0

        # Get sector distribution
        result = await db.execute(text("""
            SELECT i.sector, COUNT(*) as count
            FROM issuer i
            GROUP BY i.sector
            ORDER BY count DESC
        """))
        sector_distribution = [{"sector": row.sector, "count": row.count} for row in result.fetchall()]

        # Get score distribution (buckets)
        result = await db.execute(text("""
            SELECT s.bucket, COUNT(*) as count
            FROM score s
            INNER JOIN (
                SELECT issuer_id, MAX(ts) as max_ts
                FROM score
                GROUP BY issuer_id
            ) latest ON s.issuer_id = latest.issuer_id AND s.ts = latest.max_ts
            GROUP BY s.bucket
            ORDER BY s.bucket
        """))
        score_distribution = [{"bucket": row.bucket, "count": row.count} for row in result.fetchall()]

        return {
            "total_issuers": total_issuers,
            "improving": improving,
            "declining": declining,
            "alerts": alerts,
            "avg_score": round(avg_score, 1),
            "sector_distribution": sector_distribution,
            "score_distribution": score_distribution
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching metrics: {str(e)}")

@router.get("/metrics/sector/{sector}")
async def get_sector_metrics(sector: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Get metrics for a specific sector"""
    try:
        # Get issuers in sector
        result = await db.execute(text("""
            SELECT i.id, i.name, i.ticker, s.score, s.bucket, s.ts
            FROM issuer i
            LEFT JOIN (
                SELECT issuer_id, score, bucket, ts,
                       ROW_NUMBER() OVER (PARTITION BY issuer_id ORDER BY ts DESC) as rn
                FROM score
            ) s ON i.id = s.issuer_id AND s.rn = 1
            WHERE i.sector = :sector
        """), {"sector": sector})
        
        issuers = result.fetchall()
        
        if not issuers:
            raise HTTPException(status_code=404, detail=f"No issuers found in sector: {sector}")

        # Calculate sector metrics
        total_score = 0
        valid_scores = 0
        bucket_counts = {}
        
        for row in issuers:
            if row.score is not None:
                total_score += row.score
                valid_scores += 1
                
                bucket = row.bucket
                bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

        avg_score = total_score / valid_scores if valid_scores > 0 else 0

        return {
            "sector": sector,
            "total_issuers": len(issuers),
            "avg_score": round(avg_score, 1),
            "bucket_distribution": bucket_counts,
            "issuers": [
                {
                    "id": row.id,
                    "name": row.name,
                    "ticker": row.ticker,
                    "score": row.score,
                    "bucket": row.bucket
                }
                for row in issuers
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sector metrics: {str(e)}")

@router.get("/metrics/trends")
async def get_trends(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Get trend analysis for the last 7 days"""
    try:
        # Get daily average scores for the last 7 days
        result = await db.execute(text("""
            SELECT DATE(s.ts) as date, AVG(s.score) as avg_score, COUNT(*) as score_count
            FROM score s
            WHERE s.ts >= NOW() - INTERVAL '7 days'
            GROUP BY DATE(s.ts)
            ORDER BY date
        """))
        
        daily_trends = [
            {
                "date": row.date.strftime("%Y-%m-%d"),
                "avg_score": round(row.avg_score, 1),
                "score_count": row.score_count
            }
            for row in result.fetchall()
        ]

        # Get top movers (biggest changes in last 24h)
        result = await db.execute(text("""
            SELECT i.name, i.ticker, s.score, s.bucket,
                   s.score - LAG(s.score) OVER (PARTITION BY s.issuer_id ORDER BY s.ts) as delta
            FROM score s
            JOIN issuer i ON s.issuer_id = i.id
            WHERE s.ts >= NOW() - INTERVAL '24 hours'
            AND s.score IS NOT NULL
            ORDER BY ABS(delta) DESC
            LIMIT 10
        """))
        
        top_movers = [
            {
                "name": row.name,
                "ticker": row.ticker,
                "score": row.score,
                "bucket": row.bucket,
                "delta": round(row.delta, 1) if row.delta else 0
            }
            for row in result.fetchall()
        ]

        return {
            "daily_trends": daily_trends,
            "top_movers": top_movers
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching trends: {str(e)}")
