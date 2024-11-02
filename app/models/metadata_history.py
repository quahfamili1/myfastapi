# app/models/metadata_history.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base

class MetadataHistory(Base):
    __tablename__ = "metadata_histories"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(String(255), ForeignKey("assets.id"), nullable=False)  # Reference to Asset
    description = Column(Text)
    suggestion_type = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_by_id = Column(Integer, ForeignKey("users.id"))

    # Relationships
    asset = relationship("Asset", back_populates="metadata_histories")
    updated_by = relationship("User", back_populates="metadata_histories")
