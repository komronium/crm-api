from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import ChangePassword, LoginRequest, Token
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1", tags=["Authentication"])


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Invalid credentials"},
        401: {"description": "Authentication failed"},
        500: {"description": "Internal Server Error"},
    },
)
async def login(
    request: LoginRequest, http_request: Request, db: Session = Depends(get_db)
) -> Token:
    # nginx sets X-Real-IP to the real client address (a client cannot forge it)
    client_ip = http_request.headers.get("x-real-ip") or (
        http_request.client.host if http_request.client else "unknown"
    )
    return await AuthService.login(db, request, client_ip)


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Invalid password"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal Server Error"},
    },
)
async def change_password(
    request: ChangePassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await AuthService.change_password(db, current_user, request)
