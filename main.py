from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from typing import List, Optional
from datetime import datetime, timedelta
import jwt
import os
import shutil
import sqlite3
import logging
import uuid
from typing import List


# ---------------------- НАСТРОЙКИ ----------------------
app = FastAPI(title="Flashcards from PDF API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = "SECRET123"
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
CARDS_DIR = os.path.join(BASE_DIR, "cards")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CARDS_DIR, exist_ok=True)

# ---------------------- БАЗА ДАННЫХ ----------------------
DB_PATH = "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT DEFAULT '',
            theme TEXT DEFAULT 'light'
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------------------- МОДЕЛИ ----------------------
class RegisterData(BaseModel):
    email: EmailStr
    password: str

class LoginData(BaseModel):
    email: EmailStr
    password: str

class ChangePasswordData(BaseModel):
    old_password: str
    new_password: str

class HistoryItem(BaseModel):
    timestamp: str
    deck_name: str
    cards_count: int

class Card(BaseModel):
    id: int
    question: str
    answer: str
    deck_name: str

class UploadResponse(BaseModel):
    success: bool
    message: str
    filename: Optional[str] = None

class CardsResponse(BaseModel):
    success: bool
    cards: List[Card]
    deck_name: str
    total: int

# Обновите модель HistoryItem
class HistoryItem(BaseModel):
    id: Optional[int] = None
    type: str
    deck_name: str
    timestamp: str
    cards_count: Optional[int] = None
    file_size: Optional[int] = None
    user_email: Optional[str] = None

# ---------------------- JWT ----------------------
def create_token(email: str):
    payload = {"sub": email, "exp": datetime.utcnow() + timedelta(hours=2)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None

def get_current_user(token: str = Body(..., embed=True)):
    email = verify_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token")
    return email

# ---------------------- РЕГИСТРАЦИЯ ----------------------
@app.post("/api/register")
def register(data: RegisterData):
    if len(data.password) < 6 or not any(c.isupper() for c in data.password):
        raise HTTPException(status_code=400, detail="Password must be >=6 chars with 1 uppercase")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email = ?", (data.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email already exists")

    password_hash = pwd_context.hash(data.password)
    cursor.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (data.email, password_hash))
    conn.commit()
    conn.close()

    return {"success": True, "message": "User registered successfully"}

# ---------------------- ВХОД ----------------------
@app.post("/api/login")
def login(data: LoginData):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE email = ?", (data.email,))
    row = cursor.fetchone()
    conn.close()

    if not row or not pwd_context.verify(data.password, row[0]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(data.email)
    return {"token": token, "email": data.email}

# ---------------------- ПРОФИЛЬ ----------------------
@app.get("/api/profile")
def get_profile(email: str = Depends(get_current_user)):
    return {"email": email, "theme": "light", "name": ""}

@app.post("/api/profile/change_password")
def change_password(data: ChangePasswordData, email: str = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()

    if not row or not pwd_context.verify(data.old_password, row[0]):
        conn.close()
        raise HTTPException(status_code=400, detail="Old password incorrect")

    new_hash = pwd_context.hash(data.new_password)
    cursor.execute("UPDATE users SET password_hash = ? WHERE email = ?", (new_hash, email))
    conn.commit()
    conn.close()

    return {"success": True, "message": "Password changed"}

@app.delete("/api/profile")
def delete_profile(email: str = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM users WHERE email = ?", (email,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Profile deleted"}

# ---------------------- ФАЙЛЫ ----------------------
@app.post("/api/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are allowed")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    logger.info(f"PDF uploaded: {file.filename}")
    return UploadResponse(success=True, message=f"File {file.filename} uploaded", filename=file.filename)

# ---------------------- ДЕКИ ----------------------
@app.get("/api/decks")
def list_decks():
    decks = []
    for filename in os.listdir(UPLOAD_DIR):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(UPLOAD_DIR, filename)
            decks.append({
                "name": filename,
                "file_size": os.path.getsize(file_path),
                "created_at": datetime.utcfromtimestamp(os.path.getctime(file_path)).strftime("%Y-%m-%d")
            })
    return {"success": True, "decks": decks}

@app.post("/api/decks/{deck_name}/cards", response_model=CardsResponse)
async def create_cards(deck_name: str):
    file_path = os.path.join(UPLOAD_DIR, deck_name)
    if not os.path.exists(file_path):
        raise HTTPException(404, "PDF file not found")

    cards_data = [
        {"id": 1, "question": "Что такое машинное обучение?", "answer": "Раздел ИИ", "deck_name": deck_name},
        {"id": 2, "question": "Типы ML?", "answer": "С учителем, без учителя, с подкреплением", "deck_name": deck_name},
    ]
    cards = [Card(**card) for card in cards_data]
    return CardsResponse(success=True, cards=cards, deck_name=deck_name, total=len(cards))

@app.get("/api/decks/{deck_name}/cards", response_model=CardsResponse)
async def get_cards(deck_name: str):
    return await create_cards(deck_name)

@app.delete("/api/decks/{deck_name}")
def delete_deck(deck_name: str):
    path = os.path.join(UPLOAD_DIR, deck_name)
    if not os.path.exists(path):
        raise HTTPException(404, "PDF file not found")
    os.remove(path)
    return {"success": True, "message": f"Deck {deck_name} deleted"}


# В разделе БАЗА ДАННЫХ добавьте создание таблицы для истории
def init_db():
    conn = sqlite3.connect(DB_PATH)

    # Таблица пользователей (уже есть)
    conn.execute("""
                 CREATE TABLE IF NOT EXISTS users
                 (
                     id
                     INTEGER
                     PRIMARY
                     KEY
                     AUTOINCREMENT,
                     email
                     TEXT
                     UNIQUE
                     NOT
                     NULL,
                     password_hash
                     TEXT
                     NOT
                     NULL,
                     name
                     TEXT
                     DEFAULT
                     '',
                     theme
                     TEXT
                     DEFAULT
                     'light'
                 )
                 """)

    # НОВАЯ таблица для истории действий
    conn.execute("""
                 CREATE TABLE IF NOT EXISTS history
                 (
                     id
                     INTEGER
                     PRIMARY
                     KEY
                     AUTOINCREMENT,
                     type
                     TEXT
                     NOT
                     NULL,
                     deck_name
                     TEXT
                     NOT
                     NULL,
                     timestamp
                     TEXT
                     NOT
                     NULL,
                     cards_count
                     INTEGER,
                     file_size
                     INTEGER,
                     user_email
                     TEXT
                 )
                 """)

    conn.commit()
    conn.close()


# Обновите endpoints для истории
@app.get("/api/history")
def get_history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT id, type, deck_name, timestamp, cards_count, file_size, user_email
                   FROM history
                   ORDER BY timestamp DESC
                   """)

    history_items = []
    for row in cursor.fetchall():
        history_items.append({
            "id": str(row[0]),
            "type": row[1],
            "deck_name": row[2],
            "timestamp": row[3],
            "cards_count": row[4],
            "file_size": row[5],
            "user_email": row[6]
        })

    conn.close()
    return {"success": True, "history": history_items}


@app.post("/api/history")
def add_history_item(item: HistoryItem):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
                   INSERT INTO history (type, deck_name, timestamp, cards_count, file_size, user_email)
                   VALUES (?, ?, ?, ?, ?, ?)
                   """, (item.type, item.deck_name, item.timestamp, item.cards_count, item.file_size, item.user_email))

    conn.commit()
    conn.close()

    return {"success": True}


@app.delete("/api/history")
def clear_history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM history")

    conn.commit()
    conn.close()

    return {"success": True}
# ---------------------- ROOT ----------------------
@app.get("/")
async def root():
    return {"message": "Flashcards API is running 🚀"}

