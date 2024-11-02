from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import bcrypt
from app.models.base import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    # Column definitions
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    team = Column(String(100))
    team_id = Column(String(255))  # New field to store the OpenMetadata team ID
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    owned_assets = relationship("Asset", back_populates="owner")
    metadata_histories = relationship("MetadataHistory", back_populates="updated_by")

    # Password hashing utility method
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generate a bcrypt hash for a given password."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
