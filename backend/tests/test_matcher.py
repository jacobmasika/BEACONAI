from app.matcher import _to_vector_literal


def test_to_vector_literal_formats_pgvector_value():
    literal = _to_vector_literal([0.1, 1.25, -0.5])
    assert literal.startswith("[")
    assert literal.endswith("]")
    assert "," in literal
