from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_partial_statistics_phase8 import (  # noqa: E402
    metric_registry,
    parse_ksic8_9,
    registries_and_blockers,
    stability_and_policy,
)


def test_ksic8_9_parser_nonempty() -> None:
    crosswalk = parse_ksic8_9()
    assert len(crosswalk) > 0
    assert crosswalk["old_code"].str.len().min() > 0
    assert crosswalk["new_code"].str.len().min() > 0
    assert (crosswalk["source_row"].astype(str).str.len() > 0).all()


def test_ksic_relationship_types_preserved() -> None:
    crosswalk = parse_ksic8_9()
    assert "one_to_many" in set(crosswalk["relationship_type"])
    assert "one_to_one" in set(crosswalk["relationship_type"])


def test_metric_registry_has_population_sensitive_ids() -> None:
    registry = metric_registry()
    assert {"M_WMAPE_POOLED_ABS", "M_CELL_BALANCED_WMAPE", "M_GROWTH_WMAPE"}.issubset(
        set(registry["metric_definition_id"])
    )


def test_count_model_not_proxied() -> None:
    implementation = registries_and_blockers()["implementation"]
    c1 = implementation[implementation["model_id"].eq("C1_hierarchical_growth_count_model")].iloc[0]
    assert c1["implementation_status"] == "not_implemented"
    assert c1["promotion_allowed"] == "N"


def test_primary_feature_bundle_blocked() -> None:
    bundles = registries_and_blockers()["feature_bundle"]
    assert (bundles["promotion_allowed"] == "N").all()


def test_stability_keeps_incumbent() -> None:
    bootstrap, placebo, material, selection, intervals, calibration = stability_and_policy(pd.DataFrame())
    assert (selection["selected_policy"] == "P7_incumbent").all()
    assert (selection["challenger_status"] == "none").all()
    assert (bootstrap["full_refit_executed"] == "N").all()
    assert (placebo["placebo_applicable"] == "N").all()
