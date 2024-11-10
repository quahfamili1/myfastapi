# app/routers/assets.py

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Path
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models import User
from app.utils import get_current_user
from app.utils import get_headers
from app.asset_handlers import asset_handler_registry
import logging
import requests

router = APIRouter(
    prefix="/assets",
    tags=["Assets Management"],
    responses={404: {"description": "Not found"}},
)

OPENMETADATA_API_URL = "http://localhost:8585/api/v1"  # Adjust as necessary
logger = logging.getLogger(__name__)

class AssetUpdateModel(BaseModel):
    displayName: Optional[str] = None
    description: Optional[str] = None

class AssetClaimModel(BaseModel):
    claim: bool = True  # Default to True to initiate claim process

class AssetDataModel(BaseModel):
    title: str
    description: Optional[str]
    attributes: List[str]
    att_desc: List[str]
    # Additional fields for parent entities
    databaseServiceName: Optional[str] = None
    serviceType: Optional[str] = None
    databaseName: Optional[str] = None
    databaseSchemaName: Optional[str] = None

@router.post("/upload_assets", summary="Upload assets from data", description="Create assets in OpenMetadata based on uploaded data.")
async def upload_assets(
    assets: List[AssetDataModel],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.debug(f"Assets received: {assets}")

    created_assets = []
    errors = []

    for asset in assets:
        try:
            # Ensure that attributes and att_desc are not empty
            if not asset.attributes:
                logger.warning(f"No attributes provided for asset '{asset.title}'.")
            if not asset.att_desc:
                logger.warning(f"No attribute descriptions provided for asset '{asset.title}'.")

            # Prepare asset data
            asset_data = asset.dict()

            # Set default parent entities if not provided
            asset_data.setdefault('service_name', 'default_service')
            asset_data.setdefault('database_name', 'default_database')
            asset_data.setdefault('schema_name', 'default_schema')

            # Initialize the asset handler
            handler_class = asset_handler_registry["tables"]
            handler = handler_class(db=db, asset_data=asset_data, current_user=current_user)

            # Process the asset creation or update
            result = handler.handle()

            if result.get('success'):
                created_assets.extend(result.get('created_assets', []))
                logger.info(f"Asset '{asset.title}' created or updated successfully.")
            else:
                errors.extend(result.get('errors', []))
                logger.error(f"Failed to create or update asset '{asset.title}': {result['errors']}")

        except Exception as e:
            error_msg = f"Error creating asset '{asset.title}': {str(e)}"
            errors.append(error_msg)
            logger.exception(error_msg)

    return {
        "success": not bool(errors),
        "created_assets": created_assets,
        "errors": errors
    }

@router.post("/{type}", summary="Create a new asset", description="Create a new asset in OpenMetadata of the specified type.")
def create_asset(
    type: str,
    asset_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create an asset of the specified type in OpenMetadata."""
    if type not in asset_handler_registry:
        logger.warning(f"Unsupported asset type provided: {type}")
        raise HTTPException(status_code=400, detail="Unsupported asset type")

    handler_class = asset_handler_registry[type]
    handler = handler_class(db=db, asset_data=asset_data, current_user=current_user)
    result = handler.handle()

    if result['success']:
        return {"success": True, "message": f"Asset of type '{type}' created successfully."}
    else:
        return {"success": False, "errors": result['errors']}

@router.get("/{type}/{asset_id}", summary="Retrieve an asset by ID", description="Retrieve an asset by its ID and type.")
def get_asset_by_id(type: str, asset_id: str, db: Session = Depends(get_db)):
    """Retrieve an asset by its ID and type."""
    if type not in asset_handler_registry:
        raise HTTPException(status_code=400, detail="Unsupported asset type")

    headers = get_headers(db)
    url = f"{OPENMETADATA_API_URL}/{type}/{asset_id}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching asset by ID {asset_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to communicate with OpenMetadata API")

@router.patch("/{type}/{asset_id}", summary="Update asset details", description="Partially update asset details in OpenMetadata.")
def update_asset(
    type: str,
    asset_id: str,
    asset_data: AssetUpdateModel = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an asset's data in OpenMetadata."""
    if type not in asset_handler_registry:
        raise HTTPException(status_code=400, detail="Unsupported asset type")

    handler_class = asset_handler_registry[type]
    handler = handler_class(db=db, asset_data=asset_data.dict(exclude_unset=True), current_user=current_user)
    result = handler.update_asset(asset_id)

    if result['success']:
        return {"success": True, "message": f"Asset '{asset_id}' updated successfully"}
    else:
        raise HTTPException(status_code=500, detail=result['errors'])

@router.delete("/{type}/{asset_id}", summary="Delete an asset", description="Delete an asset by ID if the current user's team owns it.")
def delete_asset(
    type: str,
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an asset by ID if the current user's team owns it."""
    if type not in asset_handler_registry:
        raise HTTPException(status_code=400, detail="Unsupported asset type")

    handler_class = asset_handler_registry[type]
    handler = handler_class(db=db, current_user=current_user)
    result = handler.delete_asset(asset_id)

    if result['success']:
        return {"success": True, "message": "Asset deleted successfully"}
    else:
        raise HTTPException(status_code=500, detail=result['errors'])

# ClaimAsset Endpoint
@router.post("/{type}/{asset_id}/claim", summary="Claim ownership of an asset", description="Allow a logged-in user to claim ownership of an asset.")
def claim_asset_ownership(
    type: str,
    asset_id: str,
    asset_claim: AssetClaimModel = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Allow a logged-in user to claim ownership of an asset if it is unowned."""
    if type not in asset_handler_registry:
        raise HTTPException(status_code=400, detail="Unsupported asset type")

    handler_class = asset_handler_registry[type]
    handler = handler_class(db=db, asset_data={}, current_user=current_user)
    result = handler.claim_asset(asset_id)

    if result['success']:
        return {"success": True, "message": f"Asset {asset_id} claimed successfully"}
    else:
        raise HTTPException(status_code=500, detail=result['errors'])
