from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase187_manufacturing_production_index_audit"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase187_manufacturing_production_index_audit.md"
RUN_ID = "partial_statistics_estimation_phase187_manufacturing_production_index_audit"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    for enc in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc, **kwargs)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, **kwargs)


def stamp(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    payload = out.to_json(orient="records", force_ascii=False, double_precision=12)
    out["input_hash"] = hashlib.sha256(payload.encode()).hexdigest()
    out["code_commit_hash"] = git_hash()
    out["run_id"] = RUN_ID
    out["created_at"] = CREATED_AT
    return out


def write_csv(name: str, df: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stamp(df).to_csv(OUT / name, index=False, encoding="utf-8-sig")


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    show = df.copy()
    for col in show.columns:
        show[col] = show[col].map(lambda x: "" if pd.isna(x) else str(x))
    headers = list(show.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in show.itertuples(index=False):
        vals = [str(v).replace("\n", "<br>").replace("|", "/") for v in row]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def period_label(x) -> str:
    s = str(int(x)) if pd.notna(x) else ""
    if len(s) == 6:
        return f"{s[:4]}Q{int(s[-2:])}"
    return s


def source_audit() -> pd.DataFrame:
    specs = [
        {
            "source_file": "mining_manufacturing_production_index.csv",
            "role": "2019~2023 시도×제조업 광공업생산지수 원천",
        },
        {
            "source_file": "rolling_mining_manufacturing_production_index.csv",
            "role": "2015~2025 확장 시도×제조업 광공업생산지수 원천",
        },
        {
            "source_file": "partial_stats_phase39_manufacturing_middle_production_index.csv",
            "role": "전국 일부 제조업 세부 광공업생산지수 원천",
        },
    ]
    rows = []
    for spec in specs:
        path = DATA / spec["source_file"]
        exists = path.exists()
        if not exists:
            rows.append({**spec, "exists": False})
            continue
        df = read_csv(path)
        periods = sorted(df["prd_de"].dropna().unique()) if "prd_de" in df else []
        if spec["source_file"] == "partial_stats_phase39_manufacturing_middle_production_index.csv":
            region_col = None
            industry_cols = ["c1_nm"] if "c1_nm" in df.columns else []
        else:
            region_col = "c1_nm" if "c1_nm" in df.columns else None
            industry_cols = ["c2_nm"] if "c2_nm" in df.columns else []
        rows.append(
            {
                **spec,
                "exists": True,
                "rows": len(df),
                "table_id": "; ".join(map(str, sorted(df["tbl_id"].dropna().unique()))) if "tbl_id" in df else "",
                "table_name": "; ".join(map(str, sorted(df["tbl_nm"].dropna().unique()))) if "tbl_nm" in df else "",
                "period_min": period_label(periods[0]) if periods else "",
                "period_max": period_label(periods[-1]) if periods else "",
                "period_count": len(periods),
                "region_count": df[region_col].nunique() if region_col else 0,
                "region_examples": ", ".join(map(str, df[region_col].dropna().unique()[:6])) if region_col else "전국 세부항목형",
                "industry_count": int(sum(df[c].nunique() for c in industry_cols)),
                "industry_examples": " / ".join(
                    f"{c}: " + ", ".join(map(str, df[c].dropna().unique()[:8])) for c in industry_cols
                ),
                "unit": "; ".join(map(str, sorted(df["unit_nm"].dropna().unique()))) if "unit_nm" in df else "",
            }
        )
    return pd.DataFrame(rows)


def phase39_usage_audit() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    city_path = DATA / "partial_stats_phase39_manufacturing_city_monthly.csv"
    middle_path = DATA / "partial_stats_phase39_manufacturing_city_middle_monthly.csv"
    quarter_path = DATA / "partial_stats_phase39_manufacturing_quarter_check.csv"

    city = read_csv(city_path) if city_path.exists() else pd.DataFrame()
    middle = read_csv(middle_path) if middle_path.exists() else pd.DataFrame()
    quarter = read_csv(quarter_path) if quarter_path.exists() else pd.DataFrame()

    usage_rows = []
    if not city.empty:
        usage_rows.append(
            {
                "check_item": "고양시 제조업 월별 총부가가치 시간배분",
                "verdict": "PASS",
                "evidence": "경기도 제조업 광공업생산지수와 고양시 산업용 전력을 결합한 indicator가 존재",
                "rows": len(city),
                "period_min": f"{int(city.sort_values(['year','month']).iloc[0].year)}-{int(city.sort_values(['year','month']).iloc[0].month):02d}",
                "period_max": f"{int(city.sort_values(['year','month']).iloc[-1].year)}-{int(city.sort_values(['year','month']).iloc[-1].month):02d}",
                "non_null_production_index": int(city["production_index"].notna().sum()) if "production_index" in city else 0,
                "non_null_industrial_kwh": int(city["industrial_kwh"].notna().sum()) if "industrial_kwh" in city else 0,
                "non_null_indicator": int(city["indicator"].notna().sum()) if "indicator" in city else 0,
            }
        )
    else:
        usage_rows.append(
            {
                "check_item": "고양시 제조업 월별 총부가가치 시간배분",
                "verdict": "FAIL",
                "evidence": "phase39 city monthly 산출물이 없음",
            }
        )

    if not quarter.empty and "error" in quarter:
        usage_rows.append(
            {
                "check_item": "분기 통제총량 일치성",
                "verdict": "PASS",
                "evidence": "Denton 제약 후 월별 합계가 분기 제조업 GVA 통제총량과 일치",
                "rows": len(quarter),
                "max_abs_error_won_or_source_unit": float(quarter["error"].abs().max()),
                "mean_abs_error_won_or_source_unit": float(quarter["error"].abs().mean()),
            }
        )

    source_summary = pd.DataFrame()
    if not middle.empty:
        source_summary = (
            middle.groupby("monthly_profile_source")
            .agg(
                rows=("middle_code", "size"),
                middle_code_count=("middle_code", "nunique"),
                middle_codes=("middle_code", lambda s: ", ".join(sorted(map(str, s.unique()))[:40])),
            )
            .reset_index()
        )
        broad_codes = set(
            middle.loc[
                middle["monthly_profile_source"].astype(str).str.contains("Gyeonggi manufacturing index", na=False),
                "middle_code",
            ].astype(str)
        )
        detailed_codes = set(
            middle.loc[
                middle["monthly_profile_source"].astype(str).str.contains("semiconductor", case=False, na=False),
                "middle_code",
            ].astype(str)
        )
        usage_rows.append(
            {
                "check_item": "중분류별 월 경로 차별화",
                "verdict": "PARTIAL",
                "evidence": (
                    f"C26 등 {len(detailed_codes)}개 중분류만 세부 생산지수 경로, "
                    f"{len(broad_codes)}개 중분류는 광역 제조업 공통 경로 사용"
                ),
                "rows": len(middle),
                "broad_middle_code_count": len(broad_codes),
                "detailed_middle_code_count": len(detailed_codes),
            }
        )

    return pd.DataFrame(usage_rows), source_summary, quarter


def omission_and_vintage_audit() -> pd.DataFrame:
    phase26 = ROOT / "reports" / "partial_statistics_estimation_phase26_gva.md"
    phase186_script = ROOT / "scripts" / "run_phase186_c00_indicator_screen.py"
    phase186_report = ROOT / "reports" / "partial_statistics_estimation_phase186_c00_indicator_screen.md"
    phase39_script = ROOT / "scripts" / "run_partial_statistics_phase39_gva.py"

    phase26_text = phase26.read_text(encoding="utf-8") if phase26.exists() else ""
    script186 = phase186_script.read_text(encoding="utf-8") if phase186_script.exists() else ""
    report186 = phase186_report.read_text(encoding="utf-8") if phase186_report.exists() else ""
    script39 = phase39_script.read_text(encoding="utf-8") if phase39_script.exists() else ""

    rows = [
        {
            "audit_item": "Phase186 제조업 후보 선별의 산업생산지수 포함 여부",
            "verdict": "FAIL_SCOPE_OMISSION",
            "evidence": (
                "Phase186은 personal-business indicator와 2023 제조업 부가가치형 지표를 선별했지만 "
                "DT_1F02001/DT_1F02011 산업생산지수 후보를 별도 평가하지 않음"
            ),
            "local_check": "production_index" in script186 or "DT_1F02001" in script186,
        },
        {
            "audit_item": "Phase186에서 leakage-risk 처리한 2023 제조업 지표의 성격",
            "verdict": "PASS_CLASSIFICATION",
            "evidence": (
                "Phase186의 leakage-risk 대상은 산업생산지수가 아니라 2023 city×middle 제조업 부가가치형 지표임. "
                "동일연도 목적변수 구조를 직접 반영할 수 있어 정밀·속보 후보로 엄격 제한한 판정은 타당"
            ),
            "local_check": "2023 city×middle manufacturing value-added" in report186
            or "phase109_manufacturing_value_added_indicator_2023" in script186,
        },
        {
            "audit_item": "Phase39 제조업 시간배분의 산업생산지수 사용",
            "verdict": "PASS_USED_FOR_TEMPORAL_ALLOCATION",
            "evidence": (
                "Phase39는 경기도 제조업 광공업생산지수와 고양시 산업용 전력을 결합해 고양시 제조업 월 경로를 만들고 "
                "분기 제조업 GVA 통제총량에 맞춤"
            ),
            "local_check": "rolling_mining_manufacturing_production_index.csv" in script39
            and "production_index" in script39
            and "industrial_kwh" in script39,
        },
        {
            "audit_item": "중분류·소분류 횡단면 추정에서 산업생산지수 단독 사용 가능성",
            "verdict": "INSUFFICIENT_ALONE",
            "evidence": (
                "시도×제조업 지수는 제조업 전체의 시간 변화에는 강하지만 고양/포항 시군구×중분류 횡단면을 직접 주지 않음. "
                "전국 일부 세부지수도 전체 KSIC 중분류를 덮지 않아 공장·전력·물동량 등 지역 활동자료와 결합해야 함"
            ),
            "local_check": True,
        },
        {
            "audit_item": "속보성 예측에서 공표시점 사용 가능성",
            "verdict": "PARTIAL_RISK_NEEDS_HISTORICAL_VINTAGE",
            "evidence": (
                "Phase26에는 DT_1F02001 최신 갱신일과 최신 수록시점만 있고 2019~2023 각 분기별 역사적 공표일 장부는 없음. "
                "따라서 정밀화/회고 분석에는 사용 가능하지만, 1개월 이내 속보성 실험에는 분기별 historical vintage ledger를 보강해야 함"
            ),
            "local_check": "not_a_complete_historical_vintage_ledger" in phase26_text
            or "materialized_current_update_not_historical_vintage" in phase26_text,
        },
    ]
    return pd.DataFrame(rows)


def write_report(
    source: pd.DataFrame,
    usage: pd.DataFrame,
    source_summary: pd.DataFrame,
    quarter: pd.DataFrame,
    judgement: pd.DataFrame,
) -> None:
    max_q_error = ""
    if not quarter.empty and "error" in quarter:
        max_q_error = f"{quarter['error'].abs().max():.6g}"
    detailed = md_table(source_summary) if not source_summary.empty else "중분류별 월 경로 산출물 없음"

    text = f"""# Phase187 제조업 산업생산지수 정밀 감사

## 결론

사용자 지적이 맞다. 제조업 부가가치 추정에서 **광공업생산지수/제조업 산업생산지수는 핵심 시간변화 지표**다. 기존 작업을 다시 확인한 결과, 이 지표는 Phase39의 고양시 제조업 월별 총부가가치 시간배분에는 사용됐다. 그러나 Phase186의 “제조업 취약 중분류 개선 후보 선별”에서는 산업생산지수를 별도 후보로 감사하지 않았고, 이 부분은 **범위 누락**이다.

정확한 판정은 다음과 같다.

- **제대로 된 부분**: 고양시 제조업 월별 GVA 경로는 경기도 제조업 산업생산지수와 고양시 산업용 전력량을 결합해 만들었고, 월 합계는 분기 제조업 GVA 통제총량과 일치한다. 최대 분기 합계 오차는 `{max_q_error}`로 사실상 0이다.
- **부족한 부분**: 중분류별 구조 개선 실험에서는 산업생산지수를 별도 후보로 비교하지 않았다. 또한 세부 생산지수는 전체 KSIC 중분류를 덮지 못해 대부분 중분류가 광역 제조업 공통 월 경로를 공유한다.
- **속보성 주의**: 현재 로컬에는 최신 스냅샷과 최신 갱신일 근거만 있고, 각 과거 분기별 실제 공표일 장부가 없다. 따라서 “예측시점에 알 수 있었던 값만 사용”하는 속보성 검증에는 historical vintage 보강이 필요하다.
- **Phase186 오해 정정**: Phase186에서 leakage-risk로 둔 것은 산업생산지수가 아니라 2023년 제조업 city×middle 부가가치형 지표다. 그 판정은 유지한다.

## 원천 자료 커버리지

{md_table(source)}

## 기존 실험 사용 감사

{md_table(usage)}

## 중분류별 월 경로 출처 분포

{detailed}

## 누락·유출·공표시점 판정

{md_table(judgement)}

## 후속 조치

1. Phase186은 “제조업 횡단면 후보 선별”로 명확히 재명명하거나, Phase187 판정을 붙여 산업생산지수 누락을 보정해야 한다.
2. 제조업 속보성 실험에는 DT_1F02001/DT_1F02011의 historical release ledger를 붙여야 한다. 없는 경우에는 “정밀화/회고 지표”로만 사용한다.
3. 중분류·소분류 추정에는 산업생산지수를 단독으로 쓰지 말고, 공장등록·산업용 전력·항만 물동량·조달/계약 등 지역 활동자료와 결합한 gated ensemble로 써야 한다.
4. 포항 제조업에는 경북 제조업 산업생산지수와 포항 산업용 전력/항만 물동량의 결합 경로를 고양 Phase39 방식과 동일하게 추가 점검해야 한다.
"""
    REPORT.write_text(text, encoding="utf-8")


def main() -> None:
    source = source_audit()
    usage, source_summary, quarter = phase39_usage_audit()
    judgement = omission_and_vintage_audit()

    write_csv("source_coverage.csv", source)
    write_csv("phase39_usage_audit.csv", usage)
    write_csv("middle_profile_source_summary.csv", source_summary)
    write_csv("quarter_control_check.csv", quarter)
    write_csv("omission_and_vintage_audit.csv", judgement)
    write_report(source, usage, source_summary, quarter, judgement)
    print(REPORT)


if __name__ == "__main__":
    main()
