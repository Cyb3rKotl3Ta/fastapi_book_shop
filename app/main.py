import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.base import engine, Base
from app.api.routers import auth, books, purchases, users

# Create the main FastAPI application instance
app = FastAPI(
    title="Book Shop API",
    description="API for an online book shop.",
    version="0.1.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event to initialize the database and the SQLAdmin panel
@app.on_event("startup")
async def startup():
    # Create database tables if they do not exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Initialize the SQLAdmin panel
    from app.api.routers.sqladmin import init_admin
    init_admin(app)

# Include your API routers
app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])
app.include_router(books.router, prefix="/api/v1/books", tags=["Books"])
app.include_router(purchases.router, prefix="/api/v1/purchases", tags=["Purchases"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Book Shop API! Admin available at /admin"}
