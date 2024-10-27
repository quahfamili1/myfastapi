# routers/assets.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import schemas
from ..database import get_db
from ..models import Asset
from datetime import datetime

router = APIRouter(prefix="/assets", tags=["assets"])

@router.post("/", response_model=schemas.Asset)
def create_asset(asset: schemas.AssetCreate, db: Session = Depends(get_db)):
    new_asset = Asset(
        display_name=asset.display_name,
        description=asset.description,
        owner_id=asset.owner_id,
    )
    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)
    return new_asset

@router.get("/{asset_id}", response_model=schemas.Asset)
def read_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset

@router.put("/{asset_id}", response_model=schemas.Asset)
def update_asset(asset_id: int, asset_update: schemas.AssetUpdate, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset.display_name = asset_update.display_name or asset.display_name
    asset.description = asset_update.description or asset.description
    asset.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(asset)
    return asset
