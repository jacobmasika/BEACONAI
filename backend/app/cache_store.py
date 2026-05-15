import json
import sqlite3
from pathlib import Path
from typing import Any


class SQLiteCacheStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_sightings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payload TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS public_case_photos (
                    id TEXT PRIMARY KEY,
                    data_url TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def add_pending_sighting(self, payload: dict[str, Any]) -> int:
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO pending_sightings (payload) VALUES (?)",
                (json.dumps(payload),),
            )
            conn.commit()
            return int(cur.lastrowid)

    def get_pending_sightings(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT id, payload, created_at FROM pending_sightings ORDER BY id ASC LIMIT ?",
                (limit,),
            )
            rows = cur.fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            results.append(
                {
                    "id": row[0],
                    "payload": json.loads(row[1]),
                    "created_at": row[2],
                }
            )
        return results

    def delete_pending_sighting(self, row_id: int) -> None:
        with self._get_conn() as conn:
            conn.execute("DELETE FROM pending_sightings WHERE id = ?", (row_id,))
            conn.commit()

    def add_public_case_photo(self, data_url: str) -> str:
        import uuid

        photo_id = str(uuid.uuid4())
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO public_case_photos (id, data_url) VALUES (?, ?)",
                (photo_id, data_url),
            )
            conn.commit()
        return photo_id

    def get_public_case_photo(self, photo_id: str) -> str | None:
        with self._get_conn() as conn:
            row = conn.execute("SELECT data_url FROM public_case_photos WHERE id = ?", (photo_id,)).fetchone()
        return row[0] if row else None
