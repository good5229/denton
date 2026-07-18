from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from partial_stats_phase5c_core import (  # noqa: E402
    aggregate_prediction_metrics,
    build_support_registry,
    decide_constraint,
    hamilton_integerize,
    reconcile_least_squares,
    reconcile_residual_share,
    wmape,
)


class MetricTests(unittest.TestCase):
    def test_wmape_perfect(self) -> None:
        self.assertEqual(wmape([0, 1, 10], [0, 1, 10]), 0.0)

    def test_wmape_tiny_denominator(self) -> None:
        self.assertTrue(math.isclose(wmape([0.001], [0.002]), 1.0))

    def test_zero_actual_handling(self) -> None:
        self.assertEqual(wmape([0, 0], [0, 0]), 0.0)
        self.assertTrue(math.isnan(wmape([0, 0], [1, 0])))

    def test_cell_balanced_metric(self) -> None:
        frame = pd.DataFrame(
            {
                "target_name": ["x", "x", "x"],
                "model_id": ["m", "m", "m"],
                "mask_id": ["a", "b", "b"],
                "mask_scenario": ["s", "s", "s"],
                "cell_id": [1, 1, 2],
                "actual": [10.0, 10.0, 10.0],
                "prediction": [0.0, 10.0, 10.0],
            }
        )
        result = aggregate_prediction_metrics(frame).iloc[0]
        self.assertTrue(math.isclose(float(result["cell_balanced_wmape"]), 0.25))

    def test_repeat_weighted_metric(self) -> None:
        frame = pd.DataFrame(
            {
                "target_name": ["x", "x"],
                "model_id": ["m", "m"],
                "mask_id": ["a", "b"],
                "mask_scenario": ["s", "s"],
                "cell_id": [1, 2],
                "actual": [100.0, 1.0],
                "prediction": [90.0, 0.0],
            }
        )
        result = aggregate_prediction_metrics(frame).iloc[0]
        self.assertTrue(math.isclose(float(result["scenario_weighted_wmape"]), 11 / 101))


class ConstraintTests(unittest.TestCase):
    def test_parent_residual(self) -> None:
        decision = decide_constraint(100, 60, True)
        self.assertEqual(decision.role, "hard")
        self.assertEqual(decision.residual_total, 40)

    def test_negative_residual_rejected(self) -> None:
        self.assertEqual(decide_constraint(10, 11, True).reason, "negative_residual")

    def test_external_child_handling(self) -> None:
        self.assertEqual(decide_constraint(100, 60, False).reason, "incomplete_child_universe")

    def test_duplicate_constraint_rejected(self) -> None:
        self.assertEqual(decide_constraint(100, 60, True, duplicate_parent_count=2).reason, "duplicate_parent")

    def test_hidden_children_sum(self) -> None:
        result = reconcile_residual_share([1, 3], 20)
        self.assertTrue(np.all(result >= 0))
        self.assertTrue(math.isclose(float(result.sum()), 20))

    def test_soft_constraint_conflict(self) -> None:
        result = reconcile_least_squares([2, 8], 5)
        self.assertTrue(np.all(result >= 0))
        self.assertTrue(math.isclose(float(result.sum()), 5, abs_tol=1e-7))

    def test_integerization_total_preserved(self) -> None:
        result = hamilton_integerize([1.2, 2.2, 3.6], total=7)
        self.assertEqual(int(result.sum()), 7)


class RouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cells = pd.DataFrame(
            {
                "cell_id": [1, 2, 3, 4],
                "region_key": ["A x", "A x", "A y", "B z"],
                "source_region": ["A", "A", "A", "B"],
                "industry_code": ["C10", "C10", "C10", "C11"],
                "industry_section": ["C", "C", "C", "C"],
                "period": ["2021", "2022", "2022", "2022"],
                "target_name": ["employees"] * 4,
                "valid_parent": [True, True, True, False],
            }
        )

    def test_support_class_deterministic(self) -> None:
        first = build_support_registry(self.cells, {1, 3})
        second = build_support_registry(self.cells, {1, 3})
        pd.testing.assert_frame_equal(first, second)

    def test_router_no_actual_dependency(self) -> None:
        first = build_support_registry(self.cells.assign(observed_value=[1, 2, 3, 4]), {1, 3})
        second = build_support_registry(self.cells.assign(observed_value=[999, 0, 7, 8]), {1, 3})
        pd.testing.assert_frame_equal(first, second)

    def test_not_estimable_fallback(self) -> None:
        result = build_support_registry(self.cells, {1, 3})
        self.assertEqual(result.set_index("cell_id").loc[4, "support_class"], "S6_not_estimable")

    def test_target_specific_policy(self) -> None:
        employee = build_support_registry(self.cells, {1, 3})
        establishment = build_support_registry(self.cells.assign(target_name="establishments"), {1, 3})
        self.assertEqual(len(employee), len(establishment))


if __name__ == "__main__":
    unittest.main()
