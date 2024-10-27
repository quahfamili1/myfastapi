# app/models/claim_request.py
from sqlalchemy import Column, Integer, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from datetime import datetime
from app.base import Base

class ClaimRequest(Base):
    __tablename__ = "claim_requests"
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    requested_by_id = Column(Integer, ForeignKey("users.id"))
    requested_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="pending")  # e.g., "pending", "approved", "rejected"

    # Use string references for relationships
    asset = relationship("Asset", back_populates="claim_requests")
    requested_by = relationship("User")
