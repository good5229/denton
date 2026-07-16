# Electricity Feature Data Contract

## Source

- Source ID: `kepco_sigungu_electricity_sales`
- Institution: 한국전력공사
- URL: https://www.kepco.co.kr/home/customer/library/electricity-statistics/sales-volume/boardList.do
- License: 이용허락범위 제한 없음

## Grain

- Spatial level: 시군구
- Temporal level: 월
- Raw format: monthly XLSX files
- Sheets: `계약종별`, `용도업종별`

## Eligibility

The source file for month `YYYYMM` can revise prior months in the same year. The pipeline keeps source vintages for audit, selects the latest source period for each observation key, and sets:

```text
first_eligible_period = max(observation_period + 2 months, publication_month)
```

Downstream ML must enforce:

```text
first_eligible_period <= prediction_origin_period
```

## Key Outputs

- `municipality_electricity_monthly.csv`
- `municipality_electricity_features.csv`
- `electricity_source_revision_log.csv`
- `electricity_region_crosswalk_audit.csv`
- `electricity_total_consistency_audit.csv`
