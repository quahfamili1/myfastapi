# app/models/settings.py
from sqlalchemy import Column, String
from app.models.base import Base  # Ensure this import is correct

class Settings(Base):
    __tablename__ = "settings"

    id = Column(String(36), primary_key=True, index=True)  # Specify length for MySQL
    openmetadata_token = Column(String(1024), nullable=True)  # Specify length for openmetadata_token
