from pydantic import BaseModel, EmailStr

# Базовые данные пользователя (используются в нескольких схемах)
class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None

# При регистрации нужно ввести пароль
class UserCreate(UserBase):
    password: str

# При логине тоже нужен пароль
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Ответ клиенту — без пароля!
class UserResponse(UserBase):
    id: int

    class Config:
        orm_mode = True  # Позволяет возвращать объекты ORM (SQLAlchemy)
