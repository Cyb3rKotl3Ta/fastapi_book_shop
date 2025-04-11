from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt

from app.core import security
from app.db.base import get_db
from app.db.models.user import User
from app.crud.crud_user import user as crud_user
from app.schemas import TokenData

# security_bearer = HTTPBearer()

security_bearer = OAuth2PasswordBearer(tokenUrl="/api/v1/login")

async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(security_bearer)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    username = security.decode_access_token(token)
    if username is None:
        raise credentials_exception
    token_data = TokenData(username=username)

    user = await crud_user.get_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not crud_user.is_active(current_user):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if not crud_user.is_superuser(current_user):
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user

# Dependency for pagination parameters
async def get_pagination_params(
    skip: int = 0,
    limit: int = 100,
) -> dict:
    # Add validation if needed (e.g., limit <= max_limit)
    return {"skip": skip, "limit": limit}