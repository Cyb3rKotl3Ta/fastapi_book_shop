from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, update, delete, and_
from sqlalchemy.orm import selectinload, joinedload

from app.crud.base import CRUDBase, BaseModel
from app.db.models.book import Book, Comment, Rating, BookAvailability
from app.db.models.user import User
from app.schemas import BookCreate, BookUpdate, CommentCreate, RatingCreate

class CRUDBook(CRUDBase[Book, BookCreate, BookUpdate]):

    async def create_book(self, db: AsyncSession, obj_in: BookCreate) -> Book:
        db_obj = Book(**obj_in.dict())
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update_book(self, db: AsyncSession, book_id: int, obj_in: BookUpdate) -> Book:
        db_obj = await db.execute(select(Book).filter(Book.id == book_id))
        db_obj = db_obj.scalar_one()
        for key, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, key, value)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete_book(self, db: AsyncSession, book_id: int) -> None:
        db_obj = await db.execute(select(Book).filter(Book.id == book_id))
        db_obj = db_obj.scalar_one()
        await db.delete(db_obj)
        await db.commit()

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


    async def get_book_with_details(self, db: AsyncSession, book_id: int) -> Optional[Book]:
        """ Gets a single book with comments, ratings, and avg rating """
        # Calculate average rating
        avg_rating_subquery = (
            select(func.avg(Rating.score).label("avg_rating"))
            .filter(Rating.book_id == book_id)
            .scalar_subquery()
        )

        result = await db.execute(
            select(Book, avg_rating_subquery)
            .outerjoin(Rating, Book.id == Rating.book_id) # Ensure book is returned even with 0 ratings
            .options(
                selectinload(Book.comments).options(joinedload(Comment.user)), # Load comments and their users
                selectinload(Book.ratings).options(joinedload(Rating.user))   # Load ratings and their users
             )
            .filter(Book.id == book_id)
            .group_by(Book.id) # Group by Book ID to make aggregate work correctly with joins
        )
        # Use .first() because we expect one book or None
        row = result.first()
        if row:
            book, avg_rating = row
            book.average_rating = float(avg_rating) if avg_rating is not None else None
            return book
        return None


    async def add_favorite(self, db: AsyncSession, *, user: User, book: Book) -> None:
        if book not in user.favorite_books:
            user.favorite_books.append(book)
            db.add(user)
            await db.commit()
            # await db.refresh(user, ["favorite_books"]) # Refresh might be needed if accessed immediately after

    async def remove_favorite(self, db: AsyncSession, *, user: User, book: Book) -> None:
        if book in user.favorite_books:
            user.favorite_books.remove(book)
            db.add(user)
            await db.commit()
            # await db.refresh(user, ["favorite_books"]) # Refresh might be needed

    async def get_user_favorites(self, db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> List[Book]:
        result = await db.execute(
            select(Book)
            .join(Book.favorited_by_users)
            .filter(User.id == user_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def add_comment(self, db: AsyncSession, *, obj_in: CommentCreate, book_id: int, user_id: int) -> Comment:
        db_comment = Comment(**obj_in.dict(), book_id=book_id, user_id=user_id)
        db.add(db_comment)
        await db.commit()
        await db.refresh(db_comment, ["user"]) # Load user relationship after commit
        return db_comment

    async def get_book_comments(self, db: AsyncSession, book_id: int, skip: int = 0, limit: int = 100) -> List[Comment]:
        result = await db.execute(
            select(Comment)
            .options(joinedload(Comment.user)) # Eager load user info
            .filter(Comment.book_id == book_id)
            .order_by(Comment.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def add_or_update_rating(self, db: AsyncSession, *, obj_in: RatingCreate, book_id: int, user_id: int) -> Rating:
        # Check if rating already exists
        existing_rating_result = await db.execute(
            select(Rating).filter(Rating.user_id == user_id, Rating.book_id == book_id)
        )
        db_rating = existing_rating_result.scalars().first()

        if db_rating:
            # Update existing rating
            db_rating.score = obj_in.score
            # Optionally update timestamp: db_rating.created_at = func.now() # Or add an updated_at field
            db.add(db_rating)
        else:
            # Create new rating
            db_rating = Rating(**obj_in.dict(), book_id=book_id, user_id=user_id)
            db.add(db_rating)

        await db.commit()
        await db.refresh(db_rating, ["user"]) # Load user relationship
        return db_rating

    async def get_book_ratings(self, db: AsyncSession, book_id: int, skip: int = 0, limit: int = 100) -> List[Rating]:
        result = await db.execute(
            select(Rating)
            .options(joinedload(Rating.user)) # Eager load user info
            .filter(Rating.book_id == book_id)
            .order_by(Rating.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    # Optional: Calculate average rating separately if not done in get_book_with_details
    async def get_average_rating(self, db: AsyncSession, book_id: int) -> Optional[float]:
         result = await db.execute(
             select(func.avg(Rating.score)).filter(Rating.book_id == book_id)
         )
         avg_rating = result.scalar_one_or_none()
         return float(avg_rating) if avg_rating is not None else None


book = CRUDBook(Book)
comment = CRUDBase(Comment, CommentCreate, BaseModel) # Basic CRUD for comments if needed elsewhere
rating = CRUDBase(Rating, RatingCreate, BaseModel) # Basic CRUD for ratings if needed elsewhere