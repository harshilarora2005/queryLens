import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("GCP_PROJECT_ID", "fake-test-project")

from ingestion import schema_refresh


@pytest.fixture(autouse=True)
def _clear_cache_resource():
    yield
    schema_refresh._start_scheduler_once.clear()


def test_start_only_launches_scheduler_once_across_multiple_calls():
    fake_scheduler_cls = MagicMock()
    fake_scheduler_instance = MagicMock()
    fake_scheduler_cls.return_value = fake_scheduler_instance

    thread_starts = []

    class FakeThread:
        def __init__(self, target, daemon):
            self.target = target
            thread_starts.append(target)

        def start(self):
            pass 

    with patch(
        "apscheduler.schedulers.background.BackgroundScheduler",
        fake_scheduler_cls,
    ), patch.object(schema_refresh.threading, "Thread", FakeThread):
        for _ in range(5):
            schema_refresh.start(interval_hours=24)
    assert fake_scheduler_cls.call_count == 1
    assert fake_scheduler_instance.start.call_count == 1
    assert len(thread_starts) == 1


def test_do_refresh_updates_schema_and_clears_date_range_cache():
    fake_new_schema = {"tables": [{"name": "fake_table"}]}

    with patch("ingestion.schema_extractor.main") as mock_extract, \
        patch("pathlib.Path.read_text",
            return_value='{"tables": [{"name": "fake_table"}]}'):
        import core.sql_generator as gen
        with patch.object(gen, "_fetch_date_range") as mock_cache:
            ok = schema_refresh._do_refresh()

    assert ok is True
    mock_extract.assert_called_once()
    mock_cache.clear.assert_called_once()
    assert gen.SCHEMA == fake_new_schema


def test_do_refresh_reports_failure_on_exception():
    with patch("ingestion.schema_extractor.main", side_effect=RuntimeError("boom")):
        ok = schema_refresh._do_refresh()
    assert ok is False


def test_start_falls_back_gracefully_without_apscheduler():
    with patch.dict("sys.modules", {"apscheduler.schedulers.background": None}):
        schema_refresh.start(interval_hours=24) 