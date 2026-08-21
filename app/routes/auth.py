from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_db, settings

from app.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResendOtpRequest,
    ResetPasswordRequest,
    VerifyOtpRequest
)

from app.models import User

from app.services.user_service import user_service
from app.utils.auth_utils import get_current_user
from app.utils.helpers import success_response

router = APIRouter(prefix="/auth", tags=["Authentication & OTP"])


@router.post("/register", status_code=status.HTTP_201_CREATED, summary="User Registration")
async def register(request_data: RegisterRequest, db: Session = Depends(get_db)):
    """Registers a new user and dispatches a 6-digit OTP verification code."""
    data = await user_service.register_user(
        db=db,
        name=request_data.name,
        email=request_data.email,
        password=request_data.password
    )
    return success_response(
        data=data,
        message="Registration successful. OTP verification code sent to your email."
    )

@router.post("/verify-otp", summary="Verify OTP Code")
def verify_otp(request_data: VerifyOtpRequest, request: Request, db: Session = Depends(get_db)):
    """Verifies 6-digit OTP code for email verification, 2FA login, or password recovery."""
    data = user_service.verify_otp(
        db=db,
        email=request_data.email,
        code=request_data.otp,
        purpose=request_data.purpose,
        request=request
    )
    return success_response(
        data=data,
        message="OTP verified successfully."
    )


@router.post("/resend-otp", summary="Resend OTP Code")
async def resend_otp(request_data: ResendOtpRequest, db: Session = Depends(get_db)):
    """Resends a fresh 6-digit OTP code to specified email address."""
    expires_in = await user_service.resend_otp(
        db=db,
        email=request_data.email,
        purpose=request_data.purpose
    )
    return {
        "success": True,
        "message": "A new OTP code has been dispatched to your email address.",
        "otpExpiresInSeconds": expires_in
    }


@router.post("/login", summary="User Login")
async def login(request_data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticates user credentials and returns Access & Refresh Tokens."""
    data = await user_service.login_user(
        db=db,
        email=request_data.email,
        password=request_data.password,
        request=request
    )
    return success_response(data=data, message="Login successful.")


@router.post("/refresh-token", summary="Refresh Access Token")
def refresh_token(request_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Issues new Access Token using a valid Refresh Token."""
    data = user_service.refresh_token(db=db, refresh_token_str=request_data.refreshToken)
    return success_response(data=data, message="Access token refreshed.")


@router.post("/logout", summary="User Logout")
def logout(
    request_data: Optional[RefreshTokenRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Invalidates active refresh tokens and terminates user session."""
    raw_token = request_data.refreshToken if request_data else None
    user_service.logout_user(db=db, user=current_user, refresh_token_str=raw_token)
    return success_response(data=None, message="Logged out successfully.")


@router.post("/forgot-password", summary="Forgot Password Request")
async def forgot_password(request_data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Initiates password recovery by sending 6-digit OTP code to user's email."""
    data = await user_service.forgot_password(db=db, email=request_data.email)
    return success_response(
        data=data,
        message="Password reset OTP sent to your email."
    )


@router.post("/reset-password", summary="Reset Password")
async def reset_password(request_data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Resets account password using verified OTP code."""
    if request_data.newPassword != request_data.confirmNewPassword:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "PASSWORD_MISMATCH", "message": "New password and confirmation password do not match."}
        )

    await user_service.reset_password(
        db=db,
        email=request_data.email,
        otp=request_data.otp,
        new_password=request_data.newPassword
    )
    return success_response(
        data=None,
        message="Password reset successful. You may now log in with your new password."
    )
