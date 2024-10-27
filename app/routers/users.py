# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas import UserLogin, UserCreate, User as UserSchema  # Rename the Pydantic schema for clarity
from app.utils import verify_password, create_access_token, get_password_hash
from datetime import timedelta
import requests  # Import requests to make API calls
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from `.env`

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

# Constants and API token
OPENMETADATA_API_URL = "http://localhost:8585/api/v1/teams"
OPENMETADATA_TOKEN = "eyJraWQiOiJHYjM4OWEtOWY3Ni1nZGpzLWE5MmotMDI0MmJrOTQzNTYiLCJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJvcGVuLW1ldGFkYXRhLm9yZyIsInN1YiI6ImNhdGFsb2ciLCJyb2xlcyI6W10sImVtYWlsIjoiY2F0YWxvZ0BvcGVuLW1ldGFkYXRhLm9yZyIsImlzQm90Ijp0cnVlLCJ0b2tlblR5cGUiOiJCT1QiLCJpYXQiOjE3Mjg4MTg3MzIsImV4cCI6bnVsbH0.zUtNXPA9FHIDFZ68hn_SXcYlcDF_No9EjsjkV8kRHXeEKw1CEKgAy9Tmcrb8Rc0kvbBYXHvwhVO7x0ST29fg0A7PY_OI7RJkuTjqlZ_oZkMxsnanKBrmkh9cJi07x5wyYqGFptdF4AxjRzvH4GuE_xaMsmsxESnpq7C-eFauOwJ7mXy0KAYxIFC8nc4ps5MGzi5JgCytkaVS8OWnlVLvMx-PfeW-qwtJ_CgZcoDXb8g93O2FPiAUrfZv196b7vaygEPRZt0DBrvzlju9RB62llwjrvefD6BkQF_L9KhTU9rX5gE3Y3VFMFNdheKc6ecq1H4OsaZ7uyO7SH2GBiVE5Q"  # Replace with your actual token

# Helper function to get headers for OpenMetadata API
def get_headers():
    if not OPENMETADATA_TOKEN:
        raise Exception("OpenMetadata API token is not set")
    return {"Authorization": f"Bearer {OPENMETADATA_TOKEN}", "Content-Type": "application/json"}

# Function to check if a team exists in the OpenMetadata catalog
def check_team_in_catalog(team_name: str) -> bool:
    headers = get_headers()
    response = requests.get(f"{OPENMETADATA_API_URL}/name/{team_name}", headers=headers)
    return response.status_code == 200

# Function to create a team in the OpenMetadata catalog
def create_team_in_catalog(team_name: str):
    headers = get_headers()
    payload = {
        "name": team_name,
        "displayName": team_name
    }

    print(f"Sending team creation request. Payload: {payload}, Headers: {headers}", flush=True)

    response = requests.post(OPENMETADATA_API_URL, json=payload, headers=headers)

    if response.status_code != 201:  # Expected status code for successful creation is 201
        print(f"Failed to create team. Status code: {response.status_code}, Response: {response.text}", flush=True)
        raise HTTPException(status_code=500, detail="Failed to create team in catalog")
    else:
        print(f"Team '{team_name}' created successfully. Response: {response.json()}", flush=True)

# User login endpoint
@router.post("/login")
def login(user_login: UserLogin, db: Session = Depends(get_db)):
    # Print the login attempt details for debugging
    print(f"Login attempt for user: {user_login.username}", flush=True)

    try:
        user = db.query(User).filter(User.username == user_login.username).first()

        if user is None:
            print(f"User {user_login.username} not found", flush=True)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not verify_password(user_login.password, user.password_hash):
            print(f"Password verification failed for user: {user_login.username}", flush=True)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create a JWT token for the user if verification is successful
        print(f"Password verified for user: {user_login.username}", flush=True)

        # Check if the user's team exists in the data catalog
        if user.team:
            print(f"Checking if team '{user.team}' exists in catalog...", flush=True)
            team_exists = check_team_in_catalog(user.team)
            if not team_exists:
                print(f"Team '{user.team}' does not exist in catalog. Creating...", flush=True)
                create_team_in_catalog(user.team)
                print(f"Team '{user.team}' created successfully", flush=True)
            else:
                print(f"Team '{user.team}' already exists in catalog", flush=True)

        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "username": user.username,
                "team": user.team
            }
        }

    except HTTPException as e:
        print(f"HTTPException occurred: {e.detail}", flush=True)
        raise e
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.post("/", response_model=UserSchema)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Hash the password using the utility function
    hashed_password = get_password_hash(user.password)

    # Create new user
    new_user = User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        role=user.role,
        team=user.team  # Store the team information in the database
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
