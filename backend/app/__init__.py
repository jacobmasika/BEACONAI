import logging
import os
from flask import Flask
from flask_cors import CORS

from .cache_store import SQLiteCacheStore
from .config import Config
from .db_sqlite import SQLiteDB
from .extensions import db
from .routes import api_bp


logger = logging.getLogger(__name__)


def _vercel_sqlite_fallback_allowed() -> bool:
    return os.getenv("VERCEL_ALLOW_SQLITE_FALLBACK", "1").strip().lower() not in {"0", "false", "no"}


def _enable_sqlite_fallback(app: Flask, reason: str) -> None:
    app.db_backend = "sqlite"
    app.db_backend_error = reason
    app.sqlite_db = SQLiteDB()
    logger.warning("Using SQLite fallback backend (%s)", reason)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    app.is_vercel = bool(os.getenv("VERCEL"))

    CORS(app)

    app.cache_store = SQLiteCacheStore(app.config["SQLITE_CACHE_PATH"])

    # Try PostgreSQL first; fall back to SQLite if unavailable.
    use_postgres = False
    try:
        from sqlalchemy import text

        db.init_app(app)
        with app.app_context():
            db.session.execute(text("SELECT 1"))
        use_postgres = True
        logger.info("Using PostgreSQL backend")
    except Exception as e:
        if app.is_vercel:
            reason = f"PostgreSQL unavailable on Vercel: {e}"
            if _vercel_sqlite_fallback_allowed():
                _enable_sqlite_fallback(app, reason)
            else:
                app.db_backend = "unavailable"
                app.db_backend_error = str(e)
                logger.error(
                    "PostgreSQL unavailable on Vercel (%s). Refusing SQLite fallback; configure DATABASE_URL for persistent storage.",
                    e,
                )
        else:
            logger.warning(f"PostgreSQL unavailable ({e}), falling back to SQLite")

    if use_postgres:
        with app.app_context():
            initialized = _init_postgres_db(app)
        if initialized:
            app.db_backend = "postgres"
        else:
            if app.is_vercel:
                reason = getattr(app, "db_backend_error", None) or "PostgreSQL schema initialization failed"
                if _vercel_sqlite_fallback_allowed():
                    _enable_sqlite_fallback(app, reason)
                else:
                    app.db_backend = "unavailable"
                    app.db_backend_error = reason
                    logger.error(
                        "PostgreSQL schema initialization failed on Vercel. Refusing SQLite fallback; configure DATABASE_URL and pgvector."
                    )
            else:
                logger.warning("PostgreSQL schema initialization failed, falling back to SQLite")
                app.db_backend = "sqlite"
                app.sqlite_db = SQLiteDB()
    elif not hasattr(app, "db_backend"):
        app.db_backend = "sqlite"
        app.sqlite_db = SQLiteDB()

    app.register_blueprint(api_bp, url_prefix="/api")

    return app


def _init_postgres_db(app: Flask) -> bool:
    from sqlalchemy import text
    from . import models  # noqa: F401

    try:
        # Some managed Postgres services may restrict CREATE EXTENSION permissions.
        # We proceed to schema creation and fall back to SQLite if vector types are unavailable.
        try:
            db.session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            db.session.commit()
        except Exception as extension_error:
            db.session.rollback()
            logger.warning(f"Could not ensure pgvector extension: {extension_error}")

        db.create_all()
        db.session.commit()

        # Cosine index improves nearest-neighbor match latency at larger scale.
        try:
            db.session.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS idx_missing_persons_embedding_cosine
                    ON missing_persons USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100)
                    """
                )
            )
            db.session.commit()
        except Exception as index_error:
            # Do not fail startup if ANN index creation is unavailable.
            db.session.rollback()
            logger.warning(f"Could not create ivfflat index: {index_error}")

        logger.info("PostgreSQL initialization complete")
        return True
    except Exception as e:
        db.session.rollback()
        app.db_backend_error = str(e)
        logger.error(f"Failed to initialize PostgreSQL: {e}")
        return False
