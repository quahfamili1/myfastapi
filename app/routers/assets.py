# app/routers/assets.py
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Settings, Asset, User
from app.utils import get_current_user 
import requests
import logging

router = APIRouter(
    prefix="/assets",
    tags=["assets"]
)

OPENMETADATA_API_URL = "http://localhost:8585/api/v1"
logger = logging.getLogger(__name__)

# Dynamic type mapping
asset_type_map = {
    "searchIndexes": "searchIndexes",
    "tables": "tables",
    "dashboards":"dashboards",
    "storedProcedures":"storedProcedures",
    "docStore":"docStore",
    "dataProducts":"dataProducts",
    "mlmodels":"mlmodels",
    "pipelines":"pipelines",
    "containers":"containers",
    "topics":"topics"
    # Additional types can be added here
}

def get_openmetadata_token(db: Session):
    """Retrieve the OpenMetadata token from the database."""
    settings = db.query(Settings).first()
    if settings and settings.openmetadata_token:
        return settings.openmetadata_token
    logger.error("OpenMetadata API token not found in the database.")
    raise HTTPException(status_code=500, detail="OpenMetadata API token is not configured in the database")

def get_headers(db: Session):
    """Return headers for OpenMetadata API requests."""
    token = get_openmetadata_token(db)
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

@router.get("/unowned")
def fetch_unowned_assets(db: Session = Depends(get_db)):
    headers = get_headers(db)
    unowned_assets = []

    try:
        for asset_type, endpoint in asset_type_map.items():
            response = requests.get(
                f"{OPENMETADATA_API_URL}/{endpoint}?fields=owners&limit=1000000", headers=headers
            )
            if response.status_code != 200:
                logger.error(f"Failed to fetch {asset_type}: {response.text}")
                raise HTTPException(status_code=500, detail=f"Error fetching {asset_type} from OpenMetadata")

            assets = [
                {
                    "id": item["id"],
                    "displayName": item.get("displayName", item["name"]),
                    "updatedAt": item["updatedAt"],
                    "dataType": asset_type
                }
                for item in response.json().get("data", [])
                if not item.get("owners")
            ]
            unowned_assets.extend(assets)

        logger.info(f"Successfully fetched {len(unowned_assets)} unowned assets.")
        return unowned_assets

    except requests.RequestException as e:
        logger.error(f"Error communicating with OpenMetadata API: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to communicate with OpenMetadata API")

@router.patch("/{asset_id}/type/{type}/owner")
def update_asset_owner(
    asset_id: str, type: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    headers = get_headers(db)
    headers["Content-Type"] = "application/json-patch+json"

    # Verify if type is supported
    if type not in asset_type_map:
        raise HTTPException(status_code=400, detail="Unsupported asset type")

    # Construct OpenMetadata API URL dynamically
    openmetadata_url = f"{OPENMETADATA_API_URL}/{asset_type_map[type]}/{asset_id}"

    # Prepare the payload for PATCH request to update the owner
    payload = [
        {
            "op": "replace",
            "path": "/owners",
            "value": [
                {
                    "type": "team",
                    "id": current_user.team_id,
                    "name": current_user.team
                }
            ]
        }
    ]

    try:
        response = requests.patch(openmetadata_url, json=payload, headers=headers)
        if response.status_code == 200:
            logger.info(f"Successfully updated ownership for asset ID {asset_id}")
            return {"success": True}
        else:
            logger.error(f"Failed to update ownership: {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Failed to update asset ownership")

    except requests.RequestException as e:
        logger.error(f"Error updating asset ownership: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to communicate with OpenMetadata API")

@router.get("/teams/{team_name}")
def get_team_assets(team_name: str, db: Session = Depends(get_db)):
    headers = get_headers(db)
    team_url = f"{OPENMETADATA_API_URL}/teams/name/{team_name}?fields=owns"

    try:
        response = requests.get(team_url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to fetch team '{team_name}': {response.text}")
            raise HTTPException(status_code=500, detail=f"Error fetching team data from OpenMetadata")

        team_data = response.json()
        team_assets = team_data.get("owns", [])
        updated_assets = []

        for asset in team_assets:
            asset_entry = db.query(Asset).filter_by(id=asset["id"]).first()
            if asset_entry is None:
                asset_entry = Asset(
                    id=asset["id"],
                    display_name=asset.get("displayName", asset["name"]),
                    description=asset.get("description", ""),
                    updated_at=datetime.utcfromtimestamp(team_data.get("updatedAt") / 1000),
                    owner_team=team_name,
                    type=asset["type"]
                )
                db.add(asset_entry)
                db.commit()
                db.refresh(asset_entry)
            updated_assets.append(asset_entry)

        return {"team_assets": [asset.to_dict() for asset in updated_assets]}

    except requests.RequestException as e:
        logger.error(f"Error communicating with OpenMetadata API: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to communicate with OpenMetadata API")
