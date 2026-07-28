from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase197_detail_manufacturing_index_mapping_audit"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase197_detail_manufacturing_index_mapping_audit.md"
RUN_ID = "partial_statistics_estimation_phase197_detail_manufacturing_index_mapping_audit"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


KSIC_MIDDLE = {
    "C10": "식료품 제조업",
    "C11": "음료 제조업",
    "C13": "섬유제품 제조업; 의복제외",
    "C14": "의복 의복 액세서리 및 모피제품 제조업",
    "C15": "가죽 가방 및 신발 제조업",
    "C16": "목재 및 나무제품 제조업; 가구 제외",
    "C17": "펄프 종이 및 종이제품 제조업",
    "C18": "인쇄 및 기록매체 복제업",
    "C19": "코크스 연탄 및 석유정제품 제조업",
    "C20": "화학물질 및 화학제품 제조업; 의약품 제외",
    "C21": "의료용 물질 및 의약품 제조업",
    "C22": "고무 및 플라스틱제품 제조업",
    "C23": "비금속 광물제품 제조업",
    "C24": "1차 금속 제조업",
    "C25": "금속가공제품 제조업; 기계 및 가구 제외",
    "C26": "전자부품 컴퓨터 영상 음향 및 통신장비 제조업",
    "C27": "의료 정밀 광학기기 및 시계 제조업",
    "C28": "전기장비 제조업",
    "C29": "기타 기계 및 장비 제조업",
    "C30": "자동차 및 트레일러 제조업",
    "C31": "기타 운송장비 제조업",
    "C32": "가구 제조업",
    "C33": "기타 제품 제조업",
    "C34": "산업용 기계 및 장비 수리업",
}


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


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
        return "_해당 없음_"
    view = df.copy()
    for col in view.columns:
        view[col] = view[col].map(lambda x: "" if pd.isna(x) else str(x))
    lines = ["| " + " | ".join(view.columns) + " |", "| " + " | ".join(["---"] * len(view.columns)) + " |"]
    for row in view.itertuples(index=False):
        lines.append("| " + " | ".join(str(v).replace("|", "/") for v in row) + " |")
    return "\n".join(lines)


def main() -> int:
    detail_path = DATA / "phase195_monthly_detail_manufacturing_production_index.csv"
    if not detail_path.exists():
        raise FileNotFoundError("Run Phase195 first: " + str(detail_path.relative_to(ROOT)))
    detail = pd.read_csv(detail_path, encoding="utf-8-sig")
    codes = detail[["c1_id", "c1_nm"]].drop_duplicates().sort_values(["c1_nm", "c1_id"]).reset_index(drop=True)
    codes["period_count"] = codes["c1_id"].map(detail.groupby("c1_id")["prd_de"].nunique())
    codes["period_min"] = codes["c1_id"].map(detail.groupby("c1_id")["prd_de"].min())
    codes["period_max"] = codes["c1_id"].map(detail.groupby("c1_id")["prd_de"].max())

    # Conservative mapping: only ICT-related detailed labels can be interpreted as a partial C26 signal.
    rows = []
    available_names = set(codes["c1_nm"])
    for code, name in KSIC_MIDDLE.items():
        if code == "C26":
            matched = sorted(available_names & {"사무회계·통신기기·반도체", "영상음향", "반도체 및 부품"})
            rows.append(
                {
                    "ksic_middle_code": code,
                    "ksic_middle_name": name,
                    "usable_detail_index": "partial",
                    "matched_index_names": ", ".join(matched),
                    "safe_use": "C26 내부 ICT 계열 월별 시간경로 보정 후보",
                    "unsafe_use": "C26 전체 금액 또는 타 중분류 대체지표로 사용 금지",
                }
            )
        else:
            rows.append(
                {
                    "ksic_middle_code": code,
                    "ksic_middle_name": name,
                    "usable_detail_index": "none",
                    "matched_index_names": "",
                    "safe_use": "시도 제조업 총지수 또는 직접 활동자료 필요",
                    "unsafe_use": "DT_1F02011 제한항목을 해당 중분류의 직접 생산지수처럼 사용 금지",
                }
            )
    mapping = pd.DataFrame(rows)
    summary = pd.DataFrame(
        [
            {
                "check": "DT_1F02011 local monthly rows",
                "value": len(detail),
            },
            {
                "check": "DT_1F02011 unique code count",
                "value": codes["c1_id"].nunique(),
            },
            {
                "check": "DT_1F02011 unique display name count",
                "value": codes["c1_nm"].nunique(),
            },
            {
                "check": "KSIC middle divisions in target manufacturing actuals",
                "value": len(KSIC_MIDDLE),
            },
            {
                "check": "KSIC middle divisions with safe direct detail index",
                "value": int(mapping["usable_detail_index"].eq("partial").sum()),
            },
        ]
    )

    write_csv("phase197_detail_index_codes.csv", codes)
    write_csv("phase197_ksic_middle_mapping_audit.csv", mapping)
    write_csv("phase197_summary.csv", summary)

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        f"""# Phase197 월간 세부 제조업 생산지수 KSIC 중분류 매핑 감사

## 목적

Phase195에서 수집한 `DT_1F02011 기본분류 일부항목 제외 광공업생산지수`를 KSIC 제조업 중분류 개선에 직접 사용할 수 있는지 점검했다.

## 핵심 결론

이 자료는 월간 자료이므로 시간 해상도 측면에서는 가치가 있다. 그러나 로컬 수집 결과의 항목명은 `총지수`, `광업 및 제조업`, `제조업`, `사무회계·통신기기·반도체`, `영상음향`, `반도체 및 부품` 등 제한 항목으로 구성된다. 대상 제조업 중분류 C10~C34 전체를 직접 덮지 못한다.

따라서 안전한 사용 범위는 다음으로 제한한다.

- C00 제조업 전체 월 경로: `DT_1F02001 시도×제조업 월간 생산지수` 사용
- C26 전자부품·컴퓨터·영상·음향·통신장비 제조업: `DT_1F02011`의 ICT/반도체 관련 항목을 **부분 시간경로 후보**로 사용 가능
- C10~C25, C27~C34: 직접 생산지수로 쓰면 안 되며, KICOX 공장 생산품·면적·종업원, 항만 품목 물동량, 산업용 전력 중분류 매핑 등 별도 활동자료가 필요

## 요약

{md_table(summary.rename(columns={"check": "검증", "value": "값"}))}

## DT_1F02011 코드·이름 목록

{md_table(codes.rename(columns={
    "c1_id": "KOSIS코드",
    "c1_nm": "항목명",
    "period_count": "시점수",
    "period_min": "시작",
    "period_max": "종료",
}))}

## KSIC 중분류별 사용 판정

{md_table(mapping.rename(columns={
    "ksic_middle_code": "KSIC중분류",
    "ksic_middle_name": "업종명",
    "usable_detail_index": "세부지수 사용성",
    "matched_index_names": "매칭 항목",
    "safe_use": "안전한 사용",
    "unsafe_use": "금지 사용",
}))}
""",
        encoding="utf-8",
    )
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
