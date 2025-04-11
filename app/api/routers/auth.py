from typing import List, Any
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, Security
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core import security
from app import schemas
from app.crud import crud_book, crud_user
from app.db.models.user import User
from app.api import deps

router = APIRouter()


@router.post("/", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
async def register_user(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_in: schemas.UserCreate,
) -> schemas.User:
    """
    Create a new user.
    """
    # Check if a user with the given username already exists.
    existing_user = await crud_user.user.get_by_username(db, username=user_in.username)
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="User with this username already exists in the system."
        )

    # Check if a user with the given email already exists.
    existing_user = await crud_user.user.get_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists in the system."
        )

    # Create and return the new user.
    new_user = await crud_user.user.create(db=db, obj_in=user_in)
    return new_user


@router.post("/login", response_model=schemas.Token)
async def login_for_access_token(
    db: AsyncSession = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login. Receives username and password in form data
    and returns a bearer token if authentication is successful.
    """
    user = await crud_user.user.authenticate(
        db, username=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not crud_user.user.is_active(user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Generate the access token with an expiration time.
    token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=token_expires
    )
    return {"token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserProfile)
async def read_users_me(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Security(deps.get_current_active_user),
) -> schemas.UserProfile:
    """
    Retrieve the current user's profile, including favorite books.
    """
    print(f"Current user: {current_user.username}")
    profile = await crud_user.user.get_user_profile(db, user_id=current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return profile


@router.put("/me", response_model=schemas.User)
async def update_user_me(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_in: schemas.UserUpdate,
    current_user: User = Security(deps.get_current_active_user),
) -> schemas.User:
    """
    Update the current user's data.
    """
    # Ensure the new username, if provided, is unique.
    if user_in.username and user_in.username != current_user.username:
        existing_user = await crud_user.user.get_by_username(db, username=user_in.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username is already taken.")

    # Ensure the new email, if provided, is unique.
    if user_in.email and user_in.email != current_user.email:
        existing_user = await crud_user.user.get_by_email(db, email=user_in.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email is already registered.")

    updated_user = await crud_user.user.update(db, db_obj=current_user, obj_in=user_in)
    return updated_user


@router.get("/me/purchases", response_model=List[schemas.Purchase])
async def read_my_purchases(
    db: AsyncSession = Depends(deps.get_db),
    pagination: dict = Depends(deps.get_pagination_params),
    current_user: User = Security(deps.get_current_active_user),
) -> List[schemas.Purchase]:
    """
    Retrieve the list of completed purchases for the current user.
    """
    purchases = await crud_user.user.get_user_purchases(
        db, user_id=current_user.id, skip=pagination["skip"], limit=pagination["limit"]
    )
    return purchases


@router.get("/me/favorites", response_model=List[schemas.Book])
async def read_my_favorites(
    db: AsyncSession = Depends(deps.get_db),
    pagination: dict = Depends(deps.get_pagination_params),
    current_user: User = Security(deps.get_current_active_user),
) -> List[schemas.Book]:
    """
    Retrieve the list of favorite books for the current user.
    """
    favorites = await crud_book.book.get_user_favorites(
        db, user_id=current_user.id, skip=pagination["skip"], limit=pagination["limit"]
    )
    return favorites


@router.get("/me/stats", response_model=schemas.UserStats)
async def read_my_stats(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Security(deps.get_current_active_user),
) -> schemas.UserStats:
    """
    Retrieve user statistics (such as total spent and genre preferences).
    """
    stats = await crud_user.user.get_user_stats(db, user_id=current_user.id)
    return stats


@router.get("/{user_id}", response_model=schemas.User)
async def read_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Security(deps.get_current_active_user),
) -> schemas.User:
    """
    Retrieve a specific user by id (Admin only).
    """
    user = await crud_user.user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User with the given id does not exist in the system.",
        )
    return user
