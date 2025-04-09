from sqlalchemy import Table, Column, Integer, ForeignKey
from app.db.base import Base

# Many-to-Many table for User Favorites
user_favorite_books_table = Table(
    'user_favorite_books',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('book_id', Integer, ForeignKey('books.id'), primary_key=True)
)