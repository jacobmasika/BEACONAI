import logging
from flask import Flask
from flask_cors import CORS

from .cache_store import SQLiteCacheStore
from .config import Config
from .db_sqlite import SQLiteDB
from .extensions import db
from .routes import api_bp


logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

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
        logger.warning(f"PostgreSQL unavailable ({e}), falling back to SQLite")

    if use_postgres:
        with app.app_context():
            initialized = _init_postgres_db(app)
        if initialized:
            app.db_backend = "postgres"
        else:
            logger.warning("PostgreSQL schema initialization failed, falling back to SQLite")
            app.db_backend = "sqlite"
            app.sqlite_db = SQLiteDB()
    else:
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
        except Exception as extension_error:
            logger.warning(f"Could not ensure pgvector extension: {extension_error}")

        db.create_all()

        # Cosine index improves nearest-neighbor match latency at larger scale.
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
        logger.info("PostgreSQL initialization complete")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to initialize PostgreSQL: {e}")
        return False
