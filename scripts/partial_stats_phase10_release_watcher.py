from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT, load_env, write_json


TABLE_ID = "101/DT_1FS1101"
LOG_PATH = PROCESSED_DIR / "partial_stats_phase10_release_probe_log.csv"
FIRST_SEEN_PATH = PROCESSED_DIR / "partial_stats_phase10_release_first_seen.csv"
HASH_PATH = PROCESSED_DIR / "partial_stats_phase10_release_response_hashes.csv"
STATUS_PATH = PROCESSED_DIR / "partial_stats_phase10_release_watcher_status.json"


def now_pair() -> tuple[str, str]:
    utc = datetime.now(timezone.utc)
    kst = utc.astimezone().isoformat(timespec="seconds")
    return utc.isoformat(timespec="seconds"), kst


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, encoding=CSV_ENCODING, dtype=str, keep_default_na=False)


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding=CSV_ENCODING, errors="replace")


def mask_key(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return value[:4] + "***" + value[-4:]


def local_metadata_snapshot() -> dict[str, Any]:
    manifest = PROCESSED_DIR / "partial_stats_phase9_raw_source_manifest.csv"
    periods: list[str] = []
    if manifest.exists():
        df = pd.read_csv(manifest, encoding=CSV_ENCODING, dtype=str, keep_default_na=False)
        for col in ["min_reference_year", "max_reference_year"]:
            if col in df:
                periods.extend(df[col].dropna().astype(str).tolist())
    periods = sorted({p for p in periods if p})
    latest = max(periods) if periods else ""
    return {
        "org_id": "101",
        "table_id": "DT_1FS1101",
        "metadata_source": "local_phase9_manifest_no_target_value_request",
        "periods_detected": periods,
        "latest_period": latest,
    }


def record_probe(mode: str) -> dict[str, Any]:
    utc, kst = now_pair()
    env = load_env()
    masked = mask_key(env.get("KOSIS_API_KEY", "") or env.get("KOSIS_KEY", ""))
    snapshot = local_metadata_snapshot()
    body = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
    response_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    probe_id = hashlib.sha256(f"{TABLE_ID}|{utc}|{response_hash}|{mode}".encode("utf-8")).hexdigest()[:16]
    sanitized_request = {
        "endpoint": "local_metadata_snapshot",
        "table_id": TABLE_ID,
        "api_key": masked,
        "target_values_requested": False,
    }
    row = {
        "probe_id": probe_id,
        "probe_time_utc": utc,
        "probe_time_kst": kst,
        "endpoint": "local_metadata_snapshot",
        "sanitized_request": json.dumps(sanitized_request, ensure_ascii=False, sort_keys=True),
        "response_status": "local_metadata_recorded",
        "response_headers": "{}",
        "periods_detected": ",".join(snapshot["periods_detected"]),
        "latest_period": snapshot["latest_period"],
        "response_hash": response_hash,
        "mode": mode,
        "api_key_persisted": "N",
        "target_values_requested": "N",
    }
    log = read_csv(LOG_PATH)
    log = pd.concat([log, pd.DataFrame([row])], ignore_index=True)
    log = log.drop_duplicates(["response_hash", "mode"], keep="first")
    write_csv(LOG_PATH, log)
    hashes = read_csv(HASH_PATH)
    hashes = pd.concat(
        [
            hashes,
            pd.DataFrame(
                [
                    {
                        "response_hash": response_hash,
                        "first_probe_id": probe_id,
                        "first_seen_at_utc": utc,
                        "latest_period": snapshot["latest_period"],
                        "deduplication_status": "stored_once",
                    }
                ]
            ),
        ],
        ignore_index=True,
    ).drop_duplicates(["response_hash"], keep="first")
    write_csv(HASH_PATH, hashes)
    first = read_csv(FIRST_SEEN_PATH)
    candidate = str(int(snapshot["latest_period"]) + 1) if snapshot["latest_period"].isdigit() else ""
    if first.empty:
        first = pd.DataFrame(
            [
                {
                    "candidate_target_period": candidate,
                    "first_observed_available_at": "",
                    "first_observed_probe_id": "",
                    "first_observed_response_hash": "",
                    "availability_status": "not_detected",
                }
            ]
        )
        write_csv(FIRST_SEEN_PATH, first)
    write_json(
        STATUS_PATH,
        {
            "watcher_status": "metadata_probe_ready",
            "last_probe_id": probe_id,
            "last_probe_time_utc": utc,
            "latest_period_detected": snapshot["latest_period"],
            "candidate_target_period": candidate,
            "first_seen_status": first.iloc[0].to_dict() if not first.empty else {},
            "target_values_requested": False,
            "api_key_persisted": False,
        },
    )
    return {"probe": row, "status": json.loads(STATUS_PATH.read_text(encoding="utf-8"))}


def status() -> dict[str, Any]:
    if STATUS_PATH.exists():
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    return {
        "watcher_status": "not_started",
        "target_values_requested": False,
        "api_key_persisted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 10 metadata-only release watcher")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--record-metadata", action="store_true")
    parser.add_argument("--capture-new-vintage", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    if args.status:
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    if args.capture_new_vintage:
        result = record_probe("capture-new-vintage")
        result["status"]["capture_status"] = "not_detected_or_not_captured_metadata_only"
        write_json(STATUS_PATH, result["status"])
        print(json.dumps(result["status"], ensure_ascii=False, indent=2))
        return 0
    mode = "record-metadata" if args.record_metadata else "check-only"
    result = record_probe(mode)
    print(json.dumps(result["status"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
