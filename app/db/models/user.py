# app/db/models/user.py
import enum
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal

from app.db.base import Base
from app.db.models.association_tables import user_favorite_books_table

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, index=True, nullable=True)
    balance = Column(Float(precision=10, decimal_return_scale=2), nullable=False, default=0.0) # Use Float or Numeric for money
    is_active = Column(Boolean(), default=True, nullable=False)
    is_superuser = Column(Boolean(), default=False, nullable=False) # Optional: for admin roles
    is_book_manager = Column(Boolean(), default=False, nullable=False) # New field for book management role
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    purchases = relationship("Purchase", back_populates="user")
    comments = relationship("Comment", back_populates="user")
    ratings = relationship("Rating", back_populates="user")
    favorite_books = relationship(
        "Book",
        secondary=user_favorite_books_table,
        back_populates="favorited_by_users"
    )