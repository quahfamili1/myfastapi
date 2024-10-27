# app/utils.py
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional

# Secret key for signing the JWT tokens. Replace with a secure value.
SECRET_KEY = "YOUR_SECRET_KEY"  # Replace with a strong secret key (e.g., from environment variables)
ALGORITHM = "HS256"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Add print statements to debug and flush output to console
    print(f"Plain Password: {plain_password}", flush=True)
    print(f"Hashed Password from DB: {hashed_password}", flush=True)
    
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Function to create a JWT access token
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)  # Default to 15 minutes if no expiry provided
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
