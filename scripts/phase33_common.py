from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from kosis_common import CSV_ENCODING, ROOT, cp949_safe


DERIVED_DIR = ROOT / "data" / "derived"
PROCESSED_DIR = ROOT / "data" / "processed"
RAW_DIR = ROOT / "data" / "raw"
REPORT_DIR = ROOT / "reports"
RUN_ID = "partial_statistics_estimation_phase33_final"
GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
SEED = 20260720
MIN_RANK_N = 5
GRADE_ORDER = {"O": 6, "A": 5, "B": 4, "C": 3, "D": 2, "E": 1, "U": 0}


def git_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return ""


CODE_COMMIT_HASH = git_hash()


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def read_table(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return read_csv(path)


def num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def safe_div(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    den = denominator.replace(0, np.nan)
    return numerator / den


def add_audit(frame: pd.DataFrame, include_hash: bool = True) -> pd.DataFrame:
    out = frame.copy()
    if include_hash:
        base = [c for c in out.columns if c not in {"input_hash", "code_commit_hash", "run_id", "created_at"}]
        out["input_hash"] = stable_hash(out[base].head(20000).to_dict("records")) if len(out) else ""
    out["code_commit_hash"] = CODE_COMMIT_HASH
    out["run_id"] = RUN_ID
    out["created_at"] = GENERATED_AT
    return out


def write_csv(name: str, frame: pd.DataFrame) -> Path:
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    path = DERIVED_DIR / name
    out = frame.copy()
    for column in out.columns:
        if out[column].dtype == object:
            out[column] = out[column].map(cp949_safe)
    out.to_csv(path, index=False, encoding=CSV_ENCODING, errors="replace")
    return path


def write_json(name: str, payload: dict[str, Any]) -> Path:
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    path = DERIVED_DIR / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def markdown_table(frame: pd.DataFrame, max_rows: int = 20) -> str:
    if frame is None or frame.empty:
        return "_No rows_"
    subset = frame.head(max_rows).copy()
    subset = subset.astype(str).replace({"nan": "", "NaN": "", "None": "", "<NA>": ""})
    columns = list(subset.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in subset.to_dict("records"):
        values = [str(row[col]).replace("|", "/").replace("\n", " ") for col in columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_report(name: str, title: str, sections: Iterable[tuple[str, str]]) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", ""]
    for index, (heading, body) in enumerate(sections, start=1):
        lines.extend([f"## {index}. {heading}", "", body, ""])
    path = REPORT_DIR / name
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def weakest_grade(grades: Iterable[str]) -> str:
    values = [grade for grade in grades if grade in GRADE_ORDER]
    if not values:
        return "U"
    return min(values, key=lambda grade: GRADE_ORDER[grade])


def runtime_manifest() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "locale_policy": "CSV=cp949; markdown/json=utf-8",
        "timezone": str(datetime.now().astimezone().tzinfo),
        "random_seed": SEED,
        "code_commit_hash": CODE_COMMIT_HASH,
        "generated_at": GENERATED_AT,
    }


def require_columns(frame: pd.DataFrame, columns: Iterable[str], label: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{label} missing columns: {missing}")


def assert_unique(frame: pd.DataFrame, keys: list[str], label: str) -> None:
    require_columns(frame, keys, label)
    duplicate_count = int(frame.duplicated(keys).sum())
    if duplicate_count:
        raise ValueError(f"{label} duplicate key count={duplicate_count}, keys={keys}")
