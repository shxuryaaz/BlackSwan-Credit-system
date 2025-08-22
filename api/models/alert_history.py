from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from services.db import Base

class AlertHistory(Base):
    __tablename__ = "alert_history"
    
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("alert_subscription.id"), nullable=False, index=True)
    issuer_id = Column(Integer, ForeignKey("issuer.id"), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)
    message = Column(Text)
    score_change = Column(Float)
    triggered_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<AlertHistory(id={self.id}, issuer_id={self.issuer_id}, alert_type='{self.alert_type}')>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "subscription_id": self.subscription_id,
            "issuer_id": self.issuer_id,
            "alert_type": self.alert_type,
            "message": self.message,
            "score_change": self.score_change,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None
        }





