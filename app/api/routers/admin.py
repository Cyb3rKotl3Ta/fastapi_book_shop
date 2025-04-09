# In admin.py
from fastapi_admin import BaseModelView
from app.db.models.book import Book
from app.db.models.user import User
import fastapi_admin as admin

class BookAdmin(BaseModelView):
    model = Book
    # Customize the columns and actions in the admin interface if needed

class UserAdmin(BaseModelView):
    model = User
    # Customize the columns and actions in the admin interface if needed

# Register models with FastAPI Admin
admin.register(BookAdmin)
admin.register(UserAdmin)
