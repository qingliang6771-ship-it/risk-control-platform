"""Authentication router - Lark OAuth."""
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..config import settings
from ..database import get_db
from ..models.user import User
from ..services.lark_auth import lark_auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()


def create_access_token(data: dict) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> dict:
    """Verify JWT token and return payload."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_current_user_dep(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency to get current authenticated user."""
    token = credentials.credentials
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is deactivated")
    return user


@router.get("/lark/login")
async def lark_login():
    """Get Lark OAuth login URL."""
    login_url = lark_auth_service.get_login_url(state="risk-control")
    return {"login_url": login_url}


@router.get("/lark/callback")
async def lark_callback(code: str, state: str = "", db: AsyncSession = Depends(get_db)):
    """Handle Lark OAuth callback."""
    try:
        # Exchange code for user access token
        token_data = await lark_auth_service.get_user_access_token(code)
        user_access_token = token_data["access_token"]

        # Get user info from Lark
        user_info = await lark_auth_service.get_user_info(user_access_token)

        open_id = user_info.get("open_id")
        name = user_info.get("name", "Unknown")
        email = user_info.get("email", "")
        avatar_url = user_info.get("avatar_url", "")
        union_id = user_info.get("union_id", "")

        # Upsert user in database
        result = await db.execute(select(User).where(User.lark_open_id == open_id))
        user = result.scalar_one_or_none()

        if user:
            user.name = name
            user.email = email
            user.avatar_url = avatar_url
            user.last_login = datetime.utcnow()
        else:
            user = User(
                id=open_id,
                name=name,
                email=email,
                avatar_url=avatar_url,
                lark_open_id=open_id,
                lark_union_id=union_id,
            )
            db.add(user)

        await db.commit()

        # Create JWT token
        access_token = create_access_token({"sub": open_id, "name": name, "email": email})

        # Redirect to frontend with token
        redirect_url = f"{settings.FRONTEND_URL}/auth/callback?token={access_token}"
        return RedirectResponse(url=redirect_url)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user_dep)):
    """Get current user profile."""
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "avatar_url": current_user.avatar_url,
        "department": current_user.department,
    }
