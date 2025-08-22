from sqlalchemy import Column, Integer, Float, DateTime, Text, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from services.db import Base


class Score(Base):
    __tablename__ = "score"
    
    id = Column(Integer, primary_key=True, index=True)
    issuer_id = Column(Integer, ForeignKey("issuer.id"), nullable=False)
    ts = Column(DateTime, nullable=False, server_default=func.now())
    
    # Score components
    score = Column(Float, nullable=False)
    bucket = Column(String(10), nullable=False)
    base = Column(Float)
    market = Column(Float)
    event_delta = Column(Float)
    macro_adj = Column(Float)
    model_version = Column(String(50))
    explanation = Column(Text)
    
    # Relationships
    issuer = relationship("Issuer", back_populates="scores")
