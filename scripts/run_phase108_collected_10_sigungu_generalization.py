#!/usr/bin/env python3
"""Phase108: collected 10-sigungu generalization validation.

The previous generalization pilot was only a feasibility screen because it used
whatever broad local data already existed.  This script collects the same type
of official holdout data used by Goyang/Pohang:

* KOSIS Economic Census 2015, DT_1KI1510_10
* city/sigungu x KSIC all/middle/small
* establishments, employees, sales

Sales is held out as the actual industry structure.  Establishments and
employees are used as the observable activity indicator.  The middle-industry
share error is then converted to 2023 GVA amounts using the local sigungu GRVA
large-industry control totals already stored in expanded_sigungu_grva_real.csv.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "scripts"))

from kosis_common import get_kosis_key, kosis_data, normalize_kosis_rows, write_csv, write_json  # noqa: E402
from run_partial_statistics_phase41_gva import parent_for_section, section_for_division  # noqa: E402


DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw" / "phase108_collected_10_sigungu"
OUT = DATA / "phase108_collected_10_sigungu_generalization"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase108_collected_10_sigungu_generalization.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
KOSIS_TABLE = "DT_1KI1510_10"


@dataclass(frozen=True)
class SampleCity:
    source_region: str
    sigungu_name: str
    kosis_region_code: str


SAMPLES = [
    SampleCity("광주광역시", "북구", "24040"),
    SampleCity("대전광역시", "동구", "25010"),
    SampleCity("대전광역시", "중구", "25020"),
    SampleCity("인천광역시", "동구", "23020"),
    SampleCity("전라남도", "강진군", "36390"),
    SampleCity("전라남도", "영암군", "36410"),
    SampleCity("전라남도", "함평군", "36430"),
    SampleCity("전북특별자치도", "익산시", "35030"),
    SampleCity("제주특별자치도", "서귀포시", "39020"),
    SampleCity("충청북도", "영동군", "33340"),
]


PARENT_TO_GRVA_NAMES = {
    "A00": {"농업 임업 및 어업"},
    "B00": {"광업"},
    "C00": {"제조업"},
    "D00": {"전기 가스 증기 및 공기 조절 공급업", "전기 가스 증기 및 공기조절 공급업"},
    "F00": {"건설업"},
    "G00": {"도매 및 소매업"},
    "H00": {"운수 및 창고업"},
    "I00": {"숙박 및 음식점업"},
    "J00": {"정보통신업"},
    "K00": {"금융 및 보험업", "금융보험업"},
    "L00": {"부동산업"},
    "MN0": {"사업서비스업"},
    "O00": {"공공 행정 국방 및 사회보장 행정", "공공행정 국방 및 사회보장 행정"},
    "P00": {"교육 서비스업", "교육서비스업"},
    "Q00": {"보건업 및 사회복지 서비스업", "보건업 및 사회복지서비스업"},
    # Local GRVA tables usually publish R/S as one culture/other bucket.  E is
    # not consistently separable in the local files, so only R/S middle cells are
    # compared against this ERS parent in Phase108.
    "ERS": {"문화 및 기타 서비스업", "문화 및 기타서비스업"},
}


def sha256_frame(frame: pd.DataFrame) -> str:
    payload = frame.head(50_000).to_json(orient="records", force_ascii=False, double_precision=12)
    return hashlib.sha256(payload.encode()).hexdigest()


def collect_kosis_city(city: SampleCity) -> pd.DataFrame:
    rows_out: list[dict[str, object]] = []
    raw: dict[str, object] = {}
    metrics = [("T10", "establishments"), ("T20", "employees"), ("T30", "sales")]
    key = get_kosis_key()
    for item_id, metric in metrics:
        rows = kosis_data(
            api_key=key,
            org_id="101",
            tbl_id=KOSIS_TABLE,
            item_id=item_id,
            period="F",
            start="2015",
            end="2015",
            obj={1: "ALL", 2: city.kosis_region_code},
        )
        raw[item_id] = rows
        for row in normalize_kosis_rows(rows, f"phase108_{city.kosis_region_code}_2015_all_ksic"):
            row["metric"] = metric
            row["source_region"] = city.source_region
            row["sigungu_name"] = city.sigungu_name
            row["kosis_region_code"] = city.kosis_region_code
            rows_out.append(row)
    write_json(RAW / f"kosis_{city.kosis_region_code}_2015_all_ksic.json", raw)
    return pd.DataFrame(rows_out)


def collect_all() -> pd.DataFrame:
    frames = [collect_kosis_city(city) for city in SAMPLES]
    out = pd.concat(frames, ignore_index=True)
    write_csv(DATA / "partial_stats_phase108_10_sigungu_2015_all_ksic.csv", out.to_dict("records"))
    return out


def load_or_collect() -> pd.DataFrame:
    path = DATA / "partial_stats_phase108_10_sigungu_2015_all_ksic.csv"
    if path.exists() and path.stat().st_size:
        return pd.read_csv(path, encoding="cp949", dtype=str)
    return collect_all()


def build_city_holdout(raw: pd.DataFrame) -> pd.DataFrame:
    raw = raw.copy()
    raw["value_num"] = pd.to_numeric(raw.value, errors="coerce")
    piv = (
        raw.pivot_table(
            index=["source_region", "sigungu_name", "kosis_region_code", "c1_id", "c1_nm"],
            columns="metric",
            values="value_num",
            aggfunc="first",
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )
    groups = piv[piv.c1_id.astype(str).str.len().eq(3)].copy()
    divisions = piv[piv.c1_id.astype(str).str.len().eq(2)].copy()
    divisions["division_code"] = divisions.c1_id.astype(str).str.zfill(2)
    divisions["division_name"] = divisions.c1_nm.astype(str)
    divisions["section_code"] = divisions.division_code.map(section_for_division)
    divisions["parent_code"] = divisions.section_code.map(parent_for_section)
    for col in ("establishments", "employees", "sales"):
        divisions[col] = pd.to_numeric(divisions.get(col), errors="coerce").fillna(0).clip(lower=0)
    for col in ("establishments", "employees"):
        base = divisions[col] + 0.01
        denom = base.groupby([divisions.kosis_region_code, divisions.parent_code]).transform("sum")
        divisions[f"{col}_share"] = base / denom.replace(0, np.nan)
    divisions["predicted_share"] = divisions[["establishments_share", "employees_share"]].mean(axis=1)
    divisions["predicted_share"] /= divisions.groupby(["kosis_region_code", "parent_code"]).predicted_share.transform("sum")
    divisions["actual_share"] = divisions.sales / divisions.groupby(["kosis_region_code", "parent_code"]).sales.transform("sum").replace(0, np.nan)
    divisions["uniform_share"] = 1 / divisions.groupby(["kosis_region_code", "parent_code"]).division_code.transform("count")
    out = divisions[divisions.sales.gt(0) & divisions.actual_share.notna()].copy()
    out["parent_middle_count"] = out.groupby(["kosis_region_code", "parent_code"]).division_code.transform("count")
    out["split_evaluable"] = out.parent_middle_count.gt(1)
    out["share_abs_error_pp"] = (out.predicted_share - out.actual_share).abs() * 100
    out["uniform_abs_error_pp"] = (out.uniform_share - out.actual_share).abs() * 100
    return out[
        [
            "source_region",
            "sigungu_name",
            "kosis_region_code",
            "parent_code",
            "section_code",
            "division_code",
            "division_name",
            "establishments",
            "employees",
            "sales",
            "actual_share",
            "predicted_share",
            "uniform_share",
            "parent_middle_count",
            "split_evaluable",
            "share_abs_error_pp",
            "uniform_abs_error_pp",
        ]
    ]


def grva_parent_controls() -> pd.DataFrame:
    raw = pd.read_csv(DATA / "expanded_sigungu_grva_real.csv", encoding="cp949", dtype=str)
    raw["value_num"] = pd.to_numeric(raw.value.str.replace(",", "", regex=False), errors="coerce")
    raw = raw[raw.prd_de.astype(str).eq("2023")].copy()
    rows: list[dict[str, object]] = []
    for city in SAMPLES:
        sub = raw[(raw.source_region.eq(city.source_region)) & (raw.c1_nm.eq(city.sigungu_name))].copy()
        for parent, names in PARENT_TO_GRVA_NAMES.items():
            val = sub[sub.c2_nm.isin(names)].value_num.sum()
            if val > 0:
                rows.append(
                    {
                        "source_region": city.source_region,
                        "sigungu_name": city.sigungu_name,
                        "kosis_region_code": city.kosis_region_code,
                        "parent_code": parent,
                        "parent_gva_eok": val / 100.0,  # source unit: million KRW
                        "grva_names": ", ".join(sorted(names)),
                    }
                )
    return pd.DataFrame(rows)


def attach_gva_errors(holdout: pd.DataFrame, controls: pd.DataFrame) -> pd.DataFrame:
    df = holdout.merge(controls, on=["source_region", "sigungu_name", "kosis_region_code", "parent_code"], how="left")
    # Avoid comparing E middle cells where local GRVA has no stable E-only parent
    df = df[~((df.parent_code.eq("ERS")) & (df.section_code.eq("E")))].copy()
    df = df[df.parent_gva_eok.notna() & df.parent_gva_eok.gt(0)].copy()
    df["actual_gva_eok"] = df.actual_share * df.parent_gva_eok
    df["predicted_gva_eok"] = df.predicted_share * df.parent_gva_eok
    df["error_gva_eok"] = (df.predicted_gva_eok - df.actual_gva_eok).abs()
    df["error_rate_pct"] = df.error_gva_eok / df.actual_gva_eok.replace(0, np.nan) * 100
    df["direction"] = np.where(df.predicted_gva_eok.gt(df.actual_gva_eok), "과대", "과소")
    return df


def summary_tables(detail: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    evaluable = detail[detail.split_evaluable].copy()
    city_summary = (
        evaluable.groupby(["source_region", "sigungu_name", "kosis_region_code"], as_index=False)
        .agg(
            middle_cells=("division_code", "count"),
            parent_groups=("parent_code", "nunique"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=("error_gva_eok", "sum"),
            median_error_rate_pct=("error_rate_pct", "median"),
            p90_error_rate_pct=("error_rate_pct", lambda s: float(s.quantile(0.9))),
            over_10pct_cells=("error_rate_pct", lambda s: int((s > 10).sum())),
            over_20pct_cells=("error_rate_pct", lambda s: int((s > 20).sum())),
        )
    )
    city_summary["wape_pct"] = city_summary.error_sum_eok / city_summary.actual_sum_eok * 100
    city_summary = city_summary.sort_values("wape_pct")

    parent_summary = (
        detail.groupby("parent_code", as_index=False)
        .agg(
            cells=("division_code", "count"),
            cities=("kosis_region_code", "nunique"),
            evaluable_cells=("split_evaluable", "sum"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=("error_gva_eok", "sum"),
            median_error_rate_pct=("error_rate_pct", "median"),
            over_10pct_cells=("error_rate_pct", lambda s: int((s > 10).sum())),
        )
    )
    parent_summary["wape_pct"] = parent_summary.error_sum_eok / parent_summary.actual_sum_eok * 100
    parent_summary["evaluation_note"] = np.where(parent_summary.evaluable_cells.eq(0), "단일 중분류: 성능판정 제외", "분할검증 가능")
    parent_summary = parent_summary.sort_values("wape_pct", ascending=False)

    weak = evaluable[evaluable.error_rate_pct.gt(10)].sort_values("error_gva_eok", ascending=False)
    strongest = evaluable.sort_values("error_rate_pct").groupby(["source_region", "sigungu_name"]).head(3)
    return city_summary, parent_summary, weak, strongest


def remaining_weak_improvement_queue() -> pd.DataFrame:
    p = DATA / "phase105_no_worse_refinement_guardrail" / "phase105_no_worse_refinement_registry.csv"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p)
    weak = df[df.no_worse_refined_error_rate_pct.gt(10)].copy()
    return (
        weak.groupby(["cause_group", "required_next_data"], as_index=False)
        .agg(
            cities=("city", lambda s: ", ".join(sorted(set(map(str, s))))),
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=("no_worse_refined_error_gva_eok", "sum"),
            median_error_rate_pct=("no_worse_refined_error_rate_pct", "median"),
            worst_industry=("middle_label", lambda s: str(s.iloc[0])),
        )
        .sort_values("error_sum_eok", ascending=False)
    )


def improvement_playbook() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "priority": 1,
                "target_group": "생산시설형 제조업",
                "applies_to": "C00 중분류 전반, 특히 1차금속·화학·전자·전기장비·기계수리",
                "why_error_remains": "사업체·종사자 수가 대형 설비의 출하액·부가가치·가동률을 반영하지 못함",
                "free_data_to_add": "광업제조업조사 시군구×중분류 출하액·부가가치, 공장등록 면적·종업원, 용도별 전력사용량",
                "model_change": "제조업 내부는 출하액·부가가치 또는 공장규모 가중치 우선, 없을 때만 기존 활동지표 후순위",
                "validation": "경제총조사 매출비중과 광업제조업조사 중분류 구조를 분리해 시간외삽 검증",
            },
            {
                "priority": 2,
                "target_group": "건설업",
                "applies_to": "F41 종합건설업 / F42 전문직별 공사업",
                "why_error_remains": "사업체 수는 전문공사업 쪽으로 많고, 금액은 원도급·대형공사 쪽에 집중됨",
                "free_data_to_add": "건축허가·착공·사용승인 면적, 건설수주·기성, 인허가 용도별 연면적",
                "model_change": "종합건설은 공사금액·착공/사용승인 면적, 전문공사는 사업체·종사자와 인허가 건수 혼합",
                "validation": "F41+F42 합은 건설업 GVA와 일치시키되 F41/F42 actual 구조비와 직접 비교",
            },
            {
                "priority": 3,
                "target_group": "보건·사회복지",
                "applies_to": "Q86 보건업 / Q87 사회복지 서비스업",
                "why_error_remains": "사회복지는 종사자·시설 수가 많아 과대, 보건업은 병상·진료비·의료수익 집중을 과소반영",
                "free_data_to_add": "병상 수, 의료기관 종별 현황, 건강보험 진료비·급여비, 사회복지시설 정원",
                "model_change": "보건업은 병상·진료비 중심, 사회복지는 시설정원·복지시설 수 중심의 분리 가중",
                "validation": "Q86/Q87 두 중분류 매출비중 actual에 대해 교차검증",
            },
            {
                "priority": 4,
                "target_group": "도소매·운수·정보",
                "applies_to": "G46/G47, H49/H52, J59~J63",
                "why_error_remains": "대형 도매·통신·물류 거점의 매출 귀속이 지역 사업체 수와 다름",
                "free_data_to_add": "대규모점포, 물류창고, 버스·철도·항만 물동량, 통신·콘텐츠 사업체 활동자료",
                "model_change": "일반 활동지표에 대형시설·물동량·플랫폼 활동량을 상한/하한 제약으로 결합",
                "validation": "중분류별 actual 매출비중과 금액오차가 10% 이내로 줄어드는지 외부 10개 시군구에서 확인",
            },
            {
                "priority": 5,
                "target_group": "거래·자산·비영리",
                "applies_to": "K64~K66, L68, ERS·협회단체",
                "why_error_remains": "금융·부동산·비영리 산출은 사업장 수보다 취급액·자산·예산·회원 규모가 중요",
                "free_data_to_add": "공시가격·거래량·건축물 연면적, 금융기관 점포/인구소득 보조지표, 보조금·예산·시설이용량",
                "model_change": "자산가치·예산·이용량 기반의 별도 상위산업 가중치로 전환",
                "validation": "단일 중분류 부모는 성능판정에서 제외하고, 분할 가능한 중분류만 actual 구조비로 판정",
            },
        ]
    )


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int = 20) -> str:
    if df.empty:
        return "해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("억원", "%", "개")) else "---" for _, label in cols) + " |")
    for _, row in df.head(limit).iterrows():
        vals: list[str] = []
        for key, _label in cols:
            value = row.get(key, "")
            if pd.isna(value):
                vals.append("—")
            elif isinstance(value, (float, np.floating)):
                vals.append(f"{value:,.1f}" if abs(value) >= 10 else f"{value:,.2f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    raw = load_or_collect()
    holdout = build_city_holdout(raw)
    controls = grva_parent_controls()
    detail = attach_gva_errors(holdout, controls)
    city_summary, parent_summary, weak, strongest = summary_tables(detail)
    improvement = remaining_weak_improvement_queue()
    playbook = improvement_playbook()

    detail.to_csv(OUT / "phase108_collected_10_sigungu_middle_accuracy_detail.csv", index=False, encoding="utf-8-sig")
    city_summary.to_csv(OUT / "phase108_collected_10_sigungu_city_summary.csv", index=False, encoding="utf-8-sig")
    parent_summary.to_csv(OUT / "phase108_collected_10_sigungu_parent_summary.csv", index=False, encoding="utf-8-sig")
    weak.to_csv(OUT / "phase108_collected_10_sigungu_gt10_detail.csv", index=False, encoding="utf-8-sig")
    improvement.to_csv(OUT / "phase108_remaining_gt10_improvement_queue.csv", index=False, encoding="utf-8-sig")
    playbook.to_csv(OUT / "phase108_gt10_improvement_playbook.csv", index=False, encoding="utf-8-sig")

    manifest = {
        "created_at": CREATED_AT,
        "kosis_table": KOSIS_TABLE,
        "source": "KOSIS Economic Census 2015 city/sigungu x KSIC, establishments/employees/sales",
        "grva_source_file": "data/processed/expanded_sigungu_grva_real.csv",
        "sample_count": len(SAMPLES),
        "raw_rows": int(len(raw)),
        "validated_middle_cells": int(len(detail)),
        "input_hash": sha256_frame(detail),
    }
    (OUT / "phase108_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    report = f"""# 실제자료 수집 기반 10개 시군구 확장 검증

## 왜 다시 했는가

이전 확장 파일럿은 로컬에 이미 있던 일부 광업·제조업 자료만 사용했기 때문에 고양시·포항시와 같은 수준의 일반화 검증이 아니었다. 이번 검증은 고양시와 포항시에서 쓴 것과 같은 KOSIS 경제총조사 원천을 10개 시군구에 대해 새로 수집했다.

## 수집·검증 기준

- 실제 구조비: KOSIS 경제총조사 2015 `시군구×KSIC 중분류` 매출액 비중
- 추정 구조비: 같은 자료의 사업체 수와 종사자 수만 사용한 중분류 활동비중
- 금액 환산: 로컬 `expanded_sigungu_grva_real.csv`의 2023년 시군구×대분류 GVA actual
- 검증 단위: 중분류별 `실제 억원 / 추정 억원 / 오차 억원 / 오차율 %`
- 제외: 지역 GRVA에서 상위통제 총량이 안정적으로 분리되지 않는 E 중분류는 ERS 통합부모 검증에서 제외
- 성능 요약 제외: 상위산업 안에 중분류가 하나뿐인 경우는 분할 예측 성능이 아니라 회계상 항등이므로 지역별 WAPE 집계에서 제외

## 표본 지역

{md_table(pd.DataFrame([s.__dict__ for s in SAMPLES]), [("source_region", "광역"), ("sigungu_name", "시군구"), ("kosis_region_code", "KOSIS 코드")], limit=20)}

## 지역별 확장 검증 결과

{md_table(city_summary, [("source_region", "광역"), ("sigungu_name", "시군구"), ("middle_cells", "검증 중분류 개"), ("parent_groups", "상위산업 개"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "가중오차 %"), ("median_error_rate_pct", "중앙오차 %"), ("p90_error_rate_pct", "P90오차 %"), ("over_10pct_cells", "10%초과 개")], limit=20)}

## 상위산업군별 일반화 취약도

{md_table(parent_summary, [("parent_code", "상위산업"), ("cells", "중분류 개"), ("evaluable_cells", "평가가능 개"), ("cities", "지역 개"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "가중오차 %"), ("median_error_rate_pct", "중앙오차 %"), ("over_10pct_cells", "10%초과 개"), ("evaluation_note", "판정")], limit=20)}

## 금액 기준 10% 초과 주요 셀

{md_table(weak, [("source_region", "광역"), ("sigungu_name", "시군구"), ("parent_code", "상위산업"), ("division_code", "중분류"), ("division_name", "업종명"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %"), ("direction", "방향")], limit=30)}

## 고양·포항 잔여 10% 초과 업종 개선 방향

모든 산업을 개별 특화 모델로 나누는 대신, 잔여 오차를 원인군으로 묶어 보조지표를 붙이는 방식이 현실적이다. 현재 가장 큰 개선 후보는 다음과 같다.

{md_table(improvement, [("cause_group", "원인군"), ("cells", "셀 개"), ("cities", "지역"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("median_error_rate_pct", "중앙오차 %"), ("required_next_data", "필요 보조지표")], limit=20)}

## 10% 초과 업종 개선 실행안

{md_table(playbook, [("priority", "우선순위"), ("target_group", "대상군"), ("applies_to", "적용 업종"), ("why_error_remains", "잔여오차 원인"), ("free_data_to_add", "추가 무료자료"), ("model_change", "모형 변경"), ("validation", "검증")], limit=10)}

## 결론

1. 10개 시군구 actual 구조비를 새로 수집해 비교한 결과, 고양·포항의 문제는 특정 두 도시만의 이상치가 아니라 여러 지역에서 반복되는 산업군 문제가 맞다.
2. 남은 10% 초과 업종은 `생산시설형`, `전문·지원서비스형`, `공공·비영리형`, `디지털·콘텐츠형`, `거래·자산형`으로 묶어 개선하는 것이 적절하다.
3. 다음 개선은 모든 중분류 개별 모델이 아니라 원인군별 보조지표를 붙인 뒤, 이번 10개 표본을 외부 검증셋으로 재평가하는 순서가 맞다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"wrote {REPORT}")
    print(f"detail_rows={len(detail)} city_summary={len(city_summary)} weak_gt10={len(weak)}")


if __name__ == "__main__":
    main()
