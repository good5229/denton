#!/usr/bin/env python3
"""Extract loaded JS function bodies for file download flow from the browser."""

from __future__ import annotations

import json
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


URL = "https://data.gg.go.kr/portal/data/service/selectServicePage.do?infId=MZCREO5CKHZM6PJEA55P37391662&infSeq=2"
OUT = Path("data/raw/phase58_gg_bus_auto/selenium_file_tab")
DRIVER = ".tools/chromedriver-150/chromedriver-mac-arm64/chromedriver"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    opts = Options()
    opts.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1600,2200")
    driver = webdriver.Chrome(service=Service(DRIVER), options=opts)
    try:
        driver.get(URL)
        time.sleep(10)
        script = """
        const names = [
          'downloadFile','showDsUsePurp','changeTab',
          'insertDownloadHist','fn_fileDownload','fileDownload',
          'downloadFileData','downloadDocData','checkGridCnt',
          'ajaxCall','showAlert','showConfirm'
        ];
        const out = {};
        for (const n of names) {
          try { out[n] = (typeof window[n] === 'function') ? window[n].toString() : String(window[n]); }
          catch(e) { out[n] = 'ERR:' + e; }
        }
        out.fileButtons = Array.from(document.querySelectorAll('[data-action-key="fileDownloadBtn"]')).map(b => ({
          text: b.innerText, fileSeq: b.dataset.fileSeq,
          parentText: b.closest('li, tr, div')?.innerText
        }));
        out.forms = Array.from(document.querySelectorAll('form')).map(f => ({
          id: f.id, name: f.name, method: f.method, action: f.action,
          inputs: Array.from(f.querySelectorAll('input')).map(i => ({
            id: i.id, name: i.name, type: i.type, value: i.value
          }))
        }));
        return out;
        """
        data = driver.execute_script(script)
        (OUT / "download_js_extract.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({
            "functions": {k: (v[:80] if isinstance(v, str) else str(type(v))) for k, v in data.items() if k != "fileButtons" and k != "forms"},
            "file_buttons": len(data.get("fileButtons", [])),
            "first_buttons": data.get("fileButtons", [])[:5],
            "forms": data.get("forms", []),
            "out": str(OUT / "download_js_extract.json"),
        }, ensure_ascii=False, indent=2))
    finally:
        driver.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
