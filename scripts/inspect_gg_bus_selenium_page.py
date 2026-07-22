#!/usr/bin/env python3
"""Inspect the Gyeonggi Data Dream bus dataset page with Selenium."""

from __future__ import annotations

import json
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By


URL = "https://data.gg.go.kr/portal/data/service/selectServicePage.do?infId=MZCREO5CKHZM6PJEA55P37391662&infSeq=1"
OUT = Path("data/raw/phase58_gg_bus_auto/selenium_inspect")
DRIVER = ".tools/chromedriver-150/chromedriver-mac-arm64/chromedriver"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    options = Options()
    options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1600,2200")
    options.add_argument("--lang=ko-KR")
    options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": str((OUT / "downloads").resolve()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        },
    )
    driver = webdriver.Chrome(service=Service(DRIVER), options=options)
    try:
        driver.get(URL)
        time.sleep(8)
        html = driver.page_source
        (OUT / "page.html").write_text(html, encoding="utf-8", errors="ignore")
        driver.save_screenshot(str(OUT / "page.png"))
        records = []
        for selector in ["a", "button", "input", "label", "[onclick]", ".tab", "li"]:
            for i, el in enumerate(driver.find_elements(By.CSS_SELECTOR, selector)[:500]):
                try:
                    records.append(
                        {
                            "selector": selector,
                            "tag": el.tag_name,
                            "text": el.text[:300],
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
            "contains_file": "파일" in html,
            "contains_download": "다운로드" in html,
            "contains_research": "연구" in html,
            "elements": len(records),
            "out": str(OUT),
        }, ensure_ascii=False, indent=2))
    finally:
        driver.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
