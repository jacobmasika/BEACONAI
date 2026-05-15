import json
import sqlite3
from pathlib import Path

from .config import Config


class SQLiteDB:
    """SQLite implementation for demo/offline when Postgres is unavailable."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.SQLITE_CACHE_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS missing_persons (
                    id TEXT PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    guardian_contact TEXT NOT NULL,
                    description TEXT NOT NULL,
                    government_case_id TEXT,
                    status TEXT DEFAULT 'active',
                    embedding BLOB NOT NULL,
                    metadata_payload TEXT DEFAULT '{}',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sighting_reports (
                    id TEXT PRIMARY KEY,
                    source_device_id TEXT NOT NULL,
                    sighting_text TEXT NOT NULL,
                    captured_at_iso TEXT,
                    status TEXT DEFAULT 'received',
                    embedding BLOB NOT NULL,
                    matched_missing_person_id TEXT,
                    similarity_score REAL,
                    government_handoff_flagged INTEGER DEFAULT 0,
                    local_cache_fallback_used INTEGER DEFAULT 0,
                    payload TEXT DEFAULT '{}',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS public_case_reports (
                    id TEXT PRIMARY KEY,
                    reporter_name TEXT NOT NULL,
                    reporter_relationship TEXT NOT NULL,
                    reporter_contact TEXT NOT NULL,
                    missing_person_name TEXT NOT NULL,
                    missing_person_age INTEGER,
                    missing_since_iso TEXT,
                    last_seen_location TEXT NOT NULL,
                    circumstances TEXT NOT NULL,
                    status TEXT DEFAULT 'submitted',
                    payload TEXT DEFAULT '{}',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def add_missing_person(self, payload: dict) -> str:
        import uuid

        person_id = str(uuid.uuid4())
        embedding_bytes = json.dumps(payload["embedding"]).encode()

        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO missing_persons
                (id, full_name, guardian_contact, description, government_case_id, embedding, metadata_payload)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    person_id,
                    payload.get("full_name", "Unknown"),
                    payload.get("guardian_contact", "not-provided"),
                    payload.get("description", ""),
                    payload.get("government_case_id"),
                    embedding_bytes,
                    json.dumps(payload.get("metadata_payload", {})),
                ),
            )
            conn.commit()
        return person_id

    def find_best_match(self, embedding: list[float], threshold: float = 0.85) -> dict | None:
        """Find best cosine similarity match using SQLite."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT id, full_name, guardian_contact, description, government_case_id, embedding FROM missing_persons WHERE status='active'"
            ).fetchall()

        best_match = None
        best_sim = 0.0

        for row in rows:
            stored_emb = json.loads(row["embedding"])
            sim = self._cosine_similarity(embedding, stored_emb)
            if sim > best_sim:
                best_sim = sim
                best_match = row

        if best_match and best_sim >= threshold:
            return {
                "id": best_match["id"],
                "full_name": best_match["full_name"],
                "guardian_contact": best_match["guardian_contact"],
                "description": best_match["description"],
                "government_case_id": best_match["government_case_id"],
                "similarity": float(best_sim),
            }
        return None

    def search_missing_persons(
        self, query_text: str | None = None, embedding: list[float] | None = None, limit: int = 10
    ) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT id, full_name, guardian_contact, description, government_case_id, embedding FROM missing_persons WHERE status='active'"
            ).fetchall()

        normalized_query = (query_text or "").strip().lower()
        candidates = []

        for row in rows:
            similarity = None
            if embedding:
                stored_emb = json.loads(row["embedding"])
                similarity = self._cosine_similarity(embedding, stored_emb)

            keyword_score = 0.0
            if normalized_query:
                haystack = " ".join(
                    [
                        row["full_name"] or "",
                        row["description"] or "",
                        row["government_case_id"] or "",
                    ]
                ).lower()
                if normalized_query in haystack:
                    keyword_score = 0.7

            if similarity is None and keyword_score <= 0.0:
                continue

            combined_score = float(similarity if similarity is not None else 0.0) + keyword_score
            candidates.append(
                {
                    "id": row["id"],
                    "source": "missing_registry",
                    "full_name": row["full_name"],
                    "guardian_contact": row["guardian_contact"],
                    "description": row["description"],
                    "government_case_id": row["government_case_id"],
                    "similarity": float(similarity) if similarity is not None else None,
                    "score": combined_score,
                }
            )

        candidates.sort(key=lambda item: item["score"], reverse=True)
        return candidates[:limit]

    def search_public_case_reports(
        self, query_text: str | None = None, embedding: list[float] | None = None, limit: int = 10
    ) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    reporter_name,
                    reporter_relationship,
                    reporter_contact,
                    missing_person_name,
                    missing_person_age,
                    missing_since_iso,
                    last_seen_location,
                    circumstances,
                    status,
                    created_at,
                    payload
                FROM public_case_reports
                ORDER BY created_at DESC
                """
            ).fetchall()

        normalized_query = (query_text or "").strip().lower()
        candidates = []

        for row in rows:
            payload = json.loads(row["payload"]) if row["payload"] else {}
            case_embedding = payload.get("missing_person_photo_embedding")

            similarity = None
            if embedding and isinstance(case_embedding, list) and len(embedding) == len(case_embedding):
                similarity = self._cosine_similarity(embedding, case_embedding)

            keyword_score = 0.0
            if normalized_query:
                haystack = " ".join(
                    [
                        row["missing_person_name"] or "",
                        row["circumstances"] or "",
                    ]
                ).lower()
                if normalized_query in haystack:
                    keyword_score = 0.7

            if similarity is None and keyword_score <= 0.0:
                continue

            combined_score = float(similarity if similarity is not None else 0.0) + keyword_score
            candidates.append(
                {
                    "id": row["id"],
                    "report_id": row["id"],
                    "source": "public_case_report",
                    "full_name": row["missing_person_name"],
                    "missing_person_name": row["missing_person_name"],
                    "description": row["circumstances"],
                    "circumstances": row["circumstances"],
                    "reporter_name": row["reporter_name"],
                    "reporter_relationship": row["reporter_relationship"],
                    "reporter_contact": row["reporter_contact"],
                    "missing_person_age": row["missing_person_age"],
                    "missing_since_iso": row["missing_since_iso"],
                    "last_seen_location": row["last_seen_location"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "government_case_id": None,
                    "has_photo": bool(payload.get("missing_person_photo_data_url") or payload.get("missing_person_photo_embedding")),
                    "photo_url": f"/api/public/cases/{row['id']}/photo" if payload.get("missing_person_photo_data_url") else None,
                    "similarity": float(similarity) if similarity is not None else None,
                    "score": combined_score,
                }
            )

        candidates.sort(key=lambda item: item["score"], reverse=True)
        return candidates[:limit]

    def add_sighting(self, payload: dict) -> str:
        import uuid

        sighting_id = str(uuid.uuid4())
        embedding_bytes = json.dumps(payload["embedding"]).encode()

        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO sighting_reports
                (id, source_device_id, sighting_text, captured_at_iso, embedding, payload, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sighting_id,
                    payload.get("source_device_id", "unknown-device"),
                    payload.get("description", ""),
                    payload.get("captured_at_iso"),
                    embedding_bytes,
                    json.dumps(payload),
                    "received",
                ),
            )
            conn.commit()
        return sighting_id

    def update_sighting_match(
        self, sighting_id: str, matched_person_id: str, similarity: float, flagged: bool
    ) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE sighting_reports
                SET matched_missing_person_id=?, similarity_score=?, government_handoff_flagged=?, status=?
                WHERE id=?
                """,
                (matched_person_id, similarity, 1 if flagged else 0, "matched" if flagged else "no_match", sighting_id),
            )
            conn.commit()

    def get_matches(self, limit: int = 20) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT id, sighting_text, similarity_score, matched_missing_person_id, created_at
                FROM sighting_reports
                WHERE similarity_score IS NOT NULL
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        results = []
        for row in rows:
            results.append(
                {
                    "report_id": row["id"],
                    "sighting_text": row["sighting_text"],
                    "similarity_score": row["similarity_score"],
                    "matched_missing_person_id": row["matched_missing_person_id"],
                    "created_at": row["created_at"],
                }
            )
        return results

    def add_public_case_report(self, payload: dict) -> str:
        import uuid

        report_id = str(uuid.uuid4())

        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO public_case_reports
                (
                    id,
                    reporter_name,
                    reporter_relationship,
                    reporter_contact,
                    missing_person_name,
                    missing_person_age,
                    missing_since_iso,
                    last_seen_location,
                    circumstances,
                    status,
                    payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    payload["reporter_name"],
                    payload["reporter_relationship"],
                    payload["reporter_contact"],
                    payload["missing_person_name"],
                    payload.get("missing_person_age"),
                    payload.get("missing_since_iso"),
                    payload["last_seen_location"],
                    payload["circumstances"],
                    payload.get("status", "submitted"),
                    json.dumps(payload),
                ),
            )
            conn.commit()

        return report_id

    def update_public_case_photo_embedding(self, report_id: str, embedding: list[float]) -> bool:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT payload FROM public_case_reports WHERE id = ?",
                (report_id,),
            ).fetchone()

            if not row:
                return False

            payload = json.loads(row["payload"]) if row["payload"] else {}
            payload["missing_person_photo_embedding"] = embedding

            conn.execute(
                "UPDATE public_case_reports SET payload = ? WHERE id = ?",
                (json.dumps(payload), report_id),
            )
            conn.commit()

        return True

    def get_public_case_reports(self, limit: int = 20) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    reporter_name,
                    reporter_relationship,
                    reporter_contact,
                    missing_person_name,
                    missing_person_age,
                    missing_since_iso,
                    last_seen_location,
                    circumstances,
                    status,
                    payload,
                    created_at
                FROM public_case_reports
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        items = []
        for row in rows:
            payload = json.loads(row["payload"]) if row["payload"] else {}
            items.append(
                {
                    "report_id": row["id"],
                    "reporter_name": row["reporter_name"],
                    "reporter_relationship": row["reporter_relationship"],
                    "reporter_contact": row["reporter_contact"],
                    "missing_person_name": row["missing_person_name"],
                    "has_photo": bool(payload.get("missing_person_photo_data_url") or payload.get("missing_person_photo_embedding")),
                    "photo_url": f"/api/public/cases/{row['id']}/photo" if payload.get("missing_person_photo_data_url") else None,
                    "has_photo_embedding": bool(payload.get("missing_person_photo_embedding")),
                    "missing_person_age": row["missing_person_age"],
                    "missing_since_iso": row["missing_since_iso"],
                    "last_seen_location": row["last_seen_location"],
                    "circumstances": row["circumstances"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                }
            )

        return items

    def get_public_case_photo_data_url(self, report_id: str) -> str | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT payload FROM public_case_reports WHERE id = ?",
                (report_id,),
            ).fetchone()

        if not row:
            return None

        payload = json.loads(row["payload"]) if row["payload"] else {}
        return payload.get("missing_person_photo_data_url")

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        return dot_product / (norm_a * norm_b)
