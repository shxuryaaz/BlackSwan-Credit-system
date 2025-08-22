from sqlalchemy import Column, Integer, String, DateTime, Float, Text
from sqlalchemy.sql import func
from services.db import Base

class Macro(Base):
    __tablename__ = "macro"
    
    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    key = Column(Text, nullable=False, index=True)
    value = Column(Float)
    source = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<Macro(id={self.id}, key='{self.key}', value={self.value}, ts='{self.ts}')>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "ts": self.ts.isoformat() if self.ts else None,
            "key": self.key,
            "value": self.value,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }





