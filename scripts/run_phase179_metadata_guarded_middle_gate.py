#!/usr/bin/env python3
"""Phase179: metadata-guarded middle gate.

Phase178 showed that middle-only external routing is too aggressive.  Most
worsening happened when rows already marked as operational/accurate were
overwritten.  This phase starts from Phase177 and only adds middle-only routes
for rows whose pre-existing metadata says they still need improvement.

Route decision does not use Goyang/Pohang actual values:
* source route: Phase177 baseline;
* add Phase178 middle-only peer prediction only for rows with
  public_claim_track == "추가개선 필요",
  operational_track == "운영 개선 필요",
  phase92_queue in {"주의", "취약"},
  and the middle external gate passed.

Target actual is used only for audit.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"
OUT = DATA / "phase179_metadata_guarded_middle_gate"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase179_metadata_guarded_middle_gate.md"

PHASE124 = DATA / "phase124_pps_subblock_no_worse/phase124_registry.csv"
PHASE177 = DATA / "phase177_middle_safe_peer_port_gate/phase177_middle_safe_peer_port_registry.csv"
PHASE178 = DATA / "phase178_middle_only_gate_diagnostic/phase178_middle_only_gate_registry.csv"


def md_table(df: pd.DataFrame, digits: int = 2, max_rows: int | None = None) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    if max_rows is not None and len(view) > max_rows:
        view = view.head(max_rows).copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
    view = view.fillna("").astype(str)
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join(["---"] * len(view.columns)) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(row[c].replace("|", "\\|") for c in view.columns) + " |")
    if max_rows is not None and len(df) > max_rows:
        lines.append(f"\n_상위 {max_rows}개 표시, 전체 {len(df):,}개는 CSV 참조_")
    return "\n".join(lines)


def summarize(df: pd.DataFrame, pred: str, err: str, rate: str, label: str) -> pd.DataFrame:
    rows = []
    for city, g in df.groupby("city", sort=False):
        actual = float(g["actual_gva_eok"].sum())
        error = float(g[err].sum())
        rows.append(
            {
                "candidate": label,
                "city": city,
                "actual_sum_eok": actual,
                "error_sum_eok": error,
                "wape_pct": error / actual * 100,
                "gt10_cells": int((g[rate] > 10).sum()),
                "gt20_cells": int((g[rate] > 20).sum()),
                "gt50_cells": int((g[rate] > 50).sum()),
            }
        )
    actual = float(df["actual_gva_eok"].sum())
    error = float(df[err].sum())
    rows.append(
        {
            "candidate": label,
            "city": "합계",
            "actual_sum_eok": actual,
            "error_sum_eok": error,
            "wape_pct": error / actual * 100,
            "gt10_cells": int((df[rate] > 10).sum()),
            "gt20_cells": int((df[rate] > 20).sum()),
            "gt50_cells": int((df[rate] > 50).sum()),
        }
    )
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p124 = pd.read_csv(PHASE124)
    p177 = pd.read_csv(PHASE177)
    p178 = pd.read_csv(PHASE178)
    key = ["city", "parent_code", "middle_code"]

    reg = p177.copy()
    reg["phase179_predicted_gva_eok"] = reg["phase177_predicted_gva_eok"].astype(float)
    reg["phase179_route"] = reg["phase177_route"]

    extra = p178[key + ["phase178_predicted_gva_eok", "phase178_route"]].copy()
    joined = reg[key + ["public_claim_track", "operational_track", "phase92_queue", "phase177_route"]].merge(extra, on=key, how="left")
    extra_ok = (
        joined["phase177_route"].eq("기준 유지")
        & joined["phase178_route"].eq("외부검증 통과 중분류 독립 peer 배분")
        & joined["public_claim_track"].eq("추가개선 필요")
        & joined["operational_track"].eq("운영 개선 필요")
        & joined["phase92_queue"].isin(["주의", "취약"])
    )
    reg.loc[extra_ok.values, "phase179_predicted_gva_eok"] = joined.loc[extra_ok, "phase178_predicted_gva_eok"].to_numpy()
    reg.loc[extra_ok.values, "phase179_route"] = "메타게이트 통과 중분류 독립 peer 배분"

    reg["phase179_error_gva_eok"] = (reg["phase179_predicted_gva_eok"] - reg["actual_gva_eok"]).abs()
    reg["phase179_error_rate_pct"] = reg["phase179_error_gva_eok"] / reg["actual_gva_eok"].abs() * 100
    reg["phase179_delta_vs_phase124_eok"] = reg["phase179_error_gva_eok"] - reg["phase124_error_gva_eok"]
    reg["phase179_delta_vs_phase177_eok"] = reg["phase179_error_gva_eok"] - reg["phase177_error_gva_eok"]
    reg["phase179_worsened_vs_phase124"] = reg["phase179_delta_vs_phase124_eok"] > 1e-8
    reg["phase179_worsened_vs_phase177"] = reg["phase179_delta_vs_phase177_eok"] > 1e-8

    base = p124.copy()
    base["phase124_error_rate_pct"] = base["phase124_error_gva_eok"] / base["actual_gva_eok"].abs() * 100
    summ = pd.concat(
        [
            summarize(base, "phase124_predicted_gva_eok", "phase124_error_gva_eok", "phase124_error_rate_pct", "Phase124 기준선"),
            summarize(p177, "phase177_predicted_gva_eok", "phase177_error_gva_eok", "phase177_error_rate_pct", "Phase177 중분류 안전 게이트"),
            summarize(reg, "phase179_predicted_gva_eok", "phase179_error_gva_eok", "phase179_error_rate_pct", "Phase179 메타게이트"),
        ],
        ignore_index=True,
    )
    parent = (
        reg.groupby(["city", "parent_code"], as_index=False)
        .agg(
            actual_sum_eok=("actual_gva_eok", "sum"),
            phase124_error_eok=("phase124_error_gva_eok", "sum"),
            phase177_error_eok=("phase177_error_gva_eok", "sum"),
            phase179_error_eok=("phase179_error_gva_eok", "sum"),
            worsened_vs_177_cells=("phase179_worsened_vs_phase177", "sum"),
            worsened_vs_124_cells=("phase179_worsened_vs_phase124", "sum"),
            gt20_cells=("phase179_error_rate_pct", lambda s: int((s > 20).sum())),
            routes=("phase179_route", lambda s: ", ".join(sorted(set(s)))),
        )
    )
    parent["phase124_wape_pct"] = parent["phase124_error_eok"] / parent["actual_sum_eok"] * 100
    parent["phase177_wape_pct"] = parent["phase177_error_eok"] / parent["actual_sum_eok"] * 100
    parent["phase179_wape_pct"] = parent["phase179_error_eok"] / parent["actual_sum_eok"] * 100
    parent["phase179_reduction_vs_177_eok"] = parent["phase177_error_eok"] - parent["phase179_error_eok"]
    parent = parent.sort_values(["city", "phase179_reduction_vs_177_eok"], ascending=[True, False])

    applied = reg[reg["phase179_route"].eq("메타게이트 통과 중분류 독립 peer 배분")].copy().sort_values("phase179_delta_vs_phase177_eok")
    worsened177 = reg[reg["phase179_worsened_vs_phase177"]].copy().sort_values("phase179_delta_vs_phase177_eok", ascending=False)
    worsened124 = reg[reg["phase179_worsened_vs_phase124"]].copy().sort_values("phase179_delta_vs_phase124_eok", ascending=False)
    residual = reg[reg["phase179_error_rate_pct"] > 20].copy().sort_values("phase179_error_gva_eok", ascending=False)

    reg.to_csv(OUT / "phase179_metadata_guarded_registry.csv", index=False, encoding="utf-8-sig")
    summ.to_csv(OUT / "phase179_summary.csv", index=False, encoding="utf-8-sig")
    parent.to_csv(OUT / "phase179_parent_audit.csv", index=False, encoding="utf-8-sig")
    applied.to_csv(OUT / "phase179_applied_cells.csv", index=False, encoding="utf-8-sig")
    worsened177.to_csv(OUT / "phase179_worsened_vs_phase177_cells.csv", index=False, encoding="utf-8-sig")
    worsened124.to_csv(OUT / "phase179_worsened_vs_phase124_cells.csv", index=False, encoding="utf-8-sig")
    residual.to_csv(OUT / "phase179_residual_gt20.csv", index=False, encoding="utf-8-sig")
    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "phase": "phase179_metadata_guarded_middle_gate",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "target_actual_use": "audit only",
                "decision_rule": {
                    "base": "Phase177",
                    "additional_route": {
                        "phase177_route": "기준 유지",
                        "phase178_route": "외부검증 통과 중분류 독립 peer 배분",
                        "public_claim_track": "추가개선 필요",
                        "operational_track": "운영 개선 필요",
                        "phase92_queue": ["주의", "취약"],
                    },
                },
                "outputs": {
                    "applied_cells": len(applied),
                    "worsened_vs_phase177_cells": len(worsened177),
                    "worsened_vs_phase124_cells": len(worsened124),
                    "residual_gt20_cells": len(residual),
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    REPORT.write_text(
        f"""# Phase179 메타게이트 보강 중분류 실험

## 목적

Phase178은 외부 중분류 검증만 믿고 독립 적용하면 원래 잘 맞던 업종까지 흔들린다는 점을 확인했다. 이번 단계는 Phase177을 기본값으로 두고, 기존 메타판정이 `추가개선 필요 / 운영 개선 필요 / 주의·취약`인 셀에만 중분류 독립 peer 배분을 추가한다.

고양·포항 actual은 적용 판단에 쓰지 않고 사후감사에만 사용한다.

## 전체 성능

{md_table(summ[["candidate","city","actual_sum_eok","error_sum_eok","wape_pct","gt10_cells","gt20_cells","gt50_cells"]], 2)}

## 상위산업별 감사

{md_table(parent[["city","parent_code","routes","actual_sum_eok","phase124_error_eok","phase177_error_eok","phase179_error_eok","phase124_wape_pct","phase177_wape_pct","phase179_wape_pct","phase179_reduction_vs_177_eok","worsened_vs_177_cells","worsened_vs_124_cells","gt20_cells"]].head(20), 2)}

## 추가 적용 셀

{md_table(applied[["city","parent_code","middle_code","middle_label","phase92_queue","public_claim_track","operational_track","actual_gva_eok","phase177_error_gva_eok","phase179_error_gva_eok","phase179_error_rate_pct","phase179_delta_vs_phase177_eok"]].rename(columns={
    "city":"도시",
    "parent_code":"상위산업",
    "middle_code":"중분류",
    "middle_label":"업종명",
    "phase92_queue":"기존 판정",
    "public_claim_track":"공개 주장 트랙",
    "operational_track":"운영 트랙",
    "actual_gva_eok":"실제 GVA(억원)",
    "phase177_error_gva_eok":"Phase177 오차(억원)",
    "phase179_error_gva_eok":"Phase179 오차(억원)",
    "phase179_error_rate_pct":"Phase179 오차율(%)",
    "phase179_delta_vs_phase177_eok":"오차 증감(억원)",
}), 2, 30)}

## Phase177 대비 악화 셀

{md_table(worsened177[["city","parent_code","middle_code","middle_label","phase92_queue","actual_gva_eok","phase177_error_gva_eok","phase179_error_gva_eok","phase179_error_rate_pct","phase179_delta_vs_phase177_eok"]].rename(columns={
    "city":"도시",
    "parent_code":"상위산업",
    "middle_code":"중분류",
    "middle_label":"업종명",
    "phase92_queue":"기존 판정",
    "actual_gva_eok":"실제 GVA(억원)",
    "phase177_error_gva_eok":"Phase177 오차(억원)",
    "phase179_error_gva_eok":"Phase179 오차(억원)",
    "phase179_error_rate_pct":"Phase179 오차율(%)",
    "phase179_delta_vs_phase177_eok":"오차 증가(억원)",
}), 2, 30)}

## 남은 20% 초과 셀

{md_table(residual[["city","parent_code","middle_code","middle_label","actual_gva_eok","phase179_predicted_gva_eok","phase179_error_gva_eok","phase179_error_rate_pct","phase179_route"]].head(30).rename(columns={
    "city":"도시",
    "parent_code":"상위산업",
    "middle_code":"중분류",
    "middle_label":"업종명",
    "actual_gva_eok":"실제 GVA(억원)",
    "phase179_predicted_gva_eok":"추정 GVA(억원)",
    "phase179_error_gva_eok":"오차(억원)",
    "phase179_error_rate_pct":"오차율(%)",
    "phase179_route":"적용 경로",
}), 2, 30)}

## 판정

1. Phase179는 Phase178의 과적용 문제를 줄이기 위해 기존 메타판정을 안전장치로 사용했다.
2. Phase177보다 전체 오차가 낮아지고 악화 셀이 없거나 작으면 운영 후보로 승격 가능하다.
3. 악화 셀이 의미 있게 남으면 Phase177을 운영 기준으로 유지하고, Phase179는 진단 후보로만 둔다.
4. 남은 20% 초과 셀은 peer 구조가 아니라 조달·금융·폐기물·콘텐츠·제조 세부 활동자료가 필요하다.
""",
        encoding="utf-8",
    )
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
