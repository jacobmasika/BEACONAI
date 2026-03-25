import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_CACHE = (
    Path("/tmp") / "beaconai_cache.db"
    if os.getenv("VERCEL")
    else BASE_DIR / "instance" / "beaconai_cache.db"
)


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://beaconai:beaconai@localhost:5432/beaconai",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLITE_CACHE_PATH = os.getenv("SQLITE_CACHE_PATH", str(DEFAULT_SQLITE_CACHE))

    VECTOR_DIMENSIONS = int(os.getenv("VECTOR_DIMENSIONS", "512"))
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.85"))
    IMAGE_SEARCH_MIN_SIMILARITY = float(os.getenv("IMAGE_SEARCH_MIN_SIMILARITY", "0.55"))
    MATCH_QUERY_LIMIT = int(os.getenv("MATCH_QUERY_LIMIT", "5"))

    AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "")
    AZURE_AI_MODEL_DEPLOYMENT = os.getenv("AZURE_AI_MODEL_DEPLOYMENT", "")
    AZURE_AI_API_KEY = os.getenv("AZURE_AI_API_KEY", "")

    LAW_ENFORCEMENT_API_BASE_URL = os.getenv("LAW_ENFORCEMENT_API_BASE_URL", "")
    LAW_ENFORCEMENT_API_KEY = os.getenv("LAW_ENFORCEMENT_API_KEY", "")
