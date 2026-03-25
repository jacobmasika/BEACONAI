import logging
from typing import Any


logger = logging.getLogger(__name__)


def trigger_guardian_notification(match_payload: dict[str, Any]) -> None:
    # Placeholder for SMS/email push integration.
    logger.warning(
        "Guardian notification triggered for %s (contact=%s, similarity=%.4f)",
        match_payload.get("full_name"),
        match_payload.get("guardian_contact"),
        match_payload.get("similarity", 0.0),
    )


def build_law_enforcement_handoff_payload(match_payload: dict[str, Any], sighting_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "caseId": match_payload.get("government_case_id"),
        "matchedPersonName": match_payload.get("full_name"),
        "guardianContact": match_payload.get("guardian_contact"),
        "similarityScore": match_payload.get("similarity"),
        "sightingDescription": sighting_payload.get("description"),
        "capturedAt": sighting_payload.get("captured_at_iso"),
        "location": sighting_payload.get("location", {}),
        "schemaVersion": "1.0",
    }
