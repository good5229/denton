#!/usr/bin/env python3
"""Collect Goyang portal layers used by Phase134.

The downloaded CSV files are stored under data/raw and are intentionally ignored
by git.  This script records how to reproduce the free public collection of
high-gap sports/movie candidate layers.
"""

from __future__ import annotations

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "phase37_goyang_emd"
URL = "https://www.goyang.go.kr/bigdata/lvlhmap/getFeatureFile.do"
REFERRER = "https://www.goyang.go.kr/bigdata/lvlhmap/map.do"

LAYERS = {
    "LYR0084": "영화상영관",
    "LYR0099": "골프연습장업",
    "LYR0100": "골프장",
    "LYR0101": "당구장업",
    "LYR0102": "빙상장업",
    "LYR0103": "수영장업",
    "LYR0104": "승마장업",
    "LYR0105": "썰매장업",
    "LYR0106": "체육도장업",
    "LYR0107": "체력단련장업",
}


def download_layer(layer_id: str, title: str) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"goyang_layer_{layer_id}.csv"
    command = [
        "curl",
        "-sS",
        "-L",
        "-A",
        "Mozilla/5.0",
        "-e",
        REFERRER,
        "-X",
        "POST",
        "-d",
        f"lyrId={layer_id}&lyrTit={title}",
        URL,
        "-o",
        str(path),
    ]
    subprocess.run(command, check=True)
    return path


def main() -> None:
    for layer_id, title in LAYERS.items():
        path = download_layer(layer_id, title)
        print(f"{layer_id}\t{title}\t{path}\t{path.stat().st_size}")


if __name__ == "__main__":
    main()
