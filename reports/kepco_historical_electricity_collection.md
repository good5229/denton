# KEPCO 과거 시군구 전력자료 확보 및 ML 재개 조건 점검

## 실행 요약

KEPCO 전력판매량 게시판 전체 7페이지를 수집해 과거 시군구별 전력사용량 후보 파일을 탐색하고, 다운로드·스키마 fingerprint·2021~2023 관측월 커버리지를 점검했다.

| 항목 | 결과 |
| --- | ---: |
| board items | 74 |
| sigungu candidates | 69 |
| 2021~2023 source candidates | 24 |
| downloaded files | 69 |
| parsed files | 59 |
| schema families | 3 |
| available target months | 36 |

## 완료 조건 판단

| 조건 | 결과 |
| --- | --- |
| 2021~2023 중 24개월 이상 확보 | Y |
| 95% 이상 지역 coverage | Y |
| rolling split 후보 구성 | Y |
| official actual region join | Y |

## 생성 산출물

| 파일 | 내용 |
| --- | --- |
| `data/processed/kepco_historical_board_inventory.csv` | 게시판 7페이지 게시물·첨부 토큰 목록 |
| `data/processed/kepco_historical_download_inventory.csv` | 다운로드 파일, 해시, 크기, source period |
| `data/processed/kepco_historical_schema_fingerprint.csv` | 시트별 header/schema fingerprint |
| `data/processed/kepco_historical_parse_audit.csv` | 파일별 parser 성공 여부와 관측기간 |
| `data/processed/kepco_historical_2021_2023_long.csv` | 2021~2023 관측월 latest-source long table |
| `data/processed/kepco_historical_2021_2023_wide.csv` | 2021~2023 관측월 시군구 wide table |
| `data/processed/municipality_electricity_features_2021_2023.csv` | 2021~2023 ML-ready historical electricity feature table |
| `data/processed/kepco_historical_official_join_readiness.csv` | 기존 official actual pilot과 region join 가능성 |
| `data/processed/kepco_historical_monthly_coverage.csv` | 월별 시군구 coverage |
| `data/processed/kepco_historical_coverage_summary.csv` | Experiment 1 완료조건 요약 |

## 해석

게시판에는 2021~2023년과 겹치는 시군구별 전력사용량 파일이 존재한다. 특히 일부 source file은 해당 연도 1월부터 source month까지 누적 월별 표를 포함하므로, 월별 게시물 자체가 누락돼도 관측월은 복원될 수 있다.

과거 전력 feature table은 생성됐고, 기존 official actual pilot과의 지역 join readiness도 산출했다. 다음 단계에서는 동일 모집단 split을 고정한 뒤 baseline, global policy, electricity-only를 비교하는 dry-run harness를 실행한다.

주의할 점은 latest-source 값과 prediction-origin availability를 분리해야 한다는 것이다. `first_eligible_period_latest_source`는 latest-source 값 자체의 공표시점이고, `first_observed_eligible_period`는 해당 관측월이 어떤 vintage에서든 최초로 관측 가능해진 시점이다. 실제 ablation에서는 `first_observed_eligible_period`만으로 latest-source 값을 조기 사용하지 말고, prediction origin별로 사용 가능한 source vintage를 선택해야 한다.

## Official Actual Join Readiness

| year | actual_regions | feature_regions | common_regions | eligible_common_regions | join_rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2021 | 228 | 230 | 228 | 228 | 1.000 |
| 2022 | 228 | 230 | 228 | 228 | 1.000 |
| 2023 | 148 | 230 | 148 | 148 | 1.000 |
