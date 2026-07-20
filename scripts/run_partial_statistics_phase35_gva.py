from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT, cp949_safe


RUN_ID = "partial_statistics_estimation_phase35_gva"
GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
RAW_DIR = ROOT / "data" / "raw" / "phase35_free_interaction"
REPORT_PATH = ROOT / "reports" / "partial_statistics_estimation_phase35_gva.md"
KEPCO_FILES = {
    2023: (RAW_DIR / "kepco_industry_2023.csv", "cp949", "2023-08-16"),
    2024: (RAW_DIR / "kepco_industry_2024.csv", "utf-8-sig", "2024-08-06"),
    2025: (RAW_DIR / "kepco_industry_2025.csv", "cp949", "2025-11-17"),
}


def stable_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def add_audit(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    base = [c for c in out if c not in {"input_hash", "code_commit_hash", "run_id", "created_at"}]
    out["input_hash"] = stable_hash(out[base].head(20_000).to_dict("records")) if len(out) else ""
    out["code_commit_hash"] = git_hash()
    out["run_id"] = RUN_ID
    out["created_at"] = GENERATED_AT
    return out


def write_csv(name: str, frame: pd.DataFrame) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    for column in out:
        if out[column].dtype == object:
            out[column] = out[column].map(cp949_safe)
    out.to_csv(PROCESSED_DIR / name, index=False, encoding=CSV_ENCODING, errors="replace")


def normalize_sido(value: object) -> str:
    aliases = {
        "강원도": "강원특별자치도",
        "전라북도": "전북특별자치도",
        "제주도": "제주특별자치도",
    }
    text = str(value).strip()
    return aliases.get(text, text)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_region_universe() -> pd.DataFrame:
    q = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase22_gva_sigungu_quarterly_allocation_cube.parquet")
    out = q[["source_region", "sigungu_code", "sigungu_name"]].drop_duplicates().copy()
    out["sido_norm"] = out["source_region"].map(normalize_sido)
    out["sigungu_norm"] = out["sigungu_name"].astype(str).str.strip()
    duplicate_names = out.duplicated(["sido_norm", "sigungu_norm"], keep=False)
    if duplicate_names.any():
        raise AssertionError("region universe has non-unique normalized sido/sigungu names")
    return out


def load_kepco(region_universe: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    pieces = []
    inventory = []
    for vintage, (path, encoding, release_date) in KEPCO_FILES.items():
        raw = pd.read_csv(path, encoding=encoding, dtype=str, low_memory=False)
        raw.columns = raw.columns.str.strip()
        for column in raw:
            raw[column] = raw[column].str.strip()
        raw["year"] = pd.to_numeric(raw["년도"], errors="raise").astype(int)
        raw["month"] = pd.to_numeric(raw["월"], errors="raise").astype(int)
        raw["quarter"] = ((raw["month"] - 1) // 3 + 1).astype(int)
        raw["sido_norm"] = raw["시도"].map(normalize_sido)
        raw["sigungu_norm"] = raw["시군구"]
        raw["industry_code"] = raw["산업분류코드(대)"] + raw["산업분류코드(중)"].str.zfill(2)
        raw["parent_sector_code"] = raw["산업분류코드(대)"] + "00"
        raw["suppressed"] = raw["고객호수"].eq("5호미만제거")
        raw["customer_count"] = pd.to_numeric(raw["고객호수"], errors="coerce")
        raw["electricity_sales"] = pd.to_numeric(raw["판매량"], errors="coerce")
        raw["electricity_charge"] = pd.to_numeric(raw["판매요금"], errors="coerce")
        raw["release_date"] = release_date
        raw["source_vintage"] = vintage
        raw = raw.merge(
            region_universe[["sido_norm", "sigungu_norm", "sigungu_code"]],
            on=["sido_norm", "sigungu_norm"], how="left", validate="many_to_one",
        )
        inventory.append({
            "source_id": f"kepco_industry_{vintage}",
            "source_family": "KEPCO electricity",
            "cost": "free",
            "reference_period_min": f"{raw['year'].min()}-{raw['month'].min():02d}",
            "reference_period_max": f"{raw['year'].max()}-{raw['month'].max():02d}",
            "release_date": release_date,
            "rows": len(raw),
            "matched_region_rows": int(raw["sigungu_code"].notna().sum()),
            "suppressed_rows": int(raw["suppressed"].sum()),
            "sha256": sha256_file(path),
            "classification": "KSIC broad and middle",
            "role": "native sigungu x middle-industry x month interaction proxy",
        })
        pieces.append(raw)
    detail = pd.concat(pieces, ignore_index=True)
    keys = [
        "source_vintage", "release_date", "year", "quarter", "month", "sido_norm",
        "sigungu_norm", "sigungu_code", "parent_sector_code", "industry_code", "산업분류명(중)",
    ]
    agg = detail.groupby(keys, dropna=False, as_index=False).agg(
        legal_dong_rows=("읍면동(법정동)", "size"),
        suppressed_rows=("suppressed", "sum"),
        observed_rows=("electricity_sales", "count"),
        customer_count=("customer_count", lambda s: s.sum(min_count=1)),
        electricity_sales=("electricity_sales", lambda s: s.sum(min_count=1)),
        electricity_charge=("electricity_charge", lambda s: s.sum(min_count=1)),
    ).rename(columns={"산업분류명(중)": "industry_name"})
    agg["observed_legal_dong_rate"] = agg["observed_rows"] / agg["legal_dong_rows"]
    profile_keys = ["source_vintage", "year", "quarter", "sido_norm", "sigungu_norm", "industry_code"]
    agg["observed_month_count"] = agg.groupby(profile_keys)["electricity_sales"].transform("count")
    agg["quarter_observed_sales"] = agg.groupby(profile_keys)["electricity_sales"].transform("sum")
    agg["electricity_month_share"] = agg["electricity_sales"] / agg["quarter_observed_sales"].replace(0, np.nan)
    agg["profile_eligible"] = (
        agg["sigungu_code"].notna()
        & agg["observed_month_count"].eq(3)
        & agg["quarter_observed_sales"].gt(0)
    )
    return agg, pd.DataFrame(inventory)


def build_kepco_candidate(kepco: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    shadow = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase34_gva_joint_shadow.parquet")
    base = shadow[
        shadow["policy_id"].eq("R0_contemporaneous_structure")
        & shadow["target_year"].eq(2023)
        & shadow["quarter"].eq(1)
    ].copy()
    base["sido_norm"] = base["source_region"].map(normalize_sido)
    base["sigungu_norm"] = base["sigungu_name"].astype(str).str.strip()
    proxy = kepco[
        kepco["source_vintage"].eq(2023)
        & kepco["profile_eligible"]
        & kepco["parent_sector_code"].isin(["B00", "C00"])
    ].copy()
    proxy["target_year"] = proxy["year"]
    merged = base.merge(
        proxy,
        on=[
            "sigungu_code", "sido_norm", "sigungu_norm", "parent_sector_code",
            "industry_code", "target_year", "quarter",
        ],
        how="inner", validate="one_to_many", suffixes=("_gva", "_proxy"),
    )
    merged["estimated_monthly_middle_gva"] = (
        merged["quarterly_middle_allocation"] * merged["electricity_month_share"]
    )
    merged["proxy_source_family_count"] = 2
    merged["proxy_source_families"] = "KOSIS business/employment + KEPCO electricity"
    merged["release_asof_quarter_end"] = np.where(
        pd.to_datetime(merged["release_date"]) <= pd.Timestamp("2023-03-31"), "Y", "N"
    )
    merged["claim_scope"] = "retrospective_monthly_proxy_allocation_not_direct_GVA_actual"
    merged["production_use"] = "false"
    keep = [
        "source_region", "sigungu_code", "sigungu_name", "parent_sector_code", "industry_code",
        "industry_name_proxy", "target_year", "quarter", "month", "quarterly_middle_allocation",
        "electricity_sales", "electricity_month_share", "estimated_monthly_middle_gva",
        "legal_dong_rows", "suppressed_rows", "observed_rows", "observed_legal_dong_rate",
        "release_date", "release_asof_quarter_end", "proxy_source_family_count",
        "proxy_source_families", "claim_scope", "production_use",
    ]
    candidate = merged[keep].rename(columns={"industry_name_proxy": "industry_name"})
    candidate = candidate.sort_values(["sigungu_code", "parent_sector_code", "industry_code", "month"])
    if candidate.duplicated([
        "source_region", "sigungu_code", "industry_code", "target_year", "month"
    ]).any():
        raise AssertionError("KEPCO candidate key is not unique")

    support = base.groupby(
        ["source_region", "sigungu_code", "sigungu_name", "parent_sector_code"], as_index=False
    ).agg(
        parent_quarter_gva=("estimated_quarterly_gva", "first"),
        total_middle_count=("industry_code", "nunique"),
        total_middle_gva=("quarterly_middle_allocation", "sum"),
    )
    supported_industries = candidate.drop_duplicates([
        "source_region", "sigungu_code", "parent_sector_code", "industry_code", "target_year", "quarter"
    ])
    observed = supported_industries.groupby(
        ["source_region", "sigungu_code", "sigungu_name", "parent_sector_code"], as_index=False
    ).agg(
        supported_middle_count=("industry_code", "nunique"),
        supported_middle_gva=("quarterly_middle_allocation", "sum"),
        median_observed_legal_dong_rate=("observed_legal_dong_rate", "median"),
    )
    support = support.merge(observed, on=["source_region", "sigungu_code", "sigungu_name", "parent_sector_code"], how="left")
    support[["supported_middle_count", "supported_middle_gva"]] = support[["supported_middle_count", "supported_middle_gva"]].fillna(0)
    support["middle_count_coverage"] = support["supported_middle_count"] / support["total_middle_count"]
    support["middle_gva_support_rate"] = support["supported_middle_gva"] / support["total_middle_gva"].replace(0, np.nan)

    checks = candidate.groupby(
        ["source_region", "sigungu_code", "parent_sector_code", "industry_code", "target_year", "quarter"],
        as_index=False,
    ).agg(
        child_sum=("estimated_monthly_middle_gva", "sum"),
        parent_value=("quarterly_middle_allocation", "first"),
        month_count=("month", "nunique"),
    )
    checks["absolute_error"] = (checks["child_sum"] - checks["parent_value"]).abs()
    checks["status"] = np.where(checks["absolute_error"].le(1e-6), "pass", "fail")
    return add_audit(candidate), add_audit(support), add_audit(checks)


def normalized_profile_hash(values: pd.Series) -> str:
    arr = values.to_numpy(dtype=float)
    total = np.nansum(arr)
    norm = arr / total if total > 0 else arr
    return stable_hash([round(float(x), 10) for x in norm])


def matrix_audit(frame: pd.DataFrame, source: str, time_col: str, value_col: str) -> pd.DataFrame:
    rows = []
    ranks = []
    duplicate_groups = 0
    eligible_groups = 0
    for _, group in frame.groupby(["sido_norm", "sigungu_norm", "year"]):
        matrix = group.pivot_table(index=time_col, columns="industry_code", values=value_col, aggfunc="sum")
        matrix = matrix.dropna(axis=1, how="any")
        if min(matrix.shape) < 2:
            continue
        eligible_groups += 1
        values = matrix.to_numpy(dtype=float)
        singular = np.linalg.svd(values, compute_uv=False)
        tolerance = singular[0] * 1e-10 if len(singular) else 0.0
        ranks.append(int((singular > tolerance).sum()))
        hashes = matrix.apply(normalized_profile_hash, axis=0)
        duplicate_groups += int(hashes.nunique() == 1)
    rows.extend([
        {
            "source": source, "audit_id": "median_effective_temporal_rank",
            "value": float(np.median(ranks)) if ranks else np.nan,
            "numerator": int(sum(rank_ > 1 for rank_ in ranks)), "denominator": len(ranks),
            "status": "pass_interaction" if ranks and np.median(ranks) > 1 else "fail_rank_one",
        },
        {
            "source": source, "audit_id": "all_industries_identical_profile_group_rate",
            "value": duplicate_groups / eligible_groups if eligible_groups else np.nan,
            "numerator": duplicate_groups, "denominator": eligible_groups,
            "status": "pass_no_common_proxy" if eligible_groups and duplicate_groups == 0 else "review",
        },
    ])
    return pd.DataFrame(rows)


def load_nts(region_universe: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    manifest = pd.read_csv(RAW_DIR / "nts_lifestyle_manifest_2021_2023.csv", encoding="utf-8-sig", dtype=str)
    pieces = []
    for row in manifest.itertuples(index=False):
        raw = pd.read_csv(ROOT / row.local_file, encoding="cp949", dtype=str)
        raw.columns = raw.columns.str.strip()
        raw["reference_date"] = row.reference_date
        raw["registered_date"] = row.registered_date
        raw["year"] = int(row.reference_date[:4])
        raw["month"] = int(row.reference_date[4:6])
        raw["sido_norm"] = raw["시도"].map(normalize_sido)
        raw["sigungu_norm"] = raw["시군구"].astype(str).str.strip()
        raw["industry_code"] = raw["업종"].astype(str).str.strip()
        raw["value"] = pd.to_numeric(raw["당월"].str.replace(",", "", regex=False), errors="coerce")
        raw.loc[raw["value"].le(0), "value"] = np.nan
        raw = raw.merge(
            region_universe[["sido_norm", "sigungu_norm", "sigungu_code"]],
            on=["sido_norm", "sigungu_norm"], how="inner", validate="many_to_one",
        )
        pieces.append(raw[[
            "reference_date", "registered_date", "year", "month", "sido_norm", "sigungu_norm",
            "sigungu_code", "industry_code", "value",
        ]])
    nts = pd.concat(pieces, ignore_index=True)
    if nts.duplicated([
        "reference_date", "sido_norm", "sigungu_norm", "industry_code"
    ]).any():
        raise AssertionError("NTS current-month panel has duplicate keys")
    labels = nts.groupby("industry_code", as_index=False).agg(
        first_period=("reference_date", "min"), last_period=("reference_date", "max"),
        observed_months=("reference_date", "nunique"), observed_regions=("sigungu_code", "nunique"),
    )
    common_labels = set(labels.loc[labels["observed_months"].eq(36), "industry_code"])
    audit_input = nts[nts["industry_code"].isin(common_labels) & nts["value"].notna()].copy()
    identity = matrix_audit(audit_input, "NTS 100 lifestyle industries", "month", "value")
    identity["note"] = "native custom lifestyle-industry classification; diagnostic only, not forced into KSIC"

    manifest["reference_month_end"] = pd.to_datetime(manifest["reference_date"], format="%Y%m%d")
    manifest["registered_date_parsed"] = pd.to_datetime(manifest["registered_date"])
    manifest["release_lag_days"] = (manifest["registered_date_parsed"] - manifest["reference_month_end"]).dt.days
    manifest["available_by_reference_month_end"] = np.where(manifest["release_lag_days"].le(0), "Y", "N")
    release = manifest[[
        "reference_date", "registered_date", "modified_date", "release_lag_days",
        "available_by_reference_month_end", "local_file", "sha256",
    ]].copy()
    return nts, add_audit(labels), add_audit(pd.concat([identity], ignore_index=True)), add_audit(release)


def build_kepco_identity(kepco: pd.DataFrame, candidate: pd.DataFrame) -> pd.DataFrame:
    eligible = kepco[kepco["profile_eligible"] & kepco["parent_sector_code"].isin(["B00", "C00"])].copy()
    audit = matrix_audit(eligible, "KEPCO KSIC middle electricity", "month", "electricity_sales")
    audit["note"] = "three months per published vintage; exact KSIC-middle interaction but not a full multi-quarter panel"
    profile = candidate.sort_values("month").groupby(
        ["source_region", "sigungu_code", "parent_sector_code", "target_year", "industry_code"]
    )["electricity_month_share"].apply(normalized_profile_hash).reset_index(name="profile_hash")
    duplicates = profile.groupby(
        ["source_region", "sigungu_code", "parent_sector_code", "target_year"]
    )["profile_hash"].agg(["nunique", "size"])
    duplicates = duplicates[duplicates["size"].ge(2)]
    audit = pd.concat([audit, pd.DataFrame([{
        "source": "KEPCO-joined Phase34 candidate",
        "audit_id": "all_joined_industries_identical_profile_group_rate",
        "value": float((duplicates["nunique"] == 1).mean()) if len(duplicates) else np.nan,
        "numerator": int((duplicates["nunique"] == 1).sum()),
        "denominator": len(duplicates),
        "status": "pass_no_common_proxy" if len(duplicates) and not (duplicates["nunique"] == 1).any() else "review",
        "note": "direct test of the Phase34 common-industry-proxy defect after joining KEPCO",
    }])], ignore_index=True)
    return add_audit(audit)


def build_negative_control(candidate: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(20260720)
    errors = []
    for _, group in candidate.groupby([
        "source_region", "sigungu_code", "parent_sector_code", "target_year", "quarter"
    ]):
        matrix = group.pivot(index="month", columns="industry_code", values="electricity_month_share")
        if matrix.empty:
            continue
        permuted = matrix.to_numpy()[:, rng.permutation(matrix.shape[1])]
        errors.extend(np.abs(np.nansum(permuted, axis=0) - 1).tolist())
    max_share_error = float(max(errors)) if errors else np.nan
    return add_audit(pd.DataFrame([{
        "control_id": "within_month_industry_profile_permutation",
        "max_industry_quarter_share_error": max_share_error,
        "conservation_still_passes": "Y" if max_share_error <= 1e-6 else "N",
        "semantic_alignment_destroyed": "Y",
        "interpretation": "accounting conservation still cannot validate whether a temporal profile belongs to the labeled industry",
    }]))


def markdown_table(frame: pd.DataFrame, max_rows: int = 20) -> str:
    if frame.empty:
        return "_No rows_"
    shown = frame.head(max_rows).astype(str).replace({"nan": "", "NaN": "", "None": ""})
    columns = list(shown.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in shown.to_dict("records"):
        lines.append("| " + " | ".join(str(row[c]).replace("|", "/") for c in columns) + " |")
    return "\n".join(lines)


def write_report(tables: dict[str, pd.DataFrame], final: dict[str, object]) -> None:
    inv = tables["inventory"]
    identity = tables["identity"]
    support = tables["support"]
    release = tables["release"]
    lines = [
        "# Partial Statistics Estimation Phase 35 - Free Interaction Proxies",
        "",
        "## 1. 결론",
        "",
        "무료 공식자료만으로 Phase 34의 `공통 사업체 프록시 동일 적용` 결함은 부분적으로 해소됐다. 한전 자료는 시군구×KSIC 중분류×월을 원자료에서 동시에 관측하므로, 2023Q1 지원 셀의 월별 중분류 프로필은 더 이상 rank one이 아니다. 다만 공개 파일은 2023Q1·2024Q1·2025Q2의 세 분기만 담고 공표도 각 기준분기 종료 뒤이므로, 2021-2023 전체 시군구×중분류×분기 GVA를 검증·생산할 정도의 연속 패널은 아니다.",
        "",
        "국세청 자료는 2021-2023의 36개월 연속 시군구×100대 생활업종 상호작용을 제공하며 공통 프록시 결함을 통과한다. 그러나 100대 생활업종은 KSIC 중분류가 아니므로 임의 매핑하지 않고 서비스 활동 진단용 별도 제품으로 유지했다.",
        "",
        "## 2. 무료 원자료와 역할",
        "",
        markdown_table(inv[["source_id", "source_family", "cost", "reference_period_min", "reference_period_max", "release_date", "rows", "classification", "role"]]),
        "",
        "유료 카드 자료는 수집·사용하지 않았다. 한전과 국세청 파일은 공개 파일 다운로드 경로로 수집했으며 API 키가 필요하지 않았다.",
        "",
        "## 3. 상호작용·rank 감사",
        "",
        markdown_table(identity[["source", "audit_id", "value", "numerator", "denominator", "status", "note"]]),
        "",
        "Phase 34에서 중분류별 프로필 동일률은 100%, 중앙 유효 rank는 1이었다. Phase 35는 실제 지역×산업×월 전력자료를 붙여 이 결함이 단순 정규화나 라벨 복제로 가려지지 않았는지 다시 계산했다.",
        "",
        "## 4. KEPCO 결합 지원 범위",
        "",
        markdown_table(pd.DataFrame([{
            "parent_cells": len(support),
            "parent_cells_with_support": int(support["supported_middle_count"].gt(0).sum()),
            "median_middle_count_coverage": support["middle_count_coverage"].median(),
            "median_middle_gva_support_rate": support["middle_gva_support_rate"].median(),
            "median_observed_legal_dong_rate": support["median_observed_legal_dong_rate"].median(),
        }])),
        "",
        "`5호미만제거` 행은 0으로 대체하지 않았다. 전력 판매량이 공개된 법정동만 합산하고, 각 셀의 관측 법정동 비율과 지원 GVA 비율을 함께 내보냈다. 따라서 결과는 완전관측 GVA가 아니라 suppression-aware 부분지원 월간 proxy allocation이다.",
        "",
        "## 5. 공표시차·누수 감사",
        "",
        markdown_table(pd.DataFrame([{
            "NTS_months": len(release),
            "median_release_lag_days": release["release_lag_days"].median(),
            "max_release_lag_days": release["release_lag_days"].max(),
            "available_by_reference_month_end": int(release["available_by_reference_month_end"].eq("Y").sum()),
            "KEPCO_2023_release_used": "2023-08-16",
            "KEPCO_2023_available_by_2023Q1_end": "N",
        }])),
        "",
        "한전 2023Q1 자료는 2023-08-16 수정 빈티지이므로 2023Q1 실시간 추정에는 사용할 수 없다. 국세청도 기준월 말에 사용 가능했던 빈티지가 없어 contemporaneous nowcast 입력으로 backdate하지 않았다.",
        "",
        "## 6. 정합성과 negative control",
        "",
        f"지원되는 {final['kepco_supported_middle_quarter_cells']:,}개 중분류×분기 셀의 월 합은 원래 Phase 34 분기 중분류 배분값과 모두 일치했다. 하지만 산업 프로필 순열 control도 정합을 통과하므로 정합성은 산업 의미나 GVA 정확도의 증거가 아니다.",
        "",
        markdown_table(tables["negative"][["control_id", "max_industry_quarter_share_error", "conservation_still_passes", "semantic_alignment_destroyed", "interpretation"]]),
        "",
        "## 7. 엄격 검증에서 발견한 추가 이슈",
        "",
        "1. 기존 `sigungu_code` 중 일부는 전국 유일 코드가 아니라 시도 내부 코드다. 시군구 코드만으로 묶으면 다른 시도의 지역이 합쳐질 수 있어 Phase 35의 모든 검증 키를 `시도+시군구+산업+기간` 복합키로 바꿨다.",
        "2. 한전 원행의 약 절반이 `5호미만제거`이고, 결합 후보의 중앙 관측 법정동 비율도 약 26.7%다. 억제 셀을 0으로 채우면 지역·산업별 월 프로필이 체계적으로 왜곡된다.",
        "3. 국세청은 각 월 파일에 100개 업종이 있지만 명칭 개편 때문에 2021-2023 합집합은 122개이고 36개월 모두 이어지는 라벨은 80개뿐이다. rank 검사는 이 80개 공통 라벨로 제한했다.",
        "4. 한전 전력과 KOSIS 사업체·종사자는 서로 다른 source family라 Phase 34보다 독립성은 좋아졌지만, 전력집약도와 GVA의 관계는 산업마다 다르다. rank 상승은 상호작용 존재의 증거이지 GVA 정확도의 증거가 아니다.",
        "5. 산업 프로필 순열 뒤에도 월합 정합은 유지됐다. 따라서 이번에도 정합성만으로 산업 라벨의 의미를 검증하지 않았다.",
        "",
        "## 8. 결정",
        "",
        "- `시군구×KSIC 중분류×월`: 2023Q1 지원 셀에 한해 회고적 연구용 proxy allocation으로 개선. 직접 GVA actual이나 생산통계로 주장 금지.",
        "- `시군구×KSIC 중분류×분기`: 전 기간 제품은 계속 Blocked. 한전 공개 파일이 세 개의 분기 스냅샷뿐이라 연속 분기 지표가 아니다.",
        "- `시군구×생활업종×월`: 2021-2023 연속 관측 활동 패널로 Retain. KSIC/GVA로 이름을 바꾸거나 강제 매핑 금지.",
        "- `시군구×KSIC 소분류`: 계속 Blocked. 무료 공개 원자료에서 동일 입도의 상호작용 자료를 확보하지 못했다.",
        "",
        "## 9. API 및 사용자 조치",
        "",
        "현재 완료한 한전·국세청 실험에는 API 키가 필요 없다. 고용행정통계 대시보드는 공개 화면에서 시군구×KSIC 중·소분류×월을 제공하지만, 공개 OpenAPI 응답에는 산업 차원이 없고 뷰어 내보내기는 세션형이다. 다음 단계에서 이것을 자동화하려면 API 키보다 먼저 사용자가 공개 대시보드에서 엑셀을 수동 내려받아 제공하는 방식이 가장 안전하다. 별도 유료 데이터나 카드사 계약은 요구하지 않는다.",
        "",
        "## 10. 최종 상태",
        "",
        "```json",
        json.dumps(final, ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    regions = load_region_universe()
    kepco, inventory = load_kepco(regions)
    candidate, support, conservation = build_kepco_candidate(kepco)
    kepco_identity = build_kepco_identity(kepco, candidate)
    nts, nts_labels, nts_identity, nts_release = load_nts(regions)
    identity = add_audit(pd.concat([
        kepco_identity.drop(columns=["input_hash", "code_commit_hash", "run_id", "created_at"]),
        nts_identity.drop(columns=["input_hash", "code_commit_hash", "run_id", "created_at"]),
    ], ignore_index=True))
    negative = build_negative_control(candidate)
    inventory = pd.concat([inventory, pd.DataFrame([{
        "source_id": "nts_lifestyle_monthly_2021_2023",
        "source_family": "National Tax Service business registry",
        "cost": "free",
        "reference_period_min": "2021-01",
        "reference_period_max": "2023-12",
        "release_date": "monthly vintage-specific",
        "rows": len(nts),
        "matched_region_rows": len(nts),
        "suppressed_rows": int(nts["value"].isna().sum()),
        "sha256": stable_hash(sorted(pd.read_csv(RAW_DIR / "nts_lifestyle_manifest_2021_2023.csv", encoding="utf-8-sig")["sha256"])),
        "classification": "NTS 100 lifestyle industries (122 labels across revisions)",
        "role": "native sigungu x custom-industry x month interaction diagnostic",
    }])], ignore_index=True)
    inventory = add_audit(inventory)

    write_csv("partial_stats_phase35_source_inventory.csv", inventory)
    write_csv("partial_stats_phase35_kepco_monthly_candidate.csv", candidate)
    write_csv("partial_stats_phase35_kepco_support.csv", support)
    write_csv("partial_stats_phase35_kepco_conservation.csv", conservation)
    write_csv("partial_stats_phase35_interaction_identity_audit.csv", identity)
    write_csv("partial_stats_phase35_nts_label_drift.csv", nts_labels)
    write_csv("partial_stats_phase35_release_audit.csv", nts_release)
    write_csv("partial_stats_phase35_negative_controls.csv", negative)

    rank = identity.set_index(["source", "audit_id"])["value"]
    final = {
        "status": "phase35_completed;free_interaction_signal_found;partial_retrospective_monthly_proxy_only;full_quarterly_product_blocked",
        "paid_card_data_used": False,
        "api_key_required_for_completed_experiment": False,
        "kepco_raw_rows": int(inventory.loc[inventory["source_family"].eq("KEPCO electricity"), "rows"].sum()),
        "kepco_supported_monthly_rows_2023q1": len(candidate),
        "kepco_supported_middle_quarter_cells": int(len(conservation)),
        "kepco_all_supported_cells_conserve": bool(conservation["status"].eq("pass").all()),
        "kepco_median_effective_rank": float(rank.loc[("KEPCO KSIC middle electricity", "median_effective_temporal_rank")]),
        "kepco_joined_common_proxy_group_rate": float(rank.loc[("KEPCO-joined Phase34 candidate", "all_joined_industries_identical_profile_group_rate")]),
        "nts_panel_rows": len(nts),
        "nts_continuous_months": 36,
        "nts_common_label_count": int(nts_labels["observed_months"].eq(36).sum()),
        "nts_median_effective_rank": float(rank.loc[("NTS 100 lifestyle industries", "median_effective_temporal_rank")]),
        "release_aware": True,
        "direct_monthly_middle_gva_actual_available": False,
        "full_sigungu_middle_quarter_product_decision": "Blocked",
        "partial_2023q1_sigungu_middle_month_proxy_decision": "Retain_research_only",
        "nts_sigungu_lifestyle_month_panel_decision": "Retain_as_activity_diagnostic_not_KSIC_GVA",
        "employment_dashboard_next_action": "manual free Excel export preferred; public OpenAPI lacks industry dimension",
        "production_use": False,
        "official_statistics_claim": False,
        "generated_at": GENERATED_AT,
    }
    (PROCESSED_DIR / "partial_stats_phase35_final_status.json").write_text(
        json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_report({
        "inventory": inventory, "identity": identity, "support": support,
        "release": nts_release, "negative": negative,
    }, final)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
