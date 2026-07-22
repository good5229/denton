# 경기버스 정류소별 승하차 원본 파일 자동화 점검

## 결론

- 경기데이터드림 `경기도 정류소 별 승하차 인원 집계`는 자동화 가능하다.
- `Sheet` 탭의 CSV 다운로드는 2025-06-01 하루 샘플 30,030행만 제공한다.
- 전체 원본은 `File` 탭의 ZIP 목록에서 `fileSeq`를 추출한 뒤 아래 endpoint로 직접 받을 수 있다.

```text
https://data.gg.go.kr/portal/data/file/downloadFileData.do?infId=MZCREO5CKHZM6PJEA55P37391662&infSeq=2&fileSeq={fileSeq}
```

## 페이지 구조

| 구분 | 확인 내용 |
|---|---|
| 랜딩 URL | `https://data.gg.go.kr/portal/data/service/selectServicePage.do?infId=MZCREO5CKHZM6PJEA55P37391662&infSeq=1` |
| Sheet 탭 | `infSeq=1`, `downloadSheetData.do`, 샘플 시트 |
| File 탭 | `infSeq=2`, 렌더링 후 ZIP 파일 목록 노출 |
| 활용목적 팝업 | `연구 (논문, 분석 등)` 라디오 존재 |
| 원본 ZIP endpoint | `/portal/data/file/downloadFileData.do` |

## 확인된 원본 파일 목록

렌더링된 File 탭에서 20개 파일이 확인되었다.

| 기간 | 정제상태 | fileSeq | 크기 |
|---:|---|---:|---:|
| 202603 | D-4 | 16315 | 14 MB |
| 202602 | D-45 | 16314 | 13 MB |
| 202601 | D-45 | 16154 | 14 MB |
| 202512 | D-45 | 16053 | 14 MB |
| 202511 | D-45 | 15812 | 14 MB |
| 202510 | D-45 | 15562 | 14 MB |
| 202509 | D-45 | 15385 | 14 MB |
| 202508 | D-45 | 15208 | 15 MB |
| 202507 | D-45 | 15018 | 15 MB |
| 202506 | D-45 | 14743 | 14 MB |
| 202505 | D-45 | 14605 | 15 MB |
| 202504 | D-45 | 14661 | 14 MB |
| 202503 | D-45 | 14659 | 14 MB |
| 202502 | D-45 | 14657 | 13 MB |
| 202501 | D-45 | 14655 | 14 MB |
| 2024 | D-45 | 14654 | 144 MB |
| 2023 | D-45 | 14672 | 133 MB |
| 2022 | D-45 | 14713 | 131 MB |
| 2021 | D-45 | 14742 | 158 MB |
| 2020 | D-45 | 14801 | 158 MB |

## 구현 산출물

- 목록/다운로드 스크립트: `scripts/collect_gg_bus_boarding_files.py`
- Selenium File 탭 렌더링 스크립트: `scripts/inspect_gg_bus_file_tab_selenium.py`
- Selenium 함수 추출 스크립트: `scripts/extract_gg_bus_download_js_selenium.py`
- 다운로드 manifest: `data/raw/phase58_gg_bus_auto/gg_bus_original_file_manifest.json`
- 테스트 다운로드 파일: `data/raw/phase58_gg_bus_auto/original_zips/경기도 정류소 별 승하차 인원 집계_202602_D-45.zip`

## 실행 예시

파일 목록만 확인:

```bash
python3 scripts/collect_gg_bus_boarding_files.py --list
```

최신 정제완료 월만 다운로드:

```bash
python3 scripts/collect_gg_bus_boarding_files.py --period 202602
```

전체 20개 파일 다운로드:

```bash
python3 scripts/collect_gg_bus_boarding_files.py --all
```

## 검증 결과

2026-02 정제완료 파일로 다운로드를 검증했다.

| 항목 | 값 |
|---|---:|
| 기간 | 202602 |
| fileSeq | 16314 |
| 다운로드 크기 | 13,588,559 bytes |
| ZIP 무결성 | 정상 (`ZipFile.testzip() == None`) |
| 내부 파일 | `CARD_STATION45_202602.tar` |

## 주의 사항

- 2026-03 파일은 `D-4`로 표기되어 최신 미정제/참고용일 가능성이 있으므로 분석·보고서에는 우선 `D-45` 파일을 쓰는 편이 안전하다.
- 원본 전체 수집 시 2020~2024 연도 파일이 각각 130~158MB 수준이라 전체 다운로드는 1GB 이상이 될 수 있다.
- 직접 HTML 요청만으로는 File 탭 목록이 안정적으로 나오지 않아, 현재 스크립트는 Selenium으로 저장한 File 탭 HTML cache를 fallback으로 사용한다.
