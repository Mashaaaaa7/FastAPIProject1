from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.services.user_service import create_user, login_user
from app.core.database import get_db
from app.models.user import User
from app.shemas.user_shema import UserCreate, UserResponse, UserLogin

router = APIRouter()


@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
    return create_user(db, user_in)

@router.post("/login")
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    """Вход и получение JWT-токена"""
    auth = login_user(db, user_in.email, user_in.password)
    if not auth:
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    return auth
