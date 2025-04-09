import os
import sys
print(sys.path)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


# --- End Admin Model Definition ---

app = FastAPI(
    title="Book Shop API",
    description="API for an online book shop.",
    version="0.1.0",
    openapi_url=f"/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)


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

# --- Include your API routers ---
app.include_router(auth_router, prefix="/api/v1", tags=["Auth"])
app.include_router(books_router, prefix="/api/v1/books", tags=["Books"])
app.include_router(purchases_router, prefix="/api/v1/purchases", tags=["Purchases"])
app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Book Shop API! Admin available at /admin"}