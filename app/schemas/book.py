from pydantic import BaseModel, Field, constr
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal # Import Decimal
from app.db.models.book import BookAvailability # Keep this for read schemas

# --- Base Schema (Common fields for creation/reading, excluding auto-managed ones) ---
class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(..., min_length=1, max_length=100)
    genre: Optional[str] = Field(None, max_length=50)
    pages: Optional[int] = Field(None, gt=0)
    description: Optional[str] = None
    # Use Decimal for currency fields
    cost: Decimal = Field(..., gt=Decimal('0.00'), decimal_places=2)
    language: Optional[str] = Field(None, max_length=50)
    # book_count is required as per model (nullable=False) and drives availability
    book_count: int = Field(..., ge=0) # Must be >= 0
    publication_date: Optional[date] = None
    # availability_status is removed - it will be set by the model event listener

class CommentBase(BaseModel):
    text: str = Field(..., min_length=1)

class RatingBase(BaseModel):
    score: int = Field(..., ge=1, le=5)

# --- Schemas for Creation ---
class BookCreate(BookBase):
    # Inherits all fields from BookBase.
    # User provides book_count, availability_status is determined automatically.
    pass

class CommentCreate(CommentBase):
    pass

class RatingCreate(RatingBase):
    pass

# --- Schemas for Reading (API Responses) ---
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

# Define Book read schema explicitly to include all necessary fields
class Book(BaseModel): # Don't inherit BookBase if it omits fields needed for read
    id: int
    title: str
    author: str
    genre: Optional[str] = None
    pages: Optional[int] = None
    description: Optional[str] = None
    cost: Decimal # Output cost as Decimal
    language: Optional[str] = None
    book_count: int
    availability_status: BookAvailability # Include status read from DB
    publication_date: Optional[date] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    average_rating: Optional[float] = None # Keep calculated field

    class Config:
        orm_mode = True
        # If using Decimal, Pydantic v1 might need json_encoders
        # json_encoders = {Decimal: str} # To serialize Decimal as string in JSON

class BookDetail(Book): # Inherit from the corrected Book read schema
    comments: List[Comment] = []
    ratings: List[Rating] = []
    # Config is inherited


# --- Schemas for Updating ---
class BookUpdate(BaseModel):
    # All fields are optional for partial updates
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    author: Optional[str] = Field(None, min_length=1, max_length=100)
    genre: Optional[str] = Field(None, max_length=50)
    pages: Optional[int] = Field(None, gt=0)
    description: Optional[str] = None
    cost: Optional[Decimal] = Field(None, gt=Decimal('0.00'), decimal_places=2)
    language: Optional[str] = Field(None, max_length=50)
    # User can update book_count
    book_count: Optional[int] = Field(None, ge=0)
    publication_date: Optional[date] = None