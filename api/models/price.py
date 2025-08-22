from sqlalchemy import Column, Integer, String, DateTime, Float, BigInteger, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from services.db import Base

class Price(Base):
    __tablename__ = "price"
    
    id = Column(Integer, primary_key=True, index=True)
    issuer_id = Column(Integer, ForeignKey("issuer.id"), nullable=False, index=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    open = Column(Numeric(10, 4))
    high = Column(Numeric(10, 4))
    low = Column(Numeric(10, 4))
    close = Column(Numeric(10, 4))
    volume = Column(BigInteger)
    adj_close = Column(Numeric(10, 4))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    issuer = relationship("Issuer", back_populates="prices")
    
    def __repr__(self):
        return f"<Price(id={self.id}, issuer_id={self.issuer_id}, close={self.close}, ts='{self.ts}')>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "issuer_id": self.issuer_id,
            "ts": self.ts.isoformat() if self.ts else None,
            "open": float(self.open) if self.open else None,
            "high": float(self.high) if self.high else None,
            "low": float(self.low) if self.low else None,
            "close": float(self.close) if self.close else None,
            "volume": self.volume,
            "adj_close": float(self.adj_close) if self.adj_close else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }





