#!/usr/bin/env python3
"""Inspect Gyeonggi bus stop status page and extract OpenAPI hints."""

from __future__ import annotations

import json
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By


URL = "https://data.gg.go.kr/portal/data/service/selectServicePage.do?page=1&rows=10&sortColumn=&sortDirection=&infId=GDKWAGWYRKJYIRVX110226832213&infSeq=3"
OUT = Path("data/raw/phase60_gg_bus_stop_api")
DRIVER = ".tools/chromedriver-150/chromedriver-mac-arm64/chromedriver"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    opts = Options()
    opts.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1600,2400")
    opts.add_argument("--lang=ko-KR")
    driver = webdriver.Chrome(service=Service(DRIVER), options=opts)
    try:
        driver.get(URL)
        time.sleep(12)
        html = driver.page_source
        (OUT / "page.html").write_text(html, encoding="utf-8", errors="ignore")
        driver.save_screenshot(str(OUT / "page.png"))
        records = []
        for selector in ["a", "button", "input", "textarea", "pre", "code", "table", "[href]", "[onclick]"]:
            for el in driver.find_elements(By.CSS_SELECTOR, selector)[:1000]:
                try:
                    records.append(
                        {
                            "selector": selector,
                            "tag": el.tag_name,
                            "text": el.text[:1000],
                            "id": el.get_attribute("id"),
                            "class": el.get_attribute("class"),
                            "name": el.get_attribute("name"),
                            "href": el.get_attribute("href"),
                            "onclick": el.get_attribute("onclick"),
                            "value": el.get_attribute("value")[:500] if el.get_attribute("value") else "",
                            "displayed": el.is_displayed(),
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    records.append({"selector": selector, "error": repr(exc)})
        (OUT / "elements.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        text = driver.find_element(By.TAG_NAME, "body").text
        (OUT / "body.txt").write_text(text, encoding="utf-8", errors="ignore")
        print(json.dumps({
            "url": driver.current_url,
            "title": driver.title,
            "html_bytes": len(html.encode("utf-8")),
            "contains_openapi_gg": "openapi.gg.go.kr" in html,
            "contains_api_key": "KEY" in html or "Key" in html,
            "contains_wgs": "WGS" in html,
            "out": str(OUT),
        }, ensure_ascii=False, indent=2))
    finally:
        driver.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
