# app/routers/unowned_assets.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Settings
import requests
import logging

router = APIRouter(
    prefix="/unowned-assets",
    tags=["Unowned Assets"],
    responses={404: {"description": "Not found"}},
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

@router.get("/", summary="Fetch all unowned assets", description="Retrieve a list of all assets that currently have no owner in OpenMetadata.")
def fetch_unowned_assets(db: Session = Depends(get_db)):
    """Fetch unowned assets for each specified asset type in OpenMetadata."""
    headers = get_headers(db)
    unowned_assets = []

    try:
        for asset_type, endpoint in asset_type_map.items():
            url = f"{OPENMETADATA_API_URL}/{endpoint}?fields=owners,fullyQualifiedName,displayName,updatedAt&limit=1000000"
            logger.info(f"Fetching unowned assets of type {asset_type} from {url}")
            
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch unowned assets for type {asset_type}: {response.text}")
                continue
            
            # Collect assets that have no owner
            assets = [
                {
                    "id": item["id"],
                    "displayName": item.get("displayName", item["name"]),
                    "updatedAt": item["updatedAt"],
                    "dataType": asset_type,
                    "fullyQualifiedName": item["fullyQualifiedName"]
                }
                for item in response.json().get("data", [])
                if not item.get("owners")
            ]
            unowned_assets.extend(assets)

        if not unowned_assets:
            logger.info("No unowned assets found across all asset types.")
        else:
            logger.info(f"Successfully fetched {len(unowned_assets)} unowned assets.")

        return unowned_assets

    except requests.RequestException as e:
        logger.error(f"Error communicating with OpenMetadata API: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to communicate with OpenMetadata API")
