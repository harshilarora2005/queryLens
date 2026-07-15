from unittest.mock import MagicMock, patch

import pytest

from core import bq_executor
from core.bq_executor import (
    QueryCost,
    QueryTooExpensiveError,
    estimate_and_run,
)


def _make_fake_client(dry_run_bytes: int, real_df):
    client = MagicMock()

    dry_run_job = MagicMock()
    dry_run_job.total_bytes_processed = dry_run_bytes

    real_job = MagicMock()
    real_job.to_dataframe.return_value = real_df

    def query_side_effect(sql, job_config=None):
        if job_config is not None and getattr(job_config, "dry_run", False):
            return dry_run_job
        return real_job

    client.query.side_effect = query_side_effect
    return client


def test_query_under_cap_executes():
    import pandas as pd
    df = pd.DataFrame({"x": [1]})
    fake_client = _make_fake_client(dry_run_bytes=1_000_000, real_df=df)  # 1 MB

    with patch.object(bq_executor, "get_client", return_value=fake_client), \
        patch.object(bq_executor.settings, "MAX_BYTES_BILLED", 1_000_000_000):
        cost, result_df = estimate_and_run("SELECT * FROM `p.d.t` LIMIT 10")

    assert isinstance(cost, QueryCost)
    assert len(result_df) == 1


def test_query_over_cap_rejected_before_executing():
    import pandas as pd
    df = pd.DataFrame({"x": [1]})
    fake_client = _make_fake_client(dry_run_bytes=5_000_000_000, real_df=df)

    with patch.object(bq_executor, "get_client", return_value=fake_client), \
        patch.object(bq_executor.settings, "MAX_BYTES_BILLED", 1_000_000_000):
        with pytest.raises(QueryTooExpensiveError):
            estimate_and_run("SELECT * FROM `p.d.t`")

    real_calls = [
        call for call in fake_client.query.call_args_list
        if not (call.kwargs.get("job_config") and
                getattr(call.kwargs["job_config"], "dry_run", False))
    ]
    assert len(real_calls) == 0, "Query executed despite exceeding the cost cap"


def test_run_query_passes_maximum_bytes_billed_to_job_config():
    import pandas as pd
    fake_client = MagicMock()
    fake_client.query.return_value.to_dataframe.return_value = pd.DataFrame({"x": [1]})

    with patch.object(bq_executor, "get_client", return_value=fake_client):
        bq_executor.run_query("SELECT 1", max_bytes_billed=123_456)

    _, kwargs = fake_client.query.call_args
    job_config = kwargs["job_config"]
    assert job_config.maximum_bytes_billed == 123_456