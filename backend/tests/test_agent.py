from app.agent import build_law_enforcement_handoff_payload


def test_build_law_enforcement_handoff_payload_shapes_data():
    match_payload = {
        "government_case_id": "CASE-123",
        "full_name": "Jane Doe",
        "guardian_contact": "+15555550123",
        "similarity": 0.92,
    }
    sighting_payload = {
        "description": "Green shirt near station",
        "captured_at_iso": "2026-03-24T12:00:00Z",
        "location": {"lat": 1.0, "lng": 2.0},
    }

    result = build_law_enforcement_handoff_payload(match_payload, sighting_payload)

    assert result["caseId"] == "CASE-123"
    assert result["matchedPersonName"] == "Jane Doe"
    assert result["guardianContact"] == "+15555550123"
    assert result["similarityScore"] == 0.92
    assert result["sightingDescription"] == "Green shirt near station"
    assert result["schemaVersion"] == "1.0"
