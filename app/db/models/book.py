import enum
from sqlalchemy import Column, Integer, String, Text, Float, Enum as SQLEnum, ForeignKey, Date, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal

from app.db.base import Base
from app.db.models.association_tables import user_favorite_books_table

class BookAvailability(str, enum.Enum):
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress" # e.g., pre-order or being restocked
    NOT_AVAILABLE = "not_available"

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    author = Column(String, index=True, nullable=False)
    genre = Column(String, index=True, nullable=True)
    pages = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    cost = Column(Float(precision=10, decimal_return_scale=2), nullable=False) # Use Float or Numeric
    language = Column(String, nullable=True)
    availability_status = Column(SQLEnum(BookAvailability), nullable=False, default=BookAvailability.AVAILABLE)
    publication_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    purchases = relationship("Purchase", back_populates="book")
    comments = relationship("Comment", back_populates="book")
    ratings = relationship("Rating", back_populates="book")
    favorited_by_users = relationship(
        "User",
        secondary=user_favorite_books_table,
        back_populates="favorite_books"
    )

class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)

    user = relationship("User", back_populates="comments")
    book = relationship("Book", back_populates="comments")

class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (UniqueConstraint('user_id', 'book_id', name='_user_book_uc'),)

    id = Column(Integer, primary_key=True, index=True)
    score = Column(Integer, nullable=False) # e.g., 1 to 5
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)

    user = relationship("User", back_populates="ratings")
    book = relationship("Book", back_populates="ratings")