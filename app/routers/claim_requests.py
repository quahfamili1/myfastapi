# routers/claim_requests.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import schemas
from ..database import get_db
from ..models import Asset, ClaimRequest

router = APIRouter(prefix="/claim_requests", tags=["claim_requests"])

@router.post("/assets/{asset_id}/claim", response_model=schemas.ClaimRequest)
def request_claim(asset_id: int, claim_request: schemas.ClaimRequestCreate, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset.owner_id is not None:
        raise HTTPException(status_code=400, detail="Asset is already owned")
    new_claim = ClaimRequest(
        asset_id=asset_id,
        requested_by_id=claim_request.requested_by_id,
        status="pending",
    )
    db.add(new_claim)
    db.commit()
    db.refresh(new_claim)
    return new_claim

@router.get("/{claim_id}", response_model=schemas.ClaimRequest)
def read_claim_request(claim_id: int, db: Session = Depends(get_db)):
    claim_request = db.query(ClaimRequest).filter(ClaimRequest.id == claim_id).first()
    if claim_request is None:
        raise HTTPException(status_code=404, detail="Claim request not found")
    return claim_request