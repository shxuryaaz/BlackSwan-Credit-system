from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from services.db import Base

class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshot"
    
    id = Column(Integer, primary_key=True, index=True)
    issuer_id = Column(Integer, ForeignKey("issuer.id"), nullable=False, index=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    feature_name = Column(Text, nullable=False, index=True)
    value = Column(Float)
    source = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    issuer = relationship("Issuer", back_populates="feature_snapshots")
    
    def __repr__(self):
        return f"<FeatureSnapshot(id={self.id}, issuer_id={self.issuer_id}, feature='{self.feature_name}', value={self.value})>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "issuer_id": self.issuer_id,
            "ts": self.ts.isoformat() if self.ts else None,
            "feature_name": self.feature_name,
            "value": self.value,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }





