import json
import re

from openai import OpenAI

from app.core.config import settings


SYSTEM_PROMPT = """
You are an expert educational dataset creator.

Generate exactly 8 English question-answer pairs.

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
        """
        Инициализация клиента OpenAI.
        Вызывается один раз при старте FastAPI.
        """
        if self.client is not None:
            return

        try:
            self.client = OpenAI(
                api_key=settings.OPENAI_API_KEY
            )
            print("✅ OpenAI QA Generator initialized")

        except Exception as e:
            self._init_error = str(e)
            raise RuntimeError(f"OpenAI init failed: {e}")

    def _ensure_model(self):
        if self.client is None:
            self._initialize()

        if self._init_error:
            raise RuntimeError(self._init_error)

    @staticmethod
    def _extract_json(text: str):
        text = text.replace("```json", "")
        text = text.replace("```", "")

        match = re.search(r"\[.*\]", text, re.S)

        if not match:
            raise ValueError("JSON not found")

        return json.loads(match.group())

    def generate(self, text: str):

        self._ensure_model()

        response = self.client.chat.completions.create(
            model="gpt-4.1",
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": f"""
Generate 8 high-quality English question-answer pairs.

TEXT:

{text}
"""
                }
            ]
        )

        content = response.choices[0].message.content

        return self._extract_json(content)