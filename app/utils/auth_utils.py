import base64
import hashlib
import io
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
import pyotp
import qrcode
from sqlalchemy.orm import Session
from app.config import settings, get_db

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash password securely using PBKDF2-HMAC-SHA256 with 100,000 iterations and a 16-byte random salt."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"pbkdf2_sha256$100000${salt.hex()}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against PBKDF2 hashed password string."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_key = bytes.fromhex(parts[3])
        
        calculated_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
        return secrets.compare_digest(calculated_key, expected_key)
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create signed JWT access token with payload and expiration."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED", "message": "Access token has expired."}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Invalid authentication token."}
        )


def generate_otp(length: int = 6) -> str:
    """Generate cryptographically secure N-digit OTP string."""
    digits = [str(secrets.randbelow(10)) for _ in range(length)]
    return "".join(digits)


def generate_refresh_token() -> str:
    """Generate secure random hex string for Refresh Token."""
    return secrets.token_hex(32)


def hash_token(token: str) -> str:
    """SHA-256 hash string for index storing of refresh tokens."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# --- TOTP 2FA Helpers ---

def generate_totp_secret() -> str:
    """Generate a base32 TOTP secret key for Google Authenticator / Authy."""
    return pyotp.random_base32()


def verify_totp_code(secret: str, code: str) -> bool:
    """Verify 6-digit TOTP code against user secret key."""
    if not secret or not code:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def generate_totp_qr_code_base64(secret: str, user_email: str) -> str:
    """Generate QR Code as base64 data URL string."""
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=user_email, issuer_name="Pulse")
    
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"


def generate_recovery_codes(count: int = 10) -> List[str]:
    """Generate N formatted 2FA recovery codes (e.g. A1B2-C3D4)."""
    codes = []
    for _ in range(count):
        part1 = "".join(secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(4))
        part2 = "".join(secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(4))
        codes.append(f"{part1}-{part2}")
    return codes


# --- Request Device & Client Parser ---

def parse_user_agent(request: Request) -> Tuple[str, str, str, str]:
    """Extract (device_name, browser, ip_address, icon_type) from request."""
    user_agent_str = request.headers.get("User-Agent", "Unknown Browser")
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ip = forwarded_for.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "127.0.0.1"

    # Simple heuristic device parsing
    browser = "Chrome 128.0"
    if "Firefox" in user_agent_str:
        browser = "Firefox"
    elif "Safari" in user_agent_str and "Chrome" not in user_agent_str:
        browser = "Safari"
    elif "Edg" in user_agent_str:
        browser = "Edge"

    device = "Linux PC (Ubuntu 24.04 LTS)"
    icon = "Laptop"
    if "iPhone" in user_agent_str or "iOS" in user_agent_str:
        device = "iPhone 15 Pro (iOS 17.5)"
        icon = "Smartphone"
    elif "Android" in user_agent_str:
        device = "Android Device"
        icon = "Smartphone"
    elif "Macintosh" in user_agent_str:
        device = "MacBook Pro (macOS Sonoma)"
        icon = "Laptop"
    elif "Windows" in user_agent_str:
        device = "Windows Workstation"
        icon = "Laptop"

    return device, browser, ip, icon


# --- Current Authenticated User Dependency ---

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """FastAPI dependency asserting valid Bearer Token and returning authenticated User model."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Authentication token missing or invalid."}
        )
    
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Invalid token payload."}
        )
    
    from app.models import User

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "User account no longer exists."}
        )
    
    return user
