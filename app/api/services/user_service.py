# user_service.py
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.shemas.user_shema import UserCreate


def create_user(db: Session, user_in: UserCreate) -> User:
    """Создаёт нового пользователя"""
    user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Проверяет email и пароль"""
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def login_user(db: Session, email: str, password: str):
    """Возвращает токен, если пользователь прошёл проверку"""
    user = authenticate_user(db, email, password)
    if not user:
        return None
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}
