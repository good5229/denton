from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT, cp949_safe


RUN_ID = "partial_statistics_estimation_phase36_gva"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
RAW_NTS = ROOT / "data" / "raw" / "phase35_free_interaction"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase36_gva.md"
SERVICE_SECTORS = {
    "G00": "도매 및 소매업", "H00": "운수 및 창고업", "I00": "숙박 및 음식점업",
    "L00": "부동산업", "MN0": "사업서비스업", "P00": "교육 서비스업",
    "Q00": "보건업 및 사회복지 서비스업", "ERS": "문화 및 기타서비스업",
}
SECTION_BRIDGE = {
    "G00": ["G"], "H00": ["H"], "I00": ["I"], "L00": ["L"],
    "MN0": ["M", "N"], "P00": ["P"], "Q00": ["Q"], "ERS": ["R", "S"],
}
GOYANG_PREFIX = {"31101": "덕양구", "31103": "일산동구", "31104": "일산서구"}


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def stable_hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def add_audit(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    base = [c for c in out if c not in {"input_hash", "code_commit_hash", "run_id", "created_at"}]
    out["input_hash"] = stable_hash(out[base].head(20_000).to_dict("records")) if len(out) else ""
    out["code_commit_hash"] = git_hash()
    out["run_id"] = RUN_ID
    out["created_at"] = CREATED_AT
    return out


def write_csv(name: str, frame: pd.DataFrame) -> None:
    out = frame.copy()
    for c in out:
        if out[c].dtype == object:
            out[c] = out[c].map(cp949_safe)
    out.to_csv(PROCESSED_DIR / name, index=False, encoding=CSV_ENCODING, errors="replace")


def generalized_proportional_denton(indicator: np.ndarray, benchmarks: np.ndarray, frequency: int = 3) -> np.ndarray:
    """Minimize adjacent changes in estimate/indicator subject to period-sum constraints."""
    i = np.asarray(indicator, dtype=float)
    b = np.asarray(benchmarks, dtype=float)
    if len(i) != len(b) * frequency or np.any(~np.isfinite(i)) or np.any(i <= 0):
        raise ValueError("positive complete indicator and compatible benchmarks required")
    n = len(i)
    m = np.diag(1.0 / i)
    d = np.zeros((n - 1, n))
    for r in range(n - 1):
        d[r, r], d[r, r + 1] = -1.0, 1.0
    h = 2.0 * (m.T @ d.T @ d @ m)
    j = np.zeros((len(b), n))
    for k in range(len(b)):
        j[k, k * frequency:(k + 1) * frequency] = 1.0
    lhs = np.block([[h, j.T], [j, np.zeros((len(b), len(b)))]] )
    rhs = np.r_[np.zeros(n), b]
    try:
        answer = np.linalg.solve(lhs, rhs)[:n]
    except np.linalg.LinAlgError:
        answer = np.linalg.lstsq(lhs, rhs, rcond=None)[0][:n]
    if np.any(answer <= 0):
        # Positive fallback preserves every quarterly control but does not smooth across boundaries.
        answer = np.concatenate([i[k*frequency:(k+1)*frequency] / i[k*frequency:(k+1)*frequency].sum() * b[k]
                                 for k in range(len(b))])
    return answer


def canonical_label(value: str) -> str:
    return str(value).strip().lower().replace("ㆍ", "").replace("?", "").replace(" ", "")


def nts_sector(label: str) -> str | None:
    x = canonical_label(label)
    if x == "업종전체":
        return None
    if any(k in x for k in ["음식점", "전문점", "분식점", "제과점", "커피", "주점", "구내식당", "패스트푸드", "여관", "모텔", "펜션", "게스트하우스"]):
        return "I00"
    if any(k in x for k in ["의원", "병원", "한의원"]):
        return "Q00"
    if any(k in x for k in ["교습", "학원", "공부방", "독서실", "스포츠교육"]):
        return "P00"
    if "부동산중개" in x:
        return "L00"
    if any(k in x for k in ["주차장운영", "여행사"]):
        return "H00" if "주차장" in x else "MN0"
    if any(k in x for k in ["변호사", "법무사", "세무사", "회계사", "노무사", "변리사", "감정평가", "건축사", "기술사", "간판광고", "결혼상담", "동물병원"]):
        return "MN0"
    if any(k in x for k in ["pc방", "노래방", "당구장", "골프", "헬스", "목욕탕", "미용실", "이발소", "세탁소", "피부관리", "사진촬영", "예식장", "자동차수리", "가전제품수리"]):
        return "ERS"
    return "G00"


def load_nts() -> pd.DataFrame:
    manifest = pd.read_csv(RAW_NTS / "nts_lifestyle_manifest_2021_2023.csv", encoding="utf-8-sig", dtype=str)
    pieces = []
    for row in manifest.itertuples(index=False):
        x = pd.read_csv(ROOT / row.local_file, encoding="cp949", dtype=str)
        x["year"] = int(row.reference_date[:4]); x["month"] = int(row.reference_date[4:6])
        x["sector_code"] = x["업종"].map(nts_sector)
        x["value"] = pd.to_numeric(x["당월"].str.replace(",", "", regex=False), errors="coerce")
        x.loc[x["value"].le(0), "value"] = np.nan  # NTS says cells below three are suppressed.
        pieces.append(x[["year", "month", "시도", "시군구", "sector_code", "value"]])
    out = pd.concat(pieces, ignore_index=True).dropna(subset=["sector_code", "value"])
    return out.groupby(["year", "month", "시도", "시군구", "sector_code"], as_index=False)["value"].sum()


def load_controls() -> pd.DataFrame:
    q = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase22_gva_sigungu_quarterly_allocation_cube.parquet")
    return q[q["year"].between(2021, 2023) & q["sector_code"].isin(SERVICE_SECTORS)].copy()


def denton_panel(indicators: pd.DataFrame, controls: pd.DataFrame, entity_cols: list[str]) -> pd.DataFrame:
    rows = []
    keys = entity_cols + ["sector_code"]
    for key, z in indicators.groupby(keys, sort=True):
        z = z.sort_values(["year", "month"])
        cquery = controls.copy()
        key_tuple = key if isinstance(key, tuple) else (key,)
        for col, value in zip(keys, key_tuple):
            cquery = cquery[cquery[col].eq(value)]
        cquery = cquery.sort_values(["year", "quarter"])
        if len(z) != 36 or len(cquery) != 12:
            continue
        fit = generalized_proportional_denton(z["value"].to_numpy(), cquery["estimated_quarterly_gva"].to_numpy())
        part = z.copy(); part["estimated_monthly_gva"] = fit
        part["quarter"] = ((part["month"] - 1) // 3 + 1).astype(int)
        part["sector_name"] = part["sector_code"].map(SERVICE_SECTORS)
        rows.append(part)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def build_seoul(nts: pd.DataFrame, controls: pd.DataFrame) -> pd.DataFrame:
    i = nts[nts["시도"].eq("서울특별시")].rename(columns={"시군구": "sigungu_name"})
    c = controls[controls["source_region"].eq("서울특별시")]
    out = denton_panel(i[["year", "month", "sigungu_name", "sector_code", "value"]], c,
                       ["sigungu_name"])
    code = c[["sigungu_name", "sigungu_code"]].drop_duplicates()
    out = out.merge(code, on="sigungu_name", how="left", validate="many_to_one")
    out["source_region"] = "서울특별시"
    out["indicator_source"] = "NTS 100 lifestyle active-business counts mapped by Phase36 judgmental bridge"
    out["benchmark_source"] = "Phase22 official annual sigungu GVA constrained quarterly allocation"
    out["claim_scope"] = "constrained monthly allocation; not direct monthly GVA actual"
    return out


def goyang_spatial_weights() -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(PROCESSED_DIR / "emd_economic_census_2015.csv", encoding="cp949",
                      dtype={"c1_id": str, "c2_id": str})
    x = raw[raw["c2_id"].str.len().eq(7) & raw["c2_id"].str.startswith(tuple(GOYANG_PREFIX))].copy()
    x["general_gu"] = x["c2_id"].str[:5].map(GOYANG_PREFIX)
    x["value"] = pd.to_numeric(x["value"], errors="coerce")
    reverse = {section: sector for sector, sections in SECTION_BRIDGE.items() for section in sections}
    x["sector_code"] = x["c1_id"].map(reverse)
    x = x.dropna(subset=["sector_code"])
    p = x.pivot_table(index=["general_gu", "c2_id", "c2_nm", "sector_code"], columns="metric",
                      values="value", aggfunc="sum", fill_value=0).reset_index()
    for metric in ["establishments", "employees", "sales"]:
        total = p.groupby(["general_gu", "sector_code"])[metric].transform("sum")
        p[f"{metric}_share"] = p[metric] / total.replace(0, np.nan)
    p["spatial_weight"] = p[["establishments_share", "employees_share"]].mean(axis=1)
    p["spatial_weight"] /= p.groupby(["general_gu", "sector_code"])["spatial_weight"].transform("sum")
    validations = []
    for key, z in p.groupby(["general_gu", "sector_code"]):
        pred, actual = z["spatial_weight"], z["sales_share"]
        uniform = np.repeat(1 / len(z), len(z))
        validations.append({"general_gu": key[0], "sector_code": key[1], "emd_count": len(z),
                            "heldout_metric": "2015 sales share",
                            "composite_mae": float(np.mean(np.abs(pred-actual))),
                            "uniform_mae": float(np.mean(np.abs(uniform-actual))),
                            "spearman": float(pred.corr(actual, method="spearman"))})
    return p, pd.DataFrame(validations)


def build_goyang(nts: pd.DataFrame, controls: pd.DataFrame, weights: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    i = nts[(nts["시도"].eq("경기도")) & nts["시군구"].str.startswith("고양시 ")].copy()
    i["시군구"] = i["시군구"].str.replace("고양시 ", "", regex=False)
    city_i = i.groupby(["year", "month", "sector_code"], as_index=False)["value"].sum()
    c = controls[(controls["source_region"].eq("경기도")) & controls["sigungu_name"].eq("고양시")]
    city_c = c.copy(); city_c["city"] = "고양시"; city_i["city"] = "고양시"
    city = denton_panel(city_i[["year", "month", "city", "sector_code", "value"]], city_c.assign(city="고양시"), ["city"])
    shares = i.merge(city_i.rename(columns={"value": "city_indicator"}), on=["year", "month", "sector_code"], how="left")
    shares["gu_share"] = shares["value"] / shares["city_indicator"]
    city = city.merge(shares[["year", "month", "sector_code", "시군구", "gu_share"]],
                      on=["year", "month", "sector_code"], how="left", validate="one_to_many")
    city["general_gu_monthly_gva"] = city["estimated_monthly_gva"] * city["gu_share"]
    out = city.merge(weights, left_on=["시군구", "sector_code"], right_on=["general_gu", "sector_code"],
                     how="inner", validate="many_to_many")
    out["estimated_emd_monthly_gva"] = out["general_gu_monthly_gva"] * out["spatial_weight"]
    out["geography_vintage"] = "2015 administrative-dong basis"
    out["indicator_source"] = "NTS general-gu monthly counts x 2015 Economic Census EMD spatial weights"
    out["benchmark_source"] = "Phase22 official annual Goyang GVA constrained quarterly allocation"
    out["claim_scope"] = "separable constrained EMD-month allocation; no EMD-specific monthly signal"
    # Strict common-profile audit: normalized profiles across EMDs inside each gu-sector-year.
    profiles = []
    for key, z in out.groupby(["general_gu", "sector_code", "year"]):
        mat = z.pivot(index="c2_id", columns="month", values="estimated_emd_monthly_gva").dropna()
        norm = mat.div(mat.sum(axis=1), axis=0)
        hashes = norm.round(12).astype(str).agg("|".join, axis=1)
        profiles.append({"general_gu": key[0], "sector_code": key[1], "year": key[2],
                         "emd_count": len(mat), "effective_rank": int(np.linalg.matrix_rank(norm.to_numpy(), tol=1e-10)),
                         "unique_normalized_profiles": int(hashes.nunique()),
                         "all_emd_profiles_identical": bool(hashes.nunique() == 1)})
    return out, pd.DataFrame(profiles)


def temporal_validation(nts: pd.DataFrame, controls: pd.DataFrame) -> pd.DataFrame:
    frames = []
    seoul = nts[nts["시도"].eq("서울특별시")].rename(columns={"시군구": "entity"})
    frames.append(("서울 구", seoul, controls[controls["source_region"].eq("서울특별시")].rename(columns={"sigungu_name":"entity"})))
    gy = nts[(nts["시도"].eq("경기도")) & nts["시군구"].str.startswith("고양시 ")].groupby(
        ["year", "month", "sector_code"], as_index=False)["value"].sum(); gy["entity"]="고양시"
    frames.append(("고양시", gy, controls[(controls["source_region"].eq("경기도")) & controls["sigungu_name"].eq("고양시")].rename(columns={"sigungu_name":"entity"})))
    rows=[]
    for scope, ind, ctl in frames:
        q = ind.assign(quarter=((ind.month-1)//3+1)).groupby(["entity","sector_code","year","quarter"],as_index=False).value.sum()
        q["indicator_share"] = q.value/q.groupby(["entity","sector_code","year"]).value.transform("sum")
        c = ctl.copy(); c["control_share"] = c.estimated_quarterly_gva/c.groupby(["entity","sector_code","year"]).estimated_quarterly_gva.transform("sum")
        z=q.merge(c[["entity","sector_code","year","quarter","control_share"]],on=["entity","sector_code","year","quarter"])
        for key,g in z.groupby(["entity","sector_code","year"]):
            rows.append({"scope":scope,"entity":key[0],"sector_code":key[1],"year":key[2],
                         "indicator_mae":float(np.mean(np.abs(g.indicator_share-g.control_share))),
                         "uniform_mae":float(np.mean(np.abs(.25-g.control_share))),
                         "spearman":float(g.indicator_share.corr(g.control_share,method="spearman")),
                         "evidence_note":"agreement with independent-source Phase22 quarterly proxy, not GVA actual accuracy"})
    return pd.DataFrame(rows)


def seoul_common_proxy_audit(nts: pd.DataFrame) -> pd.DataFrame:
    x = nts[nts["시도"].eq("서울특별시")].copy()
    rows = []
    for key, z in x.groupby(["시군구", "year"]):
        mat = z.pivot(index="sector_code", columns="month", values="value").dropna()
        norm = mat.div(mat.sum(axis=1), axis=0)
        hashes = norm.round(12).astype(str).agg("|".join, axis=1)
        rows.append({"scope": "Seoul raw NTS profiles across sectors", "region": key[0],
                     "sector_code": "ALL_SUPPORTED", "year": key[1], "profile_count": len(mat),
                     "effective_rank": int(np.linalg.matrix_rank(norm.to_numpy(), tol=1e-10)),
                     "unique_normalized_profiles": int(hashes.nunique()),
                     "all_profiles_identical": bool(hashes.nunique() == 1)})
    return pd.DataFrame(rows)


def accounting_checks(seoul: pd.DataFrame, goyang: pd.DataFrame, controls: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    sq=seoul.groupby(["sigungu_name","sector_code","year","quarter"],as_index=False).estimated_monthly_gva.sum()
    sc=controls[controls.source_region.eq("서울특별시")]
    z=sq.merge(sc,on=["sigungu_name","sector_code","year","quarter"])
    rows.append({"scope":"Seoul gu x sector x quarter","max_abs_error":float((z.estimated_monthly_gva-z.estimated_quarterly_gva).abs().max()),"cells":len(z)})
    gq=goyang.groupby(["sector_code","year","quarter"],as_index=False).estimated_emd_monthly_gva.sum()
    gc=controls[(controls.source_region.eq("경기도"))&controls.sigungu_name.eq("고양시")]
    z=gq.merge(gc,on=["sector_code","year","quarter"])
    rows.append({"scope":"Goyang EMD x sector x quarter","max_abs_error":float((z.estimated_emd_monthly_gva-z.estimated_quarterly_gva).abs().max()),"cells":len(z)})
    for scope, frame, val in [("Seoul gu x sector x year",seoul,"estimated_monthly_gva"),("Goyang EMD x sector x year",goyang,"estimated_emd_monthly_gva")]:
        keys=["sector_code","year"] if scope.startswith("Goyang") else ["sigungu_name","sector_code","year"]
        a=frame.groupby(keys,as_index=False)[val].sum(); c=controls.copy()
        if scope.startswith("Goyang"): c=c[(c.source_region.eq("경기도"))&c.sigungu_name.eq("고양시")].drop_duplicates(["sector_code","year"])
        else: c=c[c.source_region.eq("서울특별시")].drop_duplicates(["sigungu_name","sector_code","year"])
        z=a.merge(c,on=keys); rows.append({"scope":scope,"max_abs_error":float((z[val]-z.annual_benchmark_gva).abs().max()),"cells":len(z)})
    return pd.DataFrame(rows)


def main() -> dict[str, object]:
    nts, controls = load_nts(), load_controls()
    seoul = build_seoul(nts, controls)
    weights, spatial_cv = goyang_spatial_weights()
    goyang, goyang_common = build_goyang(nts, controls, weights)
    goyang_common = goyang_common.rename(columns={"general_gu":"region", "emd_count":"profile_count",
                                                   "all_emd_profiles_identical":"all_profiles_identical"})
    goyang_common["scope"] = "Goyang EMD profiles within general-gu-sector"
    common = pd.concat([seoul_common_proxy_audit(nts), goyang_common], ignore_index=True, sort=False)
    temporal = temporal_validation(nts, controls)
    temporal_sector = temporal.groupby(["scope", "sector_code"], as_index=False).agg(
        groups=("year", "size"), indicator_mae_median=("indicator_mae", "median"),
        uniform_mae_median=("uniform_mae", "median"), spearman_median=("spearman", "median"),
    )
    better = temporal.assign(better=temporal["indicator_mae"] < temporal["uniform_mae"]).groupby(
        ["scope", "sector_code"], as_index=False)["better"].mean().rename(columns={"better":"better_rate"})
    temporal_sector = temporal_sector.merge(better, on=["scope", "sector_code"])
    support = temporal_sector.pivot(index="sector_code", columns="scope", values="better_rate")
    supported_sectors = sorted(support[(support > .5).all(axis=1)].index.tolist())
    blocked_sectors = sorted(set(SERVICE_SECTORS) - set(supported_sectors))
    seoul["temporal_proxy_decision"] = np.where(seoul.sector_code.isin(supported_sectors), "retain_proxy_shape", "diagnostic_only_failed_uniform_gate")
    goyang["temporal_proxy_decision"] = np.where(goyang.sector_code.isin(supported_sectors), "retain_proxy_shape", "diagnostic_only_failed_uniform_gate")
    accounting = accounting_checks(seoul, goyang, controls)
    for name, frame in {
        "partial_stats_phase36_gva_seoul_gu_monthly.csv": add_audit(seoul),
        "partial_stats_phase36_gva_goyang_emd_monthly.csv": add_audit(goyang),
        "partial_stats_phase36_gva_accounting_checks.csv": add_audit(accounting),
        "partial_stats_phase36_gva_temporal_validation.csv": add_audit(temporal),
        "partial_stats_phase36_gva_spatial_validation.csv": add_audit(spatial_cv),
        "partial_stats_phase36_gva_common_proxy_audit.csv": add_audit(common),
    }.items(): write_csv(name, frame)
    status = {
        "run_id":RUN_ID, "seoul_rows":len(seoul), "seoul_gu":int(seoul.sigungu_name.nunique()),
        "goyang_rows":len(goyang), "goyang_emd":int(goyang.c2_id.nunique()),
        "sectors":sorted(seoul.sector_code.unique()),
        "accounting_max_abs_error":float(accounting.max_abs_error.max()),
        "temporal_groups":len(temporal),
        "temporal_indicator_better_rate":float((temporal.indicator_mae<temporal.uniform_mae).mean()),
        "temporal_supported_sectors":supported_sectors,
        "temporal_blocked_sectors":blocked_sectors,
        "spatial_groups":len(spatial_cv),
        "spatial_composite_better_rate":float((spatial_cv.composite_mae<spatial_cv.uniform_mae).mean()),
        "goyang_common_profile_rate":float(goyang_common.all_profiles_identical.mean()),
        "seoul_common_profile_rate":float(common.loc[common.scope.str.startswith("Seoul"), "all_profiles_identical"].mean()),
        "decision":"retain_seoul_gu_monthly_experimental; retain_goyang_emd_monthly_as_separable_allocation_only; block_emd_specific_monthly_dynamics_claim",
        "created_at":CREATED_AT,
    }
    (PROCESSED_DIR/"partial_stats_phase36_gva_status.json").write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding="utf-8")
    render_report(status, accounting, temporal, temporal_sector, spatial_cv, common)
    return status


def render_report(status, accounting, temporal, temporal_sector, spatial, common) -> None:
    def md(df):
        x = df.round(6).fillna("")
        header = "| " + " | ".join(map(str, x.columns)) + " |"
        rule = "|" + "|".join(["---"] * len(x.columns)) + "|"
        body = ["| " + " | ".join(map(str, row)) + " |" for row in x.itertuples(index=False, name=None)]
        return "\n".join([header, rule, *body])
    text=f"""# Phase 36: 서울·고양 시공간 이중 벤치마킹 GVA 실험

## 결론

- 서울은 **25개 구 × 8개 서비스 대분류 × 월(2021–2023)** 배분 추정치를 만들었다. 구·산업별 월 합은 분기 제약과 연간 공식 벤치마크에 동시에 맞는다.
- 고양은 **2015년 행정동 39개 × 8개 서비스 대분류 × 월(2021–2023)**의 제약 배분표를 만들었다.
- 그러나 고양 행정동에는 월별 고유 신호가 없다. 같은 일반구·산업 안의 행정동들은 2015 공간가중치만 다르고 정규화된 월 변화는 모두 같다. 따라서 `행정동별 월간 GVA의 고유 경기변동` 주장은 차단한다.
- 어떤 값도 직접 관측 월간 GVA actual 또는 C등급으로 승격하지 않는다.

## BOK 방법의 접목

참고문서 `reference/BOK이슈노트제2023-9호_지역경기상황지수의 개발 및 활용.pdf`의 비례형 Denton 원리를 분기→월에 적용했다. 목적함수는 인접 월의 `추정치/지표` 비율 변화 최소화이며, 각 3개월 합을 Phase22 분기 제약에 일치시켰다. Phase22 분기값 자체가 연간 공식 시군구 GVA에 제약되어 있으므로 연간 합도 일치한다.

다만 BOK의 전국 산업별 분기 GDP actual에 해당하는 **시군구 이하 분기 GVA actual은 없다**. 여기서 분기 제약은 Phase22 배분 추정치다. 따라서 합계 일치는 회계 검증이고 정확도 증거가 아니다.

## 산출 범위

| 항목 | 값 |
|---|---:|
| 서울 월간 행 | {status['seoul_rows']:,} |
| 서울 구 | {status['seoul_gu']} |
| 고양 월간 행 | {status['goyang_rows']:,} |
| 고양 2015 행정동 | {status['goyang_emd']} |
| 산업 | {', '.join(status['sectors'])} |

국세청 100대 생활업종은 공식 KSIC 연계표가 아니므로 명시적 판단 규칙으로 8개 서비스 묶음에 연결했다. 0은 실제 0이 아니라 3개 미만 비공개 가능성이 있어 결측으로 처리했다.

## 이중 회계 제약

{md(accounting)}

부동소수점 허용오차 내에서 분기와 연간 제약을 모두 만족한다. 이는 설계상 기대되는 보존성이다.

## 시간 교차검증

국세청 월간 지표의 분기 비중을 Phase22의 별도 출처 분기경로와 비교했다. Phase22도 actual이 아니므로 방향·계절성의 외부 프록시 일치도만 뜻한다.

| 진단 | 값 |
|---|---:|
| 비교 그룹 | {len(temporal)} |
| 균등 1/4보다 MAE가 낮은 비율 | {status['temporal_indicator_better_rate']:.3f} |
| 지표 MAE 중앙값 | {temporal.indicator_mae.median():.6f} |
| 균등 MAE 중앙값 | {temporal.uniform_mae.median():.6f} |
| Spearman 중앙값 | {temporal.spearman.median():.6f} |

{md(temporal_sector)}

서울과 고양 양쪽 모두에서 균등 계절배분보다 우세한 산업은 **{', '.join(status['temporal_supported_sectors'])}**다. **{', '.join(status['temporal_blocked_sectors'])}**는 이 최소 gate를 통과하지 못해 월간 프록시 경로를 진단용으로만 둔다. 이 판정도 actual 정확도 승격은 아니다.

## 공간 교차검증

2015 경제총조사의 사업체수·종사자수만으로 공간가중치를 만들고, 산정에 쓰지 않은 매출액 읍면동 비중을 holdout으로 비교했다. 같은 조사계열 내부 검증이므로 완전 독립 검증은 아니다.

| 진단 | 값 |
|---|---:|
| 일반구×산업 그룹 | {len(spatial)} |
| 균등배분보다 MAE가 낮은 비율 | {status['spatial_composite_better_rate']:.3f} |
| 복합가중 MAE 중앙값 | {spatial.composite_mae.median():.6f} |
| 균등 MAE 중앙값 | {spatial.uniform_mae.median():.6f} |
| Spearman 중앙값 | {spatial.spearman.median():.6f} |

## 공통 프록시 엄격 검증

{md(common.groupby(['scope','sector_code'],as_index=False).agg(groups=('year','size'), median_rank=('effective_rank','median'), identical_rate=('all_profiles_identical','mean')))}

서울에서 산업 간 원천 월 프로필이 전부 동일한 구×연도 비율은 **{status['seoul_common_profile_rate']:.1%}**로, 공통 시계열의 일괄 복제 문제는 탐지되지 않았다. 반면 고양의 동일 일반구·산업 내 행정동 정규화 월 프로필 동일률은 **{status['goyang_common_profile_rate']:.1%}**다. 이것은 과거의 “공통 사업체 프록시 동일 적용”과 같은 유형의 상호작용 결손이다. 결과표는 회계적으로 유효한 separable allocation이지만 읍면동 고유 월간 신호로 해석하면 안 된다.

## 판정과 다음 단계

1. 서울 구×서비스대분류×월: 실험용 Retain. 독립 actual 정확도 검증 전에는 운영·공식 추정 주장 금지.
2. 고양 행정동×서비스대분류×월: 제약 배분표로만 Retain. 행정동 고유 월간 변동 주장은 Block.
3. 고양을 실제 상호작용 제품으로 승격하려면 무료 데이터 중 `행정동×월`에서 움직이는 독립 신호가 필요하다. 주민등록 인구만으로 경제활동을 대체하지 말고, 행정동별 사업체·유동/상권·전력 등 시계열을 확보한 뒤 현재 공통 프로필 감사를 다시 통과해야 한다.
4. 서울 2024 사업체지도는 이후 공간 out-of-time 검증에 사용할 수 있지만, 이번 2021–2023 월 추정의 입력에는 사용하지 않았다.
"""
    REPORT.write_text(text,encoding="utf-8")


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=2))
