# app/models/temporary_asset.py
from sqlalchemy import Column, String, Integer
from app.models.base import Base  # Import Base from base.py

class TemporaryAsset(Base):
    __tablename__ = "temporary_assets"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True)  # Specify a length for VARCHAR
    description = Column(String(8000))       # Specify a length for VARCHAR
    attributes = Column(String(8000))        # Define length as per your requirements
