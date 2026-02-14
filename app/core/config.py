import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")
NOTION_STATUS_DEFAULT = os.getenv("NOTION_STATUS_DEFAULT", "Draft")

WORKER_SECRET = os.getenv("WORKER_SECRET", "")
CLOUD_SERVER_URL = os.getenv("CLOUD_SERVER_URL", "http://localhost:8000")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))

WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL_NAME", "small")
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "llama3.2")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

PORT = int(os.getenv("PORT", "8000"))
