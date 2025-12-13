from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth_routes, user_routes, wallpaper_routes
from app.core.error_handlers import add_exception_handlers
from app.core.config import settings


app = FastAPI(
    title="AI-Wallpaper Backend",
    description="Backend service for AI-Wallpaper mobile app",
    version="1.0.0",
)

# Global exception handlers
add_exception_handlers(app)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check for AWS ALB
@app.get("/health")
def health_check():
    return {"status": "ok"}

# API v1 router
api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_routes.router)
api_v1_router.include_router(user_routes.router)
api_v1_router.include_router(wallpaper_routes.router)

app.include_router(api_v1_router)

