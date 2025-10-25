from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite используется для простоты (всё хранится в файле)
# В продакшене лучше PostgreSQL
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

# connect_args нужен для SQLite (в PostgreSQL не нужен)
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# SessionLocal — объект сессии БД, через него делаются запросы
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для всех моделей (User и др.)
Base = declarative_base()

# Dependency для FastAPI — создаёт сессию, закрывает после запроса
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
