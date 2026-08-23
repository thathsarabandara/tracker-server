from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# --- Auth Request Schemas ---

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=4, max_length=10)
    purpose: str = Field("email_verification", description="email_verification, login_2fa, password_reset")


class ResendOtpRequest(BaseModel):
    email: EmailStr
    purpose: str = Field("email_verification", description="email_verification, login_2fa, password_reset")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refreshToken: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: Optional[EmailStr] = None
    otp: str
    newPassword: str = Field(..., min_length=8)
    confirmNewPassword: str = Field(..., min_length=8)


# --- Profile & User Settings Request Schemas ---

class UpdateProfileRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    jobTitle: Optional[str] = Field(None, max_length=150)
    bio: Optional[str] = Field(None, max_length=1000)


class UpdateAvatarUrlRequest(BaseModel):
    avatarUrl: str


class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str = Field(..., min_length=8)
    confirmPassword: str = Field(..., min_length=8)


# --- 2FA Request Schemas ---

class Confirm2faRequest(BaseModel):
    totpCode: str = Field(..., min_length=6, max_length=6)


class Disable2faRequest(BaseModel):
    password: str
    totpCode: str = Field(..., min_length=6, max_length=6)


from pydantic import AliasChoices, BaseModel, EmailStr, Field

# --- Common User DTO Response Schemas ---

class UserDTO(BaseModel):
    id: str
    name: str
    email: str
    avatarUrl: Optional[str] = Field(None, validation_alias=AliasChoices('avatarUrl', 'avatar_url'))
    jobTitle: Optional[str] = Field(None, validation_alias=AliasChoices('jobTitle', 'job_title'))
    bio: Optional[str] = None
    emailVerified: bool = Field(False, validation_alias=AliasChoices('emailVerified', 'is_email_verified'))
    is2faEnabled: bool = Field(False, validation_alias=AliasChoices('is2faEnabled', 'is_2fa_enabled'))

    class Config:
        from_attributes = True



class UserSessionDTO(BaseModel):
    id: str
    device: str
    browser: str
    ipAddress: str
    location: Optional[str] = "Colombo, Sri Lanka"
    lastActive: str
    isCurrent: bool = False
    icon: str = "Laptop"

    class Config:
        from_attributes = True
