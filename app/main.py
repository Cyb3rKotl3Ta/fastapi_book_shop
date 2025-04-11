import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

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

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="My Book Shop API",
        version="1.0.0",            
        description="API documentation for Book Shop",
        routes=app.routes,
    )
    openapi_schema["openapi"] = "3.0.2"  # or any valid 3.x.y version
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema
    
app.openapi = custom_openapi


@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Book Shop API! Admin available at /admin"}
