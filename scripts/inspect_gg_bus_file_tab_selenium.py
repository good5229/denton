#!/usr/bin/env python3
"""Open the File tab of the Gyeonggi Data Dream bus dataset and inspect controls."""

from __future__ import annotations

import json
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By


URL = "https://data.gg.go.kr/portal/data/service/selectServicePage.do?infId=MZCREO5CKHZM6PJEA55P37391662&infSeq=1"
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
    opts.add_argument("--lang=ko-KR")
    driver = webdriver.Chrome(service=Service(DRIVER), options=opts)
    try:
        driver.get(URL)
        time.sleep(7)
        driver.execute_script("changeTab(2, document.querySelector('#tab_data_info_04 button'));")
        time.sleep(8)
        html = driver.page_source
        (OUT / "file_tab.html").write_text(html, encoding="utf-8", errors="ignore")
        driver.save_screenshot(str(OUT / "file_tab.png"))
        records = []
        for selector in ["a", "button", "input", "label", "form", "table", "[onclick]", "[href]"]:
            for el in driver.find_elements(By.CSS_SELECTOR, selector):
                try:
                    records.append(
                        {
                            "selector": selector,
                            "tag": el.tag_name,
                            "text": el.text[:500],
                            "id": el.get_attribute("id"),
                            "class": el.get_attribute("class"),
                            "name": el.get_attribute("name"),
                            "type": el.get_attribute("type"),
                            "href": el.get_attribute("href"),
                            "onclick": el.get_attribute("onclick"),
                            "value": el.get_attribute("value"),
                            "displayed": el.is_displayed(),
                            "enabled": el.is_enabled(),
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    records.append({"selector": selector, "error": repr(exc)})
        (OUT / "elements.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({
            "url": driver.current_url,
            "title": driver.title,
            "html_bytes": len(html.encode("utf-8")),
            "contains_file_seq": "fileSeq" in html,
            "contains_file_download": "fileDownload.do" in html,
            "contains_research": "연구" in html,
            "contains_download": "다운로드" in html,
            "out": str(OUT),
            "records": len(records),
        }, ensure_ascii=False, indent=2))
    finally:
        driver.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
