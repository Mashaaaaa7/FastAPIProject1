import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
import json
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="Flashcards from PDF (backend)")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


# ✅ POST - для создания/загрузки данных
@app.post("/api/upload")
async def upload_pdf(pdf: UploadFile = File(...)):
    """Загрузить PDF файл"""
    logger.info(f"Upload request received for file: {pdf.filename}")
    if not pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF allowed")

    dest = os.path.join(UPLOAD_DIR, pdf.filename)
    with open(dest, "wb") as f:
        shutil.copyfileobj(pdf.file, f)

    logger.info(f"File saved: {dest}")
    return {"message": f"{pdf.filename} uploaded", "filename": pdf.filename}


# ✅ GET - для получения данных
@app.get("/api/decks")
def list_decks():
    """Получить список всех деков"""
    files = sorted(os.listdir(UPLOAD_DIR))
    logger.info(f"List decks request. Found files: {files}")
    return {"decks": [{"name": f} for f in files]}


# ✅ POST - для создания карточек
@app.post("/api/create_cards/{filename}")
async def create_cards(filename: str):
    """Создать карточки из PDF файла"""
    logger.info(f"Create cards request for file: {filename}")

    # Декодируем имя файла если нужно
    import urllib.parse
    filename = urllib.parse.unquote(filename)

    pdf_path = os.path.join(UPLOAD_DIR, filename)
    logger.info(f"Looking for file at: {pdf_path}")

    if not os.path.exists(pdf_path):
        logger.error(f"File not found: {pdf_path}")
        raise HTTPException(status_code=404, detail="PDF file not found")

    # Здесь будет логика создания карточек из PDF
    # Пока возвращаем тестовые данные
    cards = [
        {"question": f"Вопрос 1 по {filename}", "answer": "Ответ 1"},
        {"question": f"Вопрос 2 по {filename}", "answer": "Ответ 2"}
    ]

    logger.info(f"Created {len(cards)} cards for {filename}")
    return {"cards": cards, "filename": filename, "count": len(cards)}


# ✅ DELETE - для удаления данных
@app.delete("/api/delete_cards/{filename}")
def delete_cards(filename: str):
    """Удалить PDF файл и связанные карточки"""
    logger.info(f"Delete request for file: {filename}")

    import urllib.parse
    filename = urllib.parse.unquote(filename)

    pdf_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        os.remove(pdf_path)
        logger.info(f"File deleted: {pdf_path}")
        return {"success": True, "message": f"{filename} удалён"}
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")


# ✅ GET - корневой эндпоинт
@app.get("/")
def root():
    return {"message": "Flashcards API"}

# Если есть собранный фронтенд в ../frontend/dist — подаём статику
dist_dir = os.path.join(BASE_DIR, "..", "frontend", "dist")
if os.path.isdir(dist_dir):
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="frontend")


