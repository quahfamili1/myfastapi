# app/routers/temporary_assets.py
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import TemporaryAsset
import logging
import json

router = APIRouter(
    prefix="/temporary-assets",
    tags=["temporary-assets"]
)

logger = logging.getLogger(__name__)

@router.post("/")
async def create_temporary_asset(
    data: dict = Body(...), db: Session = Depends(get_db)
):
    """
    Create a temporary asset in the database based on the provided data.
    Data format includes title, description, and attributes, with case-insensitive field handling.
    """
    # Normalize all keys to lowercase for case-insensitive handling
    normalized_data = {key.lower(): value for key, value in data.items()}
    logger.info(f"Received normalized data for temporary asset creation: {normalized_data}")

    try:
        # Handle attributes as JSON if it's a list or dictionary
        attributes = normalized_data.get("attributes")
        if isinstance(attributes, (list, dict)):
            attributes = json.dumps(attributes)  # Convert to JSON string if necessary
        
        # Create the TemporaryAsset record in the database
        new_asset = TemporaryAsset(
            title=normalized_data.get("title"),
            description=normalized_data.get("description"),
            attributes=attributes
        )

        db.add(new_asset)
        db.commit()
        db.refresh(new_asset)

        return {"success": True, "asset_id": new_asset.id}

    except Exception as e:
        logger.error(f"Error creating temporary asset: {e}")
        raise HTTPException(status_code=500, detail="Failed to create temporary asset")
