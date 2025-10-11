from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from typing import List, Optional
import os
import shutil
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Flashcards from PDF",
    description="API для создания учебных карточек из PDF файлов",
    version="1.0.0",
    # ✅ Отключаем автоматическую документацию ошибок валидации
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS для связи с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Директории
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
CARDS_DIR = os.path.join(BASE_DIR, "cards")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CARDS_DIR, exist_ok=True)

# Модели данных
class Card(BaseModel):
    id: int
    question: str
    answer: str
    deck_name: str

class Deck(BaseModel):
    name: str
    file_size: int
    created_at: str

class UploadResponse(BaseModel):
    success: bool
    message: str
    filename: Optional[str] = None

class CardsResponse(BaseModel):
    success: bool
    cards: List[Card]
    deck_name: str
    total: int

# Маршруты API
@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "Flashcards from PDF API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/api/upload",
            "decks": "/api/decks",
            "create_cards": "/api/decks/{name}/cards",
            "get_cards": "/api/decks/{name}/cards"
        }
    }

@app.post("/api/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Загрузить PDF файл"""
    try:
        # Проверка типа файла
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(400, "Разрешены только PDF файлы")

        # Сохранение файла
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"PDF загружен: {file.filename}")
        return UploadResponse(
            success=True,
            message=f"Файл {file.filename} успешно загружен",
            filename=file.filename
        )

    except Exception as e:
        logger.error(f"Ошибка загрузки: {str(e)}")
        return UploadResponse(success=False, message=f"Ошибка загрузки: {str(e)}")

@app.get("/api/decks")
async def list_decks():
    """Получить список всех деков (PDF файлов)"""
    try:
        decks = []
        for filename in os.listdir(UPLOAD_DIR):
            if filename.lower().endswith('.pdf'):
                file_path = os.path.join(UPLOAD_DIR, filename)
                file_size = os.path.getsize(file_path)
                decks.append({
                    "name": filename,
                    "file_size": file_size,
                    "created_at": "2024-01-01"  # Заглушка
                })

        return {"success": True, "decks": decks}

    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/decks/{deck_name}/cards", response_model=CardsResponse)
async def create_cards(deck_name: str):
    """Создать карточки из PDF"""
    try:
        # Проверка существования файла
        file_path = os.path.join(UPLOAD_DIR, deck_name)
        if not os.path.exists(file_path):
            raise HTTPException(404, "PDF файл не найден")

        # Заглушка для генерации карточек
        cards_data = [
            {"id": 1, "question": "Что такое машинное обучение?", "answer": "Раздел искусственного интеллекта",
             "deck_name": deck_name},
            {"id": 2, "question": "Основные типы ML?", "answer": "Обучение с учителем, без учителя, с подкреплением",
             "deck_name": deck_name},
            {"id": 3, "question": "Что такое нейронная сеть?",
             "answer": "Математическая модель, inspired биологическими нейронами", "deck_name": deck_name}
        ]

        cards = [Card(**card) for card in cards_data]

        return CardsResponse(
            success=True,
            cards=cards,
            deck_name=deck_name,
            total=len(cards)
        )

    except HTTPException:
        raise
    except Exception as e:
        return CardsResponse(success=False, cards=[], deck_name=deck_name, total=0)

@app.get("/api/decks/{deck_name}/cards", response_model=CardsResponse)
async def get_cards(deck_name: str):
    """Получить карточки для определенного дека"""
    # В реальной реализации здесь будет чтение из БД
    return await create_cards(deck_name)  # Заглушка

@app.delete("/api/decks/{deck_name}")
async def delete_deck(deck_name: str):
    """Удалить PDF файл и связанные карточки"""
    try:
        # Декодируем имя файла
        import urllib.parse
        deck_name = urllib.parse.unquote(deck_name)

        # Пути к файлам
        pdf_path = os.path.join(UPLOAD_DIR, deck_name)
        cards_path = os.path.join(CARDS_DIR, f"{deck_name}.json")

        # Проверяем существование PDF файла
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="PDF файл не найден")

        # Удаляем PDF файл
        os.remove(pdf_path)
        logger.info(f"PDF файл удален: {pdf_path}")

        # Удаляем файл карточек если существует
        if os.path.exists(cards_path):
            os.remove(cards_path)
            logger.info(f"Файл карточек удален: {cards_path}")

        return {
            "success": True,
            "message": f"Файл {deck_name} и связанные карточки успешно удалены"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка удаления файла {deck_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления файла: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
