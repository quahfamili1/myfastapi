from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    username: str
    email: str
    role: Optional[str] = "user"  # Set a default role
    team: str  # Add team field to base schema

class UserCreate(UserBase):
    password: str  # Plain password here, will be hashed when creating the user

class UserLogin(BaseModel):
    username: str
    password: str

class User(UserBase):
    id: int
    created_at: datetime  # Datetime field to capture when the user was created

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat()  # Ensure datetime fields are serialized as ISO strings
        }

# Asset Schemas
class AssetBase(BaseModel):
    display_name: str
    description: Optional[str] = None

class AssetCreate(AssetBase):
    owner_id: Optional[int] = None

class AssetUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None

class Asset(AssetBase):
    id: int
    owner_id: Optional[int] = None
    created_at: datetime

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Metadata History Schemas
class MetadataHistoryBase(BaseModel):
    description: str
    suggestion_type: str

class MetadataHistoryCreate(MetadataHistoryBase):
    updated_by_id: int

class MetadataHistory(MetadataHistoryBase):
    id: int
    asset_id: int
    created_at: datetime

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Claim Request Schemas
class ClaimRequestBase(BaseModel):
    status: Optional[str] = "pending"

class ClaimRequestCreate(ClaimRequestBase):
    requested_by_id: int

class ClaimRequest(ClaimRequestBase):
    id: int
    asset_id: int
    requested_by_id: int
    created_at: datetime

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
