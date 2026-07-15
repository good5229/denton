from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"


FILES = [
    PROCESSED / "detailed_industry_quarterly_estimates.csv",
    PROCESSED / "service_detail_quarterly_estimates.csv",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="cp949", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    missing = [path.name for path in FILES if not path.exists()]
    if missing:
        print(f"missing files: {', '.join(missing)}")
        return 1

    rows: list[dict[str, str]] = []
    for path in FILES:
        part = read_rows(path)
        rows.extend(part)
        counts = Counter(row.get("detail_level") or "other" for row in part)
        print(f"{path.name}: {sum(counts.values()):,} rows, levels={dict(counts)}")

    options: dict[str, str] = {}
    levels: Counter[str] = Counter()
    for row in rows:
        code = row.get("detail_code", "")
        if not code:
            continue
        level = row.get("detail_level") or "other"
        levels[level] += 1
        parent = f"{row.get('parent_sector_name', '')} · " if row.get("parent_sector_name") else ""
        options.setdefault(code, f"{parent}[{level}] {row.get('detail_name', code)} ({code})")

    label_text = "\n".join(options.values())
    checks = {
        "middle": any("[middle]" in label for label in options.values()),
        "small": any("[small]" in label for label in options.values()),
        "class": any("[class]" in label for label in options.values()),
        "manufacturing": "제조업" in label_text,
        "service_or_other": any(word in label_text for word in ["서비스업", "도매", "소매", "숙박", "음식점", "수도업"]),
    }
    print(f"unique detail options: {len(options):,}")
    print(f"option level rows: {dict(levels)}")
    print(f"checks: {checks}")

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        print(f"failed checks: {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
