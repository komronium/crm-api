from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import ChangePassword, LoginRequest, Token


class AuthService:
    @staticmethod
    async def authenticate(db: Session, username: str, password: str) -> Optional[User]:
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

        access_token = create_access_token({"sub": str(user.id)})
        return Token(access_token=access_token, user=user)

    @staticmethod
    async def change_password(db: Session, user: User, request: ChangePassword):
        if not verify_password(request.current_password, user.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        user.password = hash_password(request.new_password)
        db.add(user)
        db.commit()
        return {"message": "Password changed successfully"}
