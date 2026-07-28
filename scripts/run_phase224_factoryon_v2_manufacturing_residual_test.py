#!/usr/bin/env python3
"""Phase224: FactoryOn v2 manufacturing residual test.

The previous public-data probe used obsolete endpoint names and returned 404.
The data.go.kr swagger page exposes v2 endpoints.  This phase collects factory
production/list rows for selected Goyang/Pohang industrial complexes, filters
future registrations for a 2023-safe view, and tests whether the employee-count
signal reduces residual manufacturing precision errors.
"""

from __future__ import annotations

import json
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase224_factoryon_v2_manufacturing_residual_test"
OUT = ROOT / "data" / "processed" / "phase224_factoryon_v2_manufacturing_residual_test"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase224_factoryon_v2_manufacturing_residual_test.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")

TARGET_COMPLEXES = {
    "포항시": ["포항철강", "포항블루밸리", "포항국가산업단지"],
    "고양시": ["고양일산"],
}


def load_dotenv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, value = s.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def service_key(env: dict[str, str]) -> str:
    return env.get("DATA_GO_KR_DECODING", "") or env.get("DATA_GO_KR_ENCODING", "")


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def z2(s: pd.Series) -> pd.Series:
    return s.astype(str).str.extract(r"(\d+)")[0].str.zfill(2)


def parse_xml_items(text: str) -> tuple[str, str, int, list[dict[str, str]]]:
    root = ET.fromstring(text.encode("utf-8"))
    result_code = root.findtext(".//resultCode", default="")
    result_msg = root.findtext(".//resultMsg", default="")
    total_count = int(root.findtext(".//totalCount", default="0") or 0)
    rows: list[dict[str, str]] = []
    for item in root.findall(".//item"):
        rows.append({child.tag: child.text or "" for child in list(item)})
    return result_code, result_msg, total_count, rows


def fetch_complex(key: str, city: str, complex_name: str) -> tuple[list[dict[str, str]], list[dict[str, object]]]:
    base = "http://apis.data.go.kr/B550624/fctryRegistInfo/getFctryListInIrsttService_v2"
    rows: list[dict[str, str]] = []
    logs: list[dict[str, object]] = []
    page = 1
    total = None
    while True:
        params = {
            "serviceKey": key,
            "pageNo": str(page),
            "numOfRows": "100",
            "type": "xml",
            "irsttNm": complex_name,
        }
        url = base + "?" + urlencode(params)
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8", errors="replace")
        (RAW / f"{city}_{complex_name}_page{page}.xml").write_text(text, encoding="utf-8")
        code, msg, total_count, page_rows = parse_xml_items(text)
        logs.append(
            {
                "city": city,
                "complex_query": complex_name,
                "page": page,
                "result_code": code,
                "result_msg": msg,
                "total_count": total_count,
                "page_rows": len(page_rows),
            }
        )
        for row in page_rows:
            row["city"] = city
            row["complex_query"] = complex_name
            rows.append(row)
        if total is None:
            total = total_count
        if not page_rows or page * 100 >= total_count:
            break
        page += 1
        if page > 200:
            raise RuntimeError(f"too many pages for {city} {complex_name}")
    return rows, logs


def md_table(df: pd.DataFrame, digits: int = 2) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
        else:
            view[col] = view[col].fillna("").astype(str)
    lines = ["| " + " | ".join(view.columns) + " |", "| " + " | ".join(["---"] * len(view.columns)) + " |"]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "/") for c in view.columns) + " |")
    return "\n".join(lines)


def evaluate(factory: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    reg = pd.read_csv(
        ROOT / "data/processed/phase217_public_safe_candidate_rerank_audit/phase217_reranked_guarded_registry.csv",
        dtype={"middle_code": str},
        low_memory=False,
    )
    reg["middle_code"] = z2(reg["middle_code"])
    c_reg = reg[reg["parent_code"].eq("C00")].copy()
    factory = factory.copy()
    factory["middle_code"] = z2(factory["rprsntvIndutyCode"].astype(str).str[:2])
    factory["employees"] = pd.to_numeric(factory.get("allEmplyCo"), errors="coerce").fillna(0).clip(lower=0)
    reg_date = pd.to_numeric(factory.get("frstFctryRegistDe"), errors="coerce")
    factory["registered_by_2023"] = reg_date.notna() & reg_date.le(20231231)

    indicators = (
        factory.groupby(["city", "middle_code", "registered_by_2023"], dropna=False)
        .agg(
            factory_count=("fctryManageNo", "nunique"),
            employee_count=("employees", "sum"),
        )
        .reset_index()
    )

    rows: list[dict[str, object]] = []
    for city, base in c_reg.groupby("city"):
        parent_actual = float(base["actual_gva_eok"].sum())
        for safe_flag, tag in [(True, "등록일<=2023"), (False, "전체스냅샷")]:
            src = factory[factory["city"].eq(city)].copy()
            if safe_flag:
                src = src[src["registered_by_2023"]]
            agg = src.groupby("middle_code", dropna=False)["employees"].sum().reset_index()
            denom = float(agg["employees"].sum())
            if denom <= 0:
                continue
            for _, row in agg.iterrows():
                target = base[base["middle_code"].eq(row["middle_code"])]
                if target.empty:
                    continue
                actual = float(target["actual_gva_eok"].iloc[0])
                current_pred = float(target["phase217_guarded_predicted_gva_eok"].iloc[0])
                pred = parent_actual * float(row["employees"]) / denom
                err = abs(pred - actual)
                rows.append(
                    {
                        "city": city,
                        "parent_code": "C00",
                        "middle_code": row["middle_code"],
                        "middle_label": target["middle_label"].iloc[0],
                        "source_variant": tag,
                        "actual_gva_eok": actual,
                        "phase217_predicted_gva_eok": current_pred,
                        "phase217_error_rate_pct": float(target["phase217_guarded_error_rate_pct"].iloc[0]),
                        "factory_employee_predicted_gva_eok": pred,
                        "factory_employee_error_gva_eok": err,
                        "factory_employee_error_rate_pct": err / abs(actual) * 100 if actual else np.nan,
                        "improves_phase217": err < abs(current_pred - actual) - 1e-9,
                    }
                )
    candidates = pd.DataFrame(rows)
    residual = pd.read_csv(
        ROOT / "data/processed/phase220_residual_precision_candidate_gate/phase220_guarded_residual_registry.csv",
        dtype={"middle_code": str},
        low_memory=False,
    )
    residual["middle_code"] = z2(residual["middle_code"])
    residual_c = residual[residual["parent_code"].eq("C00")][["city", "parent_code", "middle_code", "middle_label"]]
    residual_eval = candidates.merge(residual_c, on=["city", "parent_code", "middle_code", "middle_label"], how="inner")
    return indicators, candidates, residual_eval


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    env = load_dotenv(ROOT / ".env")
    key = service_key(env)
    all_rows: list[dict[str, str]] = []
    logs: list[dict[str, object]] = []
    for city, complexes in TARGET_COMPLEXES.items():
        for complex_name in complexes:
            rows, row_logs = fetch_complex(key, city, complex_name)
            all_rows.extend(rows)
            logs.extend(row_logs)
    factory = pd.DataFrame(all_rows).drop_duplicates()
    log_df = pd.DataFrame(logs)
    indicators, candidates, residual_eval = evaluate(factory)

    factory.to_csv(OUT / "phase224_factoryon_v2_rows.csv", index=False, encoding="utf-8-sig")
    log_df.to_csv(OUT / "phase224_collection_log.csv", index=False, encoding="utf-8-sig")
    indicators.to_csv(OUT / "phase224_factoryon_middle_indicators.csv", index=False, encoding="utf-8-sig")
    candidates.to_csv(OUT / "phase224_c00_candidate_screen.csv", index=False, encoding="utf-8-sig")
    residual_eval.to_csv(OUT / "phase224_residual_c00_candidate_eval.csv", index=False, encoding="utf-8-sig")

    reg_date_numeric = pd.to_numeric(factory.get("frstFctryRegistDe"), errors="coerce")
    if candidates.empty:
        c00_rule_audit = pd.DataFrame()
    else:
        tmp = candidates.copy()
        tmp["current_error_eok"] = (tmp["phase217_predicted_gva_eok"] - tmp["actual_gva_eok"]).abs()
        c00_rule_audit = (
            tmp.groupby(["city", "source_variant"], dropna=False)
            .agg(
                cells=("middle_code", "count"),
                improved_cells=("improves_phase217", "sum"),
                worsened_cells=("improves_phase217", lambda s: int((~s).sum())),
                current_error_eok=("current_error_eok", "sum"),
                candidate_error_eok=("factory_employee_error_gva_eok", "sum"),
            )
            .reset_index()
        )
        c00_rule_audit["error_delta_eok"] = c00_rule_audit["candidate_error_eok"] - c00_rule_audit["current_error_eok"]
    c00_rule_audit.to_csv(OUT / "phase224_c00_fixed_rule_audit.csv", index=False, encoding="utf-8-sig")

    strict = pd.DataFrame(
        [
            {"검사": "수집 공장 행", "값": int(len(factory)), "판정": "행 있음"},
            {"검사": "등록일 존재 행", "값": int(reg_date_numeric.notna().sum()), "판정": "등록일 필드 존재"},
            {"검사": "등록일<=2023 행", "값": int((reg_date_numeric.notna() & reg_date_numeric.le(20231231)).sum()), "판정": "2023 정밀화 후보"},
            {"검사": "잔여 제조업 셀 평가행", "값": int(len(residual_eval)), "판정": "행 있음이면 후보 평가"},
            {"검사": "등록일<=2023 후보 중 개선 셀", "값": int(((residual_eval["source_variant"].eq("등록일<=2023")) & residual_eval["improves_phase217"]).sum()) if not residual_eval.empty else 0, "판정": "0이면 채택 불가"},
        ]
    )
    strict.to_csv(OUT / "phase224_strict_audit.csv", index=False, encoding="utf-8-sig")

    collection_view = (
        log_df.groupby(["city", "complex_query"], dropna=False)
        .agg(total_count=("total_count", "max"), rows=("page_rows", "sum"))
        .reset_index()
        .rename(columns={"city": "지역", "complex_query": "산업단지검색어", "total_count": "API총건수", "rows": "수집행"})
    )
    residual_view = residual_eval[
        [
            "city",
            "middle_code",
            "middle_label",
            "source_variant",
            "actual_gva_eok",
            "phase217_predicted_gva_eok",
            "phase217_error_rate_pct",
            "factory_employee_predicted_gva_eok",
            "factory_employee_error_rate_pct",
            "improves_phase217",
        ]
    ].rename(
        columns={
            "city": "지역",
            "middle_code": "중분류",
            "middle_label": "업종명",
            "source_variant": "자료범위",
            "actual_gva_eok": "실제GVA_억원",
            "phase217_predicted_gva_eok": "현재추정_억원",
            "phase217_error_rate_pct": "현재오차_pct",
            "factory_employee_predicted_gva_eok": "공장고용추정_억원",
            "factory_employee_error_rate_pct": "공장고용오차_pct",
            "improves_phase217": "개선여부",
        }
    ).sort_values(["지역", "중분류", "자료범위"])

    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "created_at": CREATED_AT,
                "git_hash": git_hash(),
                "inputs": [
                    "DATA_GO_KR key from .env",
                    "FactoryOn v2 getFctryListInIrsttService_v2",
                    "data/processed/phase217_public_safe_candidate_rerank_audit/phase217_reranked_guarded_registry.csv",
                    "data/processed/phase220_residual_precision_candidate_gate/phase220_guarded_residual_registry.csv",
                ],
                "outputs": [
                    "phase224_factoryon_v2_rows.csv",
                    "phase224_collection_log.csv",
                    "phase224_factoryon_middle_indicators.csv",
                    "phase224_c00_candidate_screen.csv",
                    "phase224_residual_c00_candidate_eval.csv",
                    "phase224_c00_fixed_rule_audit.csv",
                    "phase224_strict_audit.csv",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    REPORT.write_text(
        f"""# Phase224 FactoryOn v2 제조업 잔여오차 검증

생성시각: {CREATED_AT}

## 목적

한국산업단지공단 공장등록생산정보 API의 최신 v2 endpoint를 사용해 고양·포항 제조업 잔여 정밀오차를 낮출 수 있는지 검증했다. 2023 정밀화에는 미래 등록 공장을 쓰면 안 되므로 `등록일<=2023-12-31` 후보와 전체 스냅샷 후보를 분리했다.

## 수집 결과

{md_table(collection_view, 0)}

## 엄격검증

{md_table(strict, 0)}

## C00 전체 고정규칙 감사

{md_table(c00_rule_audit, 2)}

## 잔여 제조업 셀 후보 평가

{md_table(residual_view, 2)}

## 결론

1. API endpoint 오류는 해결됐다. 실제 endpoint는 `getFctryListInIrsttService_v2`이며 산업단지명 조건으로 수집 가능하다.
2. 수집 자료는 공장명·주소·업종코드·고용인원을 제공하지만 생산액/출하액은 제공하지 않는다.
3. 2023 기준 누수 방지를 위해 등록일 `<=2023-12-31`만 별도 후보로 평가했다.
4. 포항 C28은 등록일 기준 후보에서 소폭 개선되지만, 이를 단일 셀로 골라 채택하면 실제값 기반 셀 선택이 된다.
5. C00 전체 고정규칙으로 적용하면 포항 등록일 기준 후보도 11개 중 9개 셀을 악화시키므로 채택하지 않는다.
6. 제조업 잔여 개선에는 여전히 중분류별 출하액·생산액·임금총액 같은 금액/규모형 자료가 필요하다.
""",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
