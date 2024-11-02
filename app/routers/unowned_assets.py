# app/routers/unowned_assets.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Settings
import requests
import logging

router = APIRouter(
    prefix="/unowned-assets",
    tags=["unowned-assets"]
)

OPENMETADATA_API_URL = "http://localhost:8585/api/v1"
logger = logging.getLogger(__name__)

# Dynamic type mapping for assets
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
    settings = db.query(Settings).first()
    if settings and settings.openmetadata_token:
        return settings.openmetadata_token
    logger.error("OpenMetadata API token not found in the database.")
    raise HTTPException(status_code=500, detail="OpenMetadata API token is not configured in the database")

def get_headers(db: Session):
    token = get_openmetadata_token(db)
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Fetch unowned assets with additional data like fullyQualifiedName
@router.get("/")
def fetch_unowned_assets(db: Session = Depends(get_db)):
    headers = get_headers(db)
    unowned_assets = []
    try:
        for asset_type, endpoint in asset_type_map.items():
            response = requests.get(
                f"{OPENMETADATA_API_URL}/{endpoint}?fields=owners,fullyQualifiedName&limit=1000000", headers=headers
            )
            if response.status_code != 200:
                logger.error(f"Failed to fetch {asset_type}: {response.text}")
                raise HTTPException(status_code=500, detail=f"Error fetching {asset_type} from OpenMetadata")

            assets = [
                {
                    "id": item["id"],
                    "displayName": item.get("displayName", item["name"]),
                    "updatedAt": item["updatedAt"],
                    "dataType": asset_type,
                    "fullyQualifiedName": item.get("fullyQualifiedName")  # Add fullyQualifiedName field
                }
                for item in response.json().get("data", [])
                if not item.get("owners")
            ]
            unowned_assets.extend(assets)

        logger.info(f"Successfully fetched {len(unowned_assets)} unowned assets with fullyQualifiedName.")
        return unowned_assets

    except requests.RequestException as e:
        logger.error(f"Error communicating with OpenMetadata API: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to communicate with OpenMetadata API")
