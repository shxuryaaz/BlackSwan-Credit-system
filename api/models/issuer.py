from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from services.db import Base


class Issuer(Base):
    __tablename__ = "issuer"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), unique=True, index=True, nullable=True)
    name = Column(Text, nullable=False)
    cik = Column(String(20), index=True)
    sector = Column(String(100))
    country = Column(String(100), default='US')
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    scores = relationship("Score", back_populates="issuer")
    prices = relationship("Price", back_populates="issuer")
    feature_snapshots = relationship("FeatureSnapshot", back_populates="issuer")
    events = relationship("Event", back_populates="issuer")
    alert_subscriptions = relationship("AlertSubscription", back_populates="issuer")
