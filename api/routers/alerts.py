from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import structlog
from pydantic import BaseModel, Field

from services.db import get_db
from models.alert_subscription import AlertSubscription
from models.alert_history import AlertHistory
from models.issuer import Issuer

logger = structlog.get_logger()
router = APIRouter()

class AlertSubscriptionRequest(BaseModel):
    issuer_id: int = Field(..., description="Issuer ID to subscribe to")
    email: Optional[str] = Field(None, description="Email for alerts")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for alerts")
    threshold: float = Field(5.0, ge=0.0, description="Score change threshold for alerts")

class AlertSubscriptionResponse(BaseModel):
    subscription_id: int
    status: str
    message: str

@router.post("/alerts/subscribe", response_model=AlertSubscriptionResponse)
async def subscribe_to_alerts(
    subscription: AlertSubscriptionRequest,
    db: Session = Depends(get_db)
):
    """
    Subscribe to alerts for an issuer.
    
    Requires either email or webhook_url to be provided.
    """
    try:
        # Verify issuer exists
        issuer = db.query(Issuer).filter(Issuer.id == subscription.issuer_id).first()
        if not issuer:
            raise HTTPException(status_code=404, detail="Issuer not found")
        
        # Validate that at least one notification method is provided
        if not subscription.email and not subscription.webhook_url:
            raise HTTPException(
                status_code=400, 
                detail="Either email or webhook_url must be provided"
            )
        
        # Check if subscription already exists
        existing = db.query(AlertSubscription).filter(
            AlertSubscription.issuer_id == subscription.issuer_id,
            AlertSubscription.email == subscription.email,
            AlertSubscription.webhook_url == subscription.webhook_url
        ).first()
        
        if existing:
            # Update existing subscription
            existing.threshold = subscription.threshold
            existing.is_active = True
            db.commit()
            
            return AlertSubscriptionResponse(
                subscription_id=existing.id,
                status="updated",
                message=f"Updated existing alert subscription for {issuer.name}"
            )
        
        # Create new subscription
        new_subscription = AlertSubscription(
            issuer_id=subscription.issuer_id,
            email=subscription.email,
            webhook_url=subscription.webhook_url,
            threshold=subscription.threshold
        )
        
        db.add(new_subscription)
        db.commit()
        db.refresh(new_subscription)
        
        return AlertSubscriptionResponse(
            subscription_id=new_subscription.id,
            status="created",
            message=f"Created alert subscription for {issuer.name}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create alert subscription", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/alerts/subscriptions")
async def list_alert_subscriptions(
    issuer_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    List alert subscriptions.
    """
    try:
        query = db.query(AlertSubscription).join(Issuer)
        
        if issuer_id:
            query = query.filter(AlertSubscription.issuer_id == issuer_id)
        
        subscriptions = query.all()
        
        return {
            "subscriptions": [
                {
                    "id": sub.id,
                    "issuer_id": sub.issuer_id,
                    "issuer_name": sub.issuer.name,
                    "email": sub.email,
                    "webhook_url": sub.webhook_url,
                    "threshold": sub.threshold,
                    "is_active": sub.is_active,
                    "created_at": sub.created_at.isoformat() if sub.created_at else None
                }
                for sub in subscriptions
            ],
            "total": len(subscriptions)
        }
    except Exception as e:
        logger.error("Failed to list alert subscriptions", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/alerts/subscription/{subscription_id}")
async def delete_alert_subscription(
    subscription_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete an alert subscription.
    """
    try:
        subscription = db.query(AlertSubscription).filter(
            AlertSubscription.id == subscription_id
        ).first()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        db.delete(subscription)
        db.commit()
        
        return {
            "status": "deleted",
            "message": f"Deleted alert subscription {subscription_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete alert subscription", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/alerts/history")
async def get_alert_history(
    issuer_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get alert history.
    """
    try:
        query = db.query(AlertHistory).join(Issuer)
        
        if issuer_id:
            query = query.filter(AlertHistory.issuer_id == issuer_id)
        
        alerts = query.order_by(AlertHistory.triggered_at.desc()).limit(limit).all()
        
        return {
            "alerts": [
                {
                    "id": alert.id,
                    "issuer_id": alert.issuer_id,
                    "issuer_name": alert.issuer.name,
                    "alert_type": alert.alert_type,
                    "message": alert.message,
                    "score_change": alert.score_change,
                    "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None
                }
                for alert in alerts
            ],
            "total": len(alerts)
        }
    except Exception as e:
        logger.error("Failed to get alert history", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/alerts/test")
async def test_alert(
    issuer_id: int = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Test alert functionality for an issuer.
    """
    try:
        # Verify issuer exists
        issuer = db.query(Issuer).filter(Issuer.id == issuer_id).first()
        if not issuer:
            raise HTTPException(status_code=404, detail="Issuer not found")
        
        # Get subscriptions for this issuer
        subscriptions = db.query(AlertSubscription).filter(
            AlertSubscription.issuer_id == issuer_id,
            AlertSubscription.is_active == True
        ).all()
        
        if not subscriptions:
            return {
                "status": "no_subscriptions",
                "message": f"No active alert subscriptions found for {issuer.name}"
            }
        
        # Create test alert
        test_alert = AlertHistory(
            subscription_id=subscriptions[0].id,
            issuer_id=issuer_id,
            alert_type="test",
            message="This is a test alert",
            score_change=0.0
        )
        
        db.add(test_alert)
        db.commit()
        
        return {
            "status": "test_sent",
            "message": f"Test alert sent for {issuer.name}",
            "subscriptions_count": len(subscriptions)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to send test alert", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")





