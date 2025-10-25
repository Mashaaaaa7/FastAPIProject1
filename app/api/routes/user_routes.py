# user_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

router = APIRouter()

# Указываем путь, где можно получить токен (используется для swagger)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    """Проверяет токен и возвращает текущего пользователя"""
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Неверный токен")
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Возвращает данные текущего авторизованного пользователя"""
    return {"email": current_user.email, "full_name": current_user.full_name}
