#!/usr/bin/env python3
"""Phase56 convert MOLIT public housing price ZIP to Parquet.

The user explicitly requested: download first, convert to Parquet, then remove
the original archive. The script streams CSV from the ZIP without expanding the
3.4GB CSV member to disk.
"""

from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase56_housing_price"
PROCESSED = ROOT / "data" / "processed" / "phase56_housing_price"
REPORTS = ROOT / "reports"
ZIP_PATH = RAW / "molit_public_housing_price_download.bin"
FULL_PARQUET = PROCESSED / "molit_public_housing_price_2025.parquet"
TARGET_PARQUET = PROCESSED / "molit_public_housing_price_2025_goyang_pohang.parquet"
MANIFEST = PROCESSED / "molit_public_housing_price_2025_manifest.json"

TARGET = {
    ("경기도", "고양덕양구"),
    ("경기도", "고양일산동구"),
    ("경기도", "고양일산서구"),
    ("경상북도", "포항남구"),
    ("경상북도", "포항북구"),
}

SCHEMA = pa.schema(
    [
        ("기준연도", pa.string()),
        ("기준월", pa.string()),
        ("법정동코드", pa.string()),
        ("도로명주소", pa.string()),
        ("시도", pa.string()),
        ("시군구", pa.string()),
        ("읍면", pa.string()),
        ("동리", pa.string()),
        ("특수지코드", pa.string()),
        ("본번", pa.string()),
        ("부번", pa.string()),
        ("특수지명", pa.string()),
        ("단지명", pa.string()),
        ("동명", pa.string()),
        ("호명", pa.string()),
        ("전용면적", pa.float64()),
        ("공시가격", pa.float64()),
        ("단지코드", pa.string()),
        ("동코드", pa.string()),
        ("호코드", pa.string()),
        ("건축물대장PK", pa.string()),
    ]
)


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    if not ZIP_PATH.exists():
        raise SystemExit(f"missing raw ZIP: {ZIP_PATH}")
    for partial in (FULL_PARQUET, TARGET_PARQUET):
        if partial.exists():
            partial.unlink()

    raw_size = ZIP_PATH.stat().st_size
    full_writer: pq.ParquetWriter | None = None
    target_writer: pq.ParquetWriter | None = None
    total_rows = 0
    target_rows = 0
    city_counts: dict[str, int] = {}

    with ZipFile(ZIP_PATH) as zf:
        csv_members = [info for info in zf.infolist() if info.filename.lower().endswith(".csv")]
        main_member = max(csv_members, key=lambda info: info.file_size)
        with zf.open(main_member) as handle:
            for chunk in pd.read_csv(handle, encoding="utf-8-sig", chunksize=500_000, dtype=str):
                total_rows += len(chunk)
                chunk = chunk.reindex(columns=SCHEMA.names)
                for col in SCHEMA.names:
                    if col not in {"전용면적", "공시가격"}:
                        chunk[col] = chunk[col].fillna("").astype(str)
                chunk["공시가격"] = pd.to_numeric(chunk["공시가격"], errors="coerce").astype(float)
                chunk["전용면적"] = pd.to_numeric(chunk["전용면적"], errors="coerce").astype(float)
                table = pa.Table.from_pandas(chunk, schema=SCHEMA, preserve_index=False)
                if full_writer is None:
                    full_writer = pq.ParquetWriter(FULL_PARQUET, table.schema, compression="zstd")
                full_writer.write_table(table)

                mask = chunk[["시도", "시군구"]].apply(tuple, axis=1).isin(TARGET)
                target = chunk[mask].copy()
                if not target.empty:
                    target_rows += len(target)
                    for key, val in target.groupby(["시도", "시군구"]).size().items():
                        city_counts[" ".join(key)] = city_counts.get(" ".join(key), 0) + int(val)
                    t_table = pa.Table.from_pandas(target, schema=SCHEMA, preserve_index=False)
                    if target_writer is None:
                        target_writer = pq.ParquetWriter(TARGET_PARQUET, t_table.schema, compression="zstd")
                    target_writer.write_table(t_table)

    if full_writer is not None:
        full_writer.close()
    if target_writer is not None:
        target_writer.close()

    full_meta = pq.read_metadata(FULL_PARQUET)
    target_meta = pq.read_metadata(TARGET_PARQUET) if TARGET_PARQUET.exists() else None
    if full_meta.num_rows != total_rows:
        raise AssertionError(f"full row mismatch: parquet={full_meta.num_rows} csv={total_rows}")
    if target_meta is not None and target_meta.num_rows != target_rows:
        raise AssertionError(f"target row mismatch: parquet={target_meta.num_rows} csv={target_rows}")

    ZIP_PATH.unlink()

    manifest = {
        "source_name": "국토교통부_주택 공시가격 정보",
        "source_url": "https://www.data.go.kr/data/3073746/fileData.do",
        "download_url": "https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000003525375&fileDetailSn=1&insertDataPrcus=N",
        "raw_zip_removed_after_conversion": True,
        "raw_zip_size_bytes": raw_size,
        "full_parquet": str(FULL_PARQUET.relative_to(ROOT)),
        "full_parquet_size_bytes": FULL_PARQUET.stat().st_size,
        "full_rows": total_rows,
        "target_parquet": str(TARGET_PARQUET.relative_to(ROOT)),
        "target_parquet_size_bytes": TARGET_PARQUET.stat().st_size if TARGET_PARQUET.exists() else 0,
        "target_rows": target_rows,
        "target_counts": city_counts,
        "compression": "zstd",
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Phase56 주택 공시가격 Parquet 변환",
        "",
        "## 결론",
        "",
        "- 공공데이터포털 주택 공시가격 2025년 ZIP을 다운로드한 뒤, ZIP 내부 CSV를 직접 streaming하여 Parquet/Zstd로 변환했다.",
        "- 전체 CSV를 별도 압축해제하지 않았고, 변환 검증 후 원본 ZIP은 삭제했다.",
        f"- 전체 행수: {total_rows:,}행",
        f"- 고양·포항 추출 행수: {target_rows:,}행",
        f"- 원본 ZIP 크기: {raw_size / 1024 / 1024:.1f}MB",
        f"- 전체 Parquet 크기: {FULL_PARQUET.stat().st_size / 1024 / 1024:.1f}MB",
        f"- 고양·포항 Parquet 크기: {(TARGET_PARQUET.stat().st_size if TARGET_PARQUET.exists() else 0) / 1024 / 1024:.1f}MB",
        "",
        "## 지역별 추출 행수",
        "",
        "| 지역 | 행수 |",
        "| --- | ---: |",
    ]
    for key, count in sorted(city_counts.items()):
        lines.append(f"| {key} | {count:,} |")
    lines.extend(
        [
            "",
            "## 산출 파일",
            "",
            f"- `{FULL_PARQUET.relative_to(ROOT)}`",
            f"- `{TARGET_PARQUET.relative_to(ROOT)}`",
            f"- `{MANIFEST.relative_to(ROOT)}`",
        ]
    )
    (REPORTS / "partial_statistics_estimation_phase56_housing_price_parquet.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
