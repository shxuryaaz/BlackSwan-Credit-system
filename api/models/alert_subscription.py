from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from services.db import Base

class AlertSubscription(Base):
    __tablename__ = "alert_subscription"
    
    id = Column(Integer, primary_key=True, index=True)
    issuer_id = Column(Integer, ForeignKey("issuer.id"), nullable=False, index=True)
    email = Column(Text)
    webhook_url = Column(Text)
    threshold = Column(Float, default=5.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    issuer = relationship("Issuer", back_populates="alert_subscriptions")
    
    def __repr__(self):
        return f"<AlertSubscription(id={self.id}, issuer_id={self.issuer_id}, threshold={self.threshold})>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "issuer_id": self.issuer_id,
            "email": self.email,
            "webhook_url": self.webhook_url,
            "threshold": self.threshold,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }





