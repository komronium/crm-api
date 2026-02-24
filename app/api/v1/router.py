from fastapi import APIRouter

from app.api.v1.endpoints import auth, lead, profile, operators

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(operators.router)
api_router.include_router(profile.router)
api_router.include_router(lead.router)
