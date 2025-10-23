from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from datetime import datetime
import logging
from typing import List, Dict, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Хранилище в памяти
files_storage = []
history_storage = []  # ← Добавляем хранилище для истории
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# Простая проверка токена (для демо)
def verify_token(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    token = authorization.replace("Bearer ", "")

    # Простая проверка (в реальном приложении проверяйте в БД)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")

    return token

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    logger.info(f"📨 Получен файл: {file.filename}")
    logger.info(f"🔐 Заголовок авторизации: {authorization}")

    if not file.filename:
        raise HTTPException(400, "No file provided")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are allowed")

    try:
        # Сохраняем файл
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        logger.info(f"💾 Сохраняем в: {file_path}")

        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        file_size = len(content)
        logger.info(f"✅ Файл сохранен, размер: {file_size} bytes")

        # Сохраняем информацию о файле
        file_info = {
            "name": file.filename,
            "file_size": file_size,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        files_storage.append(file_info)

        # Добавляем запись в историю
        history_record = {
            "action": "upload_pdf",
            "filename": file.filename,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "details": f"Uploaded PDF file: {file.filename} ({file_size} bytes)"
        }
        history_storage.append(history_record)

        return {
            "success": True,
            "message": f"File {file.filename} uploaded successfully",
            "filename": file.filename
        }

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        raise HTTPException(500, f"Server error: {str(e)}")


@app.get("/decks")
def list_decks():
    return {"success": True, "decks": files_storage}


@app.post("/decks/{deck_name}/cards")
async def create_cards(deck_name: str):
    # Проверяем есть ли файл
    file_exists = any(f["name"] == deck_name for f in files_storage)
    if not file_exists:
        raise HTTPException(404, "PDF file not found")

    # Добавляем запись в историю
    history_record = {
        "action": "create_cards",
        "deck_name": deck_name,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "details": f"Created flashcards from deck: {deck_name}"
    }
    history_storage.append(history_record)

    # Демо-карточки
    cards = [
        {"id": 1, "question": "Что такое React?", "answer": "Библиотека для UI", "deck_name": deck_name},
        {"id": 2, "question": "Что такое компонент?", "answer": "Переиспользуемая часть UI", "deck_name": deck_name},
        {"id": 3, "question": "Что такое useState?", "answer": "Хук для состояния в React", "deck_name": deck_name},
    ]

    return {"success": True, "cards": cards, "deck_name": deck_name, "total": len(cards)}


@app.delete("/decks/{deck_name}")
async def delete_deck(deck_name: str):
    # Ищем и удаляем файл
    global files_storage
    file_exists = any(f["name"] == deck_name for f in files_storage)
    if not file_exists:
        raise HTTPException(404, "PDF file not found")

    # Удаляем из хранилища
    files_storage = [f for f in files_storage if f["name"] != deck_name]

    # Добавляем запись в историю
    history_record = {
        "action": "delete_deck",
        "deck_name": deck_name,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "details": f"Deleted deck: {deck_name}"
    }
    history_storage.append(history_record)

    return {"success": True, "message": f"Deck {deck_name} deleted"}


# ← ДОБАВЛЯЕМ НОВЫЙ ENDPOINT ДЛЯ ИСТОРИИ
@app.get("/history")
async def get_history():
    logger.info("📖 Запрос истории действий")
    return {
        "success": True,
        "history": history_storage,
        "total": len(history_storage)
    }


@app.get("/")
async def root():
    return {"message": "Flashcards API is working! 🚀"}