from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Простое хранилище в памяти
uploaded_files = []
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are allowed")

    # Сохраняем файл
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Сохраняем информацию о файле
    file_info = {
        "name": file.filename,
        "file_size": os.path.getsize(file_path),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    uploaded_files.append(file_info)

    return {"success": True, "message": f"File {file.filename} uploaded"}


@app.get("/decks")
def list_decks():
    return {"success": True, "decks": uploaded_files}


@app.post("/decks/{deck_name}/cards")
async def create_cards(deck_name: str):
    # Проверяем существование файла
    file_exists = any(f["name"] == deck_name for f in uploaded_files)
    if not file_exists:
        raise HTTPException(404, "PDF file not found")

    # Демо-карточки
    cards = [
        {"id": 1, "question": "Что такое React?", "answer": "Библиотека для UI", "deck_name": deck_name},
        {"id": 2, "question": "Что такое компонент?", "answer": "Переиспользуемая часть UI", "deck_name": deck_name},
    ]

    return {"success": True, "cards": cards, "deck_name": deck_name, "total": len(cards)}


@app.delete("/decks/{deck_name}")
def delete_deck(deck_name: str):
    global uploaded_files

    # Находим и удаляем файл
    for file in uploaded_files:
        if file["name"] == deck_name:
            file_path = os.path.join(UPLOAD_DIR, deck_name)
            if os.path.exists(file_path):
                os.remove(file_path)
            break

    uploaded_files = [f for f in uploaded_files if f["name"] != deck_name]

    return {"success": True, "message": f"Deck {deck_name} deleted"}


@app.get("/")
async def root():
    return {"message": "Flashcards API is running 🚀"}