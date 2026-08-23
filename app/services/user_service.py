import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models import OtpVerification, RefreshToken, TwoFactorRecoveryCode, User, UserSession
from app.services.email_service import email_service
from app.services.storage_service import storage_service
from app.utils.auth_utils import (
    create_access_token,
    generate_otp,
    generate_recovery_codes,
    generate_refresh_token,
    generate_totp_qr_code_base64,
    generate_totp_secret,
    hash_password,
    hash_token,
    parse_user_agent,
    verify_password,
    verify_totp_code
)

logger = logging.getLogger("pulse.user_service")


class UserService:
    """Service layer executing business logic for Authentication, Profile, Sessions, and 2FA."""

    async def register_user(self, db: Session, name: str, email: str, password: str) -> Dict[str, Any]:
        """Register a new user and dispatch 6-digit OTP verification code."""
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "EMAIL_ALREADY_EXISTS", "message": "An account with this email address already exists."}
            )

        hashed_pwd = hash_password(password)
        new_user = User(
            name=name,
            email=email,
            password_hash=hashed_pwd,
            is_email_verified=False,
            is_2fa_enabled=False
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Generate OTP
        otp_code = generate_otp(6)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        otp_record = OtpVerification(
            user_id=new_user.id,
            email=email,
            code=otp_code,
            purpose="email_verification",
            expires_at=expires_at,
            is_used=False
        )
        db.add(otp_record)
        db.commit()

        # Send OTP Email
        await email_service.send_otp_email(
            to_email=email,
            user_name=name,
            otp_code=otp_code,
            expire_minutes=10
        )

        return {
            "userId": new_user.id,
            "email": new_user.email,
            "requiresOtp": True,
            "otpExpiresInSeconds": 600
        }

    def verify_otp(self, db: Session, email: str, code: str, purpose: str, request: Request) -> Dict[str, Any]:
        """Verify 6-digit OTP code and activate account or process 2FA/password reset."""
        otp_record = db.query(OtpVerification).filter(
            OtpVerification.email == email,
            OtpVerification.code == code,
            OtpVerification.purpose == purpose,
            OtpVerification.is_used == False
        ).order_by(OtpVerification.created_at.desc()).first()

        if not otp_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_OTP", "message": "Invalid or expired OTP verification code."}
            )

        # Check expiration
        now = datetime.now(timezone.utc)
        record_expiry = otp_record.expires_at
        if record_expiry.tzinfo is None:
            record_expiry = record_expiry.replace(tzinfo=timezone.utc)
            
        if now > record_expiry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "OTP_EXPIRED", "message": "OTP verification code has expired. Please request a new code."}
            )

        # Mark OTP as used
        otp_record.is_used = True
        
        user = db.query(User).filter(User.email == email).first()
        if user and purpose == "email_verification":
            user.is_email_verified = True
            
        db.commit()

        if not user:
            return {"message": "OTP verified successfully."}

        # Issue Access & Refresh Tokens
        access_token = create_access_token({"sub": user.id, "email": user.email})
        raw_refresh_token = generate_refresh_token()
        token_hash = hash_token(raw_refresh_token)
        
        device_name, browser, ip, icon = parse_user_agent(request)
        
        refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            device_info=f"{device_name} ({browser})",
            ip_address=ip,
            expires_at=now + timedelta(days=30),
            is_revoked=False
        )
        db.add(refresh_record)

        # Record User Session
        session_record = UserSession(
            user_id=user.id,
            device_name=device_name,
            browser=browser,
            ip_address=ip,
            location="Colombo, Sri Lanka",
            is_current=True
        )
        db.add(session_record)
        db.commit()

        return {
            "accessToken": access_token,
            "refreshToken": raw_refresh_token,
            "user": {
                "id": user.id,
                "name": user.name,
                "avatarUrl": user.avatar_url,
                "jobTitle": user.job_title,
                "emailVerified": user.is_email_verified,
                "is2faEnabled": user.is_2fa_enabled
            }
        }

    async def resend_otp(self, db: Session, email: str, purpose: str) -> int:
        """Resend fresh 6-digit OTP code."""
        user = db.query(User).filter(User.email == email).first()
        user_name = user.name if user else "Pulse User"

        otp_code = generate_otp(6)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        
        otp_record = OtpVerification(
            user_id=user.id if user else None,
            email=email,
            code=otp_code,
            purpose=purpose,
            expires_at=expires_at,
            is_used=False
        )
        db.add(otp_record)
        db.commit()

        await email_service.send_otp_email(
            to_email=email,
            user_name=user_name,
            otp_code=otp_code,
            expire_minutes=10
        )
        return 600

    async def login_user(self, db: Session, email: str, password: str, request: Request) -> Dict[str, Any]:
        """Authenticate user credentials and handle 2FA or token generation."""
        user = db.query(User).filter(User.email == email).first()
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email address or password."}
            )

        # Handle 2FA if enabled
        if user.is_2fa_enabled:
            otp_code = generate_otp(6)
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
            otp_record = OtpVerification(
                user_id=user.id,
                email=email,
                code=otp_code,
                purpose="login_2fa",
                expires_at=expires_at,
                is_used=False
            )
            db.add(otp_record)
            db.commit()

            await email_service.send_otp_email(
                to_email=email,
                user_name=user.name,
                otp_code=otp_code,
                expire_minutes=10
            )

            return {
                "requires2fa": True,
                "email": user.email,
                "message": "Two-Factor Authentication required. 6-digit OTP code sent to your email."
            }

        # Issue Tokens
        now = datetime.now(timezone.utc)
        access_token = create_access_token({"sub": user.id, "email": user.email})
        raw_refresh_token = generate_refresh_token()
        token_hash = hash_token(raw_refresh_token)

        device_name, browser, ip, icon = parse_user_agent(request)

        refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            device_info=f"{device_name} ({browser})",
            ip_address=ip,
            expires_at=now + timedelta(days=30),
            is_revoked=False
        )
        db.add(refresh_record)

        session_record = UserSession(
            user_id=user.id,
            device_name=device_name,
            browser=browser,
            ip_address=ip,
            location="Colombo, Sri Lanka",
            is_current=True
        )
        db.add(session_record)
        db.commit()

        return {
            "accessToken": access_token,
            "refreshToken": raw_refresh_token,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "avatarUrl": user.avatar_url,
                "jobTitle": user.job_title,
                "bio": user.bio,
                "emailVerified": user.is_email_verified,
                "is2faEnabled": user.is_2fa_enabled
            }
        }

    def refresh_token(self, db: Session, refresh_token_str: str) -> Dict[str, str]:
        """Issue new Access Token using valid Refresh Token."""
        token_hash = hash_token(refresh_token_str)
        record = db.query(RefreshToken).filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False
        ).first()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_REFRESH_TOKEN", "message": "Invalid or revoked refresh token."}
            )

        now = datetime.now(timezone.utc)
        record_expiry = record.expires_at
        if record_expiry.tzinfo is None:
            record_expiry = record_expiry.replace(tzinfo=timezone.utc)

        if now > record_expiry:
            record.is_revoked = True
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "REFRESH_TOKEN_EXPIRED", "message": "Refresh token has expired."}
            )

        # Issue new access token and rotate refresh token
        new_access_token = create_access_token({"sub": record.user_id})
        new_raw_refresh_token = generate_refresh_token()
        new_token_hash = hash_token(new_raw_refresh_token)

        record.is_revoked = True
        new_record = RefreshToken(
            user_id=record.user_id,
            token_hash=new_token_hash,
            device_info=record.device_info,
            ip_address=record.ip_address,
            expires_at=now + timedelta(days=30),
            is_revoked=False
        )
        db.add(new_record)
        db.commit()

        return {
            "accessToken": new_access_token,
            "refreshToken": new_raw_refresh_token
        }

    def logout_user(self, db: Session, user: User, refresh_token_str: Optional[str] = None):
        """Revoke active refresh tokens and terminate session."""
        if refresh_token_str:
            token_hash = hash_token(refresh_token_str)
            db.query(RefreshToken).filter(
                RefreshToken.user_id == user.id,
                RefreshToken.token_hash == token_hash
            ).update({"is_revoked": True})
        else:
            db.query(RefreshToken).filter(
                RefreshToken.user_id == user.id
            ).update({"is_revoked": True})
            
        db.commit()

    async def forgot_password(self, db: Session, email: str) -> Dict[str, Any]:
        """Send password reset OTP code to email."""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "USER_NOT_FOUND", "message": "No account found with this email address."}
            )

        otp_code = generate_otp(6)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        otp_record = OtpVerification(
            user_id=user.id,
            email=email,
            code=otp_code,
            purpose="password_reset",
            expires_at=expires_at,
            is_used=False
        )
        db.add(otp_record)
        db.commit()

        reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?otp={otp_code}&email={email}"
        await email_service.send_password_reset_email(
            to_email=email,
            user_name=user.name,
            reset_url=reset_url,
            expire_minutes=10
        )


        return {
            "resetSessionId": f"rst-sess-{secrets.token_hex(4)}",
            "otpExpiresInSeconds": 600
        }

    async def reset_password(self, db: Session, otp: str, new_password: str, email: Optional[str] = None):
        """Reset password using verified OTP code."""
        query = db.query(OtpVerification).filter(
            OtpVerification.code == otp,
            OtpVerification.purpose == "password_reset",
            OtpVerification.is_used == False
        )
        if email:
            query = query.filter(OtpVerification.email == email)

        otp_record = query.order_by(OtpVerification.created_at.desc()).first()

        if not otp_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_OTP", "message": "Invalid or expired OTP reset code."}
            )

        otp_record.is_used = True
        user = db.query(User).filter(User.id == otp_record.user_id).first() or db.query(User).filter(User.email == otp_record.email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "USER_NOT_FOUND", "message": "User not found."}
            )

        user.password_hash = hash_password(new_password)
        db.commit()

        # Send confirmation email
        await email_service.send_password_changed_email(
            to_email=user.email,
            user_name=user.name
        )

    def update_profile(self, db: Session, user: User, update_data: dict) -> User:
        """Update User Profile metadata."""
        if "name" in update_data and update_data["name"]:
            user.name = update_data["name"]
        if "jobTitle" in update_data:
            user.job_title = update_data["jobTitle"]
        if "bio" in update_data:
            user.bio = update_data["bio"]

        db.commit()
        db.refresh(user)
        return user

    def update_avatar(self, db: Session, user: User, file_bytes: bytes, filename: str, content_type: str) -> str:
        """Upload user profile picture image to Cloudflare R2 avatars/ folder with resilient fallback handling."""
        import base64
        avatar_url = None
        if storage_service.is_configured():
            try:
                avatar_url = storage_service.upload_avatar(
                    file_bytes=file_bytes,
                    original_filename=filename,
                    content_type=content_type,
                    user_id=user.id
                )
            except Exception as e:
                logger.warning(f"Cloudflare R2 upload failed ({e}). Storing image via resilient fallback.")
                b64_str = base64.b64encode(file_bytes).decode("utf-8")
                avatar_url = f"data:{content_type};base64,{b64_str}"
        else:
            b64_str = base64.b64encode(file_bytes).decode("utf-8")
            avatar_url = f"data:{content_type};base64,{b64_str}"

        user.avatar_url = avatar_url
        db.commit()
        db.refresh(user)
        return avatar_url



    async def change_password(self, db: Session, user: User, current_password: str, new_password: str):
        """Authenticated password change with current password check."""
        if not verify_password(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INCORRECT_PASSWORD", "message": "Current password provided is incorrect."}
            )

        user.password_hash = hash_password(new_password)
        db.commit()

        # Send security notification email
        await email_service.send_password_changed_email(
            to_email=user.email,
            user_name=user.name
        )

    def enable_2fa_setup(self, db: Session, user: User) -> Dict[str, Any]:
        """Generate TOTP Secret, QR Code, and 10 Recovery Codes for 2FA activation."""
        totp_secret = generate_totp_secret()
        user.totp_secret = totp_secret
        db.commit()

        qr_code_url = generate_totp_qr_code_base64(totp_secret, user.email)
        raw_recovery_codes = generate_recovery_codes(10)

        # Store recovery code hashes
        db.query(TwoFactorRecoveryCode).filter(TwoFactorRecoveryCode.user_id == user.id).delete()
        for code in raw_recovery_codes:
            code_obj = TwoFactorRecoveryCode(
                user_id=user.id,
                code_hash=hash_token(code),
                is_used=False
            )
            db.add(code_obj)
        db.commit()

        return {
            "secretKey": totp_secret,
            "qrCodeUrl": qr_code_url,
            "recoveryCodes": raw_recovery_codes
        }

    def confirm_2fa(self, db: Session, user: User, totp_code: str):
        """Confirm 6-digit TOTP code and finalize 2FA activation."""
        if not user.totp_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "SETUP_NOT_INITIATED", "message": "2FA setup has not been initiated."}
            )

        if not verify_totp_code(user.totp_secret, totp_code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_TOTP", "message": "Invalid 6-digit TOTP authentication code."}
            )

        user.is_2fa_enabled = True
        db.commit()

    def disable_2fa(self, db: Session, user: User, password: str, totp_code: str):
        """Disable 2FA after password and TOTP code verification."""
        if not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INCORRECT_PASSWORD", "message": "Password provided is incorrect."}
            )

        if not verify_totp_code(user.totp_secret, totp_code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_TOTP", "message": "Invalid TOTP authentication code."}
            )

        user.is_2fa_enabled = False
        user.totp_secret = None
        db.commit()


user_service = UserService()
