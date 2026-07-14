from __future__ import annotations

import csv
from pathlib import Path

from kosis_common import CSV_ENCODING, ROOT, cp949_safe


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8-sig", "utf-8", CSV_ENCODING):
        try:
            with path.open("r", encoding=encoding, newline="") as f:
                reader = csv.DictReader(f)
                return list(reader.fieldnames or []), list(reader)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error:
        raise last_error
    return [], []


def write_rows(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding=CSV_ENCODING, newline="", errors="replace") as f:
        if not fields:
            return
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows([{key: cp949_safe(row.get(key, "")) for key in fields} for row in rows])


def verify_cp949(path: Path) -> None:
    with path.open("r", encoding=CSV_ENCODING, newline="") as f:
        sample = f.read(4096)
    sample.encode(CSV_ENCODING)


def main() -> int:
    paths = sorted((ROOT / "data").rglob("*.csv"))
    converted = 0
    for path in paths:
        fields, rows = read_rows(path)
        write_rows(path, fields, rows)
        verify_cp949(path)
        converted += 1
    print(f"cp949 csv files verified: {converted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
