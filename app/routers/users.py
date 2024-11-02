# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models import Settings  # Import the Settings model to retrieve the token
from app.schemas import UserLogin, UserCreate, User as UserSchema
from app.utils import verify_password, create_access_token, get_password_hash
from datetime import timedelta
import requests
import os

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

OPENMETADATA_API_URL = os.getenv("OPENMETADATA_API_URL", "http://localhost:8585/api/v1/teams")

# Helper function to get headers for OpenMetadata API
def get_headers(db: Session):
    settings = db.query(Settings).first()
    if not settings or not settings.openmetadata_token:
        raise HTTPException(status_code=500, detail="OpenMetadata API token is not configured in the database")
    return {"Authorization": f"Bearer {settings.openmetadata_token}", "Content-Type": "application/json"}

# Check if a team exists in OpenMetadata
def check_team_in_catalog(team_name: str, db: Session) -> bool:
    headers = get_headers(db)
    try:
        response = requests.get(f"{OPENMETADATA_API_URL}/name/{team_name}", headers=headers)
        return response.status_code == 200
    except requests.RequestException as e:
        print(f"Error checking team in catalog: {e}", flush=True)
        return False

# Create a team in OpenMetadata
def create_team_in_catalog(team_name: str, db: Session):
    headers = get_headers(db)
    payload = {
        "name": team_name,
        "displayName": team_name
    }
    response = requests.post(OPENMETADATA_API_URL, json=payload, headers=headers)
    if response.status_code != 201:
        print(f"Failed to create team '{team_name}': {response.text}", flush=True)
        raise HTTPException(status_code=500, detail="Failed to create team in catalog")

# User login endpoint
@router.post("/login")
def login(user_login: UserLogin, db: Session = Depends(get_db)):
    print(f"Login attempt for user: {user_login.username}", flush=True)
    user = db.query(User).filter(User.username == user_login.username).first()
    
    if not user or not verify_password(user_login.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if the user's team exists in the catalog
    if user.team:
        if not check_team_in_catalog(user.team, db):
            create_team_in_catalog(user.team, db)

    # Generate JWT token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "username": user.username,
            "team": user.team
        }
    }

@router.post("/", response_model=UserSchema)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    try:
        # Log incoming user data
        print("Creating user with data:", user.dict(), flush=True)

        # Check if the username already exists
        if db.query(User).filter(User.username == user.username).first():
            raise HTTPException(status_code=400, detail="Username already registered")

        # Hash the user's password
        hashed_password = get_password_hash(user.password)

        # Ensure the user's team exists in OpenMetadata
        team_id = None
        if user.team:
            headers = get_headers(db)
            team_url = f"{OPENMETADATA_API_URL}/name/{user.team}"

            # Check if team exists in OpenMetadata
            team_response = requests.get(team_url, headers=headers)
            if team_response.status_code == 200:
                # Team exists, retrieve the ID
                team_data = team_response.json()
                team_id = team_data.get("id")
                print(f"Team '{user.team}' found with ID: {team_id}", flush=True)
            else:
                # Attempt to create the team in OpenMetadata if it doesn't exist
                payload = {"name": user.team, "displayName": user.team}
                create_response = requests.post(OPENMETADATA_API_URL, json=payload, headers=headers)
                if create_response.status_code == 201:
                    # Team created successfully, retrieve the ID
                    team_data = create_response.json()
                    team_id = team_data.get("id")
                    print(f"Team '{user.team}' created with ID: {team_id}", flush=True)
                else:
                    # Failed to create the team
                    print(f"Failed to create team '{user.team}' in OpenMetadata. Response: {create_response.text}", flush=True)
                    raise HTTPException(status_code=500, detail="Failed to create team in catalog")

        # Create the new user in the database
        new_user = User(
            username=user.username,
            email=user.email,
            password_hash=hashed_password,
            role=user.role,
            team=user.team,
            team_id=team_id  # Store the team ID in the user record
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        print("User created successfully:", new_user.username, flush=True)
        return new_user

    except Exception as e:
        print("Error creating user:", str(e), flush=True)
        raise HTTPException(status_code=500, detail="Internal server error occurred during user creation")



