from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT, cp949_safe


RUN_ID = "partial_statistics_estimation_phase34_gva"
GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
REPORT_PATH = ROOT / "reports" / "partial_statistics_estimation_phase34_gva.md"
DERIVED_DIR = ROOT / "data" / "derived"


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


CODE_COMMIT_HASH = git_hash()


def stable_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def add_audit(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    base = [c for c in out.columns if c not in {"input_hash", "code_commit_hash", "run_id", "created_at"}]
    out["input_hash"] = stable_hash(out[base].head(20_000).to_dict("records")) if len(out) else ""
    out["code_commit_hash"] = CODE_COMMIT_HASH
    out["run_id"] = RUN_ID
    out["created_at"] = GENERATED_AT
    return out


def write_csv(name: str, frame: pd.DataFrame) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    for column in out.columns:
        if out[column].dtype == object:
            out[column] = out[column].map(cp949_safe)
    out.to_csv(PROCESSED_DIR / name, index=False, encoding=CSV_ENCODING, errors="replace")


def write_parquet(name: str, frame: pd.DataFrame) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(PROCESSED_DIR / name, index=False)


def markdown_table(frame: pd.DataFrame, max_rows: int = 20) -> str:
    if frame.empty:
        return "_No rows_"
    shown = frame.head(max_rows).astype(str).replace({"nan": "", "NaN": "", "None": ""})
    columns = list(shown.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in shown.to_dict("records"):
        lines.append("| " + " | ".join(str(row[c]).replace("|", "/") for c in columns) + " |")
    return "\n".join(lines)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    structure = pd.read_csv(
        DERIVED_DIR / "phase33_product_a2_fine_industry.csv",
        encoding=CSV_ENCODING,
        dtype=str,
        keep_default_na=False,
        low_memory=False,
    )
    quarterly = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase22_gva_sigungu_quarterly_allocation_cube.parquet")
    structure["area_code"] = structure["area_code"].astype(str).str.zfill(5)
    structure["source_year"] = pd.to_numeric(structure["year"], errors="raise").astype(int)
    quarterly["sigungu_code"] = quarterly["sigungu_code"].astype(str).str.zfill(5)
    quarterly["target_year"] = pd.to_numeric(quarterly["year"], errors="raise").astype(int)
    quarterly["quarter"] = pd.to_numeric(quarterly["quarter"], errors="raise").astype(int)
    return structure, quarterly


def build_conditional_structure(structure: pd.DataFrame) -> pd.DataFrame:
    out = structure.copy()
    out["parent_sector_code"] = out["industry_code"].str[:1] + "00"
    out = out[out["parent_sector_code"].isin(["B00", "C00"])].copy()
    for column in ["business_count", "employee_count"]:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    keys = ["area_code", "source_year", "parent_sector_code"]
    out["business_conditional_share"] = out["business_count"] / out.groupby(keys)["business_count"].transform("sum").replace(0, np.nan)
    out["employee_conditional_share"] = out["employee_count"] / out.groupby(keys)["employee_count"].transform("sum").replace(0, np.nan)
    out["fine_structure_weight"] = out[["business_conditional_share", "employee_conditional_share"]].mean(axis=1, skipna=True)
    out["fine_structure_weight"] = out["fine_structure_weight"] / out.groupby(keys)["fine_structure_weight"].transform("sum").replace(0, np.nan)
    out["structure_component_count"] = out[["business_conditional_share", "employee_conditional_share"]].notna().sum(axis=1)
    out["structure_source_family_count"] = 1
    out["structure_source_family_id"] = "manufacturing_mining_sigungu_ksic_business_employment"
    return out


def build_candidate(structure: pd.DataFrame, quarterly: pd.DataFrame, policy_id: str, lag_years: int) -> pd.DataFrame:
    left = quarterly[quarterly["sector_code"].isin(["B00", "C00"])].copy()
    right = structure.copy()
    right["target_year"] = right["source_year"] + lag_years
    join_keys_left = ["sigungu_code", "target_year", "sector_code"]
    join_keys_right = ["area_code", "target_year", "parent_sector_code"]
    merged = left.merge(right, left_on=join_keys_left, right_on=join_keys_right, how="inner", validate="many_to_many")
    merged["policy_id"] = policy_id
    merged["structure_lag_years"] = merged["target_year"] - merged["source_year"]
    merged["structure_asof_eligible"] = np.where(merged["structure_lag_years"].ge(2), "Y", "N")
    merged["temporal_vintage_eligible"] = "N"
    merged["temporal_vintage_reason"] = "historical release archive absent; current-snapshot profile only"
    merged["annual_middle_allocation"] = merged["annual_benchmark_gva"] * merged["fine_structure_weight"]
    merged["quarterly_middle_allocation"] = merged["estimated_quarterly_gva"] * merged["fine_structure_weight"]
    merged["implied_middle_quarter_share"] = merged["quarterly_middle_allocation"] / merged["annual_middle_allocation"].replace(0, np.nan)
    merged["interaction_source_id"] = ""
    merged["joint_value_status"] = "mechanical_separable_allocation_not_observed_joint_GVA"
    merged["direct_quarterly_middle_actual_available"] = "N"
    merged["actual_used_in_generation"] = "annual_parent_anchor_only"
    merged["evidence_grade"] = "U_joint"
    merged["claim_scope"] = "accounting_feasibility_only_not_sigungu_middle_quarter_GVA_accuracy"
    merged["production_use"] = "false"
    merged["official_statistics_claim"] = "false"
    keep = [
        "policy_id", "source_region", "sigungu_code", "sigungu_name", "parent_sector_code",
        "sector_name", "industry_code", "industry_name", "source_year", "target_year", "quarter", "period",
        "business_count", "employee_count", "business_conditional_share", "employee_conditional_share",
        "fine_structure_weight", "structure_component_count", "structure_source_family_count",
        "structure_source_family_id", "annual_benchmark_gva", "estimated_quarterly_gva", "quarter_share",
        "annual_middle_allocation", "quarterly_middle_allocation", "implied_middle_quarter_share",
        "allocation_basis", "indicator_source", "structure_lag_years", "structure_asof_eligible",
        "temporal_vintage_eligible", "temporal_vintage_reason", "interaction_source_id", "joint_value_status",
        "direct_quarterly_middle_actual_available", "actual_used_in_generation", "evidence_grade", "claim_scope",
        "production_use", "official_statistics_claim",
    ]
    out = merged[keep].sort_values(["target_year", "sigungu_code", "parent_sector_code", "industry_code", "quarter"]).reset_index(drop=True)
    duplicate_count = out.duplicated(["policy_id", "sigungu_code", "parent_sector_code", "industry_code", "target_year", "quarter"]).sum()
    if duplicate_count:
        raise AssertionError(f"candidate duplicate key count={duplicate_count}")
    return add_audit(out)


def build_coverage(structure: pd.DataFrame, quarterly: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    expected = quarterly[quarterly["sector_code"].isin(["B00", "C00"])][
        ["sigungu_code", "target_year", "sector_code"]
    ].drop_duplicates()
    rows: list[dict[str, object]] = []
    for policy_id, group in candidates.groupby("policy_id"):
        matched = group[["sigungu_code", "target_year", "parent_sector_code"]].drop_duplicates()
        policy_years = set(group["target_year"].unique())
        for parent in ["B00", "C00", "ALL"]:
            universe = expected if parent == "ALL" else expected[expected["sector_code"].eq(parent)]
            e = universe[universe["target_year"].isin(policy_years)]
            m = matched if parent == "ALL" else matched[matched["parent_sector_code"].eq(parent)]
            rows.append({
                "policy_id": policy_id,
                "parent_sector_code": parent,
                "universe_parent_cells": len(universe),
                "expected_parent_cells": len(e),
                "matched_parent_cells": len(m),
                "parent_cell_coverage_rate": len(m) / len(e) if len(e) else np.nan,
                "all_year_universe_coverage_rate": len(m) / len(universe) if len(universe) else np.nan,
                "matched_sigungu_count": m["sigungu_code"].nunique(),
                "matched_year_min": int(m["target_year"].min()) if len(m) else "",
                "matched_year_max": int(m["target_year"].max()) if len(m) else "",
            })
    rows.append({
        "policy_id": "source_inventory",
        "parent_sector_code": "ALL",
        "universe_parent_cells": len(structure),
        "expected_parent_cells": len(structure),
        "matched_parent_cells": structure["area_code"].nunique(),
        "parent_cell_coverage_rate": np.nan,
        "all_year_universe_coverage_rate": np.nan,
        "matched_sigungu_count": structure["area_code"].nunique(),
        "matched_year_min": int(structure["source_year"].min()),
        "matched_year_max": int(structure["source_year"].max()),
    })
    return add_audit(pd.DataFrame(rows))


def build_conservation(candidates: pd.DataFrame) -> pd.DataFrame:
    quarter = candidates.groupby(
        ["policy_id", "sigungu_code", "parent_sector_code", "target_year", "quarter"], as_index=False
    ).agg(child_sum=("quarterly_middle_allocation", "sum"), parent_value=("estimated_quarterly_gva", "first"))
    quarter["check_type"] = "quarter_parent_equals_sum_middle"
    quarter["absolute_error"] = (quarter["child_sum"] - quarter["parent_value"]).abs()
    annual = candidates.groupby(
        ["policy_id", "sigungu_code", "parent_sector_code", "target_year"], as_index=False
    ).agg(child_sum=("quarterly_middle_allocation", "sum"), parent_value=("annual_benchmark_gva", "first"))
    annual["quarter"] = ""
    annual["check_type"] = "annual_parent_equals_sum_middle_quarters"
    annual["absolute_error"] = (annual["child_sum"] - annual["parent_value"]).abs()
    out = pd.concat([quarter, annual], ignore_index=True)
    out["relative_error"] = out["absolute_error"] / out["parent_value"].abs().replace(0, np.nan)
    out["status"] = np.where(out["absolute_error"].le(1e-6), "pass", "fail")
    return add_audit(out)


def profile_hash(values: pd.Series) -> str:
    return stable_hash([round(float(x), 12) for x in values])


def build_identity_audit(candidates: pd.DataFrame, structure: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for policy_id, policy in candidates.groupby("policy_id"):
        rank_values: list[int] = []
        duplicate_groups = 0
        eligible_groups = 0
        for _, group in policy.groupby(["sigungu_code", "parent_sector_code", "target_year"]):
            matrix = group.pivot(index="quarter", columns="industry_code", values="quarterly_middle_allocation")
            if min(matrix.shape) < 2:
                continue
            eligible_groups += 1
            values = matrix.fillna(0).to_numpy(dtype=float)
            singular_values = np.linalg.svd(values, compute_uv=False)
            relative_tolerance = singular_values[0] * 1e-10 if len(singular_values) else 0.0
            rank_values.append(int((singular_values > relative_tolerance).sum()))
            profiles = group.sort_values("quarter").groupby("industry_code")["implied_middle_quarter_share"].apply(profile_hash)
            duplicate_groups += int(profiles.nunique() == 1)
        region_duplicate_groups = 0
        region_groups = 0
        broad = policy[["source_region", "sigungu_code", "parent_sector_code", "target_year", "quarter", "quarter_share"]].drop_duplicates()
        for _, group in broad.groupby(["source_region", "parent_sector_code", "target_year"]):
            if group["sigungu_code"].nunique() < 2:
                continue
            region_groups += 1
            hashes = group.sort_values("quarter").groupby("sigungu_code")["quarter_share"].apply(profile_hash)
            region_duplicate_groups += int(hashes.nunique() == 1)
        rows.extend([
            {
                "policy_id": policy_id,
                "audit_id": "fine_temporal_matrix_rank",
                "value": float(np.median(rank_values)) if rank_values else np.nan,
                "numerator": int(sum(r == 1 for r in rank_values)),
                "denominator": len(rank_values),
                "status": "fail_joint_interaction" if rank_values and all(r == 1 for r in rank_values) else "review",
                "interpretation": "rank one means the joint cube is an outer product of annual fine weights and one broad quarterly profile",
            },
            {
                "policy_id": policy_id,
                "audit_id": "within_parent_identical_industry_temporal_profile_rate",
                "value": duplicate_groups / eligible_groups if eligible_groups else np.nan,
                "numerator": duplicate_groups,
                "denominator": eligible_groups,
                "status": "fail_common_proxy" if duplicate_groups else "pass",
                "interpretation": "all middle industries inherit the same quarterly movement within a parent cell",
            },
            {
                "policy_id": policy_id,
                "audit_id": "within_sido_identical_sigungu_temporal_profile_rate",
                "value": region_duplicate_groups / region_groups if region_groups else np.nan,
                "numerator": region_duplicate_groups,
                "denominator": region_groups,
                "status": "fail_common_proxy" if region_duplicate_groups else "pass",
                "interpretation": "all sigungu inherit the same sido-level quarterly movement where the parent profile is shared",
            },
        ])

    both = structure[["business_conditional_share", "employee_conditional_share"]].dropna()
    rows.extend([
        {
            "policy_id": "structure_source",
            "audit_id": "business_employee_share_correlation",
            "value": float(both.corr().iloc[0, 1]) if len(both) > 1 else np.nan,
            "numerator": len(both),
            "denominator": len(structure),
            "status": "related_same_family_not_independent",
            "interpretation": "business and employee measures come from one source family and cannot count as two independent proxies",
        },
        {
            "policy_id": "structure_source",
            "audit_id": "single_component_weight_rate",
            "value": float(structure["structure_component_count"].eq(1).mean()),
            "numerator": int(structure["structure_component_count"].eq(1).sum()),
            "denominator": len(structure),
            "status": "warning_proxy_fallback",
            "interpretation": "rows with only business or employee share silently reduce the blend to one component",
        },
    ])
    return add_audit(pd.DataFrame(rows))


def build_stability(structure: pd.DataFrame) -> pd.DataFrame:
    keys = ["area_code", "parent_sector_code", "industry_code"]
    current = structure[keys + ["source_year", "fine_structure_weight"]].copy()
    prior = current.copy()
    prior["source_year"] += 1
    prior = prior.rename(columns={"fine_structure_weight": "prior_weight"})
    joined = current.merge(prior, on=keys + ["source_year"], how="inner")
    joined["absolute_change"] = (joined["fine_structure_weight"] - joined["prior_weight"]).abs()
    rows = []
    for parent, group in joined.groupby("parent_sector_code"):
        rows.append({
            "parent_sector_code": parent,
            "comparison_rows": len(group),
            "weight_correlation": float(group[["fine_structure_weight", "prior_weight"]].corr().iloc[0, 1]),
            "mean_absolute_weight_change": float(group["absolute_change"].mean()),
            "p95_absolute_weight_change": float(group["absolute_change"].quantile(0.95)),
            "validation_scope": "proxy_stability_not_GVA_accuracy",
        })
    return add_audit(pd.DataFrame(rows))


def build_negative_control(candidates: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for policy_id, group in candidates.groupby("policy_id"):
        permuted = group.copy()
        permuted["permuted_weight"] = permuted.groupby(
            ["sigungu_code", "parent_sector_code", "target_year", "quarter"]
        )["fine_structure_weight"].transform(lambda s: s.sample(frac=1, random_state=20260720).to_numpy())
        permuted["permuted_value"] = permuted["estimated_quarterly_gva"] * permuted["permuted_weight"]
        check = permuted.groupby(
            ["sigungu_code", "parent_sector_code", "target_year", "quarter"], as_index=False
        ).agg(child_sum=("permuted_value", "sum"), parent=("estimated_quarterly_gva", "first"))
        error = float((check["child_sum"] - check["parent"]).abs().max())
        rows.append({
            "policy_id": policy_id,
            "control_id": "within_parent_industry_label_permutation",
            "max_parent_conservation_error": error,
            "conservation_still_passes": "Y" if error <= 1e-6 else "N",
            "interpretation": "parent conservation cannot validate industry semantics because permuted industry weights also conserve exactly",
        })
    return add_audit(pd.DataFrame(rows))


def build_resolution_decision() -> pd.DataFrame:
    return add_audit(pd.DataFrame([
        {"candidate_grain": "sigungu×KSIC_middle×annual", "data_support": "B/C only; 2021-2023; partial sigungu coverage", "decision": "retain_as_structure_allocation_only", "reason": "no direct middle-industry GVA actual"},
        {"candidate_grain": "sigungu×KSIC_middle×quarter", "data_support": "separable annual structure plus broad quarterly profile", "decision": "blocked_as_joint_GVA", "reason": "rank-one cube; identical temporal proxy by middle industry; no interaction source or direct actual"},
        {"candidate_grain": "sigungu×KSIC_small×quarter", "data_support": "no compatible nationwide small-industry structure source", "decision": "blocked", "reason": "industry source grain unavailable"},
        {"candidate_grain": "sigungu×KSIC_middle×month", "data_support": "quarterly parent only in current experiment", "decision": "blocked", "reason": "would require equal-month or another unsupported common proxy"},
        {"candidate_grain": "sigungu×service_middle×quarter", "data_support": "quarterly service signal is sido×service section; A2 excludes services", "decision": "blocked", "reason": "spatial fine-service structure margin unavailable"},
    ]))


def report(tables: dict[str, pd.DataFrame], final: dict[str, object]) -> None:
    coverage = tables["coverage"]
    identity = tables["identity"]
    conservation = tables["conservation"]
    lines = [
        "# Partial Statistics Estimation Phase 34 - Sigungu Fine-Quarterly Feasibility",
        "",
        "## 1. 결론",
        "",
        "시군구×중분류×분기 표를 회계적으로 생성하는 것은 가능하지만, 현재 자료로는 이를 중분류별 분기 GVA 추정치로 승격할 수 없다. 생성된 결합행렬은 연간 중분류 가중치와 광역산업 공통 분기 프로필의 외적이어서 유효 rank가 1이며, 중분류별 고유한 분기 신호가 없다.",
        "",
        "## 2. 사전등록된 후보",
        "",
        "- `R0_contemporaneous_structure`: 같은 연도 구조를 사용한 회고적 회계 배분. 구조자료 공표시차 2년을 위반하므로 예측에는 사용할 수 없다.",
        "- `S0_lag2_structure`: 2년 전 구조를 사용한 구조축 as-of 후보. 구조축 누수는 막지만 과거 분기 지표의 release archive가 없어 전체 제품은 strict vintage가 아니다.",
        "- 두 후보 모두 direct 시군구×중분류×분기 actual이 없으므로 정확도 평가는 하지 않는다.",
        "",
        "## 3. Coverage",
        "",
        markdown_table(coverage[["policy_id", "parent_sector_code", "universe_parent_cells", "expected_parent_cells", "matched_parent_cells", "parent_cell_coverage_rate", "all_year_universe_coverage_rate", "matched_sigungu_count", "matched_year_min", "matched_year_max"]]),
        "",
        "## 4. 공통 프록시·유효차원 감사",
        "",
        markdown_table(identity[["policy_id", "audit_id", "value", "numerator", "denominator", "status", "interpretation"]]),
        "",
        "## 5. 구조 프록시 안정성",
        "",
        markdown_table(tables["stability"][["parent_sector_code", "comparison_rows", "weight_correlation", "mean_absolute_weight_change", "p95_absolute_weight_change", "validation_scope"]]),
        "",
        "## 6. 정합성과 negative control",
        "",
        f"정합 검사는 {len(conservation):,}개 그룹 모두 통과했고 최대 절대오차는 {pd.to_numeric(conservation['absolute_error']).max():.3g}이다. 그러나 산업 라벨 내부 순열 negative control도 똑같이 정합을 통과했다. 따라서 정합성은 계산 정확성만 보장하며 산업 의미나 GVA 정확도를 검증하지 못한다.",
        "",
        markdown_table(tables["negative"][["policy_id", "control_id", "max_parent_conservation_error", "conservation_still_passes", "interpretation"]]),
        "",
        "## 7. 해상도별 결정",
        "",
        markdown_table(tables["resolution"][["candidate_grain", "data_support", "decision", "reason"]]),
        "",
        "## 8. 엄격 검증에서 추가로 발견한 이슈",
        "",
        "1. Phase 33 A2의 `industry_structure_index`는 B/C 전체에서 합이 1이므로 B00 또는 C00 GVA를 배분할 때 그대로 쓰면 안 된다. Phase 34는 B와 C 내부에서 다시 조건부 정규화했다.",
        "2. 사업체와 종사자는 같은 KOSIS 제조·광업 source family이므로 독립 프록시 2개로 계산할 수 없다.",
        "3. 일부 행은 종사자 또는 사업체 중 하나가 비어 있어 평균 가중치가 사실상 단일 프록시 fallback이 된다.",
        "4. 시군구 분기 부모 자체도 공식 시군구 분기 actual이 아니라 연간 anchor의 development allocation이다. 하위 중분류 값은 한 단계 더 내려간 allocation이다.",
        "5. 같은 시도 안의 시군구가 동일한 분기 프로필을 상속하고, 같은 부모산업 안의 모든 중분류도 동일한 분기 프로필을 상속한다.",
        "6. 공표시차를 지킨 S0도 temporal historical vintage가 없으므로 완전한 strict-as-of 제품은 아니다.",
        "",
        "## 9. 최종 상태",
        "",
        "```json",
        json.dumps(final, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 10. 다음 실험 조건",
        "",
        "시군구×중분류×분기를 다시 열려면 최소 하나의 `시군구×중분류×분기` 상호작용 자료가 필요하다. 후보는 산업별 전력/카드/매출/고용보험 피보험자/부가세·전자세금계산서처럼 지역·업종·월을 동시에 식별하는 자료다. 확보 전에는 `시군구×중분류×연간 구조`와 `시도×산업×분기 활동`을 별도 marginal product로 제공하는 것이 정직하다.",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    raw_structure, quarterly = load_inputs()
    structure = build_conditional_structure(raw_structure)
    retrospective = build_candidate(structure, quarterly, "R0_contemporaneous_structure", lag_years=0)
    lagged = build_candidate(structure, quarterly, "S0_lag2_structure", lag_years=2)
    candidates = pd.concat([retrospective, lagged], ignore_index=True)
    coverage = build_coverage(structure, quarterly, candidates)
    conservation = build_conservation(candidates)
    identity = build_identity_audit(candidates, structure)
    stability = build_stability(structure)
    negative = build_negative_control(candidates)
    resolution = build_resolution_decision()

    write_parquet("partial_stats_phase34_gva_joint_shadow.parquet", candidates)
    write_csv("partial_stats_phase34_gva_coverage.csv", coverage)
    write_csv("partial_stats_phase34_gva_conservation.csv", conservation)
    write_csv("partial_stats_phase34_gva_proxy_identity_audit.csv", identity)
    write_csv("partial_stats_phase34_gva_structure_stability.csv", stability)
    write_csv("partial_stats_phase34_gva_negative_controls.csv", negative)
    write_csv("partial_stats_phase34_gva_resolution_decision.csv", resolution)

    rank_rows = identity[identity["audit_id"].eq("fine_temporal_matrix_rank")]
    duplicate_rows = identity[identity["audit_id"].eq("within_parent_identical_industry_temporal_profile_rate")]
    final = {
        "status": "phase34_completed;sigungu_middle_annual_structure_retained;sigungu_middle_quarter_joint_blocked;monthly_blocked;small_industry_blocked",
        "target": "GVA",
        "retrospective_joint_shadow_rows": int(len(retrospective)),
        "lag2_structure_shadow_rows": int(len(lagged)),
        "covered_parent_cells_retrospective": int(retrospective[["sigungu_code", "parent_sector_code", "target_year"]].drop_duplicates().shape[0]),
        "covered_parent_cells_lag2": int(lagged[["sigungu_code", "parent_sector_code", "target_year"]].drop_duplicates().shape[0]),
        "median_effective_temporal_rank": float(pd.to_numeric(rank_rows["value"]).median()),
        "identical_middle_industry_temporal_profile_rate": float(pd.to_numeric(duplicate_rows["value"]).mean()),
        "all_parent_conservation_checks_passed": bool(conservation["status"].eq("pass").all()),
        "permutation_negative_control_also_conserves": bool(negative["conservation_still_passes"].eq("Y").all()),
        "direct_quarterly_middle_actual_available": False,
        "historical_temporal_release_vintage_available": False,
        "interaction_source_available": False,
        "joint_product_decision": "Blocked",
        "allowed_claim": "sigungu manufacturing/mining middle-industry annual structure allocation and broad quarterly marginal signal, separately",
        "prohibited_claim": "observed or validated sigungu x middle-industry x quarter GVA; monthly GVA; small-industry GVA; production use; official statistics equivalence",
        "production_use": False,
        "official_statistics_claim": False,
        "generated_at": GENERATED_AT,
    }
    (PROCESSED_DIR / "partial_stats_phase34_gva_final_status.json").write_text(
        json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report({
        "coverage": coverage,
        "conservation": conservation,
        "identity": identity,
        "stability": stability,
        "negative": negative,
        "resolution": resolution,
    }, final)
    subprocess.run([str(ROOT / ".venv" / "bin" / "python"), str(ROOT / "scripts" / "verify_partial_statistics_phase34_gva.py")], cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
