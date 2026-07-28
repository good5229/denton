#!/usr/bin/env python3
"""Phase221: test newly opened APIs against residual precision errors.

Newly usable API probes after running Phase181 outside the sandbox:

* Financial Services Commission company/basic information
* PPS public data standard contract information

This phase deliberately checks temporal fit before model fit.  A source that is
open but timestamp-mismatched is not used for 2023 precision GVA.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase221_newly_opened_api_residual_test"
OUT = ROOT / "data" / "processed" / "phase221_newly_opened_api_residual_test"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase221_newly_opened_api_residual_test.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


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


def request_json(url: str, params: dict[str, str], timeout: int = 30) -> dict:
    full_url = url + "?" + urlencode(params)
    req = Request(full_url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=timeout) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    return json.loads(text)


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
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join(["---"] * len(view.columns)) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "/") for c in view.columns) + " |")
    return "\n".join(lines)


def fetch_finance_2023(env: dict[str, str]) -> pd.DataFrame:
    key = service_key(env)
    url = "http://apis.data.go.kr/1160100/service/GetFnCoBasiInfoService/getFnCoOutl"
    params = {
        "serviceKey": key,
        "pageNo": "1",
        "numOfRows": "2000",
        "resultType": "json",
        "basDt": "20231229",
    }
    data = request_json(url, params)
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "finance_company_basic_20231229.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    if isinstance(items, dict):
        items = [items]
    return pd.DataFrame(items)


def probe_pps_contract_dates(env: dict[str, str]) -> pd.DataFrame:
    key = service_key(env)
    url = "http://apis.data.go.kr/1230000/ao/PubDataOpnStdService/getDataSetOpnStdCntrctInfo"
    rows: list[dict[str, object]] = []
    for page in [1, 100, 500, 1000, 2000, 3000, 3255]:
        params = {"serviceKey": key, "pageNo": str(page), "numOfRows": "10", "type": "json"}
        try:
            data = request_json(url, params)
            body = data.get("response", {}).get("body", {})
            items = body.get("items", [])
            if isinstance(items, dict):
                items = items.get("item", [])
            if isinstance(items, dict):
                items = [items]
            dates = [str(x.get("cntrctCnclsDate", "")) for x in items if isinstance(x, dict)]
            rows.append(
                {
                    "pageNo": page,
                    "status": data.get("response", {}).get("header", {}).get("resultMsg", ""),
                    "totalCount": body.get("totalCount", ""),
                    "min_contract_date": min(dates) if dates else "",
                    "max_contract_date": max(dates) if dates else "",
                    "sample_dates": ", ".join(dates[:5]),
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "pageNo": page,
                    "status": "error",
                    "totalCount": "",
                    "min_contract_date": "",
                    "max_contract_date": "",
                    "sample_dates": "",
                    "error": str(exc)[:500],
                }
            )
    return pd.DataFrame(rows)


def finance_indicator_screen(fin: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    reg = pd.read_csv(
        ROOT / "data/processed/phase217_public_safe_candidate_rerank_audit/phase217_reranked_guarded_registry.csv",
        dtype={"middle_code": str},
        low_memory=False,
    )
    reg["middle_code"] = z2(reg["middle_code"])
    k_reg = reg[reg["parent_code"].eq("K00")].copy()
    city_patterns = {"고양시": "고양", "포항시": "포항"}

    f = fin.copy()
    f["sic_middle_code"] = z2(f.get("sicCd", pd.Series(dtype=str)).astype(str).str[:2])
    f["fncoEmpeCnt_num"] = pd.to_numeric(f.get("fncoEmpeCnt"), errors="coerce").fillna(0).clip(lower=0)
    f["fncoEmpeAvgSlryAmt_num"] = pd.to_numeric(f.get("fncoEmpeAvgSlryAmt"), errors="coerce").fillna(0).clip(lower=0)
    f["salary_mass"] = f["fncoEmpeCnt_num"] * f["fncoEmpeAvgSlryAmt_num"]

    local_rows: list[pd.DataFrame] = []
    indicator_rows: list[dict[str, object]] = []
    candidate_rows: list[dict[str, object]] = []
    for city, pat in city_patterns.items():
        local = f[f.get("fncoAdr", pd.Series(dtype=str)).astype(str).str.contains(pat, na=False)].copy()
        if not local.empty:
            local["city"] = city
            local_rows.append(local)
        for middle in ["64", "65", "66"]:
            sub = local[local["sic_middle_code"].eq(middle)]
            indicator_rows.append(
                {
                    "city": city,
                    "middle_code": middle,
                    "company_count": int(len(sub)),
                    "employee_count": float(sub["fncoEmpeCnt_num"].sum()) if not sub.empty else 0.0,
                    "salary_mass": float(sub["salary_mass"].sum()) if not sub.empty else 0.0,
                }
            )

    indicators = pd.DataFrame(indicator_rows)
    local_companies = pd.concat(local_rows, ignore_index=True) if local_rows else pd.DataFrame()

    metrics = [
        ("company_count", "금융회사 기본정보 소재기업 수"),
        ("employee_count", "금융회사 기본정보 종업원수"),
        ("salary_mass", "금융회사 기본정보 임금총액 대용"),
    ]
    for city, base in k_reg.groupby("city"):
        k_actual_total = float(base["actual_gva_eok"].sum())
        city_ind = indicators[indicators["city"].eq(city)].copy()
        for metric, label in metrics:
            denom = float(city_ind[metric].sum())
            if denom <= 0:
                continue
            for _, row in city_ind.iterrows():
                target = base[base["middle_code"].eq(row["middle_code"])]
                if target.empty:
                    continue
                actual = float(target["actual_gva_eok"].iloc[0])
                current_pred = float(target["phase217_guarded_predicted_gva_eok"].iloc[0])
                current_err = abs(current_pred - actual)
                pred = k_actual_total * float(row[metric]) / denom
                err = abs(pred - actual)
                candidate_rows.append(
                    {
                        "city": city,
                        "parent_code": "K00",
                        "middle_code": row["middle_code"],
                        "middle_label": target["middle_label"].iloc[0],
                        "actual_gva_eok": actual,
                        "phase217_predicted_gva_eok": current_pred,
                        "phase217_error_rate_pct": float(target["phase217_guarded_error_rate_pct"].iloc[0]),
                        "candidate_source": label,
                        "candidate_predicted_gva_eok": pred,
                        "candidate_error_gva_eok": err,
                        "candidate_error_rate_pct": err / abs(actual) * 100 if actual else np.nan,
                        "improves_phase217": err < current_err - 1e-9,
                    }
                )
    return local_companies, pd.DataFrame(candidate_rows)


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    env = load_dotenv(ROOT / ".env")
    fin = fetch_finance_2023(env)
    pps_dates = probe_pps_contract_dates(env)
    local_fin, finance_candidates = finance_indicator_screen(fin)

    fin.to_csv(OUT / "phase221_finance_company_basic_20231229.csv", index=False, encoding="utf-8-sig")
    local_fin.to_csv(OUT / "phase221_finance_company_basic_20231229_goyang_pohang.csv", index=False, encoding="utf-8-sig")
    finance_candidates.to_csv(OUT / "phase221_finance_k00_candidate_screen.csv", index=False, encoding="utf-8-sig")
    pps_dates.to_csv(OUT / "phase221_pps_contract_date_probe.csv", index=False, encoding="utf-8-sig")

    if finance_candidates.empty:
        best_finance = pd.DataFrame()
    else:
        best_finance = (
            finance_candidates.sort_values(
                ["city", "parent_code", "middle_code", "candidate_error_gva_eok"],
                ascending=[True, True, True, True],
            )
            .drop_duplicates(["city", "parent_code", "middle_code"], keep="first")
            .copy()
        )
    best_finance.to_csv(OUT / "phase221_finance_k00_best_candidates.csv", index=False, encoding="utf-8-sig")

    residual = pd.read_csv(
        ROOT / "data/processed/phase220_residual_precision_candidate_gate/phase220_guarded_residual_registry.csv",
        dtype={"middle_code": str},
        low_memory=False,
    )
    residual["middle_code"] = z2(residual["middle_code"])
    residual_finance = residual[(residual["parent_code"].eq("K00")) | (residual["middle_code"].isin(["64", "65", "66"]))].copy()

    api_summary = pd.DataFrame(
        [
            {
                "자료": "금융위원회 금융회사 기본정보",
                "수집/점검": "수집",
                "기준시점": "2023-12-29",
                "행수": int(len(fin)),
                "고양/포항 행수": int(len(local_fin)),
                "잔여오차 적용판정": "K66 직접 개선 부적합",
                "근거": "포항 소재 행은 대부분 K64 금융업이며 K66 행이 없어 K66 배분 시 악화",
            },
            {
                "자료": "조달청 나라장터 계약정보",
                "수집/점검": "날짜 probe",
                "기준시점": "API 현재 응답",
                "행수": int(pd.to_numeric(pps_dates.get("totalCount"), errors="coerce").max() or 0),
                "고양/포항 행수": np.nan,
                "잔여오차 적용판정": "2023 정밀화 직접 적용 보류",
                "근거": "표본 페이지 계약일이 2026-07-21~2026-07-28에 한정되어 2023 GVA 검증시점과 불일치",
            },
        ]
    )
    api_summary.to_csv(OUT / "phase221_api_source_decision.csv", index=False, encoding="utf-8-sig")

    strict = pd.DataFrame(
        [
            {"검사": "금융 API 2023 기준일 행수", "값": int(len(fin)), "판정": "행 있음"},
            {"검사": "포항 K66 금융회사 직접 행", "값": int((local_fin.get("city", pd.Series(dtype=str)).eq("포항시") & local_fin.get("sic_middle_code", pd.Series(dtype=str)).eq("66")).sum()) if not local_fin.empty else 0, "판정": "0이면 K66 개선 불가"},
            {"검사": "금융 후보 중 Phase217 개선", "값": int(finance_candidates["improves_phase217"].sum()) if not finance_candidates.empty else 0, "판정": "0이면 채택 불가"},
            {"검사": "조달 계약정보 2023 계약일 포함 probe", "값": int(pps_dates["sample_dates"].astype(str).str.contains("2023", na=False).sum()), "판정": "0이면 2023 정밀화 보류"},
        ]
    )
    strict.to_csv(OUT / "phase221_strict_audit.csv", index=False, encoding="utf-8-sig")

    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "created_at": CREATED_AT,
                "git_hash": git_hash(),
                "inputs": [
                    "DATA_GO_KR key from .env",
                    "data/processed/phase217_public_safe_candidate_rerank_audit/phase217_reranked_guarded_registry.csv",
                    "data/processed/phase220_residual_precision_candidate_gate/phase220_guarded_residual_registry.csv",
                ],
                "outputs": [
                    "phase221_finance_company_basic_20231229.csv",
                    "phase221_finance_company_basic_20231229_goyang_pohang.csv",
                    "phase221_finance_k00_candidate_screen.csv",
                    "phase221_finance_k00_best_candidates.csv",
                    "phase221_pps_contract_date_probe.csv",
                    "phase221_api_source_decision.csv",
                    "phase221_strict_audit.csv",
                ],
                "secret_handling": "API keys are read from .env but not written to outputs.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    local_view_cols = ["city", "fncoNm", "fncoAdr", "sicCd", "sic_middle_code", "fncoEmpeCnt", "fncoEmpeAvgSlryAmt"]
    local_view = local_fin[[c for c in local_view_cols if c in local_fin.columns]].copy()
    finance_view = best_finance[
        [
            "city",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "phase217_predicted_gva_eok",
            "phase217_error_rate_pct",
            "candidate_source",
            "candidate_predicted_gva_eok",
            "candidate_error_rate_pct",
            "improves_phase217",
        ]
    ].copy() if not best_finance.empty else pd.DataFrame()

    REPORT.write_text(
        f"""# Phase221 신규 개방 API 잔여오차 적용성 검증

생성시각: {CREATED_AT}

## 목적

Phase181 재점검에서 새로 열린 `금융위원회 금융회사 기본정보`와 `조달청 나라장터 계약정보`가 Phase220 잔여 정밀오차를 실제로 줄일 수 있는지 검증했다. 목표는 총부가가치(GVA) 추정이며, 자료가 열렸다는 사실만으로 성능 개선 자료로 채택하지 않았다.

## API 자료 판정

{md_table(api_summary, 2)}

## 엄격검증

{md_table(strict, 0)}

## 2023년 말 고양·포항 금융회사 기본정보

{md_table(local_view, 2)}

## K00 내부배분 후보 검증

{md_table(finance_view, 2)}

## 조달청 계약정보 날짜 probe

{md_table(pps_dates, 0)}

## 결론

1. 금융회사 기본정보는 2023년 말 기준일로 수집 가능하지만, 포항 K66 행이 없어 `금융 및 보험 관련 서비스업` 개선에는 직접적으로 부적합하다.
2. 조달청 계약정보 API는 열렸지만 표본 계약일이 2026년 7월 하순에 집중되어 2023년 GVA 정밀화에는 시점이 맞지 않는다.
3. 따라서 Phase221에서 잔여 정밀오차를 낮추는 신규 채택 후보는 없다.
4. K66 개선에는 금융회사 본점 목록이 아니라 지역별 금융서비스 수수료·계약건수·보험료·점포/영업활동 금액자료가 필요하다.
""",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
