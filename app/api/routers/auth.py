from typing import List, Any
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core import security 
from app import crud, schemas
from app.crud import crud_user
from app.db.models.user import User
from app.api import deps

router = APIRouter()

@router.post("/", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
async def register_user(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_in: schemas.UserCreate,
):
    """
    Create new user.
    """
    user = await crud_user.user.get_by_username(db, username=user_in.username)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    user = await crud_user.user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    user = await crud_user.user.create(db=db, obj_in=user_in)
    # Add initial balance if desired, e.g. 100.0
    # await crud.user.update_balance(db, user=user, amount_change=100.0)
    return user

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

# Corrected imports:
from app import schemas
from app.crud.crud_user import user as crud_user # Import the specific instance
from app.api import deps
from app.core.config import settings
from app.core import security

router = APIRouter()

@router.post("/login", response_model=schemas.Token)
async def login_for_access_token(
    db: AsyncSession = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.

    Takes username and password in form data.
    """
    # Use the imported crud_user instance
    user = await crud_user.authenticate(
        db, username=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Check if user account is active using the imported crud_user instance
    if not crud_user.is_active(user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Generate the access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.UserProfile)
async def read_users_me(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Get current user profile including favorite books.
    Purchased books are available via the /me/purchases endpoint.
    """
    # Fetch user profile data including favorites
    user_profile = await crud_user.user.get_user_profile(db, user_id=current_user.id)
    if not user_profile:
         raise HTTPException(status_code=404, detail="User not found") # Should not happen if token is valid

    return user_profile # Pydantic will automatically map the relationships

@router.put("/me", response_model=schemas.User)
async def update_user_me(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_in: schemas.UserUpdate,
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Update own user.
    """
    # Check for username collision if username is being changed
    if user_in.username and user_in.username != current_user.username:
        existing_user = await crud_user.user.get_by_username(db, username=user_in.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already taken.")

    # Check for email collision if email is being changed
    if user_in.email and user_in.email != current_user.email:
        existing_user = await crud_user.user.get_by_email(db, email=user_in.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered.")

    user = await crud_user.user.update(db, db_obj=current_user, obj_in=user_in)
    return user

@router.get("/me/purchases", response_model=List[schemas.Purchase])
async def read_my_purchases(
    db: AsyncSession = Depends(deps.get_db),
    pagination: dict = Depends(deps.get_pagination_params),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Retrieve list of completed purchases for the current user.
    """
    purchases = await crud_user.user.get_user_purchases(
        db, user_id=current_user.id, skip=pagination["skip"], limit=pagination["limit"]
    )
    return purchases


@router.get("/me/favorites", response_model=List[schemas.Book])
async def read_my_favorites(
    db: AsyncSession = Depends(deps.get_db),
    pagination: dict = Depends(deps.get_pagination_params),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Retrieve list of favorite books for the current user.
    """
    favorites = await crud_user.book.get_user_favorites(
        db, user_id=current_user.id, skip=pagination["skip"], limit=pagination["limit"]
        )
    return favorites


@router.get("/me/stats", response_model=schemas.UserStats)
async def read_my_stats(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Retrieve statistics for the current user (total spent, genre preferences, etc.).
    """
    stats = await crud_user.user.get_user_stats(db, user_id=current_user.id)
    return stats


# Example Admin endpoint (requires superuser)
@router.get("/{user_id}", response_model=schemas.User)
async def read_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_superuser),
):
    """
    Get a specific user by id (Admin only).
    """
    user = await crud_user.user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    return user