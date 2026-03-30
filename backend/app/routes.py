from flask import Blueprint, current_app, jsonify, request

from .agent import build_law_enforcement_handoff_payload, trigger_guardian_notification


api_bp = Blueprint("api", __name__)


PUBLIC_CASE_REQUIRED_FIELDS = (
    "reporter_name",
    "reporter_relationship",
    "reporter_contact",
    "missing_person_name",
    "last_seen_location",
    "circumstances",
)


def _validate_embedding(embedding: list[float], dims: int) -> bool:
    return isinstance(embedding, list) and len(embedding) == dims and all(
        isinstance(value, (int, float)) for value in embedding
    )


def _backend_unavailable_response():
    error_detail = getattr(current_app, "db_backend_error", None)
    payload = {
        "error": "Database backend unavailable. On Vercel, configure DATABASE_URL to a managed PostgreSQL instance with pgvector.",
    }
    if error_detail:
        payload["detail"] = error_detail
    return jsonify(payload), 503


def _require_backend_available():
    if getattr(current_app, "db_backend", None) == "unavailable":
        return _backend_unavailable_response()
    return None


@api_bp.get("/health")
def health_check():
    backend = current_app.db_backend if hasattr(current_app, "db_backend") else "unknown"
    return jsonify({"ok": True, "service": "BeaconAI API", "db_backend": backend})


def _validate_public_case_payload(payload: dict, vector_dims: int = 512) -> str | None:
    for field in PUBLIC_CASE_REQUIRED_FIELDS:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            return f"{field} is required"

    age = payload.get("missing_person_age")
    if age is not None:
        if isinstance(age, bool) or not isinstance(age, int) or age < 0:
            return "missing_person_age must be a non-negative integer"

    photo_data_url = payload.get("missing_person_photo_data_url")
    if photo_data_url is not None and not isinstance(photo_data_url, str):
        return "missing_person_photo_data_url must be a string"

    photo_embedding = payload.get("missing_person_photo_embedding")
    if photo_embedding is not None and not _validate_embedding(photo_embedding, vector_dims):
        return f"missing_person_photo_embedding must be a numeric vector of length {vector_dims}"

    return None


@api_bp.post("/search/missing")
def search_missing_persons():
    backend_guard = _require_backend_available()
    if backend_guard:
        return backend_guard

    payload = request.get_json(silent=True) or {}
    query_text = (payload.get("description") or "").strip()
    embedding = payload.get("embedding")
    image_search = bool(payload.get("image_search", False))
    min_similarity = float(payload.get("min_similarity", current_app.config["IMAGE_SEARCH_MIN_SIMILARITY"]))
    limit = int(payload.get("limit", 10))

    if not query_text and embedding is None:
        return jsonify({"error": "Provide description and/or embedding"}), 400

    vector_dims = current_app.config["VECTOR_DIMENSIONS"]
    if embedding is not None and not _validate_embedding(embedding, vector_dims):
        return jsonify({"error": f"embedding must be a numeric vector of length {vector_dims}"}), 400

    try:
        if current_app.db_backend == "sqlite":
            registry_items = current_app.sqlite_db.search_missing_persons(
                query_text=query_text or None,
                embedding=embedding,
                limit=limit,
            )
            public_items = current_app.sqlite_db.search_public_case_reports(
                query_text=query_text or None,
                embedding=embedding,
                limit=limit,
            )
            combined = sorted(registry_items + public_items, key=lambda item: item.get("score", 0), reverse=True)[:limit]
            if image_search and embedding is not None:
                combined = [
                    item
                    for item in combined
                    if item.get("similarity") is not None and float(item.get("similarity")) >= min_similarity
                ]
            return jsonify({"count": len(combined), "results": combined})

        from sqlalchemy import text

        from .extensions import db
        from .matcher import _to_vector_literal

        if embedding is not None:
            vector_literal = _to_vector_literal([float(x) for x in embedding])
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
                  AND (
                    :query_text = '' OR
                    full_name ILIKE :query_like OR
                    description ILIKE :query_like OR
                    government_case_id ILIKE :query_like
                  )
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
                """
            )
            rows = db.session.execute(
                query,
                {
                    "embedding": vector_literal,
                    "query_text": query_text,
                    "query_like": f"%{query_text}%",
                    "limit": limit,
                },
            ).mappings().all()
        else:
            query = text(
                """
                SELECT
                    id,
                    full_name,
                    guardian_contact,
                    description,
                    government_case_id
                FROM missing_persons
                WHERE status = 'active'
                  AND (
                    full_name ILIKE :query_like OR
                    description ILIKE :query_like OR
                    government_case_id ILIKE :query_like
                  )
                ORDER BY created_at DESC
                LIMIT :limit
                """
            )
            rows = db.session.execute(
                query,
                {
                    "query_like": f"%{query_text}%",
                    "limit": limit,
                },
            ).mappings().all()

        items = []
        for row in rows:
            keyword_score = 0.0
            if query_text:
                haystack = " ".join(
                    [
                        row["full_name"] or "",
                        row["description"] or "",
                        row["government_case_id"] or "",
                    ]
                ).lower()
                if query_text.lower() in haystack:
                    keyword_score = 0.7

            similarity = float(row["similarity"]) if "similarity" in row and row["similarity"] is not None else None
            score = (similarity if similarity is not None else 0.0) + keyword_score
            items.append(
                {
                    "id": str(row["id"]),
                    "source": "missing_registry",
                    "full_name": row["full_name"],
                    "guardian_contact": row["guardian_contact"],
                    "description": row["description"],
                    "government_case_id": row["government_case_id"],
                    "similarity": similarity,
                    "score": score,
                }
            )

        from .models import PublicCaseReport

        public_rows = PublicCaseReport.query.order_by(PublicCaseReport.created_at.desc()).limit(250).all()
        public_items = []
        for row in public_rows:
            row_payload = row.payload if isinstance(row.payload, dict) else {}
            case_embedding = row_payload.get("missing_person_photo_embedding")

            similarity = None
            if embedding is not None and isinstance(case_embedding, list) and len(case_embedding) == vector_dims:
                dot_product = sum(float(a) * float(b) for a, b in zip(embedding, case_embedding))
                norm_a = sum(float(a) * float(a) for a in embedding) ** 0.5
                norm_b = sum(float(b) * float(b) for b in case_embedding) ** 0.5
                if norm_a > 0 and norm_b > 0:
                    similarity = dot_product / (norm_a * norm_b)

            keyword_score = 0.0
            if query_text:
                haystack = " ".join(
                    [
                        row.missing_person_name or "",
                        row.circumstances or "",
                    ]
                ).lower()
                if query_text.lower() in haystack:
                    keyword_score = 0.7

            if similarity is None and keyword_score <= 0.0:
                continue

            public_items.append(
                {
                    "id": str(row.id),
                    "report_id": str(row.id),
                    "source": "public_case_report",
                    "full_name": row.missing_person_name,
                    "missing_person_name": row.missing_person_name,
                    "description": row.circumstances,
                    "circumstances": row.circumstances,
                    "reporter_name": row.reporter_name,
                    "reporter_relationship": row.reporter_relationship,
                    "reporter_contact": row.reporter_contact,
                    "missing_person_age": row.missing_person_age,
                    "missing_since_iso": row.missing_since_iso,
                    "last_seen_location": row.last_seen_location,
                    "status": row.status,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "government_case_id": None,
                    "has_photo": bool(
                        row_payload.get("missing_person_photo_data_url")
                        or row_payload.get("missing_person_photo_embedding")
                    ),
                    "similarity": similarity,
                    "score": (similarity if similarity is not None else 0.0) + keyword_score,
                }
            )

        combined = sorted(items + public_items, key=lambda item: item.get("score", 0), reverse=True)[:limit]
        if image_search and embedding is not None:
            combined = [
                item
                for item in combined
                if item.get("similarity") is not None and float(item.get("similarity")) >= min_similarity
            ]
        return jsonify({"count": len(combined), "results": combined})
    except Exception as e:
        return jsonify({"error": f"Search failed: {str(e)}"}), 500


@api_bp.post("/public/cases/reindex-embedding")
def reindex_public_case_embedding():
    backend_guard = _require_backend_available()
    if backend_guard:
        return backend_guard

    payload = request.get_json(silent=True) or {}
    report_id = payload.get("report_id")
    embedding = payload.get("embedding")

    if not isinstance(report_id, str) or not report_id.strip():
        return jsonify({"error": "report_id is required"}), 400

    vector_dims = current_app.config["VECTOR_DIMENSIONS"]
    if not _validate_embedding(embedding, vector_dims):
        return jsonify({"error": f"embedding must be a numeric vector of length {vector_dims}"}), 400

    try:
        if current_app.db_backend == "sqlite":
            updated = current_app.sqlite_db.update_public_case_photo_embedding(report_id.strip(), embedding)
            if not updated:
                return jsonify({"error": "report not found"}), 404
            return jsonify({"updated": True, "report_id": report_id.strip()})

        from .extensions import db
        from .models import PublicCaseReport

        report = PublicCaseReport.query.filter_by(id=report_id.strip()).first()
        if not report:
            return jsonify({"error": "report not found"}), 404

        report_payload = report.payload if isinstance(report.payload, dict) else {}
        report_payload["missing_person_photo_embedding"] = embedding
        report.payload = report_payload
        db.session.commit()

        return jsonify({"updated": True, "report_id": report_id.strip()})
    except Exception as e:
        return jsonify({"error": f"Failed to update embedding: {str(e)}"}), 500


@api_bp.post("/public/cases")
def submit_public_case_report():
    backend_guard = _require_backend_available()
    if backend_guard:
        return backend_guard

    payload = request.get_json(silent=True) or {}
    validation_error = _validate_public_case_payload(payload, current_app.config["VECTOR_DIMENSIONS"])
    if validation_error:
        return jsonify({"error": validation_error}), 400

    sanitized_payload = {
        "reporter_name": payload["reporter_name"].strip(),
        "reporter_relationship": payload["reporter_relationship"].strip(),
        "reporter_contact": payload["reporter_contact"].strip(),
        "missing_person_name": payload["missing_person_name"].strip(),
        "missing_person_photo_data_url": payload.get("missing_person_photo_data_url"),
        "missing_person_photo_embedding": payload.get("missing_person_photo_embedding"),
        "missing_person_age": payload.get("missing_person_age"),
        "missing_since_iso": payload.get("missing_since_iso"),
        "last_seen_location": payload["last_seen_location"].strip(),
        "circumstances": payload["circumstances"].strip(),
        "status": "submitted",
    }

    try:
        if current_app.db_backend == "sqlite":
            report_id = current_app.sqlite_db.add_public_case_report(sanitized_payload)
        else:
            from .extensions import db
            from .models import PublicCaseReport

            report = PublicCaseReport(
                reporter_name=sanitized_payload["reporter_name"],
                reporter_relationship=sanitized_payload["reporter_relationship"],
                reporter_contact=sanitized_payload["reporter_contact"],
                missing_person_name=sanitized_payload["missing_person_name"],
                missing_person_age=sanitized_payload.get("missing_person_age"),
                missing_since_iso=sanitized_payload.get("missing_since_iso"),
                last_seen_location=sanitized_payload["last_seen_location"],
                circumstances=sanitized_payload["circumstances"],
                status="submitted",
                payload=sanitized_payload,
            )
            db.session.add(report)
            db.session.commit()
            report_id = str(report.id)

        return jsonify({"report_id": report_id, "status": "submitted"}), 201
    except Exception as e:
        return jsonify({"error": f"Failed to submit public case report: {str(e)}"}), 500


@api_bp.get("/public/cases")
def list_public_case_reports():
    backend_guard = _require_backend_available()
    if backend_guard:
        return backend_guard

    limit = int(request.args.get("limit", "20"))

    try:
        if current_app.db_backend == "sqlite":
            items = current_app.sqlite_db.get_public_case_reports(limit=limit)
            return jsonify({"count": len(items), "cases": items})

        from .models import PublicCaseReport

        rows = PublicCaseReport.query.order_by(PublicCaseReport.created_at.desc()).limit(limit).all()

        items = []
        for row in rows:
            items.append(
                {
                    "report_id": str(row.id),
                    "reporter_name": row.reporter_name,
                    "reporter_relationship": row.reporter_relationship,
                    "reporter_contact": row.reporter_contact,
                    "missing_person_name": row.missing_person_name,
                    "has_photo": bool(row.payload.get("missing_person_photo_data_url"))
                    if isinstance(row.payload, dict)
                    else False,
                    "has_photo_embedding": bool(row.payload.get("missing_person_photo_embedding"))
                    if isinstance(row.payload, dict)
                    else False,
                    "missing_person_age": row.missing_person_age,
                    "missing_since_iso": row.missing_since_iso,
                    "last_seen_location": row.last_seen_location,
                    "circumstances": row.circumstances,
                    "status": row.status,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
            )

        return jsonify({"count": len(items), "cases": items})
    except Exception as e:
        return jsonify({"error": f"Failed to load public case reports: {str(e)}"}), 500


@api_bp.post("/sighting")
def create_sighting():
    backend_guard = _require_backend_available()
    if backend_guard:
        return backend_guard

    payload = request.get_json(silent=True) or {}

    embedding = payload.get("embedding")
    description = payload.get("description", "")
    device_id = payload.get("source_device_id", "unknown-device")

    vector_dims = current_app.config["VECTOR_DIMENSIONS"]
    threshold = current_app.config["SIMILARITY_THRESHOLD"]

    if not _validate_embedding(embedding, vector_dims):
        return jsonify({"error": f"embedding must be a numeric vector of length {vector_dims}"}), 400

    if not description.strip():
        return jsonify({"error": "description is required"}), 400

    sighting_payload = {
        "description": description,
        "captured_at_iso": payload.get("captured_at_iso"),
        "location": payload.get("location", {}),
        "source_device_id": device_id,
    }

    try:
        if current_app.db_backend == "sqlite":
            return _create_sighting_sqlite(sighting_payload, embedding, threshold)
        else:
            return _create_sighting_postgres(sighting_payload, embedding, threshold)

    except Exception as e:
        current_app.cache_store.add_pending_sighting(payload)
        return jsonify(
            {
                "status": "queued_locally",
                "message": f"Database unavailable. Sighting queued in local cache. Error: {str(e)}",
            }
        ), 202


def _create_sighting_sqlite(sighting_payload: dict, embedding: list[float], threshold: float):
    db = current_app.sqlite_db

    sighting_id = db.add_sighting(
        {
            **sighting_payload,
            "embedding": embedding,
        }
    )

    match = db.find_best_match(embedding, threshold)
    handoff_payload = None

    if match:
        db.update_sighting_match(sighting_id, match["id"], match["similarity"], True)
        trigger_guardian_notification(match)
        handoff_payload = build_law_enforcement_handoff_payload(match, sighting_payload)
        return jsonify(
            {
                "report_id": sighting_id,
                "status": "matched",
                "matched": True,
                "threshold": threshold,
                "match": match,
                "law_enforcement_payload": handoff_payload,
            }
        ), 201
    else:
        db.update_sighting_match(sighting_id, None, None, False)
        return jsonify(
            {
                "report_id": sighting_id,
                "status": "no_match",
                "matched": False,
                "threshold": threshold,
                "match": None,
                "law_enforcement_payload": None,
            }
        ), 201


def _create_sighting_postgres(sighting_payload: dict, embedding: list[float], threshold: float):
    from sqlalchemy.exc import SQLAlchemyError

    from .extensions import db
    from .matcher import find_best_match
    from .models import SightingReport

    try:
        report = SightingReport(
            source_device_id=sighting_payload.get("source_device_id", "unknown-device"),
            sighting_text=sighting_payload.get("description", ""),
            embedding=[float(x) for x in embedding],
            captured_at_iso=sighting_payload.get("captured_at_iso"),
            payload=sighting_payload,
            status="received",
        )
        db.session.add(report)

        match = find_best_match(report.embedding)
        handoff_payload = None

        if match and match["similarity"] >= threshold:
            report.matched_missing_person_id = match["id"]
            report.similarity_score = match["similarity"]
            report.status = "matched"
            report.government_handoff_flagged = True

            trigger_guardian_notification(match)
            handoff_payload = build_law_enforcement_handoff_payload(match, sighting_payload)
        else:
            report.status = "no_match"

        db.session.commit()

        return jsonify(
            {
                "report_id": str(report.id),
                "status": report.status,
                "matched": report.status == "matched",
                "threshold": threshold,
                "match": {
                    **match,
                    "id": match["id_str"],
                }
                if match
                else None,
                "law_enforcement_payload": handoff_payload,
            }
        ), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        raise e


@api_bp.get("/matches")
def get_matches():
    backend_guard = _require_backend_available()
    if backend_guard:
        return backend_guard

    limit = int(request.args.get("limit", "20"))

    try:
        if current_app.db_backend == "sqlite":
            items = current_app.sqlite_db.get_matches(limit=limit)
            return jsonify({"count": len(items), "matches": items})
        else:
            from .models import SightingReport

            from .extensions import db

            reports = (
                SightingReport.query.filter(SightingReport.similarity_score.isnot(None))
                .order_by(SightingReport.created_at.desc())
                .limit(limit)
                .all()
            )

            items = []
            for item in reports:
                items.append(
                    {
                        "report_id": str(item.id),
                        "sighting_text": item.sighting_text,
                        "similarity_score": item.similarity_score,
                        "matched_missing_person_id": str(item.matched_missing_person_id)
                        if item.matched_missing_person_id
                        else None,
                        "created_at": item.created_at.isoformat() if item.created_at else None,
                    }
                )

            return jsonify({"count": len(items), "matches": items})

    except Exception as e:
        pending = current_app.cache_store.get_pending_sightings(limit=limit)
        return jsonify(
            {
                "count": len(pending),
                "matches": [],
                "pending_cache": pending,
                "message": "Database unavailable. Returning cached pending sightings.",
            }
        ), 206


@api_bp.post("/seed/missing")
def seed_missing_records():
    backend_guard = _require_backend_available()
    if backend_guard:
        return backend_guard

    data = request.get_json(silent=True) or {}
    records = data.get("records", [])

    if not isinstance(records, list) or not records:
        return jsonify({"error": "records array is required"}), 400

    dims = current_app.config["VECTOR_DIMENSIONS"]
    created = 0

    for row in records:
        if not _validate_embedding(row.get("embedding", []), dims):
            return jsonify({"error": f"invalid embedding length; expected {dims}"}), 400

        try:
            if current_app.db_backend == "sqlite":
                current_app.sqlite_db.add_missing_person(row)
            else:
                from .extensions import db
                from .models import MissingPerson

                db.session.add(
                    MissingPerson(
                        full_name=row.get("full_name", "Unknown"),
                        guardian_contact=row.get("guardian_contact", "not-provided"),
                        description=row.get("description", ""),
                        government_case_id=row.get("government_case_id"),
                        embedding=[float(x) for x in row["embedding"]],
                        metadata_payload=row.get("metadata_payload", {}),
                    )
                )
                db.session.commit()
            created += 1
        except Exception as e:
            return jsonify({"error": f"Failed to add record: {str(e)}"}), 500

    return jsonify({"created": created}), 201
