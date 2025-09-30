import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="Flashcards from PDF (backend)")

# CORS для разработки (vite на 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# ----- API -----

@app.post("/api/upload")
async def upload_pdf(pdf: UploadFile = File(...)):
    if not pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF allowed")
    dest = os.path.join(UPLOAD_DIR, pdf.filename)
    with open(dest, "wb") as f:
        shutil.copyfileobj(pdf.file, f)
    return {"message": f"{pdf.filename} uploaded", "filename": pdf.filename}

@app.get("/api/decks")
def list_decks():
    files = sorted(os.listdir(UPLOAD_DIR))
    return {"decks": [{"name": f} for f in files]}

@app.post("/api/create_cards/{filename}")
def create_cards(filename: str):
    # ЗАГЛУШКА: возвращаем тестовые карточки для данного файла
    cards = [
        {"question": f"Вопрос 1 по {filename}", "answer": "Ответ 1"},
        {"question": f"Вопрос 2 по {filename}", "answer": "Ответ 2"},
    ]
    return {"cards": cards}

# ----- Static serving for production build -----
# When frontend is built into frontend/dist, FastAPI will serve it
dist_dir = os.path.join(BASE_DIR, "..", "frontend", "dist")
if os.path.isdir(dist_dir):
    # mount whole dist at root
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="frontend")
else:
    # dev: expose a small message at root
    @app.get("/")
    def root():
        return {"message": "Frontend not built. Run frontend dev on :5173 or build into frontend/dist."}
