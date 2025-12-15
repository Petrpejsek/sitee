"""Authentication endpoints for magic link login"""
import uuid
import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
import jwt

from app.database import get_db
from app.models import User
from app.config import get_settings
from app.services.analytics import AnalyticsService
from app.services.access_control import AccessControlService

router = APIRouter(prefix="/auth", tags=["authentication"])
settings = get_settings()


class MagicLinkRequest(BaseModel):
    """Request magic link for email"""
    email: EmailStr
    audit_id: Optional[UUID] = None


class UserResponse(BaseModel):
    """User information response"""
    id: UUID
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True


def create_jwt_token(user_id: UUID) -> str:
    """Create JWT token for user session"""
    payload = {
        "user_id": str(user_id),
        "exp": datetime.utcnow() + timedelta(days=30),  # Session lasts 30 days
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_jwt_token(token: str) -> Optional[UUID]:
    """Verify JWT token and return user_id"""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("user_id")
        if user_id:
            return UUID(user_id)
        return None
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def get_current_user_id(
    auth_token: Optional[str] = Cookie(None, alias="auth_token")
) -> Optional[UUID]:
    """Get current user ID from cookie"""
    if not auth_token:
        return None
    return verify_jwt_token(auth_token)


@router.post("/request-magic-link")
async def request_magic_link(
    request: MagicLinkRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Request a magic link for email authentication
    
    Creates user if doesn't exist, generates magic link token
    """
    analytics = AnalyticsService(db)
    
    # Check if user exists
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()
    
    # Create user if doesn't exist
    if not user:
        user = User(
            id=uuid.uuid4(),
            email=request.email,
            created_at=datetime.utcnow()
        )
        db.add(user)
    
    # Generate magic link token (secure random string)
    magic_token = secrets.token_urlsafe(32)
    user.magic_link_token = magic_token
    user.magic_link_expires_at = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)
    
    await db.commit()
    await db.refresh(user)
    
    # Track analytics
    await analytics.track_magic_link_sent(user.id, request.email)
    if request.audit_id:
        await analytics.track_email_submitted(user.id, request.audit_id, request.email)
    
    # Build magic link URL
    magic_link = f"{settings.frontend_url}/auth/verify?token={magic_token}"
    if request.audit_id:
        magic_link += f"&audit_id={request.audit_id}"
    
    # TODO: Send email with magic link
    # For now, return it in response (for development)
    # In production, integrate with email service (SendGrid, AWS SES, etc.)
    
    return {
        "success": True,
        "message": "Magic link sent to your email",
        "user_id": str(user.id),
        # Remove this in production - only for development testing
        "magic_link": magic_link if settings.environment == "development" else None
    }


@router.get("/verify-magic-link")
async def verify_magic_link(
    token: str,
    audit_id: Optional[UUID] = None,
    response: Response = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify magic link token and create session
    
    Sets httpOnly cookie with JWT token for session management
    """
    # Find user with this token
    result = await db.execute(
        select(User).where(User.magic_link_token == token)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid magic link")
    
    # Check if token expired
    if user.magic_link_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Magic link expired")
    
    # Clear magic link token (one-time use)
    user.magic_link_token = None
    user.magic_link_expires_at = None
    await db.commit()
    
    # Create JWT session token
    jwt_token = create_jwt_token(user.id)
    
    # Track analytics
    analytics = AnalyticsService(db)
    await analytics.track_magic_link_verified(user.id, audit_id)
    
    # If audit_id provided, associate user with audit
    if audit_id:
        from app.models import AuditJob, AuditAccessState
        audit_result = await db.execute(
            select(AuditJob).where(AuditJob.id == audit_id)
        )
        audit = audit_result.scalar_one_or_none()
        if audit and not audit.user_id:
            audit.user_id = user.id
            audit.audit_access_state = AuditAccessState.LOCKED
            await db.commit()
    
    # Set httpOnly cookie
    response = RedirectResponse(
        url=f"{settings.frontend_url}/report/{audit_id}" if audit_id else settings.frontend_url
    )
    response.set_cookie(
        key="auth_token",
        value=jwt_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=30 * 24 * 60 * 60  # 30 days
    )
    
    return response


@router.get("/me")
async def get_current_user(
    user_id: Optional[UUID] = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get current authenticated user - returns null if not authenticated"""
    if not user_id:
        return {"user": None, "authenticated": False}
    
    access_control = AccessControlService(db)
    user = await access_control.get_user_by_id(user_id)
    
    if not user:
        return {"user": None, "authenticated": False}
    
    return {
        "user": UserResponse.model_validate(user),
        "authenticated": True
    }


@router.post("/logout")
async def logout(response: Response):
    """Logout user by clearing session cookie"""
    response.delete_cookie(key="auth_token")
    return {"success": True, "message": "Logged out"}
