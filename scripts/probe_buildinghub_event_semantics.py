from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from kosis_common import PROCESSED_DIR, RAW_DIR, write_csv, write_json
from probe_buildinghub_readiness import (
    response_items,
    response_status,
    request_json as request_buildinghub_json,
)
from build_buildinghub_preml_readiness import data_go_key


EVENT_FIELDS = {
    "permit": "archPmsDay",
    "start": "realStcnsDay",
    "approval": "useAprDay",
}
DATE_FIELD_HINTS = ("day", "date", "dt", "de", "ymd")
WINDOW_TYPES = ("exact_day", "month_window", "previous_month", "next_month", "plus_minus_1_day")
TARGET_ROWS = 50
ROWS_PER_PATTERN = 10
PAGE_SIZE = 100


def valid_date(value: Any) -> str:
    text = str(value or "").strip()
    return text if re.fullmatch(r"\d{8}", text) else ""


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y%m%d")


def date_windows(event_date: str) -> dict[str, tuple[str, str]]:
    day = parse_date(event_date)
    first = day.replace(day=1)
    if first.month == 12:
        next_first = first.replace(year=first.year + 1, month=1)
    else:
        next_first = first.replace(month=first.month + 1)
    prev_last = first - timedelta(days=1)
    prev_first = prev_last.replace(day=1)
    next_first_2 = next_first.replace(year=next_first.year + 1, month=1) if next_first.month == 12 else next_first.replace(month=next_first.month + 1)
    return {
        "exact_day": (event_date, event_date),
        "month_window": (first.strftime("%Y%m%d"), (next_first - timedelta(days=1)).strftime("%Y%m%d")),
        "previous_month": (prev_first.strftime("%Y%m%d"), prev_last.strftime("%Y%m%d")),
        "next_month": (next_first.strftime("%Y%m%d"), (next_first_2 - timedelta(days=1)).strftime("%Y%m%d")),
        "plus_minus_1_day": ((day - timedelta(days=1)).strftime("%Y%m%d"), (day + timedelta(days=1)).strftime("%Y%m%d")),
    }


def in_window(value: Any, start: str, end: str) -> bool:
    date = valid_date(value)
    return bool(date and start <= date <= end)


def latest_vintage_dir() -> Path:
    dirs = sorted((RAW_DIR / "buildinghub").glob("vintage_*"))
    if not dirs:
        raise SystemExit("No buildinghub vintage cache found. Run build_buildinghub_preml_readiness.py first.")
    return dirs[-1]


def historical_sample_items() -> list[dict[str, Any]]:
    samples: dict[str, dict[str, Any]] = {}
    for path in sorted(latest_vintage_dir().glob("hist_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for item in response_items(payload):
            key = str(item.get("mgmPmsrgstPk") or json.dumps(item, ensure_ascii=False, sort_keys=True))
            samples[key] = item
    return list(samples.values())


def row_patterns(row: dict[str, Any]) -> set[str]:
    flags = {event: bool(valid_date(row.get(field))) for event, field in EVENT_FIELDS.items()}
    patterns = set()
    if flags["permit"] and not flags["start"] and not flags["approval"]:
        patterns.add("permit_date_only_available")
    if flags["start"] and not flags["permit"] and not flags["approval"]:
        patterns.add("start_date_only_available")
    if flags["approval"] and not flags["permit"] and not flags["start"]:
        patterns.add("approval_date_only_available")
    if all(flags.values()):
        patterns.add("all_three_dates_available")
    dates = [valid_date(row.get(field)) for field in EVENT_FIELDS.values()]
    dates = [date for date in dates if date]
    if len({date[:6] for date in dates}) > 1:
        patterns.add("dates_in_different_months")
    if len({date[:4] for date in dates}) > 1:
        patterns.add("dates_in_different_years")
    return patterns


def sort_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("sigunguCd") or ""),
        str(row.get("bjdongCd") or ""),
        str(row.get("mgmPmsrgstPk") or ""),
    )


def select_target_rows(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wanted = (
        "permit_date_only_available",
        "start_date_only_available",
        "approval_date_only_available",
        "all_three_dates_available",
        "dates_in_different_months",
        "dates_in_different_years",
    )
    selected: dict[str, dict[str, Any]] = {}
    counts = Counter()
    for pattern in wanted:
        for row in sorted(samples, key=sort_key):
            key = str(row.get("mgmPmsrgstPk") or sort_key(row))
            if key in selected:
                continue
            if pattern in row_patterns(row):
                selected[key] = row
                counts[pattern] += 1
            if counts[pattern] >= ROWS_PER_PATTERN:
                break
    for row in sorted(samples, key=sort_key):
        if len(selected) >= TARGET_ROWS:
            break
        key = str(row.get("mgmPmsrgstPk") or sort_key(row))
        if key not in selected:
            selected[key] = row
    return list(selected.values())[:TARGET_ROWS]


def target_event_rows(target_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for idx, row in enumerate(target_rows, start=1):
        patterns = sorted(row_patterns(row))
        for event_type, field in EVENT_FIELDS.items():
            date = valid_date(row.get(field))
            if not date:
                continue
            rows.append(
                {
                    "target_row_id": idx,
                    "target_event_id": f"{idx}_{event_type}_{date}",
                    "event_type": event_type,
                    "event_field": field,
                    "event_date": date,
                    "sigungu_cd": str(row.get("sigunguCd") or "").strip(),
                    "bjdong_cd": str(row.get("bjdongCd") or "").strip(),
                    "permit_register_pk": str(row.get("mgmPmsrgstPk") or "").strip(),
                    "building_register_pk": str(row.get("mgmBldrgstPk") or "").strip(),
                    "patterns": "|".join(patterns),
                    "permit_date": valid_date(row.get("archPmsDay")),
                    "start_date": valid_date(row.get("realStcnsDay")),
                    "approval_date": valid_date(row.get("useAprDay")),
                    "main_purpose_code": str(row.get("mainPurpsCd") or "").strip(),
                    "main_purpose_name": str(row.get("mainPurpsCdNm") or "").strip(),
                }
            )
    return rows


def same_event(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_pk = str(left.get("mgmPmsrgstPk") or "").strip()
    right_pk = str(right.get("permit_register_pk") or "").strip()
    if left_pk and right_pk and left_pk == right_pk:
        return True
    return (
        str(left.get("sigunguCd") or "").strip() == right.get("sigungu_cd")
        and str(left.get("bjdongCd") or "").strip() == right.get("bjdong_cd")
        and valid_date(left.get("archPmsDay")) == right.get("permit_date")
        and valid_date(left.get("realStcnsDay")) == right.get("start_date")
        and valid_date(left.get("useAprDay")) == right.get("approval_date")
    )


def known_date_flags(row: dict[str, Any], start: str, end: str) -> dict[str, bool]:
    return {
        "permit_in_request_window": in_window(row.get("archPmsDay"), start, end),
        "start_in_request_window": in_window(row.get("realStcnsDay"), start, end),
        "approval_in_request_window": in_window(row.get("useAprDay"), start, end),
    }


def match_class(flags: dict[str, bool]) -> str:
    matched = [name for name, flag in flags.items() if flag]
    if len(matched) == 1:
        return matched[0].replace("_in_request_window", "_filter_match")
    if len(matched) > 1:
        return "multiple_event_match"
    return "unknown_filter_match"


def probe_event_semantics(event_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    key = data_go_key()
    manifest: list[dict[str, Any]] = []
    probe_rows = []
    match_rows = []
    for target in event_rows:
        for window_type, (start, end) in date_windows(target["event_date"]).items():
            params = {
                "serviceKey": key,
                "_type": "json",
                "pageNo": 1,
                "numOfRows": PAGE_SIZE,
                "sigunguCd": target["sigungu_cd"],
                "bjdongCd": target["bjdong_cd"],
                "startDate": start,
                "endDate": end,
            }
            request_id = f"d1_{target['target_event_id']}_{window_type}"
            payload = request_buildinghub_json(params, request_id, manifest)
            data = payload.get("data", {})
            body = data.get("response", {}).get("body", {}) if isinstance(data, dict) else {}
            items = response_items(payload)
            total_count = body.get("totalCount", "") if isinstance(body, dict) else ""
            returned_target = any(same_event(item, target) for item in items)
            target_flags = known_date_flags(
                {
                    "archPmsDay": target["permit_date"],
                    "realStcnsDay": target["start_date"],
                    "useAprDay": target["approval_date"],
                },
                start,
                end,
            )
            observed_classes = Counter()
            for item in items:
                flags = known_date_flags(item, start, end)
                observed_class = match_class(flags)
                observed_classes[observed_class] += 1
                match_rows.append(
                    {
                        "target_event_id": target["target_event_id"],
                        "query_event_type": target["event_type"],
                        "window_type": window_type,
                        "window_start": start,
                        "window_end": end,
                        "returned_permit_register_pk": str(item.get("mgmPmsrgstPk") or "").strip(),
                        "returned_sigungu_cd": str(item.get("sigunguCd") or "").strip(),
                        "returned_bjdong_cd": str(item.get("bjdongCd") or "").strip(),
                        "returned_permit_date": valid_date(item.get("archPmsDay")),
                        "returned_start_date": valid_date(item.get("realStcnsDay")),
                        "returned_approval_date": valid_date(item.get("useAprDay")),
                        **flags,
                        "other_date_in_request_window": "",
                        "no_known_date_in_request_window": observed_class == "unknown_filter_match",
                        "match_classification": observed_class,
                        "is_target_event": same_event(item, target),
                    }
                )
            probe_rows.append(
                {
                    **target,
                    "window_type": window_type,
                    "window_start": start,
                    "window_end": end,
                    "http_status": payload.get("http_status", ""),
                    "response_status": response_status(payload),
                    "total_count": total_count,
                    "returned_rows": len(items),
                    "page_size": PAGE_SIZE,
                    "pagination_truncated": int(total_count or 0) > len(items) if str(total_count).isdigit() else "",
                    "target_returned": returned_target,
                    **target_flags,
                    "target_match_classification": match_class(target_flags),
                    "observed_permit_filter_match_rows": observed_classes["permit_filter_match"],
                    "observed_start_filter_match_rows": observed_classes["start_filter_match"],
                    "observed_approval_filter_match_rows": observed_classes["approval_filter_match"],
                    "observed_multiple_event_match_rows": observed_classes["multiple_event_match"],
                    "observed_unknown_filter_match_rows": observed_classes["unknown_filter_match"],
                }
            )
    return probe_rows, match_rows


def date_field_inventory(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = sorted({field for row in samples for field in row})
    rows = []
    for field in fields:
        values = [str(row.get(field) or "").strip() for row in samples]
        nonempty = [value for value in values if value]
        valid_dates = [value for value in nonempty if re.fullmatch(r"\d{8}", value)]
        lower = field.lower()
        hint = any(token in lower for token in DATE_FIELD_HINTS)
        rows.append(
            {
                "field_name": field,
                "date_field_candidate": "Y" if hint or valid_dates else "N",
                "core_event_role": next((event for event, event_field in EVENT_FIELDS.items() if event_field == field), ""),
                "nonempty_count": len(nonempty),
                "valid_yyyymmdd_count": len(valid_dates),
                "valid_yyyymmdd_rate": len(valid_dates) / len(nonempty) if nonempty else 0,
                "min_date": min(valid_dates) if valid_dates else "",
                "max_date": max(valid_dates) if valid_dates else "",
                "sample_values": "|".join(nonempty[:5]),
            }
        )
    return rows


def summary_rows(probe_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in probe_rows:
        grouped[(row["event_type"], row["window_type"])].append(row)
    rows = []
    for (event_type, window_type), group in sorted(grouped.items()):
        normal = [row for row in group if row["response_status"] in {"success", "skipped_cached"}]
        target_returned = [row for row in normal if row["target_returned"]]
        single = [row for row in target_returned if row["target_match_classification"] == f"{event_type}_filter_match"]
        unknown = [row for row in normal if row["target_match_classification"] == "unknown_filter_match"]
        rows.append(
            {
                "event_type": event_type,
                "window_type": window_type,
                "query_count": len(group),
                "normal_response_count": len(normal),
                "target_returned_count": len(target_returned),
                "target_returned_rate": len(target_returned) / len(normal) if normal else 0,
                "single_event_match_count": len(single),
                "single_event_match_rate": len(single) / len(target_returned) if target_returned else 0,
                "unknown_target_match_count": len(unknown),
                "unknown_target_match_rate": len(unknown) / len(normal) if normal else 0,
                "truncated_query_count": sum(1 for row in group if row["pagination_truncated"] is True),
            }
        )
    return rows


def final_status(summary: list[dict[str, Any]]) -> dict[str, Any]:
    exact = [row for row in summary if row["window_type"] == "exact_day"]
    month = [row for row in summary if row["window_type"] == "month_window"]
    passed = [
        row
        for row in month
        if row["target_returned_rate"] >= 0.95
        and row["single_event_match_rate"] >= 0.95
        and row["unknown_target_match_rate"] <= 0.05
    ]
    return {
        "as_of": datetime.now().isoformat(timespec="seconds"),
        "experiment": "D1_event_date_filter_semantics",
        "source_status": "blocked" if not passed else "development_only",
        "selected_filter_rule": "not_selected",
        "reason": "No event date field met target_returned_rate >= 0.95, single_event_match_rate >= 0.95, and unknown <= 0.05 in the month-window probe.",
        "exact_day_summary": exact,
        "month_window_summary": month,
        "next_action": "Confirm official event-specific endpoints or use broad collection with event-date post-filtering; do not start nationwide row collection yet.",
    }


def main() -> int:
    samples = historical_sample_items()
    if not samples:
        raise SystemExit("No historical sample rows found in buildinghub cache.")
    target_rows = select_target_rows(samples)
    event_rows = target_event_rows(target_rows)
    probe_rows, match_rows = probe_event_semantics(event_rows)
    summary = summary_rows(probe_rows)

    write_csv(PROCESSED_DIR / "buildinghub_date_field_inventory.csv", date_field_inventory(samples))
    write_csv(PROCESSED_DIR / "buildinghub_date_filter_semantics_probe.csv", probe_rows)
    write_csv(PROCESSED_DIR / "buildinghub_event_match_audit.csv", match_rows)
    write_csv(PROCESSED_DIR / "buildinghub_date_filter_semantics_summary.csv", summary)
    write_json(PROCESSED_DIR / "buildinghub_source_final_status.json", final_status(summary))

    print(f"historical sample rows: {len(samples)}")
    print(f"selected target rows: {len(target_rows)}")
    print(f"target event rows: {len(event_rows)}")
    print(f"probe requests: {len(probe_rows)}")
    print(f"returned match rows: {len(match_rows)}")
    print(f"status: {final_status(summary)['source_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
