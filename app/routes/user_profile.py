from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_db
from app.middlewares.upload_middleware import r2_upload_validator
from app.models import User, UserSession
from app.schemas import (
    ChangePasswordRequest,
    Confirm2faRequest,
    Disable2faRequest,
    UpdateAvatarUrlRequest,
    UpdateProfileRequest,
    UserDTO,
    UserSessionDTO
)
from app.services.user_service import user_service
from app.utils.auth_utils import get_current_user
from app.utils.helpers import success_response

router = APIRouter(prefix="/user", tags=["Profile & User Management"])


# ==========================================
# 👤 PROFILE MANAGEMENT ENDPOINTS
# ==========================================

@router.get("/profile", summary="Get Profile Details")
def get_profile(current_user: User = Depends(get_current_user)):
    """Retrieves profile details of currently authenticated user."""
    user_dto = UserDTO.model_validate(current_user)
    return success_response(data=user_dto.model_dump(), message="Profile retrieved successfully.")


@router.put("/profile", summary="Update Profile Information")
def update_profile(
    request_data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates profile details (Name, Job Title, Bio, Tier)."""
    updated_user = user_service.update_profile(
        db=db,
        user=current_user,
        update_data=request_data.model_dump(exclude_unset=True)
    )
    user_dto = UserDTO.model_validate(updated_user)
    return success_response(data=user_dto.model_dump(), message="Profile updated successfully.")


@router.post("/avatar", summary="Upload Profile Picture / Avatar Image")
async def upload_avatar(
    file: Optional[UploadFile] = File(None),
    avatar_url: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Uploads avatar image file via multipart form data upload to Cloudflare R2 object storage ('avatars/' folder)
    or updates avatar_url string.
    """
    if file and file.filename:
        file_bytes, sanitized_name, content_type = await r2_upload_validator.validate_upload(file)
        avatar_url_res = user_service.update_avatar(
            db=db,
            user=current_user,
            file_bytes=file_bytes,
            filename=file.filename or "avatar.jpg",
            content_type=content_type
        )
        return success_response(
            data={"avatarUrl": avatar_url_res},
            message="Avatar image uploaded successfully."
        )
    elif avatar_url is not None:
        current_user.avatar_url = avatar_url
        db.commit()
        return success_response(
            data={"avatarUrl": avatar_url},
            message="Avatar URL updated successfully."
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_AVATAR_PAYLOAD", "message": "Please select a valid image file to upload."}
        )


@router.delete("/avatar", summary="Remove Avatar Picture")
def remove_avatar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Removes avatar picture from user profile."""
    current_user.avatar_url = ""
    db.commit()
    return success_response(data={"avatarUrl": ""}, message="Avatar removed successfully.")


@router.put("/change-password", summary="Change Password")
async def change_password(
    request_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Changes password for authenticated user after current password verification."""
    if request_data.newPassword != request_data.confirmPassword:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "PASSWORD_MISMATCH", "message": "New password and confirmation password do not match."}
        )

    await user_service.change_password(
        db=db,
        user=current_user,
        current_password=request_data.currentPassword,
        new_password=request_data.newPassword
    )
    return success_response(
        data=None,
        message="Password changed successfully across all active sessions."
    )


# ==========================================
# 📱 ACTIVE DEVICE SESSIONS ENDPOINTS
# ==========================================

@router.get("/sessions", summary="Get Active Device Sessions")
def get_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves all active device sessions for current user."""
    sessions = db.query(UserSession).filter(UserSession.user_id == current_user.id).all()
    session_dtos = [
        UserSessionDTO(
            id=s.id,
            device=s.device_name,
            browser=s.browser,
            ipAddress=s.ip_address,
            location=s.location or "Colombo, Sri Lanka",
            lastActive="Active Now" if s.is_current else "Recently active",
            isCurrent=s.is_current,
            icon="Laptop" if "Mac" in s.device_name or "Windows" in s.device_name or "Linux" in s.device_name else "Smartphone"
        )
        for s in sessions
    ]
    return success_response(
        data=[dto.model_dump() for dto in session_dtos],
        message="Active sessions retrieved."
    )


@router.delete("/sessions/revoke-others", summary="Revoke All Other Sessions")
def revoke_other_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revokes all active sessions except current session."""
    db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_current == False
    ).delete()
    db.commit()
    return success_response(data=None, message="All other sessions revoked successfully.")


@router.delete("/sessions/{session_id}", summary="Revoke Specific Device Session")
def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revokes a specific device session by ID."""
    session_record = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.user_id == current_user.id
    ).first()

    if not session_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SESSION_NOT_FOUND", "message": "Session not found."}
        )

    db.delete(session_record)
    db.commit()
    return success_response(data=None, message="Session revoked successfully.")


# ==========================================
# 🔐 TWO-FACTOR AUTHENTICATION (2FA) ENDPOINTS
# ==========================================

@router.post("/2fa/enable", summary="Enable 2FA Setup")
def enable_2fa_setup(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generates TOTP Secret Key, QR Code base64 URL, and 10 Recovery Codes for 2FA activation."""
    data = user_service.enable_2fa_setup(db=db, user=current_user)
    return success_response(
        data=data,
        message="2FA setup initiated successfully."
    )


@router.post("/2fa/confirm", summary="Confirm 2FA Setup")
def confirm_2fa(
    request_data: Confirm2faRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Confirms 6-digit TOTP code and finalizes 2FA activation."""
    user_service.confirm_2fa(db=db, user=current_user, totp_code=request_data.totpCode)
    return success_response(
        data=None,
        message="Two-Factor Authentication (2FA) enabled successfully."
    )


@router.post("/2fa/disable", summary="Disable 2FA")
def disable_2fa(
    request_data: Disable2faRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disables Two-Factor Authentication after password and TOTP code verification."""
    user_service.disable_2fa(
        db=db,
        user=current_user,
        password=request_data.password,
        totp_code=request_data.totpCode
    )
    return success_response(
        data=None,
        message="Two-Factor Authentication has been disabled."
    )
