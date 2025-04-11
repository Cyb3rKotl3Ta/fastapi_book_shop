import enum
from sqlalchemy import (
    Column, Integer, String, Text, Float, Enum as SQLEnum, ForeignKey,
    Date, DateTime, UniqueConstraint, event # <--- Import event
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
# from decimal import Decimal # Not used if sticking with Float

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
    # Consider sqlalchemy.Numeric if you need exact decimal precision for currency
    cost = Column(Float(precision=10, decimal_return_scale=2), nullable=False)
    language = Column(String, nullable=True)

    # --- Make book_count non-nullable and set a default ---
    book_count = Column(Integer, nullable=False, default=0) # Default to 0

    # --- Set default availability based on default book_count ---
    availability_status = Column(
        SQLEnum(BookAvailability),
        nullable=False,
        default=BookAvailability.NOT_AVAILABLE # Matches default book_count=0
    )
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

# --- Event Listener for Book Availability ---

@event.listens_for(Book, 'before_insert')
@event.listens_for(Book, 'before_update')
def update_book_availability_status(mapper, connection, target: Book):
    """
    SQLAlchemy event listener to automatically set the book's
    availability_status based on its book_count before insert or update.
    """
    # Check if book_count is explicitly set (it should be due to nullable=False)
    # but defensive check is okay.
    if target.book_count is not None:
        if target.book_count <= 0:
            # If count is zero or less, it's not available
            if target.availability_status != BookAvailability.NOT_AVAILABLE:
                 target.availability_status = BookAvailability.NOT_AVAILABLE
        else: # target.book_count > 0
            # If count is positive, it becomes available *unless* it's
            # explicitly set to IN_PROGRESS (we don't want to override that here).
            # If it was previously NOT_AVAILABLE, change it to AVAILABLE.
            if target.availability_status == BookAvailability.NOT_AVAILABLE:
                 target.availability_status = BookAvailability.AVAILABLE
    # If book_count is somehow None (despite nullable=False),
    # maybe default to NOT_AVAILABLE or log an error, depending on desired behavior.
    # Example:
    # else:
    #     if target.availability_status != BookAvailability.NOT_AVAILABLE:
    #            target.availability_status = BookAvailability.NOT_AVAILABLE


# --- Comment Model ---
class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)

    user = relationship("User", back_populates="comments")
    book = relationship("Book", back_populates="comments")

# --- Rating Model ---
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