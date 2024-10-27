# app/models.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import bcrypt
from app.base import Base  # Absolute import for Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}  # Allows SQLAlchemy to extend an existing table without errors

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    password_hash = Column(String(255))
    role = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    owned_assets = relationship("Asset", back_populates="owner")
    metadata_histories = relationship("MetadataHistory", back_populates="updated_by")

    @staticmethod
    def get_password_hash(password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    display_name = Column(String(255), index=True)
    description = Column(Text)  # LLM-generated or user-updated description
    updated_at = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    owner = relationship("User", back_populates="owned_assets")
    metadata_histories = relationship("MetadataHistory", back_populates="asset")
    claim_requests = relationship("ClaimRequest", back_populates="asset")

class MetadataHistory(Base):
    __tablename__ = "metadata_histories"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    description = Column(Text)
    suggestion_type = Column(String(50))  # e.g., "LLM_generated", "manual_update"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_by_id = Column(Integer, ForeignKey("users.id"))

    # Relationships
    asset = relationship("Asset", back_populates="metadata_histories")
    updated_by = relationship("User", back_populates="metadata_histories")

class AdminSettings(Base):
    __tablename__ = "admin_settings"

    id = Column(Integer, primary_key=True, index=True)
    setting_name = Column(String(255), unique=True, index=True)  # e.g., "api_token"
    setting_value = Column(Text)

class ClaimRequest(Base):
    __tablename__ = "claim_requests"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    requested_by_id = Column(Integer, ForeignKey("users.id"))
    requested_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="pending")  # e.g., "pending", "approved", "rejected"

    # Relationships
    asset = relationship("Asset", back_populates="claim_requests")
    requested_by = relationship("User")

from sqlalchemy import Column, String, Integer
from database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
