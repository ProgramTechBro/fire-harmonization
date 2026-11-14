import os
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

def _path(value, default):
    p = Path(value) if value else default
    return (p if p.is_absolute() else BACKEND_DIR / p).resolve()


DATA_DIR = _path(os.getenv("DATA_DIR"), BACKEND_DIR.parent / "web_data")
FRONTEND_DIST = _path(os.getenv("FRONTEND_DIST"), BACKEND_DIR.parent / "frontend" / "dist")
METEOMATICS_USERNAME = os.getenv("METEOMATICS_USERNAME", "")
METEOMATICS_PASSWORD = os.getenv("METEOMATICS_PASSWORD", "")
WEATHER_CACHE_SECONDS = int(os.getenv("WEATHER_CACHE_SECONDS", "3600"))
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
