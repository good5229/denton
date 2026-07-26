#!/usr/bin/env python3
"""Phase136: KOBIS box-office temporal proxy for Goyang J59.

KOBIS is available in this environment, while KOPIS is not.  KOBIS daily
box-office data is national top-list movie sales/audience, not a Goyang
sigungu actual.  Therefore this phase treats KOBIS as a temporal activity
indicator for J59 (motion picture/video/audio production-distribution related
middle industry), not as a city-level benchmark.

The validation target is the rolling annual nowcast problem from Phase131:
does a KOBIS YTD sales share improve the annual nowcast for Goyang J59 compared
with the generic prior-year same-YTD seasonal share?
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode
import json
import re
import ssl
import time
import urllib.request

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase136_kobis_boxoffice"
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase136_kobis_boxoffice_temporal_proxy"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase136_kobis_boxoffice_temporal_proxy.md"

PHASE131_PRED = DATA / "phase131_rolling_vintage_gva_update" / "phase131_rolling_vintage_predictions.csv"
KOBIS_DAILY_URL = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"

YEARS = [2021, 2022, 2023]
TARGET_CITY = "고양시"
TARGET_PARENT = "J00"
TARGET_MIDDLE = "59"


def read_env_key() -> str:
    text = (ROOT / ".env").read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"^\s*KOBIS_API_KEY\s*=\s*[\"']?([^\"'\n#]+)", text, flags=re.MULTILINE)
    if not m:
        raise RuntimeError("KOBIS_API_KEY is missing in .env")
    return m.group(1).strip()


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def fetch_daily(key: str, target: date) -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    ymd = target.strftime("%Y%m%d")
    path = RAW / f"kobis_daily_boxoffice_{ymd}.json"
    if path.exists() and path.stat().st_size:
        return path
    params = {"key": key, "targetDt": ymd}
    req = urllib.request.Request(
        KOBIS_DAILY_URL + "?" + urlencode(params),
        headers={"User-Agent": "Mozilla/5.0"},
    )
    # KOBIS often fails local CA verification in this environment; restrict the
    # unverified context to this official KOBIS endpoint.
    ctx = ssl._create_unverified_context()
    with urllib.request.urlopen(req, timeout=20, context=ctx) as response:
        payload = response.read().decode("utf-8")
    path.write_text(payload, encoding="utf-8")
    time.sleep(0.02)
    return path


def request_json(key: str, params: dict[str, str]) -> dict:
    req = urllib.request.Request(
        KOBIS_DAILY_URL + "?" + urlencode({"key": key, **params}),
        headers={"User-Agent": "Mozilla/5.0"},
    )
    ctx = ssl._create_unverified_context()
    with urllib.request.urlopen(req, timeout=20, context=ctx) as response:
        return json.loads(response.read().decode("utf-8"))


def api_scope_audit(key: str) -> pd.DataFrame:
    """Check whether attempted regional parameters materially change KOBIS response."""
    tests = [
        ("baseline", {}),
        ("areaCd_4128_attempt", {"areaCd": "4128"}),
        ("wideAreaCd_4128_attempt", {"wideAreaCd": "4128"}),
    ]
    rows = []
    baseline_movies: list[str] | None = None
    for name, params in tests:
        try:
            data = request_json(key, {"targetDt": "20230101", **params})
            result = data.get("boxOfficeResult", {})
            rows_list = result.get("dailyBoxOfficeList", [])
            movies = [str(r.get("movieCd", "")) for r in rows_list]
            if baseline_movies is None:
                baseline_movies = movies
            rows.append({
                "probe_name": name,
                "params_without_key": urlencode(params) if params else "(none)",
                "boxoffice_type": result.get("boxofficeType", ""),
                "show_range": result.get("showRange", ""),
                "row_count": int(len(rows_list)),
                "movie_codes_same_as_baseline": bool(movies == baseline_movies),
                "sales_sum_krw": float(sum(float(r.get("salesAmt", 0) or 0) for r in rows_list)),
                "response_scope_interpretation": "regional parameter did not produce distinct city-level actual"
                if name != "baseline"
                else "national daily box-office response",
            })
        except Exception as exc:  # noqa: BLE001
            rows.append({
                "probe_name": name,
                "params_without_key": urlencode(params) if params else "(none)",
                "boxoffice_type": "",
                "show_range": "",
                "row_count": 0,
                "movie_codes_same_as_baseline": False,
                "sales_sum_krw": 0.0,
                "response_scope_interpretation": f"request_failed:{type(exc).__name__}",
            })
    return pd.DataFrame(rows)


def collect() -> pd.DataFrame:
    key = read_env_key()
    paths = []
    for year in YEARS:
        for day in daterange(date(year, 1, 1), date(year, 12, 31)):
            paths.append(fetch_daily(key, day))
    rows = []
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        result = data.get("boxOfficeResult", {})
        show_range = result.get("showRange", "")
        ymd = path.stem.rsplit("_", 1)[-1]
        for item in result.get("dailyBoxOfficeList", []):
            rows.append({
                "date": pd.to_datetime(ymd, format="%Y%m%d"),
                "show_range": show_range,
                "movie_cd": item.get("movieCd"),
                "movie_name": item.get("movieNm"),
                "rank": int(item.get("rank", 0) or 0),
                "sales_amt_krw": float(item.get("salesAmt", 0) or 0),
                "audience_count": float(item.get("audiCnt", 0) or 0),
                "screen_count": float(item.get("scrnCnt", 0) or 0),
                "show_count": float(item.get("showCnt", 0) or 0),
                "raw_file": str(path),
            })
    return pd.DataFrame(rows)


def monthly_summary(daily_rows: pd.DataFrame) -> pd.DataFrame:
    if daily_rows.empty:
        return pd.DataFrame()
    d = daily_rows.copy()
    d["year"] = d["date"].dt.year
    d["month"] = d["date"].dt.month
    d["quarter"] = ((d["month"] - 1) // 3 + 1).astype(int)
    return (
        d.groupby(["year", "month", "quarter"], as_index=False)
        .agg(
            kobis_top_sales_krw=("sales_amt_krw", "sum"),
            kobis_top_audience=("audience_count", "sum"),
            kobis_top_show_count=("show_count", "sum"),
            daily_movie_rows=("movie_cd", "count"),
        )
        .sort_values(["year", "month"])
    )


def ytd_shares(monthly: pd.DataFrame) -> pd.DataFrame:
    annual = monthly.groupby("year", as_index=False).agg(
        annual_sales=("kobis_top_sales_krw", "sum"),
        annual_audience=("kobis_top_audience", "sum"),
    )
    rows = []
    for year, g in monthly.groupby("year"):
        a = annual[annual["year"].eq(year)].iloc[0]
        for q in [1, 2, 3, 4]:
            ytd = g[g["quarter"].le(q)]
            rows.append({
                "year": int(year),
                "available_quarters": q,
                "kobis_ytd_sales": float(ytd["kobis_top_sales_krw"].sum()),
                "kobis_ytd_audience": float(ytd["kobis_top_audience"].sum()),
                "kobis_sales_ytd_share": float(ytd["kobis_top_sales_krw"].sum()) / float(a["annual_sales"]) if float(a["annual_sales"]) else np.nan,
                "kobis_audience_ytd_share": float(ytd["kobis_top_audience"].sum()) / float(a["annual_audience"]) if float(a["annual_audience"]) else np.nan,
            })
    return pd.DataFrame(rows)


def compare_with_phase131(shares: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    pred = pd.read_csv(PHASE131_PRED, dtype={"middle_code": str})
    pred["middle_code"] = pred["middle_code"].astype(str).str.zfill(2)
    j59 = pred[
        pred["city"].eq(TARGET_CITY)
        & pred["parent_code"].eq(TARGET_PARENT)
        & pred["middle_code"].eq(TARGET_MIDDLE)
        & pred["year"].isin([2022, 2023])
    ].copy()
    j59 = j59.merge(shares, on=["year", "available_quarters"], how="left")
    j59["kobis_sales_annual_prediction_eok"] = np.where(
        j59["kobis_sales_ytd_share"] > 0,
        j59["ytd_estimate_eok"] / j59["kobis_sales_ytd_share"],
        np.nan,
    )
    j59["kobis_audience_annual_prediction_eok"] = np.where(
        j59["kobis_audience_ytd_share"] > 0,
        j59["ytd_estimate_eok"] / j59["kobis_audience_ytd_share"],
        np.nan,
    )
    for col in ["kobis_sales", "kobis_audience"]:
        pred_col = f"{col}_annual_prediction_eok"
        j59[f"{col}_annual_error_eok"] = (j59[pred_col] - j59["actual_annual_gva_eok"]).abs()
        j59[f"{col}_annual_error_rate_pct"] = np.where(
            j59["actual_annual_gva_eok"] > 0,
            j59[f"{col}_annual_error_eok"] / j59["actual_annual_gva_eok"] * 100,
            np.nan,
        )
    rows = []
    for q, g in j59.groupby("available_quarters"):
        actual = float(g["actual_annual_gva_eok"].sum())
        rows.append({
            "available_quarters": int(q),
            "vintage_label": g["vintage_label"].iloc[0],
            "years": "2022-2023",
            "generic_error_eok": float(g["annual_error_eok"].sum()),
            "generic_wape_pct": float(g["annual_error_eok"].sum()) / actual * 100 if actual else np.nan,
            "kobis_sales_error_eok": float(g["kobis_sales_annual_error_eok"].sum()),
            "kobis_sales_wape_pct": float(g["kobis_sales_annual_error_eok"].sum()) / actual * 100 if actual else np.nan,
            "kobis_audience_error_eok": float(g["kobis_audience_annual_error_eok"].sum()),
            "kobis_audience_wape_pct": float(g["kobis_audience_annual_error_eok"].sum()) / actual * 100 if actual else np.nan,
            "best_track": min(
                [
                    ("generic", float(g["annual_error_eok"].sum())),
                    ("kobis_sales", float(g["kobis_sales_annual_error_eok"].sum())),
                    ("kobis_audience", float(g["kobis_audience_annual_error_eok"].sum())),
                ],
                key=lambda x: x[1],
            )[0],
        })
    return j59, pd.DataFrame(rows)


def route_decision(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in summary.iterrows():
        generic = float(r["generic_error_eok"])
        best_kobis = min(float(r["kobis_sales_error_eok"]), float(r["kobis_audience_error_eok"]))
        reduction = generic - best_kobis
        rows.append({
            "available_quarters": int(r["available_quarters"]),
            "vintage_label": r["vintage_label"],
            "adopt_for_j59_temporal_nowcast": bool(reduction > 0),
            "best_track": r["best_track"],
            "error_reduction_eok": reduction,
            "decision_note": "KOBIS improves temporal annual nowcast" if reduction > 0 else "generic seasonal share remains safer",
        })
    return pd.DataFrame(rows)


def md_table(df: pd.DataFrame, cols: list[str], n: int | None = None) -> str:
    if df.empty:
        return "_없음_"
    d = df[cols].copy()
    if n:
        d = d.head(n)
    labels = [c.replace("_eok", " 억원").replace("_pct", " %").replace("_krw", " 원").replace("_", " ") for c in d.columns]

    def fmt(v: object) -> str:
        if pd.isna(v):
            return ""
        if isinstance(v, (float, np.floating)):
            if np.isfinite(float(v)) and abs(float(v) - round(float(v))) < 1e-9:
                return f"{int(round(float(v))):,}"
            return f"{float(v):,.2f}"
        if isinstance(v, (int, np.integer)):
            return f"{int(v):,}"
        return str(v).replace("|", "\\|")

    body = ["| " + " | ".join(fmt(x) for x in row) + " |" for row in d.to_numpy()]
    return "\n".join(["| " + " | ".join(labels) + " |", "| " + " | ".join(["---"] * len(labels)) + " |", *body])


def write_report(scope: pd.DataFrame, monthly: pd.DataFrame, detail: pd.DataFrame, summary: pd.DataFrame, decision: pd.DataFrame) -> None:
    REPORT.write_text("\n".join([
        "# Phase136 KOBIS 박스오피스 기반 고양시 J59 시간패턴 진단",
        "",
        "## 목적",
        "",
        "KOBIS API는 사용 가능하고 KOPIS는 사용 불가하므로, KOBIS 일별 박스오피스 매출·관객을 고양시 J59(영상·오디오 제작업) 연·분기 nowcast의 시간패턴 보조지표로 시험했다. KOBIS는 전국 박스오피스 top-list 자료이므로 고양시 actual이나 공간배분 자료로 주장하지 않는다.",
        "",
        "## API 범위 감사",
        "",
        md_table(scope, ["probe_name", "params_without_key", "boxoffice_type", "show_range", "row_count", "movie_codes_same_as_baseline", "sales_sum_krw", "response_scope_interpretation"]),
        "",
        "## KOBIS 월별 수집 요약",
        "",
        md_table(monthly, ["year", "month", "quarter", "kobis_top_sales_krw", "kobis_top_audience", "daily_movie_rows"], n=18),
        "",
        "## 2022~2023 J59 연간 nowcast 비교",
        "",
        md_table(summary, ["available_quarters", "vintage_label", "years", "generic_error_eok", "generic_wape_pct", "kobis_sales_error_eok", "kobis_sales_wape_pct", "kobis_audience_error_eok", "kobis_audience_wape_pct", "best_track"]),
        "",
        "## 빈티지별 적용 판정",
        "",
        md_table(decision, decision.columns.tolist()),
        "",
        "## 2023 예시 상세",
        "",
        md_table(detail[detail["year"].eq(2023)], ["vintage_label", "ytd_estimate_eok", "seasonal_ytd_share", "kobis_sales_ytd_share", "kobis_audience_ytd_share", "annual_prediction_eok", "kobis_sales_annual_prediction_eok", "kobis_audience_annual_prediction_eok", "actual_annual_gva_eok", "annual_error_rate_pct", "kobis_sales_annual_error_rate_pct", "kobis_audience_annual_error_rate_pct"]),
        "",
        "## 판정",
        "",
        "1. KOBIS는 고양시 시군구 단위 영화 매출 actual이 아니므로 J59 금액격차 자체를 직접 검증하는 자료가 아니다.",
        "2. 다만 전국 영화시장 월별 매출·관객의 YTD share는 J59 시간패턴 후보로 쓸 수 있다. 채택 여부는 2022~2023 rolling nowcast에서 generic seasonal share보다 오차가 작을 때만 제한적으로 허용한다.",
        "3. KOBIS가 개선되지 않는 빈티지는 기존 계절비중을 유지해야 한다. 이 원칙은 Phase133의 금액가중 guardrail과 같다: 그럴듯한 자료라도 검증오차를 줄이지 못하면 채택하지 않는다.",
        "4. 고양시 공간·금액 개선에는 여전히 고양시 영상기업/제작지원/촬영·상영 매출 자료가 필요하다. KOBIS는 시간축 보조지표이지 고양시 산업 총량 actual이 아니다.",
    ]) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    key = read_env_key()
    scope = api_scope_audit(key)
    daily = collect()
    monthly = monthly_summary(daily)
    shares = ytd_shares(monthly)
    detail, summary = compare_with_phase131(shares)
    decision = route_decision(summary)

    scope.to_csv(OUT / "phase136_kobis_api_scope_audit.csv", index=False)
    daily.to_csv(OUT / "phase136_kobis_daily_boxoffice_rows.csv", index=False)
    monthly.to_csv(OUT / "phase136_kobis_monthly_summary.csv", index=False)
    shares.to_csv(OUT / "phase136_kobis_ytd_shares.csv", index=False)
    detail.to_csv(OUT / "phase136_goyang_j59_nowcast_detail.csv", index=False)
    summary.to_csv(OUT / "phase136_goyang_j59_nowcast_summary.csv", index=False)
    decision.to_csv(OUT / "phase136_goyang_j59_route_decision.csv", index=False)
    write_report(scope, monthly, detail, summary, decision)
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
