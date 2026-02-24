from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from pydantic import usernameStr
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, SignupRequest, Token


class AuthService:
    @staticmethod
    async def authenticate(
        db: Session, username: usernameStr, password: str
    ) -> Optional[User]:
        user: Optional[User] = db.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.password):
            return None
        return user

    @staticmethod
    async def update_last_login(user: User, db: Session) -> None:
        user.last_login = datetime.now()
        db.commit()
        db.refresh(user)

    @staticmethod
    async def login(db: Session, request: LoginRequest) -> Token:
        user: Optional[User] = await AuthService.authenticate(
            db, request.username, request.password
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        await AuthService.update_last_login(user, db)

        access_token = create_access_token({"sub": user.username})
        return Token(access_token=access_token)

    @staticmethod
    async def signup(db: Session, request: SignupRequest) -> User:
        existing_user: Optional[User] = (
            db.query(User).filter(User.username == request.username).first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="username already exists",
            )

        hashed_password = hash_password(request.password)
        user: User = User(
            username=request.username, password=hashed_password, name=request.name
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
