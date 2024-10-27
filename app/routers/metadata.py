# routers/metadata.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import schemas
from ..database import get_db
from ..models import Asset, MetadataHistory

router = APIRouter(prefix="/metadata", tags=["metadata"])

@router.post("/assets/{asset_id}/metadata_history/", response_model=schemas.MetadataHistory)
def create_metadata_history(asset_id: int, metadata: schemas.MetadataHistoryCreate, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    new_metadata = MetadataHistory(
        asset_id=asset_id,
        description=metadata.description,
        suggestion_type=metadata.suggestion_type,
        updated_by_id=metadata.updated_by_id,
    )
    db.add(new_metadata)
    db.commit()
    db.refresh(new_metadata)
    return new_metadata

@router.get("/assets/{asset_id}/metadata_history/", response_model=list[schemas.MetadataHistory])
def read_metadata_history(asset_id: int, db: Session = Depends(get_db)):
    metadata_history = db.query(MetadataHistory).filter(MetadataHistory.asset_id == asset_id).all()
    return metadata_history
