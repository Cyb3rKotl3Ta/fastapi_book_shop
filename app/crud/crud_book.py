from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, update, delete, and_
from sqlalchemy.orm import selectinload, joinedload

from app.crud.base import CRUDBase
from app.db.models.book import Book, Comment, Rating, BookAvailability
from app.db.models.user import User
from app.schemas import BookCreate, BookUpdate, RatingCreate # Added RatingCreate


class CRUDBook(CRUDBase[Book, BookCreate, BookUpdate]):

    async def create_book(self, db: AsyncSession, *, obj_in: BookCreate) -> Book:
        return await self.create(db=db, obj_in=obj_in)

    async def update_book(
        self, db: AsyncSession, *, book_id: int, obj_in: BookUpdate
    ) -> Optional[Book]:
        db_obj = await self.get(db=db, id=book_id)
        if not db_obj:
            return None
        return await self.update(db=db, db_obj=db_obj, obj_in=obj_in)

    async def delete_book(self, db: AsyncSession, *, book_id: int) -> Optional[Book]:
        return await self.remove(db=db, id=book_id)

    async def get_multi_filtered(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        author: Optional[str] = None,
        genre: Optional[str] = None,
        availability: Optional[BookAvailability] = None,
        language: Optional[str] = None
    ) -> Tuple[List[Book], int]:
        query = select(self.model)
        count_query = select(func.count()).select_from(self.model)

        filters = []
        if author:
            filters.append(self.model.author.ilike(f"%{author}%"))
        if genre:
            filters.append(self.model.genre.ilike(f"%{genre}%"))
        if availability:
            filters.append(self.model.availability_status == availability)
        if language:
             filters.append(self.model.language.ilike(f"%{language}%"))

        if filters:
            query = query.filter(and_(*filters))
            count_query = count_query.filter(and_(*filters))

        total_count_result = await db.execute(count_query)
        total_count = total_count_result.scalar_one()

        result = await db.execute(
             query.order_by(self.model.title).offset(skip).limit(limit)
        )
        books = result.scalars().all()
        return books, total_count

    async def get_book_with_details(self, db: AsyncSession, *, book_id: int) -> Optional[Book]:
        avg_rating_subquery = (
            select(func.avg(Rating.score).label("avg_rating"))
            .filter(Rating.book_id == book_id)
            .scalar_subquery()
        )

        result = await db.execute(
            select(self.model, avg_rating_subquery)
            .outerjoin(Rating, self.model.id == Rating.book_id)
            .options(
                selectinload(self.model.comments).options(joinedload(Comment.user, innerjoin=False)),
                selectinload(self.model.ratings).options(joinedload(Rating.user, innerjoin=False))
             )
            .filter(self.model.id == book_id)
            .group_by(self.model.id)
        )

        row = result.first()
        if row:
            book_obj, avg_rating = row # Renamed book to book_obj to avoid shadowing module
            book_obj.average_rating = float(avg_rating) if avg_rating is not None else None
            return book_obj
        return None

    async def add_favorite(self, db: AsyncSession, *, user: User, book: Book) -> None:
        if user not in db:
            user = await db.merge(user)
        if book not in db:
            book = await db.merge(book)

        if book not in user.favorite_books:
            user.favorite_books.append(book)
            db.add(user)
            await db.commit()

    async def remove_favorite(self, db: AsyncSession, *, user: User, book: Book) -> None:
        if user not in db:
            user = await db.merge(user)
        if book not in db:
            book = await db.merge(book)

        if book in user.favorite_books:
            user.favorite_books.remove(book)
            db.add(user)
            await db.commit()

    async def get_user_favorites(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Book]:
        result = await db.execute(
             select(self.model)
             .join(self.model.favorited_by_users)
             .filter(User.id == user_id)
             .order_by(self.model.title)
             .offset(skip)
             .limit(limit)
        )
        return result.scalars().all()

    # --- Rating Methods Re-added ---

    async def add_or_update_rating(
        self, db: AsyncSession, *, obj_in: RatingCreate, book_id: int, user_id: int
    ) -> Rating:
        existing_rating_result = await db.execute(
            select(Rating).filter(Rating.user_id == user_id, Rating.book_id == book_id)
        )
        db_rating = existing_rating_result.scalars().first()

        if db_rating:
            db_rating.score = obj_in.score
            db.add(db_rating)
        else:
            db_rating = Rating(**obj_in.dict(), book_id=book_id, user_id=user_id)
            db.add(db_rating)

        await db.commit()
        await db.refresh(db_rating, ["user"])
        return db_rating

    async def get_book_ratings(
        self, db: AsyncSession, *, book_id: int, skip: int = 0, limit: int = 100
    ) -> List[Rating]:
        result = await db.execute(
            select(Rating)
            .options(joinedload(Rating.user))
            .filter(Rating.book_id == book_id)
            .order_by(Rating.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_average_rating(self, db: AsyncSession, *, book_id: int) -> Optional[float]:
         result = await db.execute(
             select(func.avg(Rating.score)).filter(Rating.book_id == book_id)
         )
         avg_rating = result.scalar_one_or_none()
         return float(avg_rating) if avg_rating is not None else None


book = CRUDBook(Book)