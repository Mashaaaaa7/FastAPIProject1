import json
import re
from openai import OpenAI
from app.core.config import settings


SYSTEM_PROMPT = """
You are an expert educational dataset creator.

Be factually accurate. Do not paraphrase in ways that change the meaning.
Generate exactly English question-answer pairs.

Return ONLY a JSON array.

[
  {
    "question":"...",
    "answer":"..."
  }
]
"""


class QAGeneratorService:

    def __init__(self):
        self.client = None
        self._init_error = None

    def _initialize(self):
        if self.client is not None:
            return
        try:
            self.client = OpenAI(
                api_key=settings.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1",
            )
            print("✅ Groq QA Generator initialized")
        except Exception as e:
            self._init_error = str(e)
            raise RuntimeError(f"Groq init failed: {e}")

    def _ensure_model(self):
        if self.client is None:
            self._initialize()
        if self._init_error:
            raise RuntimeError(self._init_error)

    @staticmethod
    def _extract_json(text: str):
        text = text.replace("```json", "").replace("```", "")
        match = re.search(r"\[.*\]", text, re.S)
        if not match:
            raise ValueError("JSON not found")
        return json.loads(match.group())

    def _generate_pairs(self, text: str, n: int) -> list:
        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert educational dataset creator. "
                        f"Generate exactly {n} English question-answer pairs based on the text. "
                        "Return ONLY a JSON array, no other text:\n"
                        '[{"question":"...","answer":"..."}]'
                    ),
                },
                {
                    "role": "user",
                    "content": f"TEXT:\n\n{text}",
                },
            ],
        )
        content = response.choices[0].message.content
        return self._extract_json(content)

    def generate(self, text: str):
        self._ensure_model()
        return self._generate_pairs(text, 8)

    def process_pdf(self, pdf_path: str, max_cards: int = 20):
        self._ensure_model()

        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader

        reader = PdfReader(pdf_path)
        pages_text = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                pages_text.append(t.strip())

        text = "\n".join(pages_text).strip()
        if not text:
            raise ValueError("Не удалось извлечь текст из PDF")

        text = text[:12000]
        n = min(max_cards, 20)
        pairs = self._generate_pairs(text, n)

        cards = []
        for p in pairs[:max_cards]:
            q = (p.get("question") or "").strip()
            a = (p.get("answer") or "").strip()
            if q and a:
                cards.append({
                    "question": q,
                    "answer":   a,
                    "context":  None,
                    "source":   None,
                })
        return cards