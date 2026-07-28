# Phase 210: 경기도 순생산물세 포함 GRDP 추정 검증

## 목적

기존 예측 대상은 총부가가치(GVA)지만, 통계청 실험적 통계 XLSX는 `지역내총생산(시장가격)`을 제공한다. 이번 단계는 순생산물세를 별도 추정해 `GVA + 순생산물세` 형태의 GRDP 시장가격 추정값을 만들 수 있는지 점검한다.

## 방법

| 구성요소 | 사용 방식 | 유출 방지 |
| --- | --- | --- |
| 경기도 GVA | Phase209 경기도 31개 시군×산업×분기 GVA 합계 | 예측 산출물 |
| 순생산물세 연간 규모 | 전년도 경기도 암묵 순생산물세/GVA 비율 × 당해 연도 GVA | 같은 해 공식 GRDP 수준값을 feature로 쓰지 않음 |
| 순생산물세 분기 배분 | 전국 분기 순생산물세의 연중 분기비중 | 지역 actual 미사용 |
| 검증값 | 통계청 XLSX 경기도 실질 GRDP 시장가격 | 사후 검증에만 사용 |

2020년은 현재 Phase209 큐브가 2020년부터 시작해 2019년 경기도 GVA 기반 전년도 비율이 없다. 따라서 이번 feasibility 실험에서는 2020~2023 암묵 비율 중앙값을 2020년에만 대체 적용했다. 운영형으로 쓰려면 2019년 경기도 GVA를 물질화해 이 대체값을 제거해야 한다.

## 경기도 암묵 순생산물세 연간 규모

| year | official_grdp_annual_eok | project_gva_annual_eok | implied_net_product_tax_eok | implied_npt_to_gva_ratio |
| --- | --- | --- | --- | --- |
| 2020 | 5231619.0 | 4873769.0 | 357849.0 | 0.0734 |
| 2021 | 5540064.0 | 5161905.0 | 378159.0 | 0.0733 |
| 2022 | 5719421.0 | 5353909.0 | 365512.0 | 0.0683 |
| 2023 | 5773103.0 | 5429156.0 | 343947.0 | 0.0634 |

## 분기 GRDP 추정 검증

| period | project_gva_eok | predicted_net_product_tax_eok | predicted_grdp_market_price_eok | official_grdp_eok | grdp_with_predicted_npt_gap_eok | gva_only_gap_pct | grdp_with_predicted_npt_gap_pct | npt_ratio_source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020Q1 | 1166184.0 | 78124.0 | 1244308.0 | 1244461.0 | -152.0 | 6.29 | 0.012 | feasibility_backfill_median_2020_2023_need_2019_gva |
| 2020Q2 | 1197058.0 | 84945.0 | 1282003.0 | 1294349.0 | -12346.0 | 7.517 | 0.954 | feasibility_backfill_median_2020_2023_need_2019_gva |
| 2020Q3 | 1215389.0 | 91398.0 | 1306787.0 | 1306277.0 | 510.0 | 6.958 | 0.039 | feasibility_backfill_median_2020_2023_need_2019_gva |
| 2020Q4 | 1295139.0 | 90424.0 | 1385563.0 | 1386533.0 | -970.0 | 6.592 | 0.07 | feasibility_backfill_median_2020_2023_need_2019_gva |
| 2021Q1 | 1200511.0 | 84840.0 | 1285351.0 | 1294470.0 | -9119.0 | 7.258 | 0.704 | prior_year_implied_ratio |
| 2021Q2 | 1278472.0 | 96299.0 | 1374771.0 | 1400049.0 | -25278.0 | 8.684 | 1.805 | prior_year_implied_ratio |
| 2021Q3 | 1294523.0 | 98327.0 | 1392850.0 | 1383807.0 | 9043.0 | 6.452 | 0.653 | prior_year_implied_ratio |
| 2021Q4 | 1388398.0 | 99540.0 | 1487938.0 | 1461737.0 | 26201.0 | 5.017 | 1.792 | prior_year_implied_ratio |
| 2022Q1 | 1301602.0 | 91325.0 | 1392927.0 | 1353128.0 | 39799.0 | 3.808 | 2.941 | prior_year_implied_ratio |
| 2022Q2 | 1382111.0 | 98220.0 | 1480331.0 | 1458413.0 | 21918.0 | 5.232 | 1.503 | prior_year_implied_ratio |
| 2022Q3 | 1318460.0 | 102995.0 | 1421455.0 | 1435491.0 | -14036.0 | 8.153 | 0.978 | prior_year_implied_ratio |
| 2022Q4 | 1351735.0 | 99686.0 | 1451421.0 | 1472389.0 | -20968.0 | 8.194 | 1.424 | prior_year_implied_ratio |
| 2023Q1 | 1234201.0 | 86032.0 | 1320233.0 | 1322680.0 | -2446.0 | 6.689 | 0.185 | prior_year_implied_ratio |
| 2023Q2 | 1333588.0 | 92390.0 | 1425979.0 | 1430484.0 | -4506.0 | 6.774 | 0.315 | prior_year_implied_ratio |
| 2023Q3 | 1388539.0 | 95304.0 | 1483842.0 | 1473392.0 | 10450.0 | 5.759 | 0.709 | prior_year_implied_ratio |
| 2023Q4 | 1472828.0 | 96924.0 | 1569751.0 | 1546546.0 | 23205.0 | 4.767 | 1.5 | prior_year_implied_ratio |

## 결과

- GVA 합계만 공식 GRDP와 비교한 평균 오차율: **6.509%**
- GVA 합계만 공식 GRDP와 비교한 최대 오차율: **8.684%**
- 순생산물세 추정 포함 GRDP 평균 오차율: **0.974%**
- 순생산물세 추정 포함 GRDP 최대 오차율: **2.941%**

## 판정

순생산물세까지 포함한 GRDP 시장가격 추정은 가능하다. 다만 이 값은 기존 GVA 예측과 별도 산출물로 관리해야 한다. 포스터나 보고서에서는 `총부가가치 추정`과 `순생산물세 포함 GRDP 환산 검증`을 구분해 표기하는 것이 안전하다.

## 산출물

- `data/processed/phase210_gyeonggi_net_product_tax_grdp/phase210_gyeonggi_predicted_net_product_tax_grdp_validation.csv`
- `data/processed/phase210_gyeonggi_net_product_tax_grdp/phase210_gyeonggi_implied_annual_net_product_tax.csv`
- `data/processed/phase210_gyeonggi_net_product_tax_grdp/phase210_manifest.json`
