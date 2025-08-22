from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.sql import func
from services.db import Base

class TaskStatus(Base):
    __tablename__ = "task_status"
    
    id = Column(Integer, primary_key=True, index=True)
    task_name = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)  # pending, running, completed, failed
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    task_metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<TaskStatus(id={self.id}, task_name='{self.task_name}', status='{self.status}')>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "task_name": self.task_name,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
