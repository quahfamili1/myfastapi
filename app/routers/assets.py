from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Settings, User
from app.utils import get_current_user
import requests
import logging

router = APIRouter(
    prefix="/assets",
    tags=["assets"]
)

OPENMETADATA_API_URL = "http://localhost:8585/api/v1"
logger = logging.getLogger(__name__)

# Mapping for asset types in OpenMetadata
asset_type_map = {
    "searchIndexes": "searchIndexes",
    "tables": "tables",
    "dashboards": "dashboards",
    "storedProcedures": "storedProcedures",
    "docStore": "docStore",
    "dataProducts": "dataProducts",
    "mlmodels": "mlmodels",
    "pipelines": "pipelines",
    "containers": "containers",
    "topics": "topics"
}

def get_openmetadata_token(db: Session):
    """Retrieve OpenMetadata token from the database settings."""
    settings = db.query(Settings).first()
    if settings and settings.openmetadata_token:
        return settings.openmetadata_token
    logger.error("OpenMetadata API token not found in the database.")
    raise HTTPException(status_code=500, detail="OpenMetadata API token is not configured in the database")

def get_headers(db: Session):
    """Generate headers for OpenMetadata API requests."""
    token = get_openmetadata_token(db)
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

@router.post("/{type}", summary="Create a new asset", description="Create a new asset in OpenMetadata.")
def create_asset(type: str, asset_data: dict = Body(...), db: Session = Depends(get_db)):
    """Create an asset of the specified type in OpenMetadata."""
    if type not in asset_type_map:
        logger.warning(f"Unsupported asset type provided: {type}")
        raise HTTPException(status_code=400, detail="Unsupported asset type")

    headers = get_headers(db)
    url = f"{OPENMETADATA_API_URL}/{asset_type_map[type]}"
    logger.debug(f"Creating asset of type {type} at {url}")

    try:
        response = requests.post(url, json=asset_data, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error creating asset: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to communicate with OpenMetadata API")

@router.get("/{type}/{asset_id}", summary="Retrieve an asset by ID", description="Retrieve an asset by its ID and type.")
def get_asset_by_id(type: str, asset_id: str, db: Session = Depends(get_db)):
    """Retrieve an asset by its ID and type."""
    if type not in asset_type_map:
        logger.warning(f"Unsupported asset type provided: {type}")
        raise HTTPException(status_code=400, detail="Unsupported asset type")

    headers = get_headers(db)
    url = f"{OPENMETADATA_API_URL}/{asset_type_map[type]}/{asset_id}"
    logger.debug(f"Fetching asset of type {type} with ID {asset_id} from {url}")

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching asset by ID: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to communicate with OpenMetadata API")

@router.patch("/{type}/{asset_id}", summary="Update asset details", description="Partially update asset details in OpenMetadata.")
def update_asset(
    type: str,
    asset_id: str,
    asset_data: dict = Body(..., example={"name": "Updated Name", "description": "Updated Description"}),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an asset's data and optionally its ownership in OpenMetadata."""
    if type not in asset_type_map:
        logger.warning(f"Unsupported asset type provided: {type}")
        raise HTTPException(status_code=400, detail="Unsupported asset type")

    headers = get_headers(db)
    headers["Content-Type"] = "application/json-patch+json"
    payload = []

    if "owners" in asset_data:
        payload.append({
            "op": "replace",
            "path": "/owners",
            "value": [
                {
                    "type": "team",
                    "id": current_user.team_id,
                    "name": current_user.team
                }
            ]
        })

    for key, value in asset_data.items():
        if key != "owners":
            payload.append({
                "op": "replace",
                "path": f"/{key}",
                "value": value
            })

    if not payload:
        logger.warning("No valid attributes provided for update")
        raise HTTPException(status_code=400, detail="No valid attributes provided for update")

    url = f"{OPENMETADATA_API_URL}/{asset_type_map[type]}/{asset_id}"
    logger.debug(f"Updating asset at {url} with payload {payload}")

    try:
        response = requests.patch(url, json=payload, headers=headers)
        response.raise_for_status()
        return {"success": True}
    except requests.RequestException as e:
        logger.error(f"Error updating asset: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to communicate with OpenMetadata API")

@router.delete("/{type}/{asset_id}", summary="Delete an asset", description="Delete an asset by ID if the current user's team owns it.")
def delete_asset(
    type: str, 
    asset_id: str, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Delete an asset by ID if the current user's team owns it."""
    if type not in asset_type_map:
        logger.warning(f"Unsupported asset type provided: {type}")
        raise HTTPException(status_code=400, detail="Unsupported asset type")

    headers = get_headers(db)
    asset_url = f"{OPENMETADATA_API_URL}/{asset_type_map[type]}/{asset_id}"
    logger.debug(f"Fetching asset for deletion check at {asset_url}")

    try:
        response = requests.get(asset_url, headers=headers)
        response.raise_for_status()

        asset_data = response.json()
        asset_owners = asset_data.get("owners", [])
        team_owner_id = current_user.team_id

        if not any(owner.get("id") == team_owner_id for owner in asset_owners):
            logger.warning(f"User {current_user.id} does not have permission to delete asset {asset_id}")
            raise HTTPException(status_code=403, detail="You do not have permission to delete this asset")

        logger.debug(f"Deleting asset with ID {asset_id}")
        delete_response = requests.delete(asset_url, headers=headers)
        delete_response.raise_for_status()

        return {"success": True, "message": "Asset deleted successfully"}
    except requests.RequestException as e:
        logger.error(f"Error deleting asset: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to communicate with OpenMetadata API")
