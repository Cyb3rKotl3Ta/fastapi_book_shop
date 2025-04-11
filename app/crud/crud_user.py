from typing import Any, Dict, Optional, Union, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, update
from sqlalchemy.orm import selectinload, joinedload

from app.crud.base import CRUDBase
from app.db.models.user import User
from app.db.models.purchase import Purchase, PurchaseStatus
from app.db.models.book import Book
from app.schemas import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):

    async def create_user(db: AsyncSession, obj_in: UserCreate):
        """
        Create a new user with a hashed password.
        """
        hashed_password = get_password_hash(obj_in.password)
        # Exclude the plaintext password from the data
        user_data = obj_in.dict(exclude={"password"})
        db_user = User(**user_data, hashed_password=hashed_password)
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user

    async def update_user(self, db: AsyncSession, user_id: int, obj_in: UserUpdate) -> User:
        """Update an existing user record."""
        result = await db.execute(select(User).filter(User.id == user_id))
        db_obj = result.scalar_one()
        for key, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, key, value)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete_user(self, db: AsyncSession, user_id: int) -> None:
        """Delete a user record by its ID."""
        result = await db.execute(select(User).filter(User.id == user_id))
        db_obj = result.scalar_one()
        await db.delete(db_obj)
        await db.commit()

    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """Retrieve a user by email."""
        result = await db.execute(select(self.model).filter(self.model.email == email))
        return result.scalars().first()

    async def get_by_username(self, db: AsyncSession, *, username: str) -> Optional[User]:
        """Retrieve a user by username."""
        result = await db.execute(select(self.model).filter(self.model.username == username))
        return result.scalars().first()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        """Create a new user with a hashed password."""
        hashed_password = get_password_hash(obj_in.password)
        # Exclude the plaintext password from the data dictionary
        user_data = obj_in.dict(exclude={"password"})
        db_obj = self.model(**user_data, hashed_password=hashed_password)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: User,
        obj_in: Union[UserUpdate, Dict[str, Any]]
    ) -> User:
        """
        Update an existing user record. If the password is present in the update data,
        it will be hashed and replaced.
        """
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.dict(exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        elif "password" in update_data:
            del update_data["password"]

        return await super().update(db, db_obj=db_obj, obj_in=update_data)

    async def authenticate(
        self, db: AsyncSession, *, username: str, password: str
    ) -> Optional[User]:
        """
        Authenticate a user by username and password.
        Returns the user if authentication succeeds, otherwise None.
        """
        user = await self.get_by_username(db, username=username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def is_active(self, user: User) -> bool:
        """Check whether the user account is active."""
        return user.is_active

    async def is_superuser(self, user: User) -> bool:
        """Check whether the user is a superuser."""
        return user.is_superuser

    async def get_user_profile(self, db: AsyncSession, user_id: int) -> Optional[User]:
        """
        Retrieve the user profile with eagerly loaded favorite books.
        """
        result = await db.execute(
            select(User)
            .options(selectinload(User.favorite_books))
            .filter(User.id == user_id)
        )
        return result.scalars().first()

    async def get_user_purchases(self, db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> List[Purchase]:
        """
        Retrieve completed purchases for a user with the associated book details.
        """
        result = await db.execute(
            select(Purchase)
            .options(joinedload(Purchase.book))
            .filter(Purchase.user_id == user_id, Purchase.status == PurchaseStatus.COMPLETED)
            .order_by(Purchase.purchase_date.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_user_stats(self, db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """
        Calculate statistics for a user:
          - Total amount spent.
          - Count of books purchased.
          - Genre preferences based on completed purchases.
        """
        # Total spent by the user on completed purchases
        spent_result = await db.execute(
            select(func.sum(Purchase.cost_at_purchase))
            .filter(Purchase.user_id == user_id, Purchase.status == PurchaseStatus.COMPLETED)
        )
        total_spent = spent_result.scalar_one_or_none() or 0.0

        # Count of books purchased
        count_result = await db.execute(
            select(func.count(Purchase.id))
            .filter(Purchase.user_id == user_id, Purchase.status == PurchaseStatus.COMPLETED)
        )
        books_bought_count = count_result.scalar_one()

        # Calculate genre preferences based on purchase counts for each genre
        genre_result = await db.execute(
            select(Book.genre, func.count(Purchase.id).label("genre_count"))
            .join(Book, Purchase.book_id == Book.id)
            .filter(Purchase.user_id == user_id, Purchase.status == PurchaseStatus.COMPLETED)
            .group_by(Book.genre)
            .order_by(func.count(Purchase.id).desc())
        )
        genres_preference = {genre: count for genre, count in genre_result.all() if genre}

        return {
            "total_spent": float(total_spent),  # Convert Decimal to float if necessary
            "books_bought_count": books_bought_count,
            "genres_preference": genres_preference,
        }

    async def update_balance(self, db: AsyncSession, user: User, amount_change: float) -> User:
        """
        Update the user's balance by the specified amount. A negative value will decrease the balance.
        Throws a ValueError if the new balance is negative.
        """
        new_balance = user.balance + amount_change
        if new_balance < 0:
            raise ValueError("Insufficient balance")

        stmt = (
            update(User)
            .where(User.id == user.id)
            .values(balance=new_balance)
            .returning(User.balance)
        )
        await db.execute(stmt)
        # Commit should normally be handled within the calling transaction
        await db.refresh(user, ["balance"])  # Refresh the user instance to reflect the latest balance
        return user
    

# Create an instance for use elsewhere in the project.
user = CRUDUser(User)
