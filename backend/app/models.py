import uuid
import os

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .extensions import db


VECTOR_DIMENSIONS = int(os.getenv("VECTOR_DIMENSIONS", "512"))


class MissingPerson(db.Model):
    __tablename__ = "missing_persons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    guardian_contact: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    government_case_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    metadata_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Responsible AI: only privacy-preserving embeddings are stored, never raw images.
    embedding: Mapped[list[float]] = mapped_column(Vector(VECTOR_DIMENSIONS), nullable=False)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SightingReport(db.Model):
    __tablename__ = "sighting_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_device_id: Mapped[str] = mapped_column(String(120), nullable=False)
    sighting_text: Mapped[str] = mapped_column(Text, nullable=False)
    captured_at_iso: Mapped[str | None] = mapped_column(String(60), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="received")

    # Responsible AI: vector-only record for face/sighting features.
    embedding: Mapped[list[float]] = mapped_column(Vector(VECTOR_DIMENSIONS), nullable=False)

    matched_missing_person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("missing_persons.id"), nullable=True
    )
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    government_handoff_flagged: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)
    local_cache_fallback_used: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

    missing_person: Mapped[MissingPerson | None] = relationship("MissingPerson", lazy="joined")


class PublicCaseReport(db.Model):
    __tablename__ = "public_case_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_name: Mapped[str] = mapped_column(String(200), nullable=False)
    reporter_relationship: Mapped[str] = mapped_column(String(100), nullable=False)
    reporter_contact: Mapped[str] = mapped_column(String(200), nullable=False)

    missing_person_name: Mapped[str] = mapped_column(String(200), nullable=False)
    missing_person_age: Mapped[int | None] = mapped_column(db.Integer, nullable=True)
    missing_since_iso: Mapped[str | None] = mapped_column(String(60), nullable=True)
    last_seen_location: Mapped[str] = mapped_column(String(300), nullable=False)
    circumstances: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="submitted")
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
