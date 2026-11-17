import os
from pathlib import Path

from dotenv import load_dotenv

# backend/.env — found the same way no matter where the app is started from
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# PostgreSQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# AI (any OpenAI-compatible endpoint)
AI_BASE_URL = os.getenv("AI_BASE_URL")
AI_MODEL = os.getenv("AI_MODEL")
AI_API_KEY = os.getenv("AI_API_KEY", "not-needed")
AI_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "30"))

# Login (JWT)
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))  # 8 hours
