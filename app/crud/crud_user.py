from typing import Any, Dict, Optional, Union, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, update
from sqlalchemy.orm import selectinload, joinedload
from decimal import Decimal

from app.crud.base import CRUDBase
from app.db.models.user import User
from app.db.models.purchase import Purchase, PurchaseStatus
from app.db.models.book import Book, Comment, Rating
from app.schemas import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    
    async def create_user(self, db: AsyncSession, obj_in: UserCreate) -> User:
        db_obj = User(**obj_in.dict())
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update_user(self, db: AsyncSession, user_id: int, obj_in: UserUpdate) -> User:
        db_obj = await db.execute(select(User).filter(User.id == user_id))
        db_obj = db_obj.scalar_one()
        for key, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, key, value)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete_user(self, db: AsyncSession, user_id: int) -> None:
        db_obj = await db.execute(select(User).filter(User.id == user_id))
        db_obj = db_obj.scalar_one()
        await db.delete(db_obj)
        await db.commit()
        
    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        result = await db.execute(select(self.model).filter(self.model.email == email))
        return result.scalars().first()

    async def get_by_username(self, db: AsyncSession, *, username: str) -> Optional[User]:
        result = await db.execute(select(self.model).filter(self.model.username == username))
        return result.scalars().first()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        hashed_password = get_password_hash(obj_in.password)
        # Create a dictionary excluding the plain password
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
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.dict(exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        elif "password" in update_data: # Handle case where password might be None or empty
             del update_data["password"]

        return await super().update(db, db_obj=db_obj, obj_in=update_data)

    async def authenticate(
        self, db: AsyncSession, *, username: str, password: str
    ) -> Optional[User]:
        user = await self.get_by_username(db, username=username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def is_active(self, user: User) -> bool:
        return user.is_active

    async def is_superuser(self, user: User) -> bool:
        return user.is_superuser

    async def get_user_profile(self, db: AsyncSession, user_id: int) -> Optional[User]:
        """ Gets user with eagerly loaded favorite books """
        result = await db.execute(
            select(User)
            .options(selectinload(User.favorite_books))
            .filter(User.id == user_id)
        )
        return result.scalars().first()

    async def get_user_purchases(self, db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> List[Purchase]:
        """ Gets completed purchases for a user with book details """
        result = await db.execute(
            select(Purchase)
            .options(joinedload(Purchase.book)) # Eagerly load book details
            .filter(Purchase.user_id == user_id, Purchase.status == PurchaseStatus.COMPLETED)
            .order_by(Purchase.purchase_date.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_user_stats(self, db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """ Calculates user statistics """
        # Total spent
        spent_result = await db.execute(
            select(func.sum(Purchase.cost_at_purchase))
            .filter(Purchase.user_id == user_id, Purchase.status == PurchaseStatus.COMPLETED)
        )
        total_spent = spent_result.scalar_one_or_none() or 0.0

        # Books bought count
        count_result = await db.execute(
            select(func.count(Purchase.id))
            .filter(Purchase.user_id == user_id, Purchase.status == PurchaseStatus.COMPLETED)
        )
        books_bought_count = count_result.scalar_one()

        # Genre preferences (based on completed purchases)
        genre_result = await db.execute(
            select(Book.genre, func.count(Purchase.id).label("genre_count"))
            .join(Book, Purchase.book_id == Book.id)
            .filter(Purchase.user_id == user_id, Purchase.status == PurchaseStatus.COMPLETED)
            .group_by(Book.genre)
            .order_by(func.count(Purchase.id).desc())
        )
        genres_preference = {genre: count for genre, count in genre_result.all() if genre} # Filter out None genres

        return {
            "total_spent": float(total_spent), # Ensure float conversion if using Decimal
            "books_bought_count": books_bought_count,
            "genres_preference": genres_preference,
        }

    async def update_balance(self, db: AsyncSession, user: User, amount_change: float) -> User:
        """ Updates user balance. Use negative amount_change to decrease. """
        # Use Float directly or cast if needed
        new_balance = user.balance + amount_change
        if new_balance < 0:
            raise ValueError("Insufficient balance") # Or handle this specific error elsewhere

        stmt = (
            update(User)
            .where(User.id == user.id)
            .values(balance=new_balance)
            .returning(User.balance) # Optional: return the updated balance directly
        )
        result = await db.execute(stmt)
        # await db.commit() # Commit is handled by the calling function's transaction usually
        await db.refresh(user, ["balance"]) # Refresh the user object's balance
        # Verify update (optional)
        # updated_balance = result.scalar_one()
        # if updated_balance != new_balance:
        #     # Handle potential concurrency issue or error
        #     pass
        return user


user = CRUDUser(User)