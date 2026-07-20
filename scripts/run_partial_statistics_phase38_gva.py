from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase38_gva.md"
RUN_ID = "partial_statistics_estimation_phase38_gva"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
TARGETS = {
    "I00": {"name": "숙박·음식점", "proxy": ["I00"], "gate": "strong"},
    "Q00": {"name": "보건·사회복지", "proxy": ["Q00"], "gate": "supplementary"},
    "ERS": {"name": "예술·여가·개인서비스", "proxy": ["R00", "S00"], "gate": "mixed_strong_supplementary"},
}


def safe_correlation(left: pd.Series, right: pd.Series) -> float:
    if left.nunique() < 2 or right.nunique() < 2:
        return float("nan")
    return float(left.corr(right))


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def stable_hash(frame: pd.DataFrame) -> str:
    payload = frame.head(20_000).to_json(orient="records", force_ascii=False, double_precision=12)
    return hashlib.sha256(payload.encode()).hexdigest()


def audit(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["input_hash"] = stable_hash(out)
    out["code_commit_hash"] = git_hash()
    out["run_id"] = RUN_ID
    out["created_at"] = CREATED_AT
    return out


def write_csv(name: str, frame: pd.DataFrame) -> None:
    audit(frame).to_csv(DATA / name, index=False, encoding="utf-8-sig")


def ras_biproportional(seed: np.ndarray, row_targets: np.ndarray, col_targets: np.ndarray,
                       tolerance: float = 1e-10, max_iter: int = 10_000) -> np.ndarray:
    """Scale a positive seed matrix to fixed row and column margins."""
    x = np.asarray(seed, dtype=float).copy()
    r = np.asarray(row_targets, dtype=float)
    c = np.asarray(col_targets, dtype=float)
    if x.shape != (len(r), len(c)) or np.any(x <= 0) or np.any(r <= 0) or np.any(c <= 0):
        raise ValueError("positive compatible seed and margins required")
    if not np.isclose(r.sum(), c.sum(), rtol=0, atol=max(1e-8, c.sum() * 1e-12)):
        raise ValueError("row and column margins must have the same total")
    for _ in range(max_iter):
        x *= (r / x.sum(axis=1))[:, None]
        x *= (c / x.sum(axis=0))[None, :]
        err = max(np.max(np.abs(x.sum(axis=1) - r)), np.max(np.abs(x.sum(axis=0) - c)))
        if err <= tolerance * max(1.0, c.sum()):
            return x
    raise RuntimeError("RAS failed to converge")


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    phase36 = pd.read_csv(DATA / "partial_stats_phase36_gva_goyang_emd_monthly.csv", encoding="cp949")
    proxy = pd.read_csv(DATA / "partial_stats_phase37_goyang_emd_industry_monthly_proxy.csv",
                        dtype={"emd_code": str})
    actual = pd.read_csv(DATA / "partial_stats_phase37_goyang_gu_industry_annual_actual.csv")
    emd = pd.read_csv(DATA / "partial_stats_phase37_goyang_emd_current.csv", dtype={"emd_code": str})
    return phase36, proxy, actual, emd


def city_month_controls(phase36: pd.DataFrame) -> pd.DataFrame:
    cols = ["year", "month", "sector_code", "estimated_monthly_gva", "quarter"]
    out = phase36[phase36.sector_code.isin(TARGETS)][cols].drop_duplicates()
    if out.duplicated(["year", "month", "sector_code"]).any():
        raise AssertionError("Phase36 city-month controls are not unique")
    return out.sort_values(["sector_code", "year", "month"]).reset_index(drop=True)


def actual_gu_shares(actual: pd.DataFrame) -> pd.DataFrame:
    detail = actual[actual.general_gu.ne("합계")].copy()
    rows = []
    component_map = {"I00": ["I"], "Q00": ["Q"], "ERS": ["R", "S"]}
    for target, components in component_map.items():
        x = detail[detail.sector_code.isin(components)].groupby(
            ["year", "general_gu", "metric"], as_index=False).value.sum()
        x["metric_share"] = x.value / x.groupby(["year", "metric"]).value.transform("sum")
        z = x.groupby(["year", "general_gu"], as_index=False).metric_share.mean()
        z["annual_gu_share"] = z.metric_share / z.groupby("year").metric_share.transform("sum")
        z["sector_code"] = target
        rows.append(z[["year", "general_gu", "sector_code", "annual_gu_share"]])
    return pd.concat(rows, ignore_index=True)


def proxy_gu_shares(proxy: pd.DataFrame) -> pd.DataFrame:
    x = proxy[proxy.period.between("2021-01", "2023-12")].copy()
    x["year"] = x.period.str[:4].astype(int)
    rows = []
    for target, spec in TARGETS.items():
        z = x[x.sector_code.isin(spec["proxy"])].groupby(
            ["year", "general_gu", "period"], as_index=False).active_license_stock.sum()
        z = z.groupby(["year", "general_gu"], as_index=False).active_license_stock.mean()
        z["proxy_gu_share"] = z.active_license_stock / z.groupby("year").active_license_stock.transform("sum")
        z["sector_code"] = target
        rows.append(z[["year", "general_gu", "sector_code", "proxy_gu_share"]])
    return pd.concat(rows, ignore_index=True)


def prospective_holdout(actual_share: pd.DataFrame, proxy_share: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    base = actual_share.merge(proxy_share, on=["year", "general_gu", "sector_code"], validate="one_to_one")
    previous = actual_share.rename(columns={"year": "target_year", "annual_gu_share": "previous_actual_share"}).copy()
    previous["year"] = previous.target_year + 1
    base = base.merge(previous[["year", "general_gu", "sector_code", "previous_actual_share"]],
                      on=["year", "general_gu", "sector_code"], how="left", validate="one_to_one")
    grid_rows = []
    for alpha in np.linspace(0, 1, 5):
        for year, label in [(2022, "development"), (2023, "heldout")]:
            z = base[base.year.eq(year)].copy()
            z["pred"] = alpha * z.previous_actual_share + (1 - alpha) * z.proxy_gu_share
            grid_rows.append({
                "alpha_previous_actual": alpha,
                "evaluation_year": year,
                "split": label,
                "mae_pp": float((z.pred - z.annual_gu_share).abs().mean() * 100),
            })
    grid = pd.DataFrame(grid_rows)
    selected_alpha = float(grid[grid.split.eq("development")].sort_values(
        ["mae_pp", "alpha_previous_actual"]).iloc[0].alpha_previous_actual)

    rows = []
    test = base[base.year.eq(2023)].copy()
    models = {
        "uniform": np.repeat(1 / 3, len(test)),
        "proxy_current": test.proxy_gu_share.to_numpy(),
        "carry_forward": test.previous_actual_share.to_numpy(),
        "selected_blend": (selected_alpha * test.previous_actual_share +
                           (1 - selected_alpha) * test.proxy_gu_share).to_numpy(),
    }
    for model, prediction in models.items():
        z = test.assign(predicted_share=prediction)
        for sector, g in z.groupby("sector_code"):
            rows.append({"evaluation_year": 2023, "split": "prospective_holdout", "model": model,
                         "sector_code": sector, "mae_pp": float((g.predicted_share-g.annual_gu_share).abs().mean()*100),
                         "correlation": safe_correlation(g.predicted_share, g.annual_gu_share)})
        rows.append({"evaluation_year": 2023, "split": "prospective_holdout", "model": model,
                     "sector_code": "ALL", "mae_pp": float((z.predicted_share-z.annual_gu_share).abs().mean()*100),
                     "correlation": safe_correlation(z.predicted_share, z.annual_gu_share)})
    return pd.DataFrame(rows), grid, selected_alpha


def rs_mix_weights(actual: pd.DataFrame) -> pd.DataFrame:
    detail = actual[actual.general_gu.ne("합계") & actual.sector_code.isin(["R", "S"])].copy()
    pivot = detail.pivot_table(index=["year", "general_gu", "metric"], columns="sector_code",
                               values="value", aggfunc="sum", fill_value=0).reset_index()
    pivot["r_weight"] = pivot.R / (pivot.R + pivot.S).replace(0, np.nan)
    out = pivot.groupby(["year", "general_gu"], as_index=False).r_weight.mean()
    out.r_weight = out.r_weight.fillna(.5)
    return out


def monthly_gu_allocation(controls: pd.DataFrame, annual_shares: pd.DataFrame,
                          proxy_shares: pd.DataFrame) -> pd.DataFrame:
    proxy_month = proxy_shares.copy()
    rows = []
    for (sector, year), ctl in controls.groupby(["sector_code", "year"], sort=True):
        ctl = ctl.sort_values("month")
        gu = sorted(annual_shares.general_gu.unique())
        target_share = annual_shares[(annual_shares.year.eq(year)) & annual_shares.sector_code.eq(sector)].set_index(
            "general_gu").loc[gu, "annual_gu_share"].to_numpy()
        col_targets = ctl.estimated_monthly_gva.to_numpy()
        row_targets = target_share * col_targets.sum()
        seed_shares = []
        for month in ctl.month:
            p = proxy_month[(proxy_month.year.eq(year)) & proxy_month.month.eq(month) &
                            proxy_month.sector_code.eq(sector)].set_index("general_gu").reindex(gu).proxy_gu_share
            seed_shares.append(p.fillna(1/len(gu)).to_numpy())
        seed = np.asarray(seed_shares).T * col_targets[None, :]
        fitted = ras_biproportional(seed + max(1e-9, col_targets.sum()*1e-12), row_targets, col_targets)
        for gi, general_gu in enumerate(gu):
            for mi, month in enumerate(ctl.month.tolist()):
                rows.append({"year": year, "month": month, "quarter": (month-1)//3+1,
                             "sector_code": sector, "general_gu": general_gu,
                             "estimated_gu_monthly_gva": fitted[gi, mi],
                             "annual_gu_share": target_share[gi]})
    return pd.DataFrame(rows)


def monthly_proxy_gu_shares(proxy: pd.DataFrame) -> pd.DataFrame:
    x = proxy[proxy.period.between("2021-01", "2023-12")].copy()
    x["year"] = x.period.str[:4].astype(int)
    x["month"] = x.period.str[5:7].astype(int)
    rows = []
    for target, spec in TARGETS.items():
        z = x[x.sector_code.isin(spec["proxy"])].groupby(
            ["year", "month", "general_gu"], as_index=False).active_license_stock.sum()
        z["proxy_gu_share"] = (z.active_license_stock + .5) / z.groupby(
            ["year", "month"]).active_license_stock.transform(lambda s: s.sum()+.5*len(s))
        z["sector_code"] = target
        rows.append(z[["year", "month", "general_gu", "sector_code", "proxy_gu_share"]])
    return pd.concat(rows, ignore_index=True)


def emd_monthly_shares(proxy: pd.DataFrame, actual: pd.DataFrame) -> pd.DataFrame:
    x = proxy[proxy.period.between("2021-01", "2023-12")].copy()
    x["year"] = x.period.str[:4].astype(int)
    x["month"] = x.period.str[5:7].astype(int)
    rows = []
    for target in ["I00", "Q00"]:
        z = x[x.sector_code.eq(target)].copy()
        denom = z.groupby(["year", "month", "general_gu"]).active_license_stock.transform(
            lambda s: s.sum() + .5*len(s))
        z["emd_share"] = (z.active_license_stock + .5) / denom
        z["target_sector"] = target
        z["proxy_components"] = target
        rows.append(z)

    rs = x[x.sector_code.isin(["R00", "S00"])].pivot_table(
        index=["year", "month", "period", "general_gu", "emd_code", "emd_name"],
        columns="sector_code", values="active_license_stock", aggfunc="sum", fill_value=0).reset_index()
    mix = rs_mix_weights(actual)
    rs = rs.merge(mix, on=["year", "general_gu"], how="left", validate="many_to_one")
    for c in ["R00", "S00"]:
        rs[f"{c}_share"] = (rs[c] + .5) / rs.groupby(["year", "month", "general_gu"])[c].transform(
            lambda s: s.sum()+.5*len(s))
    rs["emd_share"] = rs.r_weight * rs.R00_share + (1-rs.r_weight) * rs.S00_share
    rs["target_sector"] = "ERS"
    rs["proxy_components"] = "R00+S00"
    rows.append(rs)
    out = pd.concat([r[["year", "month", "period", "general_gu", "emd_code", "emd_name",
                        "emd_share", "target_sector", "proxy_components"]] for r in rows], ignore_index=True)
    return out.rename(columns={"target_sector": "sector_code"})


def build_final(controls: pd.DataFrame, gu_month: pd.DataFrame, emd_share: pd.DataFrame) -> pd.DataFrame:
    out = gu_month.merge(emd_share, on=["year", "month", "general_gu", "sector_code"],
                         how="inner", validate="one_to_many")
    out["estimated_emd_monthly_gva"] = out.estimated_gu_monthly_gva * out.emd_share
    out["sector_name"] = out.sector_code.map({k:v["name"] for k,v in TARGETS.items()})
    out["geography"] = "2026 current 44 administrative-dong boundaries; retrospective allocation"
    out["indicator_source"] = "Phase37 EMD-month LOCALDATA active-license stock"
    out["annual_margin_source"] = "KOSIS Goyang 3-gu x KSIC establishment and employee shares"
    out["monthly_control_source"] = "Phase36 Goyang city x sector monthly constrained allocation"
    out["claim_scope"] = "accounting-consistent EMD monthly GVA allocation estimate; not observed EMD GVA"
    return out.sort_values(["year", "month", "sector_code", "general_gu", "emd_code"]).reset_index(drop=True)


def accounting_checks(final: pd.DataFrame, gu_month: pd.DataFrame, controls: pd.DataFrame,
                      actual_shares: pd.DataFrame) -> pd.DataFrame:
    rows = []
    emd_to_gu = final.groupby(["year","month","sector_code","general_gu"],as_index=False).estimated_emd_monthly_gva.sum().merge(
        gu_month, on=["year","month","sector_code","general_gu"])
    rows.append({"scope":"EMD to gu monthly", "cells":len(emd_to_gu),
                 "max_abs_error":float((emd_to_gu.estimated_emd_monthly_gva-emd_to_gu.estimated_gu_monthly_gva).abs().max())})
    gu_to_city = gu_month.groupby(["year","month","sector_code"],as_index=False).estimated_gu_monthly_gva.sum().merge(
        controls, on=["year","month","sector_code"])
    rows.append({"scope":"gu to city monthly", "cells":len(gu_to_city),
                 "max_abs_error":float((gu_to_city.estimated_gu_monthly_gva-gu_to_city.estimated_monthly_gva).abs().max())})
    annual = gu_month.groupby(["year","sector_code","general_gu"],as_index=False).estimated_gu_monthly_gva.sum()
    annual["share"] = annual.estimated_gu_monthly_gva / annual.groupby(["year","sector_code"]).estimated_gu_monthly_gva.transform("sum")
    annual = annual.merge(actual_shares,on=["year","sector_code","general_gu"])
    rows.append({"scope":"gu annual KOSIS-derived margin", "cells":len(annual),
                 "max_abs_error":float((annual.share-annual.annual_gu_share).abs().max())})
    q = final.groupby(["year","quarter","sector_code"],as_index=False).estimated_emd_monthly_gva.sum()
    qc = controls.groupby(["year","quarter","sector_code"],as_index=False).estimated_monthly_gva.sum()
    q = q.merge(qc,on=["year","quarter","sector_code"])
    rows.append({"scope":"EMD to city quarter", "cells":len(q),
                 "max_abs_error":float((q.estimated_emd_monthly_gva-q.estimated_monthly_gva).abs().max())})
    return pd.DataFrame(rows)


def common_proxy_audit(final: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for key, z in final.groupby(["general_gu", "sector_code", "year"]):
        mat = z.pivot(index="emd_code", columns="month", values="estimated_emd_monthly_gva")
        norm = mat.div(mat.sum(axis=1), axis=0)
        hashes = norm.round(12).astype(str).agg("|".join, axis=1)
        rows.append({"general_gu":key[0], "sector_code":key[1], "year":key[2],
                     "emd_count":len(mat), "effective_rank":int(np.linalg.matrix_rank(norm.to_numpy(),tol=1e-10)),
                     "unique_normalized_profiles":int(hashes.nunique()),
                     "all_emd_profiles_identical":bool(hashes.nunique()==1),
                     "mean_pairwise_correlation":float(norm.T.corr().where(~np.eye(len(norm),dtype=bool)).stack().mean())})
    return pd.DataFrame(rows)


def report(status, holdout, grid, checks, common, sector_decision):
    def md(df):
        x=df.copy()
        for c in x.select_dtypes(include="number"): x[c]=x[c].round(6)
        x=x.fillna("")
        return "\n".join(["| "+" | ".join(x.columns)+" |", "|"+"|".join(["---"]*len(x.columns))+"|",
                          *["| "+" | ".join(map(str,r))+" |" for r in x.itertuples(index=False,name=None)]])
    text=f"""# Phase 38: 고양시 현행 44개 행정동 산업·월 GVA 재배분

## 결론

Phase 38은 Phase 36의 2015년 39개 동 고정배분을 현행 44개 동의 월별 인허가 신호로 교체했다. 결과는 2021~2023년 **44개 동 × 3개 상위 산업 × 36개월 = {status['final_rows']:,}행**이다. 시×산업×월, 구×산업×연, 분기·연간 합계를 동시에 보존한다.

그러나 행정동 GVA actual은 존재하지 않는다. 이 결과는 `행정동 월간 GVA 배분 추정치`이며 공식 통계·관측 GVA가 아니다. 회계 제약 통과는 정확도 증거와 분리한다.

## 실험 설계

1. Phase 36의 고양시×산업×월 총량을 변경하지 않는다.
2. KOSIS 3개 구×산업 사업체·종사자 actual의 평균 비중을 연간 구 마진으로 사용한다.
3. I00·Q00은 동일 산업 인허가 stock, ERS는 R00·S00을 구별 연간 구성비로 결합한다.
4. RAS로 월별 시 총량과 연간 구 마진을 동시에 맞춘 후, 구 내부를 44개 동 월별 프록시로 배분한다.
5. 결합 가중치는 2022년 개발구간에서만 선택하고 2023년 구×산업 actual을 prospective holdout으로 평가한다.

## 2023 Prospective Holdout

선택된 전년도 actual 가중치 α는 **{status['selected_alpha']:.2f}**다. `selected_blend = α×전년도 구 비중 + (1-α)×당해 인허가 비중`이다.

{md(holdout)}

### 가중치 선택 경로

{md(grid)}

holdout은 구 수준 공간갱신의 외삽력을 평가한다. 최종 산출물은 같은 연도 KOSIS 구 마진에 맞추므로 holdout 결과를 최종 행정동 정확도로 오해하면 안 된다.

## 회계 검증

{md(checks)}

## 공통 프록시 재발 검사

{md(common)}

Phase 36의 동일 프로필률은 100%였다. Phase 38의 동일 프로필 그룹률은 **{status['identical_profile_group_rate']:.1%}**다. 산업별·동별 고유 월 신호가 생겼지만, 이것은 actual 정확도 승격이 아니라 상호작용 결손 제거다.

## 산업별 사용 판정

{md(sector_decision)}

## 한계

- 2021~2023 행정동은 2026년 현행 44개 경계로 소급 표현한다.
- LOCALDATA는 전체 사업체나 매출이 아니라 인허가 대상의 영업 상태다.
- Q00과 ERS의 R00 구성은 보조적 근거다. 세부 업종별 수치 발표보다 상위 묶음과 민감도 범위를 사용한다.
- 2024~2026은 상위 GVA 통제가 없어 경제활력 지수로만 제공하고 GVA로 외삽하지 않는다.

## 재현

```bash
.venv/bin/python scripts/run_partial_statistics_phase38_gva.py
.venv/bin/python scripts/verify_partial_statistics_phase38_gva.py
.venv/bin/pytest -q tests/test_partial_statistics_phase38_gva.py
```
"""
    REPORT.write_text(text, encoding="utf-8")


def main() -> dict[str, object]:
    phase36, proxy, actual, emd = load_inputs()
    controls = city_month_controls(phase36)
    annual_shares = actual_gu_shares(actual)
    annual_proxy = proxy_gu_shares(proxy)
    holdout, grid, selected_alpha = prospective_holdout(annual_shares, annual_proxy)
    proxy_month = monthly_proxy_gu_shares(proxy)
    gu_month = monthly_gu_allocation(controls, annual_shares, proxy_month)
    shares = emd_monthly_shares(proxy, actual)
    final = build_final(controls, gu_month, shares)
    checks = accounting_checks(final, gu_month, controls, annual_shares)
    common = common_proxy_audit(final)
    held = holdout[(holdout.model.eq("selected_blend")) & holdout.sector_code.ne("ALL")].copy()
    sector_decision = pd.DataFrame([
        {"sector_code":s, "sector_name":TARGETS[s]["name"], "source_gate":TARGETS[s]["gate"],
         "holdout_mae_pp":float(held.loc[held.sector_code.eq(s),"mae_pp"].iloc[0]),
         "output_decision":"primary_allocation" if s=="I00" else "supplementary_allocation",
         "claim_limit":"no EMD actual; accounting-consistent estimate only"} for s in TARGETS
    ])
    status = {
        "run_id":RUN_ID, "final_rows":len(final), "emd_count":int(final.emd_code.nunique()),
        "sector_count":int(final.sector_code.nunique()), "month_count":int(final[["year","month"]].drop_duplicates().shape[0]),
        "selected_alpha":selected_alpha,
        "holdout_selected_mae_pp":float(holdout[(holdout.model.eq("selected_blend"))&holdout.sector_code.eq("ALL")].mae_pp.iloc[0]),
        "holdout_proxy_mae_pp":float(holdout[(holdout.model.eq("proxy_current"))&holdout.sector_code.eq("ALL")].mae_pp.iloc[0]),
        "holdout_carry_mae_pp":float(holdout[(holdout.model.eq("carry_forward"))&holdout.sector_code.eq("ALL")].mae_pp.iloc[0]),
        "accounting_max_abs_error":float(checks.max_abs_error.max()),
        "identical_profile_group_rate":float(common.all_emd_profiles_identical.mean()),
        "decision":"retain accounting-consistent experimental allocation; block official/observed EMD GVA claim",
        "created_at":CREATED_AT,
    }
    write_csv("partial_stats_phase38_goyang_emd_monthly_gva.csv", final)
    write_csv("partial_stats_phase38_goyang_gu_monthly_gva.csv", gu_month)
    write_csv("partial_stats_phase38_goyang_holdout_validation.csv", holdout)
    write_csv("partial_stats_phase38_goyang_alpha_sensitivity.csv", grid)
    write_csv("partial_stats_phase38_goyang_accounting_checks.csv", checks)
    write_csv("partial_stats_phase38_goyang_common_proxy_audit.csv", common)
    write_csv("partial_stats_phase38_goyang_sector_decision.csv", sector_decision)
    (DATA/"partial_stats_phase38_goyang_status.json").write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding="utf-8")
    report(status, holdout, grid, checks, common, sector_decision)
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return status


if __name__ == "__main__":
    main()
