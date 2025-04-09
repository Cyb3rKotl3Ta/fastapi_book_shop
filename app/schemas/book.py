from pydantic import BaseModel, Field, constr
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal # Import Decimal
from app.db.models.book import BookAvailability

# --- Base Schemas ---
class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(..., min_length=1, max_length=100)
    genre: Optional[str] = Field(None, max_length=50)
    pages: Optional[int] = Field(None, gt=0)
    description: Optional[str] = None
    cost: float = Field(..., gt=0) # Use float or Decimal
    language: Optional[str] = Field(None, max_length=50)
    availability_status: BookAvailability = BookAvailability.AVAILABLE
    publication_date: Optional[date] = None

class CommentBase(BaseModel):
    text: str = Field(..., min_length=1)

class RatingBase(BaseModel):
    score: int = Field(..., ge=1, le=5)

# --- Schemas for Creation ---
class BookCreate(BookBase):
    pass

class CommentCreate(CommentBase):
    pass

class RatingCreate(RatingBase):
    pass

# --- Schemas for Reading (API Responses) ---
# Need UserMinimal for nested display to avoid circular imports if needed later
# Or define it here/in user.py and import carefully
class UserMinimal(BaseModel):
    id: int
    username: str

    class Config:
        orm_mode = True


class Comment(CommentBase):
    id: int
    user_id: int
    book_id: int
    created_at: datetime
    user: UserMinimal # Display minimal user info

    class Config:
        orm_mode = True

class Rating(RatingBase):
    id: int
    user_id: int
    book_id: int
    created_at: datetime
    user: UserMinimal # Display minimal user info

    class Config:
        orm_mode = True

class Book(BookBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    average_rating: Optional[float] = None # Add calculated field
    # comments: List[Comment] = [] # Optionally include comments/ratings directly
    # ratings: List[Rating] = [] # Be mindful of large responses

    class Config:
        orm_mode = True 

class BookDetail(Book): # Inherit from Book and add more details
    comments: List[Comment] = []
    ratings: List[Rating] = []


# --- Schemas for Updating ---
class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    author: Optional[str] = Field(None, min_length=1, max_length=100)
    genre: Optional[str] = Field(None, max_length=50)
    pages: Optional[int] = Field(None, gt=0)
    description: Optional[str] = None
    cost: Optional[float] = Field(None, gt=0) # Use float or Decimal
    language: Optional[str] = Field(None, max_length=50)
    availability_status: Optional[BookAvailability] = None
    publication_date: Optional[date] = None