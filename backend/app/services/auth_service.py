"""
Authentication and User Management service.
Enforces password hashing, strict role assignment ('user' on public registration),
and privilege escalation protections.
"""
from fastapi import HTTPException, status
from app.config import settings
from app.database import Session
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    UserRoleUpdateRequest,
)
from app.utils.security import create_access_token, hash_password, verify_password


class AuthService:
    """Handles user registration, login, and administrative user management."""

    @staticmethod
    def register_user(db: Session, payload: RegisterRequest) -> TokenResponse:
        """
        Register a new user account.
        SECURITY RULE: Public registrations ALWAYS receive the 'user' role.
        """
        existing = db.query(User).filter(User.email == payload.email.lower()).first()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address is already registered.",
            )

        new_user = User(
            name=payload.name.strip(),
            email=payload.email.lower().strip(),
            hashed_password=hash_password(payload.password),
            role="user",  # Strictly enforced: never allow public admin creation
            is_active=True,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        access_token = create_access_token(
            subject=new_user.email,
            user_id=new_user.id,
            role=new_user.role,
        )
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.from_orm(new_user),
        )

    @staticmethod
    def authenticate_user(db: Session, payload: LoginRequest) -> TokenResponse:
        """Verify email and password, returning a signed JWT access token."""
        user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not getattr(user, "is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This user account has been deactivated by an administrator.",
            )

        access_token = create_access_token(
            subject=user.email,
            user_id=user.id,
            role=user.role,
        )
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.from_orm(user),
        )

    @staticmethod
    def update_user_by_admin(
        db: Session,
        target_user_id: int,
        payload: UserRoleUpdateRequest,
        acting_admin: User,
    ) -> User:
        """
        Allow an administrator to update a user's role or active status.
        Prevents an admin from demoting or deactivating their own account to avoid lockout.
        """
        target_user = db.query(User).filter(User.id == target_user_id).first()
        if target_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {target_user_id} not found.",
            )

        if target_user.id == acting_admin.id:
            if payload.role is not None and payload.role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Administrators cannot demote their own account.",
                )
            if payload.is_active is False:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Administrators cannot deactivate their own account.",
                )

        if payload.role is not None:
            target_user.role = payload.role
        if payload.is_active is not None:
            target_user.is_active = payload.is_active
        if payload.name is not None:
            target_user.name = payload.name.strip()

        db.add(target_user)
        db.commit()
        db.refresh(target_user)
        return target_user
