from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from partial_stats_phase6_core import (  # noqa: E402
    available_at_origin,
    cell_balanced_wmape,
    first_eligible_date,
    one_sided_trend,
    stable_hash,
    support_class,
    wmape,
)


def test_feature_not_available_after_origin() -> None:
    assert not available_at_origin("2024-12-31", "2023-12-31")
    assert available_at_origin("2022-12-31", "2022-12-31")


def test_first_eligible_origin() -> None:
    assert first_eligible_date(2023, 12) == "2024-12-31"


def test_target_not_available_at_origin() -> None:
    target_release = first_eligible_date(2023, 12)
    assert not available_at_origin(target_release, "2023-12-31")


def test_one_sided_trend_only() -> None:
    train = pd.DataFrame(
        {
            "region_key": ["r", "r"],
            "industry_code": ["i", "i"],
            "target_name": ["employees", "employees"],
            "period": [2021, 2022],
            "value": [100.0, 130.0],
        }
    )
    valid = pd.DataFrame({"region_key": ["r"], "industry_code": ["i"], "target_name": ["employees"], "period": [2023]})
    pred = one_sided_trend(train, valid)
    assert float(pred.iloc[0]) == 160.0


def test_one_sided_trend_cap() -> None:
    train = pd.DataFrame(
        {
            "region_key": ["r", "r"],
            "industry_code": ["i", "i"],
            "target_name": ["establishments", "establishments"],
            "period": [2021, 2022],
            "value": [1.0, 100.0],
        }
    )
    valid = pd.DataFrame({"region_key": ["r"], "industry_code": ["i"], "target_name": ["establishments"], "period": [2023]})
    assert float(one_sided_trend(train, valid).iloc[0]) == 150.0


def test_support_recent_temporal_no_actual_dependency() -> None:
    train = pd.DataFrame({"region_key": ["r"], "industry_code": ["i"], "target_name": ["t"], "period": [2022], "value": [1.0]})
    row = pd.Series({"region_key": "r", "industry_code": "i", "target_name": "t", "period": 2023})
    assert support_class(train, row) == "PS1_recent_temporal"


def test_region_cold_start_support() -> None:
    train = pd.DataFrame({"region_key": ["other"], "industry_code": ["i"], "target_name": ["t"], "period": [2022], "value": [1.0]})
    row = pd.Series({"region_key": "new", "industry_code": "i", "target_name": "t", "period": 2023})
    assert support_class(train, row) == "PS3_regional_cold_start"


def test_industry_cold_start_support() -> None:
    train = pd.DataFrame({"region_key": ["r"], "industry_code": ["other"], "target_name": ["t"], "period": [2022], "value": [1.0]})
    row = pd.Series({"region_key": "r", "industry_code": "new", "target_name": "t", "period": 2023})
    assert support_class(train, row) == "PS4_industry_cold_start"


def test_cell_balanced_metric_repeated_cell() -> None:
    rows = pd.DataFrame({"cell_id": [1, 1, 2], "actual": [10.0, 10.0, 10.0], "prediction": [0.0, 10.0, 10.0]})
    assert np.isclose(cell_balanced_wmape(rows), 0.25)


def test_zero_actual_wmape() -> None:
    assert wmape([0.0, 0.0], [0.0, 0.0]) == 0.0


def test_forecast_hash_recorded() -> None:
    assert stable_hash({"forecast_id": "x"}) == stable_hash({"forecast_id": "x"})

