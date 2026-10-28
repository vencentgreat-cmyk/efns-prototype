import pandas as pd
import pytest

from data.repositories.mock import MockRepository


@pytest.mark.parametrize("values, expected", [
    ([None, None], None), ([None, 3], 3), ([0], 0),
    ([-3, 1], -2), ([-3, 3], 0), ([], None),
])
def test_measurement_sums_keep_unknown_and_real_zero_separate(values, expected):
    repo = MockRepository()
    repo._production = pd.DataFrame({
        field: values for field in ("TOTAL_RECEIVED", "TOTAL_ACCEPTED", "REJECTED", "LOSS")
    })
    metrics = repo.get_production_summary_metrics()
    assert metrics["production_record_count"] == len(values)
    for field in ("total_received", "total_accepted", "total_rejected", "total_loss"):
        assert metrics[field] == expected
