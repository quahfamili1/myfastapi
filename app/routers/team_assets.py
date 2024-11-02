# app/routers/team_assets.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models import Asset, Settings  # Ensure Settings is imported
import requests
import logging

router = APIRouter(
    prefix="/teams",
    tags=["teams"]
)

OPENMETADATA_API_URL = "http://localhost:8585/api/v1"
logger = logging.getLogger(__name__)

def get_headers(db: Session):
    """Retrieve the OpenMetadata API token from the database."""
    settings = db.query(Settings).first()
    if settings and settings.openmetadata_token:
        return {"Authorization": f"Bearer {settings.openmetadata_token}", "Content-Type": "application/json"}
    raise HTTPException(status_code=500, detail="OpenMetadata API token is not configured")

@router.get("/{team_name}")
def get_team_assets(team_name: str, db: Session = Depends(get_db)):
    headers = get_headers(db)
    team_url = f"{OPENMETADATA_API_URL}/teams/name/{team_name}?fields=owns"

    try:
        response = requests.get(team_url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to fetch team '{team_name}': {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Error fetching team data")

        team_data = response.json()
        team_assets = team_data.get("owns", [])
        updated_assets = []

        for asset in team_assets:
            # Fetching display name, description, and updatedAt safely
            display_name = asset.get("displayName", asset.get("name", "Unnamed Asset"))
            description = asset.get("description", "No description available")
            updated_at = datetime.utcfromtimestamp(asset.get("updatedAt", 0) / 1000) if asset.get("updatedAt") else None

            asset_entry = db.query(Asset).filter_by(id=asset["id"]).first()
            if asset_entry is None:
                # If the asset does not exist, create a new entry in the database
                asset_entry = Asset(
                    id=asset["id"],
                    display_name=display_name,
                    description=description,
                    updated_at=updated_at,  # Store None if 'updatedAt' is missing
                    owner_team=team_name,
                    type=asset.get("type", "Unknown Type")  # Default type if not specified
                )
                db.add(asset_entry)
                db.commit()
                db.refresh(asset_entry)
            updated_assets.append(asset_entry)

        return {"team_assets": [asset.to_dict() for asset in updated_assets]}

    except requests.RequestException as e:
        logger.error(f"Error communicating with OpenMetadata API: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to communicate with OpenMetadata API")
