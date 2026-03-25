from pathlib import Path

from app.cache_store import SQLiteCacheStore


def test_cache_store_add_read_delete(tmp_path: Path):
    db_path = tmp_path / "cache.db"
    store = SQLiteCacheStore(str(db_path))

    row_id = store.add_pending_sighting({"description": "offline sighting"})
    assert row_id > 0

    rows = store.get_pending_sightings(limit=10)
    assert len(rows) == 1
    assert rows[0]["payload"]["description"] == "offline sighting"

    store.delete_pending_sighting(rows[0]["id"])
    rows_after = store.get_pending_sightings(limit=10)
    assert rows_after == []
