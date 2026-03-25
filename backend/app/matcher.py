from typing import Any

from sqlalchemy import text

from .extensions import db


def _to_vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in embedding) + "]"


def find_best_match(embedding: list[float]) -> dict[str, Any] | None:
    query = text(
        """
        SELECT
            id,
            full_name,
            guardian_contact,
            description,
            government_case_id,
            (1 - (embedding <=> CAST(:embedding AS vector))) AS similarity
        FROM missing_persons
        WHERE status = 'active'
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT 1
        """
    )

    vector_literal = _to_vector_literal(embedding)
    row = db.session.execute(query, {"embedding": vector_literal}).mappings().first()
    if not row:
        return None

    return {
        "id": row["id"],
        "id_str": str(row["id"]),
        "full_name": row["full_name"],
        "guardian_contact": row["guardian_contact"],
        "description": row["description"],
        "government_case_id": row["government_case_id"],
        "similarity": float(row["similarity"]),
    }
