# 실행 요약

## 수집 데이터

| 파일 | 행 수 | 설명 |
|---|---:|---|
| `data/processed/annual_grva_real.csv` | 2,340 | 2019-2023년 시도별 경제활동별 지역내총부가가치(실질) |
| `data/processed/mining_manufacturing_production_index.csv` | 360 | 2019Q1-2023Q4 제조업 생산지수 원지수 |
| `data/processed/mining_production_index.csv` | 272 | 2019Q1-2023Q4 광업 생산지수 원지수 |
| `data/processed/electricity_gas_production_index.csv` | 360 | 2019Q1-2023Q4 전기업 및 가스업 생산지수 원지수 |
| `data/processed/service_production_index.csv` | 4,760 | 2019Q1-2023Q4 시도별 업종별 서비스업 불변지수 |
| `data/processed/construction_orders_by_region_type.csv` | 2,640 | 2013Q1-2023Q4 공사지역/공종별 건설수주액 |
| `data/processed/national_quarterly_gdp_real.csv` | 1,140 | 2019Q1-2023Q4 경제활동별 실질 GDP/GNI |
| `data/processed/national_quarterly_gdp_deflator.csv` | 360 | 2019Q1-2023Q4 경제활동별 GDP 디플레이터 |
| `data/processed/kosis_collected_all.csv` | 12,232 | 수집 데이터의 정규화 통합본 |

원시 API 응답은 `data/raw/*.json`에 저장했다. KOSIS 표 메타데이터는 `data/processed/kosis_*_metadata.csv`에 저장했다.

## 덴튼 추정

실행 스크립트: `scripts/denton_reci.py`

산출 파일:

| 파일 | 설명 |
|---|---|
| `data/processed/denton_quarterly_gva_estimates.csv` | 2019Q1-2023Q4 제조업·서비스업 분기 GVA 덴튼 배분값 |
| `data/processed/denton_2023_extrapolation_errors.csv` | 2023년 직전 BI 비율 외삽 추정치와 실제 2023년 연간 GVA 오차 |
| `data/processed/denton_error_summary.csv` | 전체 오차 요약 |
| `data/processed/all_industries_quarterly_gva_estimates.csv` | KOSIS 공개 업종 기준 전 업종 분기 GVA 덴튼 추정값 및 GDP 벤치마크 보정값 |
| `data/processed/all_industries_2023_extrapolation_errors.csv` | 전 업종 2023년 직전 BI 비율 외삽 추정치와 실제 2023년 연간 GVA 오차 |
| `data/processed/all_industries_error_summary.csv` | 전 업종 오차 요약 |

제조업·서비스업 1차 오차 요약:

| 검증 행 수 | MAE | MAPE |
|---:|---:|---:|
| 35 | 2,046,281.879933 백만원 | 2.572431% |

전 업종 확장 오차 요약:

| 검증 행 수 | MAE | MAPE | 누락 |
|---:|---:|---:|---:|
| 288 | 420,802.044095 백만원 | 7.332936% | 0 |

전국 GDP 벤치마크 보정:

- `all_industries_quarterly_gva_estimates.csv`의 `gdp_benchmarked_gva`는 1:1 대응되는 업종에서 17개 시도 합계가 전국 분기 GDP와 일치하도록 조정한 값이다.
- `G00` 도매 및 소매업과 `I00` 숙박 및 음식점업처럼 한국은행 GDP 표가 묶음 업종으로 제공하는 경우에는 임의 분할하지 않고 `gdp_benchmark_status`에 보정 제외 사유를 남겼다.
- 전국 행(`area_code=00`)은 참고용으로 유지했고, GDP 벤치마크 스케일링은 17개 시도 행에 적용했다.

절대 백분율 오차 상위 사례:

| 지역 코드 | 산업 | 실제 2023 | 외삽 추정 2023 | 오차율 |
|---|---|---:|---:|---:|
| 36 | 제조업 | 23,523,880 | 21,671,480.464555 | -7.874549% |
| 37 | 제조업 | 46,051,126 | 43,154,356.948983 | -6.290333% |
| 26 | 제조업 | 41,040,958 | 38,494,894.344962 | -6.203714% |
| 21 | 제조업 | 15,878,622 | 15,028,477.204968 | -5.354021% |
| 25 | 제조업 | 8,312,764 | 7,963,703.568079 | -4.199090% |

## 재실행 방법

`.env`에 `KOSIS_API_KEY`를 설정한 뒤:

```bash
python3 scripts/collect_kosis.py
python3 scripts/denton_reci.py
python3 scripts/denton_all_industries.py
```

주의: `.env`는 비밀값이므로 `.gitignore`에 포함했다.
