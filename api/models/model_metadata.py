from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.sql import func
from services.db import Base

class ModelMetadata(Base):
    __tablename__ = "model_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    model_version = Column(String(50), unique=True, nullable=False)
    model_type = Column(String(50), nullable=False)
    training_date = Column(DateTime(timezone=True))
    performance_metrics = Column(JSON)
    feature_importance = Column(JSON)
    hyperparameters = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<ModelMetadata(id={self.id}, model_version='{self.model_version}', model_type='{self.model_type}')>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "model_version": self.model_version,
            "model_type": self.model_type,
            "training_date": self.training_date.isoformat() if self.training_date else None,
            "performance_metrics": self.performance_metrics,
            "feature_importance": self.feature_importance,
            "hyperparameters": self.hyperparameters,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }





