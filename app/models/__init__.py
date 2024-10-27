# app/models/__init__.py
from app.base import Base
from app.models.user import User
from app.models.asset import Asset
from app.models.metadata_history import MetadataHistory
from app.models.claim_request import ClaimRequest  # Import ClaimRequest here

__all__ = ["Base", "User", "Asset", "MetadataHistory", "ClaimRequest"]
