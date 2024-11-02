# app/models/asset.py
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base

class Asset(Base):
    __tablename__ = "assets"
    
    id = Column(String(255), primary_key=True, index=True)
    display_name = Column(String(255), index=True)
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)
    type = Column(String(50))
    owner_team = Column(String(255))
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    owner = relationship("User", back_populates="owned_assets")
    metadata_histories = relationship("MetadataHistory", back_populates="asset")

    def to_dict(self):
        return {
            "id": self.id,
            "display_name": self.display_name,
            "description": self.description,
            "updated_at": self.updated_at,
            "type": self.type,
            "owner_team": self.owner_team,
            "owner_id": self.owner_id,
        }
