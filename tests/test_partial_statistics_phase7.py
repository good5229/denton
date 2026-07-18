from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_partial_statistics_phase7 import (  # noqa: E402
    FULL_REFIT_BOOTSTRAP,
    POLICY_BOOTSTRAP,
    TARGETS,
    implementation_registry,
    policies,
    stability_artifacts,
)


def test_pm2_is_proxy_only() -> None:
    registry = implementation_registry()
    pm2 = registry[registry["model_id"].eq("PM2_hierarchical_negative_binomial_proxy")].iloc[0]
    assert pm2["implementation_status"] == "proxy_only"
    assert pm2["fallback_model"] == "PM1_one_sided_hierarchical_ridge"


def test_pb8_is_alias_of_pb0() -> None:
    registry = implementation_registry()
    pb8 = registry[registry["model_id"].eq("PB8_conservative_no_change")].iloc[0]
    assert pb8["implementation_status"] == "alias"
    assert pb8["fallback_model"] == "PB0_last_observation_level"


def test_frozen_policy_blocks_confirmatory_use() -> None:
    est_now, emp_now, est_fore, emp_fore, manifest = policies("input_hash", "feature_hash")
    for policy in [est_now, emp_now, est_fore, emp_fore]:
        assert policy["status"] == "frozen_baseline_policy"
        assert policy["production_use"] is False
        assert policy["confirmatory_use"] is False
        assert policy["official_statistics_claim"] is False
    assert manifest["frozen_policy_status"] == "baseline_policy_frozen"
    assert manifest["holdout_evaluation_allowed_before_new_sealed_vintage"] is False


def test_stability_artifacts_are_blocked_until_stable_cube() -> None:
    full_refit, policy, placebo, freq = stability_artifacts()
    assert len(full_refit) == FULL_REFIT_BOOTSTRAP * len(TARGETS) * 2
    assert (full_refit["full_refit_executed"] == "N").all()
    assert len(policy) == POLICY_BOOTSTRAP * len(TARGETS)
    assert (placebo["placebo_applicable"] == "N").all()
    assert isinstance(freq, pd.DataFrame)
