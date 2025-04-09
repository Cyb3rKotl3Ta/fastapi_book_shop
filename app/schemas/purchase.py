from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal # Import Decimal
from app.db.models.purchase import PurchaseStatus
from app.schemas.book import Book # Import Book schema for nested display
from app.schemas.user import User # Import User schema if needed


# --- Base Schemas ---
class PurchaseBase(BaseModel):
    book_id: int
    # user_id is usually implicit (current user) or handled internally
    cost_at_purchase: float # Use float or Decimal

# --- Schemas for Creation (e.g., adding to cart) ---
class CartItemCreate(BaseModel):
    book_id: int
    # Cost will be fetched from the book price when adding

# --- Schemas for Reading (API Responses) ---
class Purchase(PurchaseBase):
    id: int
    user_id: int
    purchase_date: datetime
    status: PurchaseStatus # Use the Enum directly if desired
    book: Book # Include book details

    class Config:
        orm_mode = True

# Schema for items currently in the user's cart
class CartItem(BaseModel):
    id: int # This is the purchase ID with status IN_CART
    book_id: int
    cost_at_purchase: float # Use float or Decimal
    added_at: datetime # Corresponds to purchase_date for IN_CART items
    book: Book # Include book details

    class Config:
        orm_mode = True

class Cart(BaseModel):
    items: List[CartItem] = []
    total_cost: float = 0.0 # Use float or Decimal


# --- Schemas for Updating (e.g., checkout) ---
# No specific update schema usually needed, actions trigger status changes
# Checkout might not need a body, or just confirmation details