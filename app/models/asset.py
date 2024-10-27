# app/models/asset.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.base import Base

class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True, index=True)
    display_name = Column(String(255), index=True)
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Use string references for relationships to prevent dependency issues
    owner = relationship("User", back_populates="owned_assets")
    metadata_histories = relationship("MetadataHistory", back_populates="asset")
    claim_requests = relationship("ClaimRequest", back_populates="asset")
