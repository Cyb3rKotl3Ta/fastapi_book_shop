import os
import sys
print(sys.path)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.session import SessionMiddleware  # Import SessionMiddleware
import aioredis  # Import aioredis
from aioredis import Redis  # Import Redis

# --- FastAPI Admin Imports ---
from fastapi_admin.app import app as admin_app
from fastapi_admin.providers.login import UsernamePasswordProvider
from sqlalchemy import Column, Integer, String
# --- End FastAPI Admin Imports ---

from app.api.routers.auth import router as auth_router
from app.api.routers.books import router as books_router
from app.api.routers.purchases import router as purchases_router
from app.api.routers.users import router as users_router
from app.core.config import settings
from app.db.base import engine, Base

# --- Define Admin Model for fastapi-admin ---
class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    def __str__(self):
        return self.username
# --- End Admin Model Definition ---

app = FastAPI(
    title="Book Shop API",
    description="API for an online book shop.",
    version="0.1.0",
    openapi_url=f"/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# --- Add Session Middleware HERE ---
# IMPORTANT: Add it before mounting admin_app and add your secret key here
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY, # Use your secret key
    # You might need to configure session cookie parameters like https_only=False
    # during development if not using HTTPS. Default is True.
    # https_only=False, # Uncomment if running locally without HTTPS
)
# --- End Session Middleware ---


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Mount the admin app ---
# Mount admin_app *after* adding SessionMiddleware
app.mount("/admin", admin_app, name="admin")

# --- Startup Event to Configure Admin and Create Tables ---
@app.on_event("startup")
async def on_startup():
    # --- Create tables with async engine ---
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # --- End table creation ---

    # --- Connect to Redis ---
    redis = aioredis.from_url("redis://localhost", encoding="utf8", decode_responses=True)  # Use the from_url method
    # --- End Connect to Redis ---

    # Configure fastapi-admin
    await admin_app.configure(
        # logo_url="https://example.com/logo.png",
        # REMOVE secret_key from here
        redis = redis, # Use the redis connection here
        providers=[
            UsernamePasswordProvider(
                login_logo_url="https://preview.tabler.io/static/logo.svg",
                admin_model=Admin,
            )
        ],
        # engine=engine, # engine is also not expected here
        # models=[UserResource, BookResource, PurchaseResource] # Example
    )

# --- Include your API routers ---
app.include_router(auth_router, prefix="/api/v1", tags=["Auth"])
app.include_router(books_router, prefix="/api/v1/books", tags=["Books"])
app.include_router(purchases_router, prefix="/api/v1/purchases", tags=["Purchases"])
app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Book Shop API! Admin available at /admin"}