from app.routes import _validate_embedding, _validate_public_case_payload


def test_validate_embedding_accepts_expected_shape():
    embedding = [0.1] * 512
    assert _validate_embedding(embedding, 512)


def test_validate_embedding_rejects_bad_shape_and_types():
    assert not _validate_embedding([0.1] * 511, 512)
    assert not _validate_embedding("not-a-list", 512)
    assert not _validate_embedding(["x"] * 512, 512)


def test_validate_public_case_payload_accepts_valid_payload():
    payload = {
        "reporter_name": "Mina Torres",
        "reporter_relationship": "Sister",
        "reporter_contact": "+1-555-0199",
        "missing_person_name": "Rafael Torres",
        "missing_person_age": 34,
        "last_seen_location": "Riverside Station",
        "circumstances": "Last seen after work shift.",
    }
    assert _validate_public_case_payload(payload) is None


def test_validate_public_case_payload_rejects_missing_required_fields():
    payload = {
        "reporter_name": "Mina Torres",
        "reporter_relationship": "",
        "reporter_contact": "+1-555-0199",
        "missing_person_name": "Rafael Torres",
        "last_seen_location": "Riverside Station",
        "circumstances": "Last seen after work shift.",
    }
    assert _validate_public_case_payload(payload) == "reporter_relationship is required"


def test_validate_public_case_payload_rejects_invalid_age():
    payload = {
        "reporter_name": "Mina Torres",
        "reporter_relationship": "Sister",
        "reporter_contact": "+1-555-0199",
        "missing_person_name": "Rafael Torres",
        "missing_person_age": -1,
        "last_seen_location": "Riverside Station",
        "circumstances": "Last seen after work shift.",
    }
    assert _validate_public_case_payload(payload) == "missing_person_age must be a non-negative integer"


def test_validate_public_case_payload_rejects_non_string_photo_payload():
    payload = {
        "reporter_name": "Mina Torres",
        "reporter_relationship": "Sister",
        "reporter_contact": "+1-555-0199",
        "missing_person_name": "Rafael Torres",
        "missing_person_photo_data_url": {"bad": "type"},
        "last_seen_location": "Riverside Station",
        "circumstances": "Last seen after work shift.",
    }
    assert _validate_public_case_payload(payload) == "missing_person_photo_data_url must be a string"


def test_validate_public_case_payload_rejects_invalid_photo_embedding_shape():
    payload = {
        "reporter_name": "Mina Torres",
        "reporter_relationship": "Sister",
        "reporter_contact": "+1-555-0199",
        "missing_person_name": "Rafael Torres",
        "missing_person_photo_embedding": [0.1] * 10,
        "last_seen_location": "Riverside Station",
        "circumstances": "Last seen after work shift.",
    }
    assert (
        _validate_public_case_payload(payload)
        == "missing_person_photo_embedding must be a numeric vector of length 512"
    )
