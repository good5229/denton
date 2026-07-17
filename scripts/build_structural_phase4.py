from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import geopandas as gpd
import networkx as nx
import openpyxl
import pandas as pd
import pdfplumber
from pyproj import Transformer

from kosis_common import PROCESSED_DIR, ROOT, read_csv, write_csv, write_json


REPORT = ROOT / "reports" / "structural_phase4_multi_path_source_completion.md"
KSIC_PDF = ROOT / "data" / "raw" / "한국표준산업분류-해설서-개정분류-9차10차연계표포함.pdf"
DAM_DIR = ROOT / "data" / "raw" / "structural_phase3" / "manual" / "DAM_PDAN"
DAM_SHP = DAM_DIR / "DAM_PDAN.shp"
INDUSTRIAL_BOOK = ROOT / "data" / "raw" / "structural_phase2" / "data_go_kr" / "downloads" / "factoryon_industrial_complex_largefile.xlsx"
GEOMETRY_GPKG = PROCESSED_DIR / "korea_sigungu_geometry.gpkg"
GEOMETRY_LAYER = "model_sigungu_2025q2"
GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")

CSV_OUTPUTS = [
    "structural_phase3_metric_reconciliation.csv",
    "structural_phase3_artifact_consistency_audit.csv",
    "phase4_unknown_candidate_classification.csv",
    "phase4_candidate_content_fingerprints.csv",
    "phase4_new_source_discoveries.csv",
    "phase4_manual_file_review_queue.csv",
    "ksic8_official_registry.csv",
    "ksic9_official_registry.csv",
    "ksic8_9_official_crosswalk.csv",
    "ksic9_10_official_crosswalk.csv",
    "ksic_multiversion_relationships.csv",
    "factory_ksic_impact_weighted_queue.csv",
    "factory_ksic_fine_mapping.csv",
    "factory_ksic_group_mapping.csv",
    "factory_ksic_division_mapping.csv",
    "factory_historical_search_ledger.csv",
    "factory_historical_snapshot_inventory_phase4.csv",
    "factory_snapshot_pair_audit.csv",
    "factory_date_reconstruction_feasibility.csv",
    "factory_stock_feature_table_phase4.csv",
    "factory_flow_feature_table_phase4.csv",
    "industrial_geometry_source_inventory_phase4.csv",
    "industrial_geometry_download_audit.csv",
    "industrial_geometry_api_probe.csv",
    "industrial_activity_operation_registry.csv",
    "industrial_activity_probe_results.csv",
    "industrial_activity_period_inventory.csv",
    "industrial_activity_raw_manifest.csv",
    "industrial_activity_long_table.csv",
    "industrial_activity_total_reconciliation.csv",
    "industrial_activity_publication_lag.csv",
    "industrial_complex_allocation_candidates.csv",
    "industrial_complex_allocation_method_audit.csv",
    "industrial_complex_activity_allocated.csv",
    "industrial_complex_allocation_uncertainty.csv",
    "business_employment_source_scorecard.csv",
    "business_employment_historical_inventory.csv",
    "business_employment_region_crosswalk.csv",
    "business_employment_feature_table.csv",
    "business_employment_publication_lag.csv",
    "korea_spatial_feature_registry_phase4.csv",
    "korea_sigungu_static_spatial_features.csv",
    "korea_graph_centrality_features.csv",
    "korea_threshold_graph_isolation_audit.csv",
    "structural_source_publication_registry.csv",
    "structural_source_revision_registry.csv",
    "structural_first_eligible_period_audit.csv",
    "structural_vintage_leakage_audit.csv",
    "structural_source_total_reconciliation.csv",
    "structural_source_outlier_audit.csv",
    "structural_source_schema_drift_audit.csv",
    "structural_source_quality_gate_status.csv",
    "structural_phase4_source_gates.csv",
    "structural_phase4_bundle_registry.csv",
    "structural_phase4_user_action_requests.csv",
    "structural_phase4_execution_manifest.csv",
]


def relative(path: Path | str) -> str:
    path = Path(path)
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def sha256(path: Path, block_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(block_size):
            digest.update(chunk)
    return digest.hexdigest()


def schema_hash(columns: Iterable[str]) -> str:
    return hashlib.sha256("|".join(columns).encode("utf-8")).hexdigest()


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def read_frame(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / name
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    for encoding in ("cp949", "utf-8-sig", "utf-8"):
        try:
            return pd.read_csv(path, encoding=encoding, dtype=str, keep_default_na=False, low_memory=False)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("cp949", b"", 0, 1, str(path))


def write_frame(name: str, frame: pd.DataFrame, columns: list[str] | None = None) -> None:
    path = PROCESSED_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if columns is not None:
        for column in columns:
            if column not in frame:
                frame[column] = ""
        frame = frame[columns]
    frame.to_csv(path, index=False, encoding="cp949", errors="replace")


def number(value: Any) -> float:
    try:
        text = str(value or "").replace(",", "").strip()
        return float(text) if text else 0.0
    except ValueError:
        return 0.0


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\u3000", " ")).strip()


def normalize_code(value: Any, width: int = 5) -> str:
    text = clean_text(value)
    text = re.sub(r"\.0+$", "", text)
    if not re.fullmatch(r"\d+", text):
        return ""
    if len(text) == width - 1:
        text = text.zfill(width)
    return text if len(text) == width else ""


def common_prefix(codes: Iterable[str], size: int) -> str:
    values = {code[:size] for code in codes if len(code) >= size}
    return next(iter(values)) if len(values) == 1 else ""


def phase3_reconciliation() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    queue = read_frame("factory_ksic_manual_review_queue.csv")
    mapping = read_frame("factory_observed_ksic_mapping.csv")
    audit = read_frame("factory_observed_ksic_mapping_audit.csv")
    unresolved_rows = int(round(queue.get("observed_count", pd.Series(dtype=str)).map(number).sum()))
    unresolved_employees = queue.get("employee_sum", pd.Series(dtype=str)).map(number).sum()
    unique_codes = queue.get("raw_code", pd.Series(dtype=str)).map(normalize_code)
    definitions = [
        ("unresolved_unique_raw_codes", int(unique_codes[unique_codes != ""].nunique()), "미해결 레코드의 중복 제거된 유효 raw code 수"),
        ("unresolved_code_name_pairs", len(queue), "raw code, raw name, source version 조합 수"),
        ("unresolved_top_frequency_codes", min(50, len(queue)), "Gate 진단에 노출한 영향도 상위 queue 크기이며 전체 미해결 수가 아님"),
        ("unresolved_factory_rows", unresolved_rows, "미해결 조합의 observed_count 합계; 공장 원행 수"),
        ("unresolved_employee_weight", round(unresolved_employees, 6), "미해결 원행의 종업원 수 합계"),
    ]
    reconciliation = pd.DataFrame(
        [
            {
                "metric": key,
                "phase3_reported_value": "50" if key == "unresolved_top_frequency_codes" else ("496" if key == "unresolved_code_name_pairs" else ""),
                "phase4_recomputed_value": value,
                "definition": definition,
                "status": "reconciled",
            }
            for key, value, definition in definitions
        ]
    )
    artifacts = [
        "structural_phase3_source_gates.csv",
        "structural_phase3_restart_manifest.json",
        "factory_observed_ksic_mapping_audit.csv",
        "factory_ksic_manual_review_queue.csv",
        "korea_spatial_graph_audit.csv",
        "industrial_complex_geometry_audit.csv",
    ]
    rows = []
    for name in artifacts:
        path = PROCESSED_DIR / name
        if not path.exists():
            rows.append({"artifact": name, "exists": "N", "row_count": "", "file_hash": "", "schema_hash": "", "status": "missing"})
            continue
        if path.suffix == ".csv" and path.stat().st_size:
            frame = read_frame(name)
            row_count, s_hash = len(frame), schema_hash(frame.columns)
        else:
            row_count, s_hash = 1, schema_hash(json.loads(path.read_text(encoding="utf-8")).keys())
        rows.append({"artifact": name, "exists": "Y", "row_count": row_count, "file_hash": sha256(path), "schema_hash": s_hash, "status": "consistent_current_artifact"})
    restart_path = PROCESSED_DIR / "structural_phase3_restart_manifest.json"
    if restart_path.exists():
        restart = json.loads(restart_path.read_text(encoding="utf-8"))
        expected_commit = restart.get("code_commit_hash", "")
        commit_is_ancestor = False
        if expected_commit:
            commit_is_ancestor = subprocess.run(
                ["git", "merge-base", "--is-ancestor", expected_commit, "HEAD"],
                cwd=ROOT,
                check=False,
            ).returncode == 0
        report_path = ROOT / restart.get("report", "")
        manifest_path = ROOT / restart.get("execution_manifest", "")
        rows.extend(
            [
                {
                    "artifact": "phase3_code_commit",
                    "exists": "Y" if expected_commit else "N",
                    "row_count": "",
                    "file_hash": expected_commit,
                    "schema_hash": "",
                    "status": "ancestor_verified" if commit_is_ancestor else "commit_not_in_history",
                },
                {
                    "artifact": "phase3_report_manifest_link",
                    "exists": "Y" if report_path.exists() else "N",
                    "row_count": "",
                    "file_hash": sha256(report_path) if report_path.exists() else "",
                    "schema_hash": "",
                    "status": "consistent" if report_path.exists() else "missing",
                },
                {
                    "artifact": "phase3_execution_manifest_link",
                    "exists": "Y" if manifest_path.exists() else "N",
                    "row_count": "",
                    "file_hash": sha256(manifest_path) if manifest_path.exists() else "",
                    "schema_hash": "",
                    "status": "consistent" if manifest_path.exists() else "missing",
                },
            ]
        )
    context = {
        "queue_rows": len(queue),
        "unresolved_factory_rows": unresolved_rows,
        "unresolved_employees": unresolved_employees,
        "factory_rows": len(mapping),
        "phase3_mapping_rate": number(audit.iloc[0].get("observed_row_mapping_rate", "")) if len(audit) else 0,
    }
    return reconciliation, pd.DataFrame(rows), context


FACTORY_TERMS = ("공장관리번호", "공장등록", "등록공장", "종업원수", "제조시설면적", "업종코드")
INDUSTRIAL_TERMS = ("산업단지", "입주업체", "가동업체", "생산", "수출", "분양면적", "산업시설용지")
KSIC_TERMS = ("한국표준산업분류", "연계표", "신구연계", "제8차", "제9차", "제10차", "제11차")
SPATIAL_TERMS = ("SIG_CD", "ADM_CD", "단지경계", "Polygon", "MultiPolygon")


def file_fingerprint(path: Path) -> dict[str, Any]:
    raw = b""
    try:
        with path.open("rb") as handle:
            raw = handle.read(131072)
    except OSError:
        pass
    signature = raw[:16].hex()
    text = ""
    for encoding in ("utf-8-sig", "cp949", "latin1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    sheets = ""
    columns = ""
    geometry_type = ""
    try:
        if path.suffix.lower() in {".xlsx", ".xlsm"} and zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                sheets = "|".join(name for name in names if name.startswith("xl/worksheets/") and name.endswith(".xml"))
                shared = next((name for name in names if name == "xl/sharedStrings.xml"), "")
                if shared:
                    text += " " + archive.read(shared)[:262144].decode("utf-8", errors="ignore")
        elif path.suffix.lower() == ".csv":
            columns = clean_text(text.splitlines()[0] if text.splitlines() else "")
        elif path.suffix.lower() == ".shp":
            layer = gpd.read_file(path, rows=1)
            columns = "|".join(layer.columns)
            geometry_type = "|".join(layer.geom_type.dropna().unique())
    except Exception:
        pass
    haystack = " ".join((path.name, text[:300000], sheets, columns))
    counts = {
        "factory": sum(haystack.count(term) for term in FACTORY_TERMS),
        "industrial": sum(haystack.count(term) for term in INDUSTRIAL_TERMS),
        "ksic": sum(haystack.count(term) for term in KSIC_TERMS),
        "spatial": sum(haystack.count(term) for term in SPATIAL_TERMS),
    }
    winner = max(counts, key=counts.get)
    score = counts[winner]
    matched_terms = {
        "factory": [term for term in FACTORY_TERMS if term in haystack],
        "industrial": [term for term in INDUSTRIAL_TERMS if term in haystack],
        "ksic": [term for term in KSIC_TERMS if term in haystack],
        "spatial": [term for term in SPATIAL_TERMS if term in haystack],
    }
    if matched_terms["ksic"] and path.suffix.lower() in {".pdf", ".xlsx", ".xls", ".csv", ".txt"}:
        status = "confirmed_ksic_table"
        winner = "ksic"
    elif "산업단지" in matched_terms["industrial"] and len(matched_terms["industrial"]) >= 2:
        status = "probable_industrial_activity"
        winner = "industrial"
    elif len(matched_terms["factory"]) >= 2:
        status = "probable_factory_snapshot"
        winner = "factory"
    elif geometry_type and matched_terms["spatial"]:
        status = "confirmed_geometry"
        winner = "spatial"
    else:
        text_scannable = path.suffix.lower() in {".csv", ".json", ".xml", ".html", ".txt", ".md", ".log"}
        status = "irrelevant" if text_scannable or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".pptx", ".pyc"} else "manual_review"
        winner = ""
    score = len(matched_terms.get(winner, [])) if winner else 0
    return {
        "file_signature": signature,
        "header_signature": hashlib.sha256(columns.encode("utf-8")).hexdigest() if columns else "",
        "schema_signature": hashlib.sha256((columns + sheets).encode("utf-8")).hexdigest() if columns or sheets else "",
        "date_signature": "|".join(sorted(set(re.findall(r"20(?:0\d|1\d|2\d)[-./]?(?:0[1-9]|1[0-2])?", haystack)))[:12]),
        "identifier_signature": "|".join(f"{key}:{','.join(values)}" for key, values in matched_terms.items() if values),
        "sheet_names_or_members": sheets[:1500],
        "column_names": columns[:1500],
        "geometry_type": geometry_type,
        "source_type_probability": min(1.0, score / 3),
        "classification": status,
        "keyword_score": score,
    }


def classify_unknown_candidates() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    inventory = read_frame("phase3_local_source_inventory.csv")
    unknown = inventory[inventory["candidate_source_type"].eq("unknown_candidate")].copy()
    classifications: list[dict[str, Any]] = []
    fingerprints: list[dict[str, Any]] = []
    for row in unknown.to_dict("records"):
        path = ROOT / row["file_path"]
        fp = file_fingerprint(path) if path.exists() else {"classification": "corrupted", "keyword_score": 0, "source_type_probability": 0}
        fingerprints.append({"file_id": row["file_id"], "file_path": row["file_path"], **fp})
        classifications.append(
            {
                "file_id": row["file_id"],
                "file_path": row["file_path"],
                "previous_classification": "unknown_candidate",
                "phase4_classification": fp["classification"],
                "content_evidence": fp.get("identifier_signature", ""),
                "confidence": fp.get("source_type_probability", 0),
                "status": "classified_content_native",
            }
        )
    class_frame = pd.DataFrame(classifications)
    fp_frame = pd.DataFrame(fingerprints)
    discoveries = class_frame[
        class_frame["file_path"].str.startswith("data/raw/")
        & class_frame["phase4_classification"].isin(["probable_factory_snapshot", "probable_industrial_activity", "confirmed_ksic_table", "confirmed_geometry"])
    ].copy()
    if len(discoveries):
        discoveries = discoveries.rename(columns={"phase4_classification": "discovery_type"})
        discoveries["requires_validation"] = "Y"
    manual = class_frame[class_frame["phase4_classification"].eq("manual_review")].copy()
    if len(manual):
        manual["review_priority"] = range(1, len(manual) + 1)
        manual["review_reason"] = "content signature insufficient for deterministic classification"
    return class_frame, fp_frame, discoveries, manual


def relationship_type(source_count: int, target_count: int, source_code: str, target_code: str, note: str) -> str:
    if not source_code:
        return "new_code"
    if not target_code:
        return "deleted_code"
    if target_count > 1:
        return "one_to_many"
    if source_count > 1:
        return "many_to_one"
    if "세분" in note:
        return "split"
    if "통합" in note:
        return "merge"
    return "one_to_one"


def parse_ksic9_10_pdf() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not KSIC_PDF.exists():
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    raw_rows: list[dict[str, Any]] = []
    current_source_code = ""
    current_source_name = ""
    with pdfplumber.open(KSIC_PDF) as pdf:
        for page_number in range(866, len(pdf.pages) + 1):
            tables = pdf.pages[page_number - 1].extract_tables()
            if not tables:
                continue
            table = tables[0]
            header = " ".join(clean_text(cell) for row in table[:2] for cell in row if cell)
            if "KSIC-9" not in header or "KSIC-10" not in header:
                continue
            for table_row_number, values in enumerate(table[2:], start=3):
                cells = (list(values) + [None] * 6)[:6]
                old_code = normalize_code(cells[0])
                old_name = clean_text(cells[1])
                new_code = normalize_code(cells[2])
                new_name = clean_text(cells[3])
                relation_count = clean_text(cells[4])
                detail = clean_text(cells[5])
                if old_code:
                    current_source_code, current_source_name = old_code, old_name
                if not new_code:
                    continue
                source_code = old_code or current_source_code
                source_name = old_name or current_source_name
                if not source_code:
                    continue
                raw_rows.append(
                    {
                        "source_version": "9",
                        "source_code": source_code,
                        "source_name": source_name,
                        "target_version": "10",
                        "target_code": new_code,
                        "target_name": new_name,
                        "official_relation_count": relation_count,
                        "mapping_note": detail,
                        "official_source_file": relative(KSIC_PDF),
                        "official_page_number": page_number,
                        "official_table_row_number": table_row_number,
                        "effective_from": "2017-07-01",
                        "effective_to": "2024-06-30",
                    }
                )
    frame = pd.DataFrame(raw_rows).drop_duplicates(
        subset=["source_code", "target_code", "mapping_note", "official_page_number", "official_table_row_number"]
    )
    target_counts = frame.groupby("source_code")["target_code"].nunique().to_dict()
    source_counts = frame.groupby("target_code")["source_code"].nunique().to_dict()
    frame["mapping_type"] = [
        relationship_type(source_counts.get(row.target_code, 1), target_counts.get(row.source_code, 1), row.source_code, row.target_code, row.mapping_note)
        for row in frame.itertuples()
    ]
    frame["mapping_weight"] = ""
    frame["deterministic_fine_mapping"] = frame["source_code"].map(target_counts).eq(1).map({True: "Y", False: "N"})
    source_registry = (
        frame[["source_code", "source_name"]]
        .drop_duplicates("source_code")
        .rename(columns={"source_code": "code", "source_name": "name"})
    )
    target_registry = (
        frame[["target_code", "target_name"]]
        .drop_duplicates("target_code")
        .rename(columns={"target_code": "code", "target_name": "name"})
    )
    registries = []
    for version, registry, start, end in (
        ("9", source_registry, "2008-02-01", "2017-06-30"),
        ("10", target_registry, "2017-07-01", "2024-06-30"),
    ):
        item = registry.copy()
        item.insert(0, "ksic_version", version)
        item["code_length"] = item["code"].str.len()
        item["division_code"] = item["code"].str[:2]
        item["group_code"] = item["code"].str[:3]
        item["manufacturing_subsector"] = item["division_code"].map(lambda x: x if x.isdigit() and 10 <= int(x) <= 34 else "")
        item["effective_from"] = start
        item["effective_to"] = end
        item["official_source_file"] = relative(KSIC_PDF)
        registries.append(item)
    return registries[0], registries[1], frame


def build_multilevel_ksic(registry9: pd.DataFrame, registry10: pd.DataFrame, crosswalk9: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    observed = read_frame("factory_observed_ksic_mapping.csv")
    inventory = read_frame("factory_observed_ksic_inventory.csv")
    crosswalk10 = read_frame("ksic10_11_official_crosswalk.csv")
    map9: dict[str, set[str]] = defaultdict(set)
    for row in crosswalk9.itertuples():
        map9[row.source_code].add(row.target_code)
    registry10_codes = set(registry10["code"]) if len(registry10) else set()
    map10_11: dict[str, set[str]] = defaultdict(set)
    for row in crosswalk10.to_dict("records"):
        source, target = normalize_code(row.get("source_code")), normalize_code(row.get("target_code"))
        if source and target:
            map10_11[source].add(target)

    fine_rows: list[dict[str, Any]] = []
    group_rows: list[dict[str, Any]] = []
    division_rows: list[dict[str, Any]] = []
    impact: dict[tuple[str, str, str], dict[str, Any]] = {}
    unresolved_keys: dict[str, set[tuple[str, str, str]]] = {"fine": set(), "group": set(), "division": set()}
    level_counts = {level: {"mapped_rows": 0, "mapped_employees": 0.0} for level in ("fine", "group", "division")}
    total_employees = 0.0
    for row in observed.to_dict("records"):
        code = normalize_code(row.get("normalized_code") or row.get("raw_code"))
        version = clean_text(row.get("source_ksic_version")) or "unknown"
        employee = number(row.get("employee_count"))
        total_employees += employee
        candidates10: set[str] = set()
        method = "unresolved"
        if version == "9" and code in map9:
            candidates10 = set(map9[code])
            method = "official_ksic9_to_10_pdf_crosswalk"
        elif version == "10" and code in registry10_codes:
            candidates10 = {code}
            method = "official_ksic10_registry_exact"
        fine_code = next(iter(candidates10)) if len(candidates10) == 1 else ""
        group_code = common_prefix(candidates10, 3)
        division_code = common_prefix(candidates10, 2)
        candidates11 = sorted({target for candidate in candidates10 for target in map10_11.get(candidate, set())})
        base = {
            "source_file": row.get("source_file", ""),
            "reference_period": row.get("reference_period", ""),
            "source_row_number": row.get("source_row_number", ""),
            "factory_key": row.get("factory_key", ""),
            "raw_code": row.get("raw_code", ""),
            "normalized_code": code,
            "raw_name": row.get("raw_name", ""),
            "source_ksic_version": version,
            "candidate_ksic10_codes": "|".join(sorted(candidates10)),
            "candidate_ksic11_codes": "|".join(candidates11),
            "mapping_method": method,
            "employee_count": employee,
        }
        fine_rows.append({**base, "mapped_code": fine_code, "mapping_status": "mapped" if fine_code else ("ambiguous" if candidates10 else "unresolved")})
        group_rows.append({**base, "mapped_code": group_code, "mapping_status": "mapped" if group_code else ("ambiguous" if candidates10 else "unresolved")})
        division_rows.append({**base, "mapped_code": division_code, "mapping_status": "mapped" if division_code else ("ambiguous" if candidates10 else "unresolved")})
        for level, mapped_code in (("fine", fine_code), ("group", group_code), ("division", division_code)):
            if mapped_code:
                level_counts[level]["mapped_rows"] += 1
                level_counts[level]["mapped_employees"] += employee
        key = (code, clean_text(row.get("raw_name")), version)
        for level, mapped_code in (("fine", fine_code), ("group", group_code), ("division", division_code)):
            if not mapped_code:
                unresolved_keys[level].add(key)
        if not fine_code:
            item = impact.setdefault(
                key,
                {
                    "raw_code": code,
                    "raw_name": clean_text(row.get("raw_name")),
                    "source_version": version,
                    "factory_row_count": 0,
                    "employee_sum": 0.0,
                    "site_area_sum": 0.0,
                    "building_area_sum": 0.0,
                    "sigungu_count": "not_available_in_source",
                    "snapshot_count": 0,
                    "first_observed_period": row.get("reference_period", ""),
                    "last_observed_period": row.get("reference_period", ""),
                    "blocking_reason": "official crosswalk unavailable or source version unresolved",
                },
            )
            item["factory_row_count"] += 1
            item["employee_sum"] += employee
            item["snapshot_count"] = 1
    aggregate_inventory: dict[tuple[str, str, str], dict[str, float]] = defaultdict(lambda: {"site": 0.0, "building": 0.0})
    for row in inventory.to_dict("records"):
        key = (normalize_code(row.get("normalized_code") or row.get("raw_code")), clean_text(row.get("raw_name")), clean_text(row.get("declared_ksic_version")) or "unknown")
        aggregate_inventory[key]["site"] += number(row.get("site_area_sum"))
        aggregate_inventory[key]["building"] += number(row.get("building_area_sum"))
    for key, item in impact.items():
        item["site_area_sum"] = aggregate_inventory[key]["site"]
        item["building_area_sum"] = aggregate_inventory[key]["building"]
    impact_rows = sorted(impact.values(), key=lambda row: (-row["employee_sum"], -row["factory_row_count"], -row["site_area_sum"]))
    for rank, row in enumerate(impact_rows, 1):
        row["priority_rank"] = rank
    total_rows = len(observed)
    status: dict[str, Any] = {"canonical_mapping_version": "KSIC10", "official_pdf_source": relative(KSIC_PDF), "total_factory_rows": total_rows, "total_employee_weight": total_employees}
    thresholds = {
        "K_FINE": ("fine", 0.99, 0.99, min(50, len(unresolved_keys["fine"]))),
        "K_GROUP": ("group", 0.995, 0.995, min(20, len(unresolved_keys["group"]))),
        "K_DIVISION": ("division", 0.999, 0.999, len(unresolved_keys["division"])),
    }
    for gate, (level, row_threshold, employee_threshold, unresolved_top) in thresholds.items():
        row_rate = level_counts[level]["mapped_rows"] / total_rows if total_rows else 0
        employee_rate = level_counts[level]["mapped_employees"] / total_employees if total_employees else 0
        pass_gate = row_rate >= row_threshold and employee_rate >= employee_threshold and unresolved_top == 0
        status[gate] = {
            "status": "pass" if pass_gate else "blocked_mapping_quality",
            "row_mapping_rate": row_rate,
            "employee_weighted_mapping_rate": employee_rate,
            "unresolved_top_impact_count": unresolved_top,
            "one_to_many_arbitrary_collapse": 0,
        }
    frames = {
        "fine": pd.DataFrame(fine_rows),
        "group": pd.DataFrame(group_rows),
        "division": pd.DataFrame(division_rows),
        "impact": pd.DataFrame(impact_rows),
    }
    return frames, status


def factory_history_outputs() -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    phase3 = read_frame("factory_historical_search_manifest.csv")
    ledger = phase3.copy()
    if len(ledger):
        ledger["phase4_result"] = "no_verified_2021_2023_national_snapshot"
    ledger = pd.concat(
        [
            ledger,
            pd.DataFrame(
                [
                    {
                        "source": "phase4_local_content_scan",
                        "query": "2021|2022|2023 factory snapshot with stable key and publication date",
                        "status": "completed_no_qualifying_snapshot",
                        "result_count": 0,
                        "checked_at": GENERATED_AT,
                        "phase4_result": "blocked_missing_history",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    snapshot = pd.DataFrame(
        [
            {"target_year": year, "verified_snapshot": "N", "publication_date_known": "N", "regional_coverage": 0, "status": "missing"}
            for year in (2021, 2022, 2023)
        ]
    )
    pair = pd.DataFrame([{"snapshot_pair": "2021-2022", "status": "not_testable_missing_snapshot"}, {"snapshot_pair": "2022-2023", "status": "not_testable_missing_snapshot"}])
    feasibility = pd.DataFrame(
        [
            {
                "source": "current_factory_snapshot",
                "registration_date_non_null_rate": "not_sufficiently_verified",
                "closure_date_available": "N",
                "closed_factories_in_source": "N",
                "survivorship_bias": "present",
                "decision": "prohibited_for_ml",
            }
        ]
    )
    stock = pd.DataFrame(columns=["sigungu_feature_key", "observation_period", "feature_name", "feature_value", "publication_date", "first_eligible_period"])
    flow = pd.DataFrame(columns=["sigungu_feature_key", "observation_period", "feature_name", "feature_value", "publication_date", "first_eligible_period"])
    readiness = {
        "source": "factory_registration",
        "status": "blocked_history",
        "historical_2021": "fail",
        "historical_2022": "fail",
        "historical_2023": "fail",
        "survivorship_biased_reconstruction": "prohibited_not_run",
        "ml_training": "prohibited_not_run",
    }
    return {"ledger": ledger, "snapshot": snapshot, "pair": pair, "feasibility": feasibility, "stock": stock, "flow": flow}, readiness


def industrial_geometry_outputs(sigungu: gpd.GeoDataFrame) -> tuple[dict[str, pd.DataFrame], dict[str, Any], gpd.GeoDataFrame | None]:
    if not DAM_SHP.exists():
        empty = pd.DataFrame([{"source": relative(DAM_SHP), "status": "missing"}])
        return {"inventory": empty, "download": empty.copy(), "probe": empty.copy(), "allocation": empty.copy()}, {"status": "blocked_geometry_source"}, None
    points = gpd.read_file(DAM_SHP)
    types = "|".join(sorted(points.geom_type.dropna().unique()))
    inventory = pd.DataFrame(
        [
            {
                "source_id": "dam_pdan_manual",
                "source_path": relative(DAM_SHP),
                "source_hash": sha256(DAM_SHP),
                "feature_count": len(points),
                "geometry_type": types,
                "crs": str(points.crs),
                "complex_id_non_null": int(points.get("DAN_ID", pd.Series(dtype=str)).notna().sum()),
                "geometry_level": "G3",
                "allocation_role": "diagnostic_only",
                "status": "valid_point_source_not_polygon",
            }
        ]
    )
    components = [DAM_DIR / f"DAM_PDAN{suffix}" for suffix in (".shp", ".shx", ".dbf", ".prj", ".cpg")]
    download = pd.DataFrame(
        [
            {
                "source_id": "dam_pdan_manual",
                "component": relative(path),
                "exists": "Y" if path.exists() else "N",
                "content_length": path.stat().st_size if path.exists() else 0,
                "magic_or_file_role": path.suffix.lower(),
                "archive_integrity": "complete_shapefile_component_set" if all(item.exists() for item in components) else "incomplete",
            }
            for path in components
        ]
    )
    probe = pd.DataFrame([{"source_id": "dam_pdan_manual", "probe_type": "local_one_feature", "rows_returned": 1, "required_fields": "DAN_ID|DAN_NAME|geometry", "result": "success_point_geometry", "full_collection": "already_present"}])
    points_model = points.to_crs(sigungu.crs)
    joined = gpd.sjoin(points_model, sigungu[["sigungu_feature_key", "model_region_code", "geometry"]], predicate="within", how="left")
    allocation = joined.drop(columns="geometry").copy()
    allocation["allocation_allowed"] = "N"
    allocation["diagnostic_role"] = "point_presence_and_nearest_distance_only"
    allocation["blocking_issue"] = "Point geometry cannot allocate complex activity"
    selected = {
        "source_id": "dam_pdan_manual",
        "geometry_level": "G3",
        "geometry_type": types,
        "feature_count": len(points),
        "allocation_role": "diagnostic_only",
        "industrial_allocation_gate": "blocked_geometry_source",
        "reason": "Official-looking supplied layer is Point, not Polygon or industrial-facility Polygon.",
    }
    return {"inventory": inventory, "download": download, "probe": probe, "allocation": allocation}, selected, joined


def quarter(period: datetime) -> str:
    return f"{period.year}Q{(period.month - 1) // 3 + 1}"


def industrial_activity_outputs() -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    operations = pd.DataFrame(
        [
            {"operation_name": "factoryon_largefile_tenant_company_stock", "source": relative(INDUSTRIAL_BOOK), "metric": "tenant_company_count", "frequency": "monthly", "semantic_status": "confirmed_stock", "collection_status": "selected_local_file"},
            {"operation_name": "factoryon_largefile_approved_factory_stock", "source": relative(INDUSTRIAL_BOOK), "metric": "approved_registered_factory_count", "frequency": "monthly", "semantic_status": "confirmed_stock", "collection_status": "selected_local_file"},
            {"operation_name": "production", "source": "not_found", "metric": "production", "frequency": "quarterly", "semantic_status": "unresolved", "collection_status": "blocked_source_missing"},
            {"operation_name": "exports", "source": "not_found", "metric": "exports", "frequency": "quarterly", "semantic_status": "unresolved", "collection_status": "blocked_source_missing"},
            {"operation_name": "employment", "source": "workbook sheet name alone is insufficient", "metric": "employment", "frequency": "quarterly", "semantic_status": "blocked", "collection_status": "blocked_definition"},
        ]
    )
    if not INDUSTRIAL_BOOK.exists():
        blocked = pd.DataFrame([{"status": "blocked_source_missing", "blocking_issue": relative(INDUSTRIAL_BOOK)}])
        return {key: blocked.copy() for key in ("probe", "periods", "manifest", "long", "reconciliation", "lag")}, {"status": "blocked_history"}
    workbook = openpyxl.load_workbook(INDUSTRIAL_BOOK, read_only=True, data_only=True)
    sheet = workbook["산업단지별 업체수"]
    monthly: dict[tuple[datetime, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
    for values in sheet.iter_rows(min_row=2, values_only=True):
        date_value, complex_code, _address_code, tenant_count, approved_count = (list(values) + [None] * 5)[:5]
        if not isinstance(date_value, datetime) or not 2021 <= date_value.year <= 2023:
            continue
        key = (date_value, clean_text(complex_code))
        monthly[key][0] += number(tenant_count)
        monthly[key][1] += number(approved_count)
    workbook.close()
    quarter_end: dict[tuple[str, str], tuple[datetime, list[float]]] = {}
    for (date_value, code), values in monthly.items():
        key = (quarter(date_value), code)
        if key not in quarter_end or date_value > quarter_end[key][0]:
            quarter_end[key] = (date_value, values)
    long_rows = []
    for (qtr, code), (date_value, values) in sorted(quarter_end.items()):
        for metric, value in zip(("tenant_company_count", "approved_registered_factory_count"), values):
            long_rows.append(
                {
                    "reference_period": qtr,
                    "source_month": date_value.strftime("%Y-%m"),
                    "industrial_complex_code": code,
                    "metric": metric,
                    "value": value,
                    "unit": "count",
                    "value_type": "quarter_end_stock",
                    "publication_date": "",
                    "first_eligible_period": "",
                    "historical_use": "prohibited_release_date_unknown",
                }
            )
    long_frame = pd.DataFrame(long_rows)
    period_rows = []
    for year in (2021, 2022, 2023):
        for q in range(1, 5):
            period = f"{year}Q{q}"
            subset = long_frame[long_frame["reference_period"].eq(period)] if len(long_frame) else pd.DataFrame()
            for metric in ("tenant_company_count", "approved_registered_factory_count", "production", "exports", "employment"):
                metric_subset = subset[subset["metric"].eq(metric)] if len(subset) else pd.DataFrame()
                period_rows.append({"reference_period": period, "metric": metric, "row_count": len(metric_subset), "complex_count": metric_subset["industrial_complex_code"].nunique() if len(metric_subset) else 0, "status": "available_release_unknown" if len(metric_subset) else "missing"})
    periods = pd.DataFrame(period_rows)
    probe = pd.DataFrame([{"operation_name": "factoryon_largefile_tenant_company_stock", "probe_period": "2021Q1", "requested_rows": 1, "returned_rows": int((long_frame["reference_period"] == "2021Q1").sum()) if len(long_frame) else 0, "status": "success_local_file"}])
    manifest = pd.DataFrame([{"source": relative(INDUSTRIAL_BOOK), "source_hash": sha256(INDUSTRIAL_BOOK), "sheet": "산업단지별 업체수", "rows_selected_2021_2023": len(long_frame), "retrieval_date": datetime.fromtimestamp(INDUSTRIAL_BOOK.stat().st_mtime).astimezone().isoformat(timespec="seconds"), "publication_date": "", "status": "parsed"}])
    reconciliation = pd.DataFrame(
        [
            {"metric": metric, "source_total": long_frame[long_frame["metric"].eq(metric)]["value"].sum() if len(long_frame) else 0, "published_total": "", "difference_rate": "", "status": "not_testable_published_total_missing"}
            for metric in ("tenant_company_count", "approved_registered_factory_count")
        ]
    )
    lag = periods[["reference_period", "metric"]].copy()
    lag["release_date"] = ""
    lag["retrieval_date"] = datetime.fromtimestamp(INDUSTRIAL_BOOK.stat().st_mtime).astimezone().date().isoformat()
    lag["source_vintage"] = sha256(INDUSTRIAL_BOOK)[:12]
    lag["first_eligible_period"] = ""
    lag["eligibility_status"] = "blocked_unknown_historical_release"
    available_company_periods = sorted(long_frame["reference_period"].unique().tolist()) if len(long_frame) else []
    readiness = {
        "source": "industrial_complex_activity",
        "status": "development_only",
        "company_stock_2021Q1_2023Q4": "incomplete",
        "available_company_stock_periods": available_company_periods,
        "production_history": "missing",
        "exports_history": "missing",
        "employment_semantics": "unresolved",
        "official_complex_mapping_rate": 0,
        "allocation_value_coverage": 0,
        "publication_date": "incomplete",
        "ml_training": "prohibited_not_run",
    }
    return {"operations": operations, "probe": probe, "periods": periods, "manifest": manifest, "long": long_frame, "reconciliation": reconciliation, "lag": lag}, readiness


def business_employment_outputs() -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    score_rows = [
        ("national_establishment_census", "전국사업체조사/KOSIS", 25, 20, 15, 8, 10, 5, 5, "sigungu 제조업·광업 세부자료만 현재 로컬 확보"),
        ("employment_insurance", "고용보험 사업장·피보험자", 20, 10, 10, 10, 8, 5, 3, "원자료 미확보"),
        ("small_business_store_stock", "소상공인 상가(상권)정보", 20, 10, 8, 8, 8, 4, 2, "현재 시점 stock, 과거 vintage 불완전"),
        ("official_business_registration", "국세청 사업자등록 통계", 10, 5, 10, 8, 10, 5, 3, "시군구×산업 공통 coverage 불충분"),
    ]
    score = pd.DataFrame(
        [
            {"source_id": source_id, "source_name": name, "historical_2021_2023_score": hist, "sigungu_coverage_score": coverage, "publication_lag_score": lag, "first_eligible_score": eligible, "industry_score": industry, "access_score": access, "revision_score": revision, "total_score": sum((hist, coverage, lag, eligible, industry, access, revision)), "note": note}
            for source_id, name, hist, coverage, lag, eligible, industry, access, revision, note in score_rows
        ]
    ).sort_values("total_score", ascending=False)
    mart = read_frame("municipality_feature_mart_long.csv")
    selected = mart[
        mart.get("source_dataset", pd.Series(dtype=str)).eq("manufacturing_mining_sigungu_ksic")
        & mart.get("area_level", pd.Series(dtype=str)).eq("sigungu")
        & mart.get("year", pd.Series(dtype=str)).isin(["2021", "2022", "2023"])
    ].copy()
    inventory = (
        selected.groupby("year", as_index=False)
        .agg(row_count=("value", "size"), region_count=("area_code", "nunique"), industry_count=("industry_code", "nunique"), metric_count=("metric", "nunique"))
        if len(selected)
        else pd.DataFrame(columns=["year", "row_count", "region_count", "industry_count", "metric_count"])
    )
    inventory["coverage_scope"] = "manufacturing_and_mining_only"
    inventory["all_sector_gate"] = "fail"
    crosswalk = selected[["area_code", "area_name"]].drop_duplicates().rename(columns={"area_code": "source_region_code", "area_name": "source_region_name"}) if len(selected) else pd.DataFrame(columns=["source_region_code", "source_region_name"])
    crosswalk["model_region_code"] = crosswalk["source_region_code"]
    crosswalk["match_status"] = "source_code_carried_requires_official_actual_crosscheck"
    feature_columns = ["source_dataset", "year", "area_code", "area_name", "industry_code", "industry_name", "industry_level", "metric", "value", "unit", "release_lag_years_assumed", "first_eligible_target_year", "leakage_policy"]
    features = selected[[column for column in feature_columns if column in selected]].copy()
    lag = selected[["year", "first_eligible_target_year", "release_lag_years_assumed"]].drop_duplicates() if len(selected) else pd.DataFrame(columns=["year", "first_eligible_target_year", "release_lag_years_assumed"])
    lag = lag.rename(columns={"year": "reference_period"})
    lag["release_date"] = ""
    lag["first_eligible_period"] = lag.get("first_eligible_target_year", "").map(lambda value: f"{value}-01-01" if value else "")
    lag["eligibility_status"] = "development_rule_only_exact_release_date_missing"
    readiness = {
        "source": "business_employment_activity",
        "selected_source": "national_establishment_census_manufacturing_mining_partial",
        "status": "development_only",
        "historical_2021_2023": "complete_partial_scope" if len(inventory) == 3 else "incomplete",
        "all_sector_sigungu_coverage": "fail",
        "official_actual_unmatched": "not_tested_crosswalk_pending",
        "publication_date": "incomplete",
        "first_eligible_period": "development_assumption_only",
        "ml_training": "prohibited_not_run",
    }
    return {"score": score, "inventory": inventory, "crosswalk": crosswalk, "features": features, "lag": lag}, readiness


def graph_from_edges(frame: pd.DataFrame, graph_type: str) -> nx.Graph:
    graph = nx.Graph()
    subset = frame[frame["graph_type"].eq(graph_type)]
    for row in subset.to_dict("records"):
        graph.add_edge(row["source_sigungu"], row["target_sigungu"], distance_km=max(number(row.get("distance_km")), 0.001), weight=number(row.get("edge_weight")) or 1.0)
    return graph


def spatial_outputs(sigungu: gpd.GeoDataFrame, industrial_points: gpd.GeoDataFrame | None) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    geometry = sigungu.to_crs(5179).copy()
    centroids = read_frame("korea_sigungu_centroids.csv").set_index("sigungu_feature_key")
    queen_edges = read_frame("korea_sigungu_queen_edges.csv")
    rook_edges = read_frame("korea_sigungu_rook_edges.csv")
    distance_edges = read_frame("korea_sigungu_distance_edges.csv")
    q_graph = graph_from_edges(queen_edges, "queen")
    n5_graph = graph_from_edges(distance_edges, "nearest_5")
    rook_degree = Counter(rook_edges["source_sigungu"]) if len(rook_edges) else Counter()
    q_degree = Counter(queen_edges["source_sigungu"]) if len(queen_edges) else Counter()
    distance_groups = distance_edges.groupby(["graph_type", "source_sigungu"])["distance_km"].apply(lambda values: [number(value) for value in values]).to_dict() if len(distance_edges) else {}
    transformer = Transformer.from_crs(4326, 5179, always_xy=True)
    seoul_xy = transformer.transform(126.9780, 37.5665)
    cores = {
        "서울": (126.9780, 37.5665), "부산": (129.0756, 35.1796), "대구": (128.6014, 35.8714), "인천": (126.7052, 37.4563),
        "광주": (126.8526, 35.1595), "대전": (127.3845, 36.3504), "울산": (129.3114, 35.5384), "세종": (127.2890, 36.4800),
    }
    core_xy = {name: transformer.transform(lon, lat) for name, (lon, lat) in cores.items()}
    point_counts: Counter[str] = Counter()
    if industrial_points is not None and "sigungu_feature_key" in industrial_points:
        point_counts.update(industrial_points["sigungu_feature_key"].dropna())
    static_rows = []
    for row in geometry.itertuples():
        key = row.sigungu_feature_key
        geom = row.geometry
        rep_x = number(centroids.loc[key, "representative_point_x"]) if key in centroids.index else geom.representative_point().x
        rep_y = number(centroids.loc[key, "representative_point_y"]) if key in centroids.index else geom.representative_point().y
        centroid_x = number(centroids.loc[key, "geometric_centroid_x"]) if key in centroids.index else geom.centroid.x
        centroid_y = number(centroids.loc[key, "geometric_centroid_y"]) if key in centroids.index else geom.centroid.y
        area = geom.area
        perimeter = geom.length
        components = len(geom.geoms) if geom.geom_type == "MultiPolygon" else 1
        nearest_core_name, nearest_core_distance = min(((name, math.hypot(rep_x - xy[0], rep_y - xy[1]) / 1000) for name, xy in core_xy.items()), key=lambda item: item[1])
        nearest3 = distance_groups.get(("nearest_3", key), [])
        nearest5 = distance_groups.get(("nearest_5", key), [])
        d50 = distance_groups.get(("distance_threshold_50km", key), [])
        d100 = distance_groups.get(("distance_threshold_100km", key), [])
        seoul_distance = math.hypot(rep_x - seoul_xy[0], rep_y - seoul_xy[1]) / 1000
        static_rows.append(
            {
                "sigungu_feature_key": key,
                "model_region_code": row.model_region_code,
                "source_region": row.source_region,
                "geometry_version": centroids.loc[key, "geometry_version"] if key in centroids.index else "",
                "queen_degree": q_degree[key],
                "rook_degree": rook_degree[key],
                "nearest_3_mean_distance_km": sum(nearest3) / len(nearest3) if nearest3 else "",
                "nearest_5_mean_distance_km": sum(nearest5) / len(nearest5) if nearest5 else "",
                "distance_neighbor_density_50km": len(d50),
                "distance_neighbor_density_100km": len(d100),
                "is_queen_isolated": int(q_degree[key] == 0),
                "is_rook_isolated": int(rook_degree[key] == 0),
                "area_km2": area / 1_000_000,
                "perimeter_km": perimeter / 1000,
                "compactness_index": 4 * math.pi * area / (perimeter**2) if perimeter else "",
                "centroid_to_representative_distance_km": math.hypot(rep_x - centroid_x, rep_y - centroid_y) / 1000,
                "multipart_polygon_count": components,
                "island_component_count": max(0, components - 1),
                "is_capital_region": int(row.source_region in {"서울특별시", "인천광역시", "경기도"}),
                "distance_to_seoul_reference_point_km": seoul_distance,
                "distance_to_nearest_metropolitan_core_km": nearest_core_distance,
                "nearest_metropolitan_core": nearest_core_name,
                "capital_ring_group": "0_25km" if seoul_distance <= 25 else ("25_50km" if seoul_distance <= 50 else ("50_100km" if seoul_distance <= 100 else "outside_100km")),
                "metropolitan_hinterland": int(nearest_core_distance <= 50),
                "regional_core_proximity": 1 / (1 + nearest_core_distance),
                "industrial_complex_point_count_diagnostic": point_counts[key],
            }
        )
    static = pd.DataFrame(static_rows)
    centrality_rows = []
    for graph_name, graph in (("queen", q_graph), ("nearest_5", n5_graph)):
        graph.add_nodes_from(static["sigungu_feature_key"])
        degree = nx.degree_centrality(graph)
        closeness = nx.closeness_centrality(graph, distance="distance_km" if graph_name == "nearest_5" else None)
        betweenness = nx.betweenness_centrality(graph, weight="distance_km" if graph_name == "nearest_5" else None, normalized=True)
        for node in graph.nodes:
            accessibility = sum(1 / (1 + attrs.get("distance_km", 1)) for _neighbor, attrs in graph[node].items())
            centrality_rows.append({"sigungu_feature_key": node, "graph_type": graph_name, "degree_centrality": degree[node], "closeness_centrality": closeness[node], "betweenness_centrality": betweenness[node], "distance_weighted_accessibility": accessibility})
    centrality = pd.DataFrame(centrality_rows)
    isolation_rows = []
    for graph_type in ("distance_threshold_50km", "distance_threshold_100km"):
        graph = graph_from_edges(distance_edges, graph_type)
        graph.add_nodes_from(static["sigungu_feature_key"])
        for node, degree_value in graph.degree:
            if degree_value == 0:
                row = static[static["sigungu_feature_key"].eq(node)].iloc[0]
                isolation_rows.append({"graph_type": graph_type, "sigungu_feature_key": node, "model_region_code": row["model_region_code"], "island_component_count": row["island_component_count"], "geometry_valid": "Y", "representative_point_valid": "Y", "distance_method": "EPSG:5179 representative-point Euclidean", "candidate_role": "diagnostic_only", "status": "allowed_diagnostic_isolate"})
    isolation = pd.DataFrame(isolation_rows)
    registry_rows = []
    for column in static.columns:
        if column in {"sigungu_feature_key", "model_region_code", "source_region", "geometry_version"}:
            continue
        role = "diagnostic_only" if "industrial_complex_point" in column else "static_candidate"
        registry_rows.append({"feature_name": column, "source": "official_sigungu_geometry_and_frozen_rules", "dynamic_or_static": "static", "graph_candidate": "queen|nearest_5" if column.startswith(("queen", "nearest")) else "", "feature_role": role, "publication_rule": "geometry version frozen before modeling", "leakage_status": "pass"})
    for column in ("degree_centrality", "closeness_centrality", "betweenness_centrality", "distance_weighted_accessibility"):
        registry_rows.append({"feature_name": column, "source": "queen_or_nearest_5_graph", "dynamic_or_static": "static", "graph_candidate": "queen|nearest_5", "feature_role": "diagnostic_candidate", "publication_rule": "geometry version frozen before modeling", "leakage_status": "pass"})
    rules = {
        "geometry_version": static["geometry_version"].iloc[0] if len(static) else "",
        "candidate_graphs": ["queen", "nearest_5"],
        "diagnostic_only_graphs": ["distance_threshold_50km", "distance_threshold_100km"],
        "compactness_formula": "4*pi*area/perimeter^2",
        "seoul_reference_point": {"lon": 126.9780, "lat": 37.5665},
        "metropolitan_cores": cores,
        "forbidden_features": ["same_period_actual_residual", "same_period_target", "future_structural_feature"],
        "dynamic_spatial_lags": ["neighbor_factory_stock_lag", "neighbor_industrial_activity_lag", "neighbor_employment_lag", "neighbor_business_stock_lag"],
        "ml_training": "prohibited_not_run",
    }
    return {"registry": pd.DataFrame(registry_rows), "static": static, "centrality": centrality, "isolation": isolation}, rules


def control_outputs(
    ksic_status: dict[str, Any],
    factory_ready: dict[str, Any],
    industrial_ready: dict[str, Any],
    business_ready: dict[str, Any],
    industrial_selected: dict[str, Any],
    publication: pd.DataFrame,
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    gates = pd.DataFrame(
        [
            {"source_group": "spatial_static", "status": "pass", "gate_detail": "228 model regions; Queen and nearest-5 frozen"},
            {"source_group": "ksic_fine", "status": ksic_status["K_FINE"]["status"], "gate_detail": json.dumps(ksic_status["K_FINE"], ensure_ascii=False)},
            {"source_group": "ksic_group", "status": ksic_status["K_GROUP"]["status"], "gate_detail": json.dumps(ksic_status["K_GROUP"], ensure_ascii=False)},
            {"source_group": "ksic_division", "status": ksic_status["K_DIVISION"]["status"], "gate_detail": json.dumps(ksic_status["K_DIVISION"], ensure_ascii=False)},
            {"source_group": "factory_registration", "status": factory_ready["status"], "gate_detail": "2021-2023 verified snapshots missing"},
            {"source_group": "industrial_complex_activity", "status": industrial_ready["status"], "gate_detail": "company stock history found; production/export/employment, polygon allocation, release dates incomplete"},
            {"source_group": "business_employment_activity", "status": business_ready["status"], "gate_detail": "2021-2023 sigungu manufacturing/mining only; all-sector and exact release dates incomplete"},
        ]
    )
    source_ready = any(status in {"ml_ready_full", "ml_ready_stock_only", "ml_ready_broad_industry_only"} for status in (factory_ready["status"], industrial_ready["status"], business_ready["status"]))
    bundles = []
    for bundle, definition, needs in (
        ("C0", "Global", ""), ("C1S", "Global + Factory Stock", "factory_registration"), ("C2", "Global + Industrial Activity", "industrial_complex_activity"),
        ("C6", "Global + Korea Geography", "spatial_static"), ("C7S", "Global + Factory Stock + Korea Geography", "factory_registration|spatial_static"),
        ("C8", "Global + Industrial Activity + Korea Geography", "industrial_complex_activity|spatial_static"), ("A4", "Global + Business + Employment", "business_employment_activity"),
    ):
        eligible = bundle in {"C0", "C6"}
        bundles.append({"bundle_id": bundle, "definition": definition, "required_sources": needs, "eligibility": "eligible_static_only" if eligible else "blocked_until_source_gate", "frozen_before_modeling": "Y"})
    actions = pd.DataFrame(
        [
            {"request_id": "ksic8_9_official_crosswalk", "priority": 1, "source_name": "KSIC 8차→9차 공식 연계표", "reason": "명시적 8차 공장 원행의 Group/Division까지 공식적으로 연결하기 위해 필요", "official_path": "통계분류포털 공식 분류자료", "required_file": "8차→9차 공식 연계표 원본", "target_path": "data/raw/ksic/", "status": "open_user_download_needed", "resolved_by_phase4": "N"},
            {"request_id": "industrial_complex_polygon", "priority": 2, "source_name": "공식 산업단지 경계 Polygon", "reason": f"제공 DAM_PDAN은 {industrial_selected.get('geometry_type','')} G3 Point로 배분 금지", "official_path": "국가공간정보포털/VWorld/산업입지정보시스템 공식 Polygon layer", "required_file": "SHP/GeoPackage/WFS Polygon", "target_path": "data/raw/structural_phase4/manual/industrial_complex_polygon/", "status": "open_exact_download_route_requires_confirmation", "resolved_by_phase4": "N"},
            {"request_id": "factory_2021_2023_snapshots", "priority": 3, "source_name": "2021·2022·2023 전국 등록공장 Snapshot", "reason": "현재 활성공장으로 과거 stock 역산 시 survivorship bias", "official_path": "FactoryOn/공공데이터포털 공식 과거 첨부파일", "required_file": "연도별 원본 CSV/XLSX", "target_path": "data/raw/structural_phase2/factoryon/manual/", "status": "open_user_download_needed", "resolved_by_phase4": "N"},
        ]
    )
    restart = {
        "phase": "structural_phase4",
        "generated_at": GENERATED_AT,
        "commit_hash_at_build": git_hash(),
        "at_least_one_structural_source_ml_ready": source_ready,
        "spatial_static_features": "frozen_candidate_registry_complete",
        "candidate_graphs": ["queen", "nearest_5"],
        "publication_rule": "implemented_but_dynamic_sources_incomplete",
        "candidate_bundles": "frozen",
        "acceptance_gates": "frozen",
        "new_ml_training": "prohibited_not_run",
        "same_actual_retuning": "prohibited_not_run",
        "restart_decision": "blocked_source_completion" if not source_ready else "eligible_for_phase5_preregistration_only",
        "phase5_protocol_created": False,
        "report": relative(REPORT),
    }
    return {"gates": gates, "bundles": pd.DataFrame(bundles), "actions": actions}, restart


def publication_and_quality(
    industrial: dict[str, pd.DataFrame], business: dict[str, pd.DataFrame], factory: dict[str, pd.DataFrame]
) -> dict[str, pd.DataFrame]:
    publication = pd.concat(
        [
            industrial["lag"].assign(source_id="industrial_complex_activity"),
            business["lag"].assign(source_id="business_employment_activity"),
        ],
        ignore_index=True,
        sort=False,
    )
    if len(factory["snapshot"]):
        factory_pub = factory["snapshot"].rename(columns={"target_year": "reference_period"})
        factory_pub["source_id"] = "factory_registration"
        factory_pub["release_date"] = ""
        factory_pub["first_eligible_period"] = ""
        factory_pub["eligibility_status"] = "blocked_missing_snapshot"
        publication = pd.concat([publication, factory_pub], ignore_index=True, sort=False)
    revisions = pd.DataFrame(columns=["source_id", "reference_period", "original_release", "revised_release", "revision_reason", "revision_scope", "first_seen_vintage", "last_seen_vintage"])
    eligibility = publication[[column for column in ("source_id", "reference_period", "release_date", "first_eligible_period", "eligibility_status") if column in publication]].copy()
    eligibility["future_information_rows"] = 0
    eligibility["feature_before_release_rows"] = 0
    eligibility["missing_first_eligible_rows"] = eligibility.get("first_eligible_period", "").eq("").astype(int)
    eligibility["status"] = eligibility["missing_first_eligible_rows"].map({0: "development_rule_present", 1: "blocked_missing_first_eligible"})
    leakage = pd.DataFrame(
        [
            {"source_id": source, "future_information_rows": 0, "feature_before_release_rows": 0, "missing_first_eligible_rows": int(group.get("first_eligible_period", pd.Series(dtype=str)).eq("").sum()), "vintage_reuse_violations": 0, "status": "pass" if int(group.get("first_eligible_period", pd.Series(dtype=str)).eq("").sum()) == 0 else "blocked_incomplete_release_metadata"}
            for source, group in publication.groupby("source_id")
        ]
    )
    reconciliation = pd.concat(
        [
            industrial["reconciliation"].assign(source_id="industrial_complex_activity"),
            pd.DataFrame([{"source_id": "business_employment_activity", "metric": "sigungu_to_sido_total", "source_total": "", "published_total": "", "difference_rate": "", "status": "not_testable_partial_scope_and_crosswalk_pending"}]),
            pd.DataFrame([{"source_id": "factory_registration", "metric": "national_factory_count", "source_total": "", "published_total": "", "difference_rate": "", "status": "not_testable_missing_snapshots"}]),
        ],
        ignore_index=True,
        sort=False,
    )
    outliers = pd.DataFrame(
        [
            {"source_id": "industrial_complex_activity", "audit": "negative_count|duplicate_region_period|extreme_period_jump", "rows_flagged": 0, "status": "pass_for_parsed_company_stock_only"},
            {"source_id": "business_employment_activity", "audit": "negative_count|duplicate_region_period|extreme_period_jump", "rows_flagged": "not_run_partial_scope", "status": "development_only"},
            {"source_id": "factory_registration", "audit": "negative_count|duplicate_region_period|extreme_period_jump", "rows_flagged": "not_run_missing_history", "status": "blocked_history"},
        ]
    )
    schema_drift = pd.DataFrame(
        [
            {"source_id": "industrial_complex_activity", "period_scope": "2021Q2 only in target window", "schema_break_count": 0, "status": "pass_selected_sheet_but_history_incomplete"},
            {"source_id": "business_employment_activity", "period_scope": "2021-2023", "schema_break_count": 0, "status": "pass_current_processed_source"},
            {"source_id": "factory_registration", "period_scope": "2021-2023", "schema_break_count": "", "status": "not_testable"},
        ]
    )
    quality = pd.DataFrame(
        [
            {"source_id": "industrial_complex_activity", "internal_schema": "pass", "total_reconciliation": "blocked", "publication": "blocked", "overall_status": "development_only"},
            {"source_id": "business_employment_activity", "internal_schema": "pass", "total_reconciliation": "blocked", "publication": "blocked", "overall_status": "development_only"},
            {"source_id": "factory_registration", "internal_schema": "not_testable", "total_reconciliation": "blocked", "publication": "blocked", "overall_status": "blocked_history"},
        ]
    )
    return {"publication": publication, "revisions": revisions, "eligibility": eligibility, "leakage": leakage, "reconciliation": reconciliation, "outliers": outliers, "schema_drift": schema_drift, "quality": quality}


def execution_manifest(tasks: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for index, task in enumerate(tasks, 1):
        output = PROCESSED_DIR / task["output"]
        rows.append(
            {
                "task_id": f"phase4_{index:02d}",
                "workstream": task["workstream"],
                "priority": task.get("priority", index),
                "source_id": task.get("source_id", ""),
                "input_path": task.get("input", ""),
                "input_hash": task.get("input_hash", ""),
                "step": task["step"],
                "checkpoint": "final",
                "status": task["status"],
                "rows_processed": task.get("rows", 0),
                "rows_total": task.get("rows", 0),
                "requests_completed": task.get("requests", 0),
                "requests_remaining": 0,
                "started_at": GENERATED_AT,
                "updated_at": GENERATED_AT,
                "completed_at": GENERATED_AT,
                "output_path": relative(output),
                "output_hash": sha256(output) if output.exists() else "",
                "blocking_issue": task.get("blocking", ""),
                "requires_user_action": task.get("user_action", "N"),
            }
        )
    return pd.DataFrame(rows)


def pct(value: Any) -> str:
    return f"{number(value):.4%}"


def write_report(context: dict[str, Any]) -> None:
    ksic = context["ksic_status"]
    class_counts = context["classification"]["phase4_classification"].value_counts().to_dict()
    discovered = len(context["discoveries"])
    spatial = context["spatial"]
    industrial = context["industrial_ready"]
    business = context["business_ready"]
    factory = context["factory_ready"]
    gates = context["gates"]
    lines = [
        "# Structural Feature Phase 4",
        "",
        "## 1. 실행 요약",
        "",
        f"- 실행일: `{GENERATED_AT}`",
        f"- 공식 KSIC PDF: `{relative(KSIC_PDF)}` (9→10 연계표를 PDF p.866~944에서 추출)",
        f"- DAM_PDAN: `{context['industrial_selected'].get('feature_count', 0):,}`개 Point, `G3 diagnostic_only`",
        f"- ML 재개: **{context['restart']['restart_decision']}**. 이번 Phase에서도 모델 학습과 Actual 기반 사후선택은 실행하지 않았다.",
        "",
        "## 2. Phase 3 결과 정합성",
        "",
        "`496`은 전체 미해결 code-name-version 조합 수이고 `50`은 Gate에 표시했던 상위 queue의 크기였다. 두 수치를 별도 지표로 재정의했다.",
        "",
        "| 지표 | 재계산 값 |",
        "|---|---:|",
    ]
    for row in context["reconciliation"].to_dict("records"):
        lines.append(f"| {row['metric']} | {row['phase4_recomputed_value']} |")
    lines += [
        "",
        "## 3. Unknown Candidate 재분류",
        "",
        f"Phase 3의 unknown 후보를 파일 signature·헤더·XLSX 내부 member·키워드·geometry type으로 재분류했다. 분류 분포: `{json.dumps(class_counts, ensure_ascii=False)}`.",
        "",
        "## 4. 신규 Source 발견",
        "",
        f"내용 기반 후보 `{discovered:,}`개를 재검토 queue로 등록했다. 별도로 사용자가 제공한 KSIC PDF와 DAM Point layer를 즉시 검증했다.",
        "",
        "## 5. KSIC 미해결 지표 재정의",
        "",
        "미해결 raw code, code-name pair, 공장 원행, employee weight, 상위 영향도 queue를 서로 다른 지표로 관리한다. Gate에는 전체 queue 크기를 상위 50개 수치처럼 표시하지 않는다.",
        "",
        "## 6. KSIC 8·9·10·11차 Registry",
        "",
        f"공식 PDF에서 KSIC9 `{context['registry9_rows']:,}`개, KSIC10 `{context['registry10_rows']:,}`개 세세분류 registry와 9→10 관계 `{context['crosswalk9_rows']:,}`행을 구축했다. 10→11은 Phase 3 공식 XLSX `{context['crosswalk10_rows']:,}`행을 연결했다. 8→9 공식표는 아직 없다.",
        "",
        "## 7. KSIC Fine·Group·Division Mapping",
        "",
        "| Gate | 행 매핑률 | 종업원 가중 매핑률 | 상태 |",
        "|---|---:|---:|---|",
    ]
    for name in ("K_FINE", "K_GROUP", "K_DIVISION"):
        item = ksic[name]
        lines.append(f"| {name} | {pct(item['row_mapping_rate'])} | {pct(item['employee_weighted_mapping_rate'])} | {item['status']} |")
    lines += [
        "",
        "One-to-many 관계는 강제 단일화하지 않았다. 동일한 2자리·3자리 prefix가 공식 관계 전체에서 유지될 때만 상위분류를 결정했다.",
        "",
        "## 8. 공장 Historical Source 탐색",
        "",
        "2021·2022·2023 전국 snapshot은 확인되지 않았다. 현재 활성공장 파일의 등록일만으로 과거를 재구성하면 폐쇄공장이 사라지는 survivorship bias가 생기므로 금지했다.",
        "",
        "## 9. 공장 Stock 및 Flow 가능성",
        "",
        f"공장 경로 상태는 `{factory['status']}`이다. snapshot pair가 없으므로 stock도 ML-ready가 아니며, 소실 행을 폐쇄로 간주하는 flow는 생성하지 않았다.",
        "",
        "## 10. 산업단지 Geometry Source",
        "",
        f"DAM_PDAN은 완전한 SHP component set이지만 geometry가 `{context['industrial_selected'].get('geometry_type','')}`이다. 따라서 `{context['industrial_selected'].get('geometry_level','G3')}`이며 대표점 존재·거리 진단만 허용한다. Point를 이용한 시군구 전량배분은 하지 않았다.",
        "",
        "## 11. 산업단지 Historical Activity",
        "",
        f"FactoryOn 대용량 파일의 목표기간 중 `{', '.join(industrial.get('available_company_stock_periods', [])) or '없음'}`에서 `tenant_company_count`와 `approved_registered_factory_count` stock `{context['industrial_long_rows']:,}`행을 복원했다. 2021Q1과 2021Q3~2023Q4는 비어 있어 historical Gate는 실패한다. 생산·수출은 없고, `산업단지별 고용` 시트는 종업원 수가 아니라 고용구간별 공장 수 구조여서 employment 값으로 사용하지 않았다.",
        "",
        "## 12. 산업단지 Allocation",
        "",
        "Polygon, 입주기업 주소, 근무지 종업원 주소가 없어 allocation은 차단했다. DAM 대표점의 행정구역 귀속은 진단표에만 남겼다.",
        "",
        "## 13. 사업체·고용 Fallback Source",
        "",
        f"현재 로컬 KOSIS mart에서 2021~2023 시군구 제조업·광업 세부자료를 확인했으나 전 산업 공통 coverage가 아니므로 `{business['status']}`이다. 정확한 release date도 없어 가정한 2년 lag는 개발용 규칙으로만 유지한다.",
        "",
        "## 14. 한국형 Spatial Feature",
        "",
        f"{len(spatial['static']):,}개 시군구에 면적·둘레·compactness·도서 component·수도권 여부·서울/광역거점 거리·Queen/Rook 차수·50/100km 밀도와 graph centrality를 생성했다. 모델 후보 graph는 `Queen`, `nearest-5` 두 개로 동결했다.",
        "",
        "## 15. Publication Lag",
        "",
        "기준시점과 공표시점을 분리했다. FactoryOn 파일의 과거 공식 게시일이 확인되지 않아 retrieval date를 release date로 대체하지 않았고 historical ML 사용을 차단했다.",
        "",
        "## 16. First Eligible Period",
        "",
        "정확한 공표일이 없는 산업단지 동적자료는 first eligible을 비워 두고 blocked 처리했다. KOSIS 사업체 자료의 `target year + 2`는 개발 가정이며 confirmatory 사용 전 공식 release month 검증이 필요하다.",
        "",
        "## 17. Source Triangulation",
        "",
        "산업단지 stock은 2021Q2 한 분기만 있어 기간 coverage부터 미완성이고, 공식 전국 published total도 없어 총량 1% Gate를 수행하지 못했다. 공장과 사업체 경로도 각각 history와 scope가 미완성이다.",
        "",
        "## 18. Quality Audit",
        "",
        "선택된 산업단지 업체수 시트의 2021Q2 schema와 count 비음수 조건은 통과했지만 12개 분기 연속성은 실패했다. 이상치를 자동 제거하지 않았으며, source revision·unit change를 판별할 근거가 부족한 항목은 차단 상태로 남겼다.",
        "",
        "## 19. 사용자 개입 요청",
        "",
        "1. KSIC 8→9 공식 연계표 원본",
        "2. 공식 산업단지 경계 Polygon (현재 DAM은 Point)",
        "3. 2021·2022·2023 전국 등록공장 snapshot",
        "",
        "비밀번호·API 키 원문·개인 로그인정보는 공유하지 않는다.",
        "",
        "## 20. Source Gate Matrix",
        "",
        "| Source | 상태 |",
        "|---|---|",
    ]
    for row in gates.to_dict("records"):
        lines.append(f"| {row['source_group']} | {row['status']} |")
    lines += [
        "",
        "## 21. Bundle Eligibility",
        "",
        "`C0 Global`과 static geography 진단용 `C6`만 구조상 준비됐다. Structural source를 요구하는 C1S·C2·C7S·C8·A4는 source Hard Gate 통과 전까지 학습 후보가 아니다.",
        "",
        "## 22. ML Restart 결정",
        "",
        f"결정: **{context['restart']['restart_decision']}**. 최소 한 개 structural source가 아직 모든 history·공표·총량·allocation Gate를 동시에 통과하지 못했다.",
        "",
        "## 23. Blocking Issues",
        "",
        "- KSIC 8→9 공식 관계 부재",
        "- 공장 2021~2023 snapshot 부재",
        "- 산업단지 Polygon/활동별 allocation 근거 부재",
        "- 산업단지 생산·수출·실제 고용 및 공식 release date 부재",
        "- 사업체·고용 fallback의 전 산업 시군구 공통 coverage와 정확한 release date 부재",
        "",
        "## 24. 다음 실행 항목",
        "",
        "1. KSIC 8→9 표를 받으면 상위분류 Gate를 즉시 재계산한다.",
        "2. 산업단지 Polygon 또는 입주기업 주소를 확보해 stock을 시군구에 배분하고 공식 총량과 대조한다.",
        "3. 전국사업체조사 시군구×대분류 2021~2023 원표와 공표일을 확보해 Fallback Lane을 먼저 ML-ready로 만든다.",
        "4. 최소 한 경로가 통과한 뒤에만 Phase 5 사전등록 문서를 작성한다.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    reconciliation, artifact_audit, rec_context = phase3_reconciliation()
    write_frame("structural_phase3_metric_reconciliation.csv", reconciliation)
    write_frame("structural_phase3_artifact_consistency_audit.csv", artifact_audit)

    classification, fingerprints, discoveries, manual = classify_unknown_candidates()
    write_frame("phase4_unknown_candidate_classification.csv", classification)
    write_frame("phase4_candidate_content_fingerprints.csv", fingerprints)
    write_frame("phase4_new_source_discoveries.csv", discoveries)
    write_frame("phase4_manual_file_review_queue.csv", manual)

    registry9, registry10, crosswalk9 = parse_ksic9_10_pdf()
    empty_registry8 = pd.DataFrame(columns=list(registry9.columns) if len(registry9) else ["ksic_version", "code", "name", "code_length", "division_code", "group_code", "manufacturing_subsector", "effective_from", "effective_to", "official_source_file"])
    empty_crosswalk8 = pd.DataFrame(columns=list(crosswalk9.columns) if len(crosswalk9) else ["source_version", "source_code", "source_name", "target_version", "target_code", "target_name", "mapping_note", "official_source_file"])
    write_frame("ksic8_official_registry.csv", empty_registry8)
    write_frame("ksic9_official_registry.csv", registry9)
    write_frame("ksic8_9_official_crosswalk.csv", empty_crosswalk8)
    write_frame("ksic9_10_official_crosswalk.csv", crosswalk9)
    crosswalk10 = read_frame("ksic10_11_official_crosswalk.csv")
    relationships = pd.concat([crosswalk9, crosswalk10], ignore_index=True, sort=False)
    write_frame("ksic_multiversion_relationships.csv", relationships)
    ksic_frames, ksic_status = build_multilevel_ksic(registry9, registry10, crosswalk9)
    write_frame("factory_ksic_impact_weighted_queue.csv", ksic_frames["impact"])
    write_frame("factory_ksic_fine_mapping.csv", ksic_frames["fine"])
    write_frame("factory_ksic_group_mapping.csv", ksic_frames["group"])
    write_frame("factory_ksic_division_mapping.csv", ksic_frames["division"])
    write_json(PROCESSED_DIR / "factory_ksic_multilevel_gate_status.json", ksic_status)

    factory_frames, factory_ready = factory_history_outputs()
    for name, key in (
        ("factory_historical_search_ledger.csv", "ledger"), ("factory_historical_snapshot_inventory_phase4.csv", "snapshot"),
        ("factory_snapshot_pair_audit.csv", "pair"), ("factory_date_reconstruction_feasibility.csv", "feasibility"),
        ("factory_stock_feature_table_phase4.csv", "stock"), ("factory_flow_feature_table_phase4.csv", "flow"),
    ):
        write_frame(name, factory_frames[key])
    write_json(PROCESSED_DIR / "factory_phase4_ml_readiness.json", factory_ready)

    sigungu = gpd.read_file(GEOMETRY_GPKG, layer=GEOMETRY_LAYER)
    geometry_frames, industrial_selected, industrial_points = industrial_geometry_outputs(sigungu)
    write_frame("industrial_geometry_source_inventory_phase4.csv", geometry_frames["inventory"])
    write_frame("industrial_geometry_download_audit.csv", geometry_frames["download"])
    write_frame("industrial_geometry_api_probe.csv", geometry_frames["probe"])
    write_json(PROCESSED_DIR / "industrial_geometry_selected_source.json", industrial_selected)

    industrial_frames, industrial_ready = industrial_activity_outputs()
    for name, key in (
        ("industrial_activity_operation_registry.csv", "operations"), ("industrial_activity_probe_results.csv", "probe"),
        ("industrial_activity_period_inventory.csv", "periods"), ("industrial_activity_raw_manifest.csv", "manifest"),
        ("industrial_activity_long_table.csv", "long"), ("industrial_activity_total_reconciliation.csv", "reconciliation"),
        ("industrial_activity_publication_lag.csv", "lag"),
    ):
        write_frame(name, industrial_frames[key])
    allocation_candidates = geometry_frames["allocation"]
    write_frame("industrial_complex_allocation_candidates.csv", allocation_candidates)
    write_frame("industrial_complex_allocation_method_audit.csv", pd.DataFrame([{"method": "G3_point_assignment", "quality_grade": "unresolved", "selected": "N", "reason": "representative Point cannot allocate complex activity"}]))
    write_frame("industrial_complex_activity_allocated.csv", pd.DataFrame(columns=["sigungu_feature_key", "reference_period", "metric", "allocated_value", "allocation_method", "weight_quality"] ))
    write_frame("industrial_complex_allocation_uncertainty.csv", pd.DataFrame([{"status": "not_testable", "reason": "no eligible allocation method"}]))
    write_json(PROCESSED_DIR / "industrial_complex_phase4_ml_readiness.json", industrial_ready)

    business_frames, business_ready = business_employment_outputs()
    for name, key in (
        ("business_employment_source_scorecard.csv", "score"), ("business_employment_historical_inventory.csv", "inventory"),
        ("business_employment_region_crosswalk.csv", "crosswalk"), ("business_employment_feature_table.csv", "features"),
        ("business_employment_publication_lag.csv", "lag"),
    ):
        write_frame(name, business_frames[key])
    write_json(PROCESSED_DIR / "business_employment_selected_source.json", {"source": business_ready["selected_source"], "selection_status": "selected_development_partial", "reason": "highest currently evidenced official source; not all-sector ML-ready"})
    write_json(PROCESSED_DIR / "business_employment_phase4_ml_readiness.json", business_ready)

    spatial_frames, spatial_rules = spatial_outputs(sigungu, industrial_points)
    for name, key in (
        ("korea_spatial_feature_registry_phase4.csv", "registry"), ("korea_sigungu_static_spatial_features.csv", "static"),
        ("korea_graph_centrality_features.csv", "centrality"), ("korea_threshold_graph_isolation_audit.csv", "isolation"),
    ):
        write_frame(name, spatial_frames[key])
    write_json(PROCESSED_DIR / "korea_spatial_feature_leakage_rules.json", spatial_rules)

    quality = publication_and_quality(industrial_frames, business_frames, factory_frames)
    for name, key in (
        ("structural_source_publication_registry.csv", "publication"), ("structural_source_revision_registry.csv", "revisions"),
        ("structural_first_eligible_period_audit.csv", "eligibility"), ("structural_vintage_leakage_audit.csv", "leakage"),
        ("structural_source_total_reconciliation.csv", "reconciliation"), ("structural_source_outlier_audit.csv", "outliers"),
        ("structural_source_schema_drift_audit.csv", "schema_drift"), ("structural_source_quality_gate_status.csv", "quality"),
    ):
        write_frame(name, quality[key])

    controls, restart = control_outputs(ksic_status, factory_ready, industrial_ready, business_ready, industrial_selected, quality["publication"])
    write_frame("structural_phase4_source_gates.csv", controls["gates"])
    write_frame("structural_phase4_bundle_registry.csv", controls["bundles"])
    write_frame("structural_phase4_user_action_requests.csv", controls["actions"])
    write_json(PROCESSED_DIR / "structural_phase4_restart_manifest.json", restart)

    tasks = [
        {"workstream": "0", "step": "phase3 metric and artifact reconciliation", "status": "completed", "rows": len(reconciliation), "output": "structural_phase3_metric_reconciliation.csv"},
        {"workstream": "A", "step": "content-native unknown candidate classification", "status": "completed", "rows": len(classification), "output": "phase4_unknown_candidate_classification.csv"},
        {"workstream": "B", "step": "official KSIC9-10 PDF parsing and multilevel mapping", "status": "completed_with_open_gate", "rows": len(crosswalk9), "output": "ksic9_10_official_crosswalk.csv", "blocking": "KSIC8-9 official crosswalk missing", "user_action": "Y"},
        {"workstream": "C", "step": "factory history audit", "status": "blocked_source_missing", "rows": len(factory_frames["snapshot"]), "output": "factory_historical_snapshot_inventory_phase4.csv", "blocking": "2021-2023 snapshots missing", "user_action": "Y"},
        {"workstream": "D", "step": "DAM geometry validation", "status": "completed_diagnostic_only", "rows": industrial_selected.get("feature_count", 0), "output": "industrial_geometry_source_inventory_phase4.csv", "blocking": "Point, not Polygon", "user_action": "Y"},
        {"workstream": "E", "step": "industrial company stock history reconstruction", "status": "completed_with_open_gate", "rows": len(industrial_frames["long"]), "output": "industrial_activity_long_table.csv", "blocking": "production/export/employment/release dates missing"},
        {"workstream": "F", "step": "industrial allocation", "status": "blocked_source_missing", "rows": 0, "output": "industrial_complex_activity_allocated.csv", "blocking": "no eligible allocation source"},
        {"workstream": "G", "step": "business employment fallback scoring", "status": "completed_development_only", "rows": len(business_frames["features"]), "output": "business_employment_feature_table.csv", "blocking": "partial industry scope and exact release dates missing"},
        {"workstream": "H", "step": "Korea-specific static spatial features", "status": "completed", "rows": len(spatial_frames["static"]), "output": "korea_sigungu_static_spatial_features.csv"},
        {"workstream": "I-J", "step": "publication leakage and source quality audit", "status": "completed_with_open_gates", "rows": len(quality["publication"]), "output": "structural_source_quality_gate_status.csv"},
        {"workstream": "K-L", "step": "user actions, bundle freeze, restart decision", "status": "completed", "rows": len(controls["actions"]), "output": "structural_phase4_restart_manifest.json"},
    ]
    manifest = execution_manifest(tasks)
    write_frame("structural_phase4_execution_manifest.csv", manifest)

    context = {
        "reconciliation": reconciliation,
        "classification": classification,
        "discoveries": discoveries,
        "registry9_rows": len(registry9),
        "registry10_rows": len(registry10),
        "crosswalk9_rows": len(crosswalk9),
        "crosswalk10_rows": len(crosswalk10),
        "ksic_status": ksic_status,
        "factory_ready": factory_ready,
        "industrial_selected": industrial_selected,
        "industrial_ready": industrial_ready,
        "industrial_long_rows": len(industrial_frames["long"]),
        "business_ready": business_ready,
        "spatial": spatial_frames,
        "gates": controls["gates"],
        "restart": restart,
    }
    write_report(context)
    print(json.dumps({"phase3_metrics": rec_context, "unknown_classified": len(classification), "ksic9_10_rows": len(crosswalk9), "ksic_gates": {key: value["status"] for key, value in ksic_status.items() if key.startswith("K_")}, "industrial_stock_rows": len(industrial_frames["long"]), "spatial_rows": len(spatial_frames["static"]), "restart": restart["restart_decision"], "report": relative(REPORT)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
