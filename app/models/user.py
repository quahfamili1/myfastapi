# app/models/user.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import bcrypt
from app.base import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    password_hash = Column(String(255))
    role = Column(String(50))
    team = Column(String(100))  # Add a column for team
    created_at = Column(DateTime, default=datetime.utcnow)

    # Use string references for relationships
    owned_assets = relationship("Asset", back_populates="owner")
    metadata_histories = relationship("MetadataHistory", back_populates="updated_by")

    @staticmethod
    def get_password_hash(password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
