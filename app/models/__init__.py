# app/models/__init__.py

# Import Base from models/base.py to avoid circular imports
from app.models.base import Base

# Import each model
from app.models.user import User
from app.models.asset import Asset
from app.models.metadata_history import MetadataHistory
from app.models.settings import Settings  # Ensure Settings is imported
from .temporary_asset import TemporaryAsset

# Specify all models in __all__ for easier imports elsewhere
__all__ = ["Base", "User", "Asset", "MetadataHistory", "Settings", "TemporaryAsset"]
