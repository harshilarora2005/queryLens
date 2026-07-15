import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("GCP_PROJECT_ID", "fake-test-project")

from ingestion import schema_refresh


@pytest.fixture(autouse=True)
def _clear_cache_resource():
    yield
    schema_refresh._start_scheduler_once.clear()  # type: ignore[attr-defined]


def test_do_refresh_updates_schema_and_clears_date_range_cache():
    fake_new_schema = {"tables": [{"name": "fake_table"}]}

    with (
        patch("ingestion.schema_extractor.main") as mock_extract,
        patch(
            "pathlib.Path.read_text",
            return_value='{"tables": [{"name": "fake_table"}]}',
        ),
    ):
        import core.sql_generator as gen

        mock_cache = MagicMock()

        with patch.object(gen, "_fetch_date_range", mock_cache):
            ok = schema_refresh._do_refresh()

    assert ok is True
    mock_extract.assert_called_once()
    mock_cache.clear.assert_called_once()
    assert gen.SCHEMA == fake_new_schema


def test_do_refresh_reports_failure_on_exception():
    with patch(
        "ingestion.schema_extractor.main",
        side_effect=RuntimeError("boom"),
    ):
        ok = schema_refresh._do_refresh()

    assert ok is False


def test_start_falls_back_gracefully_without_apscheduler():
    with patch.dict("sys.modules", {"apscheduler.schedulers.background": None}):
        schema_refresh.start(interval_hours=24)