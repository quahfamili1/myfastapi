# app/models/metadata_history.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.base import Base

class MetadataHistory(Base):
    __tablename__ = "metadata_histories"
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    description = Column(Text)
    suggestion_type = Column(String(50))  # e.g., "LLM_generated", "manual_update"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_by_id = Column(Integer, ForeignKey("users.id"))

    # Use string references for relationships
    asset = relationship("Asset", back_populates="metadata_histories")
    updated_by = relationship("User", back_populates="metadata_histories")
