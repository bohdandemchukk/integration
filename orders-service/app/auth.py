from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db           
from app.models import User
from app.security_config import (
    JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


_DUMMY_HASH = pwd_context.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        pwd_context.verify(password, _DUMMY_HASH)  
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(username: str) -> str:
    iat = datetime.now(timezone.utc)
    exp = iat + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "iat": iat, "exp": exp}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])  # whitelist
        username = payload.get("sub")
        if not isinstance(username, str):
            raise credentials_exc
    except jwt.PyJWTError:
        raise credentials_exc

    user = db.scalar(select(User).where(User.username == username))
    if user is None or not user.is_active:
        raise credentials_exc
    return user