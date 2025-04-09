from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.db.models.user import User
from app.api import deps
from app.db.models.book import BookAvailability # Import enum

router = APIRouter()

@router.get("/", response_model=List[schemas.Book])
async def read_books(
    db: AsyncSession = Depends(deps.get_db),
    pagination: dict = Depends(deps.get_pagination_params),
    author: Optional[str] = Query(None, description="Filter by author name (case-insensitive)"),
    genre: Optional[str] = Query(None, description="Filter by genre (case-insensitive)"),
    availability: Optional[BookAvailability] = Query(None, description="Filter by availability status"),
    language: Optional[str] = Query(None, description="Filter by language (case-insensitive)"),
    # Add more filters: title, price range etc.
):
    """
    Retrieve books with optional filtering and pagination.
    Accessible to all users (registered or not).
    """
    books, total_count = await crud.book.get_multi_filtered(
        db,
        skip=pagination["skip"],
        limit=pagination["limit"],
        author=author,
        genre=genre,
        availability=availability,
        language=language,
    )
    # You can add total_count to response headers if needed (e.g., 'X-Total-Count')
    return books

@router.get("/{book_id}", response_model=schemas.BookDetail)
async def read_book(
    *,
    db: AsyncSession = Depends(deps.get_db),
    book_id: int,
):
    """
    Get book by ID, including comments and ratings.
    Accessible to all users.
    """
    book = await crud.book.get_book_with_details(db=db, book_id=book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@router.post("/{book_id}/favorite", response_model=schemas.Message, status_code=status.HTTP_201_CREATED)
async def mark_book_as_favorite(
    *,
    db: AsyncSession = Depends(deps.get_db),
    book_id: int,
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Mark a book as favorite for the current user.
    """
    book = await crud.book.get(db=db, id=book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Eagerly load favorites to prevent extra query inside add_favorite if checking there
    # user_with_favorites = await crud.user.get_user_profile(db, user_id=current_user.id)
    # await crud.book.add_favorite(db=db, user=user_with_favorites, book=book) # Pass the loaded user

    # Or load lazily (might issue another query inside add_favorite check)
    await crud.book.add_favorite(db=db, user=current_user, book=book)
    return {"message": f"Book '{book.title}' added to favorites"}

@router.delete("/{book_id}/favorite", response_model=schemas.Message)
async def unmark_book_as_favorite(
    *,
    db: AsyncSession = Depends(deps.get_db),
    book_id: int,
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Remove a book from the current user's favorites.
    """
    book = await crud.book.get(db=db, id=book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Load user with favorites to perform removal check efficiently
    # user_with_favorites = await crud.user.get_user_profile(db, user_id=current_user.id)
    # if book not in user_with_favorites.favorite_books:
    #      raise HTTPException(status_code=400, detail="Book not in favorites")
    # await crud.book.remove_favorite(db=db, user=user_with_favorites, book=book)

    # Or rely on lazy loading / check within remove_favorite
    await crud.book.remove_favorite(db=db, user=current_user, book=book) # Need to ensure the check happens

    return {"message": f"Book '{book.title}' removed from favorites"}


@router.post("/{book_id}/comments", response_model=schemas.Comment, status_code=status.HTTP_201_CREATED)
async def add_comment_to_book(
    *,
    db: AsyncSession = Depends(deps.get_db),
    book_id: int,
    comment_in: schemas.CommentCreate,
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Add a comment to a book.
    """
    book = await crud.book.get(db=db, id=book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    comment = await crud.book.add_comment(
        db=db, obj_in=comment_in, book_id=book_id, user_id=current_user.id
    )
    return comment

@router.get("/{book_id}/comments", response_model=List[schemas.Comment])
async def get_book_comments(
    *,
    db: AsyncSession = Depends(deps.get_db),
    book_id: int,
    pagination: dict = Depends(deps.get_pagination_params),
):
    """
    Get comments for a specific book.
    Accessible to all users.
    """
    book = await crud.book.get(db=db, id=book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    comments = await crud.book.get_book_comments(
        db=db, book_id=book_id, skip=pagination["skip"], limit=pagination["limit"]
        )
    return comments


@router.post("/{book_id}/rate", response_model=schemas.Rating)
async def rate_book(
    *,
    db: AsyncSession = Depends(deps.get_db),
    book_id: int,
    rating_in: schemas.RatingCreate,
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Add or update a rating for a book by the current user.
    """
    book = await crud.book.get(db=db, id=book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # You might want to add a check: can only rate if purchased?
    # purchases = await crud.user.get_user_purchases(db, user_id=current_user.id)
    # book_ids_purchased = {p.book_id for p in purchases}
    # if book_id not in book_ids_purchased:
    #     raise HTTPException(status_code=403, detail="You can only rate books you have purchased.")

    rating = await crud.book.add_or_update_rating(
        db=db, obj_in=rating_in, book_id=book_id, user_id=current_user.id
    )
    return rating

@router.get("/{book_id}/ratings", response_model=List[schemas.Rating])
async def get_book_ratings(
    *,
    db: AsyncSession = Depends(deps.get_db),
    book_id: int,
    pagination: dict = Depends(deps.get_pagination_params),
):
    """
    Get ratings for a specific book.
    Accessible to all users.
    """
    book = await crud.book.get(db=db, id=book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    ratings = await crud.book.get_book_ratings(
        db=db, book_id=book_id, skip=pagination["skip"], limit=pagination["limit"]
    )
    return ratings

# --- Admin Routes for Books ---
@router.post("/", response_model=schemas.Book, status_code=status.HTTP_201_CREATED)
async def create_book(
    *,
    db: AsyncSession = Depends(deps.get_db),
    book_in: schemas.BookCreate,
    current_user: User = Depends(deps.get_current_active_superuser), # Require admin
):
    """
    Create a new book (Admin only).
    """
    book = await crud.book.create(db=db, obj_in=book_in)
    return book

@router.put("/{book_id}", response_model=schemas.Book)
async def update_book(
    *,
    db: AsyncSession = Depends(deps.get_db),
    book_id: int,
    book_in: schemas.BookUpdate,
    current_user: User = Depends(deps.get_current_active_superuser), # Require admin
):
    """
    Update a book (Admin only).
    """
    book = await crud.book.get(db=db, id=book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    book = await crud.book.update(db=db, db_obj=book, obj_in=book_in)
    return book

@router.delete("/{book_id}", response_model=schemas.Message)
async def delete_book(
    *,
    db: AsyncSession = Depends(deps.get_db),
    book_id: int,
    current_user: User = Depends(deps.get_current_active_superuser), # Require admin
):
    """
    Delete a book (Admin only). Consider implications (existing purchases, etc.).
    Maybe mark as unavailable instead of deleting.
    """
    book = await crud.book.get(db=db, id=book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Add checks here: are there purchases associated with this book?
    # If so, maybe prevent deletion or handle it differently (e.g., anonymize book details).
    # For now, we just delete.
    deleted_book = await crud.book.remove(db=db, id=book_id)
    if not deleted_book: # Should not happen if found above, but good practice
         raise HTTPException(status_code=404, detail="Book not found during deletion")

    return {"message": f"Book '{deleted_book.title}' deleted successfully"}