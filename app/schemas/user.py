from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal # Import Decimal
from app.schemas.book import Book # Import Book schema for favorites/purchases
# Import Purchase schema (define below or in purchase.py)

# Forward declaration or define Purchase schema first
class Purchase(BaseModel): # Define Purchase schema here or import from purchase.py
    id: int
    book_id: int
    purchase_date: datetime
    status: str # Use the enum from models or string
    cost_at_purchase: float # Use float or Decimal
    book: Book # Nested Book info

    class Config:
        orm_mode = True


# --- Base Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    # Add is_book_manager here if you want it settable during creation by default
    # is_book_manager: bool = False

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    # Explicitly allow setting roles on creation if needed (usually done by admin later)
    is_active: bool = True
    is_superuser: bool = False
    is_book_manager: bool = False


# --- Schemas for Reading (API Responses) ---
class User(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    is_book_manager: bool # Add the field here
    balance: float # Use float or Decimal
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Avoid sending password hash

    class Config:
        orm_mode = True

# Schema for the user's personal dashboard/profile
class UserProfile(User):
    favorite_books: List[Book] = []
    # purchased_books are derived from 'purchases' relationship in the model
    # Add purchased_books field if you want direct access after processing purchases
    # purchased_books: List[Book] = [] # This would require extra logic in the endpoint

# Schema for user statistics
class UserStats(BaseModel):
    total_spent: float = 0.0 # Use float or Decimal
    books_bought_count: int = 0
    genres_preference: dict[str, int] = {} # Genre: Count

# --- Schemas for Updating ---
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=6) # For password change
    is_active: Optional[bool] = None  # Allow admin/user to update active status
    is_superuser: Optional[bool] = None # Allow admin to update superuser status
    is_book_manager: Optional[bool] = None # Allow admin to update book manager status