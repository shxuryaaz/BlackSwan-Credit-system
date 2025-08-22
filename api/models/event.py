from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from services.db import Base

class Event(Base):
    __tablename__ = "event"
    
    id = Column(Integer, primary_key=True, index=True)
    issuer_id = Column(Integer, ForeignKey("issuer.id"), nullable=False, index=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)
    sentiment = Column(Float)
    weight = Column(Float)
    headline = Column(Text)
    url = Column(Text)
    raw_hash = Column(String(64), unique=True, index=True)
    decay_factor = Column(Float, default=1.0)
    source = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    issuer = relationship("Issuer", back_populates="events")
    
    def __repr__(self):
        return f"<Event(id={self.id}, issuer_id={self.issuer_id}, type='{self.type}', sentiment={self.sentiment})>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "issuer_id": self.issuer_id,
            "ts": self.ts.isoformat() if self.ts else None,
            "type": self.type,
            "sentiment": self.sentiment,
            "weight": self.weight,
            "headline": self.headline,
            "url": self.url,
            "raw_hash": self.raw_hash,
            "decay_factor": self.decay_factor,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @property
    def effective_weight(self):
        """Get effective weight considering decay factor"""
        return self.weight * self.decay_factor if self.weight and self.decay_factor else 0.0
    
    @property
    def impact_description(self):
        """Get human-readable impact description"""
        if not self.weight:
            return "No impact"
        
        impact = abs(self.effective_weight)
        direction = "negative" if self.weight < 0 else "positive"
        
        if impact >= 5.0:
            severity = "major"
        elif impact >= 2.0:
            severity = "moderate"
        else:
            severity = "minor"
        
        return f"{severity} {direction} impact"





