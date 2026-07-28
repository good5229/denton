#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import ssl
import subprocess
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase199_kicox_high_error_factory_enrichment"
OUT = ROOT / "data" / "processed" / "phase199_kicox_high_error_factory_enrichment"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase199_kicox_high_error_factory_enrichment.md"
RUN_ID = "partial_statistics_estimation_phase199_kicox_high_error_factory_enrichment"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")

ENDPOINT = "http://apis.data.go.kr/B550624/fctryRegistInfo/getFctryPrdctnService_v2"
PRIORITY = {
    "고양시": ["C29", "C23", "C13", "C21", "C14"],
    "포항시": ["C28", "C24", "C25", "C23", "C34", "C20", "C29", "C27"],
}


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def service_key(env: dict[str, str]) -> str:
    for k in ("DATA_GO_KR_DECODING", "DATA_GO_KR_ENCODING"):
        if env.get(k):
            return env[k]
    raise SystemExit("DATA_GO_KR_DECODING or DATA_GO_KR_ENCODING is required in .env")


def redact(text: str, env: dict[str, str]) -> str:
    out = text
    for k, v in env.items():
        if any(t in k.upper() for t in ["KEY", "TOKEN"]) and v:
            out = out.replace(v, "[REDACTED_SERVICE_KEY]")
    return out


def safe_name(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣_.-]+", "_", s).strip("_")[:120]


def request_company(company: str, key: str, env: dict[str, str]) -> tuple[list[dict], dict]:
    RAW.mkdir(parents=True, exist_ok=True)
    params = {"serviceKey": key, "pageNo": "1", "numOfRows": "100", "type": "xml", "cmpnyNm": company}
    url = ENDPOINT + "?" + urlencode(params)
    cache = RAW / f"{safe_name(company)}.xml"
    meta = {"company": company, "status": "", "result_code": "", "result_msg": "", "total_count": 0, "item_count": 0}
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=30, context=ssl._create_unverified_context()) as resp:
            text = resp.read().decode("utf-8", errors="replace")
        cache.write_text(redact(text, env), encoding="utf-8")
        root = ET.fromstring(text.encode("utf-8"))
        def t(path: str) -> str:
            n = root.find(path)
            return n.text.strip() if n is not None and n.text else ""
        meta.update(
            {
                "status": "ok",
                "result_code": t(".//resultCode"),
                "result_msg": t(".//resultMsg"),
                "total_count": int(t(".//totalCount") or 0),
            }
        )
        rows = []
        for item in root.findall(".//item"):
            rows.append({child.tag: (child.text or "").strip() for child in item})
        meta["item_count"] = len(rows)
        return rows, meta
    except HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")
        meta.update({"status": "http_error", "result_msg": msg[:200]})
    except (URLError, TimeoutError, Exception) as e:
        meta.update({"status": "error", "result_msg": str(e)[:200]})
    return [], meta


def stamp(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    payload = out.head(100_000).to_json(orient="records", force_ascii=False, double_precision=12)
    out["input_hash"] = hashlib.sha256(payload.encode()).hexdigest()
    out["code_commit_hash"] = git_hash()
    out["run_id"] = RUN_ID
    out["created_at"] = CREATED_AT
    return out


def write_csv(name: str, df: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stamp(df).to_csv(OUT / name, index=False, encoding="utf-8-sig")


def md_table(df: pd.DataFrame, digits: int = 2, limit: int | None = None) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.head(limit).copy() if limit else df.copy()
    for c in view.columns:
        if pd.api.types.is_float_dtype(view[c]):
            view[c] = view[c].map(lambda x: "" if pd.isna(x) else f"{x:,.{digits}f}")
        else:
            view[c] = view[c].map(lambda x: "" if pd.isna(x) else str(x).replace("\n", "<br>").replace("|", "/"))
    lines = ["| " + " | ".join(view.columns) + " |", "| " + " | ".join(["---"] * len(view.columns)) + " |"]
    for row in view.itertuples(index=False):
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    if limit and len(df) > limit:
        lines.append(f"\n_상위 {limit:,}개 표시, 전체 {len(df):,}개는 CSV 참조_")
    return "\n".join(lines)


def top_candidates() -> pd.DataFrame:
    p = ROOT / "data" / "raw" / "public_data_portal" / "factory_full_snapshot_15106170_download.csv"
    df = pd.read_csv(p, encoding="cp949", dtype=str)
    for c in ["종업원합계", "제조시설면적", "건축면적", "용지면적"]:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", "", regex=False), errors="coerce").fillna(0.0)
    df["middle_code"] = "C" + df["대표업종"].astype(str).str.extract(r"(\d{2})", expand=False).fillna("")
    rows = []
    for city, codes in PRIORITY.items():
        x = df[df["시군구명"].astype(str).str.startswith(city) & df["middle_code"].isin(codes)].copy()
        for code, g in x.groupby("middle_code"):
            top = g.sort_values(["종업원합계", "제조시설면적"], ascending=False).head(15)
            for _, r in top.iterrows():
                rows.append(
                    {
                        "target_city": city,
                        "target_middle_code": code,
                        "company": r["회사명"],
                        "local_factory_manage_no": r["공장관리번호"],
                        "local_employees": r["종업원합계"],
                        "local_mfg_area": r["제조시설면적"],
                        "local_representative_industry": r["대표업종"],
                        "local_industry_name": r["업종명"],
                        "local_product": r["생산품"],
                        "local_address": r["공장주소"],
                    }
                )
    return pd.DataFrame(rows).drop_duplicates(["target_city", "target_middle_code", "company"]).reset_index(drop=True)


def normalize_api_rows(rows: list[dict], request_company_name: str) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    x = pd.DataFrame(rows)
    x["request_company"] = request_company_name
    x["allEmplyCo_num"] = pd.to_numeric(x.get("allEmplyCo", ""), errors="coerce").fillna(0.0)
    x["frstFctryRegistDe_num"] = pd.to_numeric(x.get("frstFctryRegistDe", ""), errors="coerce")
    x["representative_middle_code"] = "C" + x.get("rprsntvIndutyCode", "").astype(str).str.extract(r"(\d{2})", expand=False).fillna("")
    return x


def match_api_to_targets(candidates: pd.DataFrame, api_rows: pd.DataFrame) -> pd.DataFrame:
    if api_rows.empty:
        return pd.DataFrame()
    c = candidates[["target_city", "target_middle_code", "company"]].drop_duplicates()
    merged = api_rows.merge(c, left_on="request_company", right_on="company", how="left")
    merged["address_match"] = merged["rnAdres"].astype(str).str.contains("고양시|포항시", na=False)
    merged["target_city_match"] = merged.apply(lambda r: str(r.get("target_city", "")) in str(r.get("rnAdres", "")), axis=1)
    merged["middle_match"] = merged.apply(
        lambda r: str(r.get("target_middle_code", ""))[1:] in str(r.get("indutyCodes", ""))[:200]
        or str(r.get("representative_middle_code", "")) == str(r.get("target_middle_code", "")),
        axis=1,
    )
    return merged[merged["target_city_match"] & merged["middle_match"]].copy()


def eligibility_summary(matched: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    detail_rows = []
    for year in [2023, 2024]:
        ymd = year * 10000 + 1231
        x = matched.copy()
        x["target_year"] = year
        x["registration_status"] = np.where(
            x["frstFctryRegistDe_num"].isna(),
            "unknown_registration_date",
            np.where(x["frstFctryRegistDe_num"] <= ymd, "eligible_by_registration_date", "future_registered_excluded"),
        )
        detail_rows.append(x)
    detail = pd.concat(detail_rows, ignore_index=True) if detail_rows else pd.DataFrame()
    if detail.empty:
        return detail, pd.DataFrame()
    summary = (
        detail.groupby(["target_city", "target_middle_code", "target_year", "registration_status"], as_index=False)
        .agg(
            matched_factories=("fctryManageNo", "nunique"),
            employees=("allEmplyCo_num", "sum"),
            companies=("cmpnyNm", "nunique"),
        )
        .sort_values(["target_city", "target_middle_code", "target_year", "registration_status"])
    )
    return detail, summary


def main() -> int:
    env = load_env()
    key = service_key(env)
    candidates = top_candidates()
    company_names = sorted(candidates["company"].dropna().astype(str).unique())
    api_frames = []
    metas = []
    for i, company in enumerate(company_names, 1):
        rows, meta = request_company(company, key, env)
        metas.append(meta)
        if rows:
            api_frames.append(normalize_api_rows(rows, company))
        # Keep polite and small; current run is limited to 168 company-name calls.
        if i % 25 == 0:
            time.sleep(0.2)
    api_rows = pd.concat(api_frames, ignore_index=True) if api_frames else pd.DataFrame()
    meta_df = pd.DataFrame(metas)
    matched = match_api_to_targets(candidates, api_rows)
    eligible_detail, eligible_summary = eligibility_summary(matched)

    write_csv("phase199_collection_targets.csv", candidates)
    write_csv("phase199_api_request_summary.csv", meta_df)
    write_csv("phase199_api_rows_normalized.csv", api_rows)
    write_csv("phase199_matched_target_factories.csv", matched)
    write_csv("phase199_registration_eligibility_detail.csv", eligible_detail)
    write_csv("phase199_registration_eligibility_summary.csv", eligible_summary)

    request_summary = pd.DataFrame(
        [
            {
                "requested_companies": len(company_names),
                "ok_requests": int(meta_df["status"].eq("ok").sum()) if not meta_df.empty else 0,
                "api_rows": len(api_rows),
                "matched_target_factories": matched["fctryManageNo"].nunique() if not matched.empty else 0,
                "matched_target_companies": matched["cmpnyNm"].nunique() if not matched.empty else 0,
            }
        ]
    )
    write_csv("phase199_summary.csv", request_summary)

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        f"""# Phase199 KICOX 고오차 제조업 공장 생산정보 제한 수집

## 목적

고양시·포항시 제조업 중분류 고오차 업종에 대해 KICOX 공장등록 생산정보 API가 실제 개선 후보가 될 수 있는지 제한 수집했다. 전수 수집이 아니라, 각 고오차 중분류별 종업원·제조시설면적 상위 공장 최대 15개 회사명을 대상으로 조회했다.

## 수집 요약

{md_table(request_summary.rename(columns={
    "requested_companies": "요청 회사수",
    "ok_requests": "정상 요청수",
    "api_rows": "API 응답 행수",
    "matched_target_factories": "대상도시·중분류 매칭 공장수",
    "matched_target_companies": "대상도시·중분류 매칭 회사수",
}), 0)}

## 등록일 기반 시간 적격성 요약

KICOX 생산정보의 `frstFctryRegistDe`를 사용해 2023년·2024년 시점에 이미 등록된 공장인지 확인했다. 이 단계는 현재 스냅샷의 미래등록 공장 혼입을 줄이기 위한 감사다.

{md_table(eligible_summary.rename(columns={
    "target_city": "지역",
    "target_middle_code": "중분류",
    "target_year": "대상연도",
    "registration_status": "등록일 판정",
    "matched_factories": "공장수",
    "employees": "종업원수",
    "companies": "회사수",
}), 1, limit=80)}

## 판정

1. KICOX 생산정보 API는 고오차 제조업 중분류의 생산품·업종코드·종업원·최초등록일을 보강하는 데 사용할 수 있다.
2. 다만 회사명 검색형 API라 전수 자동화는 로컬 전국 공장 스냅샷의 회사명 목록을 기반으로 제한적으로 수행해야 한다.
3. 이번 제한 수집은 고오차 업종 상위 공장 중심이므로 전체 중분류 GVA 예측값을 바로 대체하지 않는다.
4. 다음 단계는 `등록일 적격 공장 활동자료`와 기존 공장 스냅샷 지표를 함께 써서 C13/C21/C23/C29, C23/C24/C25/C28/C34 등의 중분류별 후보식을 외부연도 검증하는 것이다.
5. 필지정보 API는 Phase193에서 403이므로, 면적 보강은 현재 로컬 스냅샷 면적을 사용하거나 별도 활용신청 확인이 필요하다.
""",
        encoding="utf-8",
    )
    print(json.dumps({"requested_companies": len(company_names), "api_rows": len(api_rows), "matched": len(matched), "report": str(REPORT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
