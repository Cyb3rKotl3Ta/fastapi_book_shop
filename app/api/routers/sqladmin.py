from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqlalchemy import create_engine

from app.db.models.book import Book  # Corrected import path assuming models are in db/models
from app.db.models.user import User  # Corrected import path assuming models are in db/models
from app.core.config import settings  # Ensure settings.DATABASE_URL is configured properly

if settings.DATABASE_URL.startswith("postgresql+asyncpg"):
    sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
elif settings.DATABASE_URL.startswith("mysql+aiomysql"):
     sync_db_url = settings.DATABASE_URL.replace("+aiomysql", "+pymysql") # Or +mysqlconnector
elif settings.DATABASE_URL.startswith("sqlite+aiosqlite"):
     sync_db_url = settings.DATABASE_URL.replace("+aiosqlite", "")
else:
    # Assume it's already sync or handle other drivers
    sync_db_url = settings.DATABASE_URL

sync_engine = create_engine(sync_db_url)


# Define the admin view for the Book model
class BookAdmin(ModelView, model=Book):
    name = "Books"  # Display name in the admin panel
    icon = "fas fa-book"  # Icon (if supported by your UI)
    # List the columns to show in the table view
    column_list = [
        Book.id,
        Book.title,
        Book.author,
        Book.genre,
        Book.pages,
        Book.description,
        Book.cost,
        Book.language,
        Book.availability_status,
        Book.publication_date,
    ]
    # Add columns you want to be able to search on
    column_searchable_list = [Book.title, Book.author, Book.genre]
    # Add columns you want to be able to filter by
    column_filters = [Book.genre, Book.language, Book.availability_status]
    # Add columns for sorting
    column_sortable_list = [Book.id, Book.title, Book.author, Book.genre, Book.pages, Book.cost, Book.publication_date]


# Define the admin view for the User model
class UserAdmin(ModelView, model=User):
    name = "Users"
    icon = "fas fa-user"
    column_list = [
        User.id,
        User.username,
        User.email,
        User.full_name,
        User.balance,
        User.is_active,
        User.is_superuser,
        User.is_book_manager,
    ]
    # Add columns you want to be able to search on
    column_searchable_list = [User.username, User.email, User.full_name]
    # Add columns you want to be able to filter by
    column_filters = [User.is_active, User.is_superuser, User.is_book_manager]
    # Add columns for sorting
    column_sortable_list = [User.id, User.username, User.email, User.full_name, User.balance]


def init_admin(app: FastAPI):
    """
    Initialize SQLAdmin by binding it to the FastAPI app instance and registering model views.
    """
    # Create the Admin instance with the provided app
    admin = Admin(app, engine=sync_engine, base_url="/admin") # Removed trailing slash from base_url if not intended

    # Register your admin views using add_view
    admin.add_view(BookAdmin) # <--- CORRECT METHOD
    admin.add_view(UserAdmin) # <--- CORRECT METHOD