# Partial Statistics Estimation Phase 12-GVA

## 1. 실행 요약

GVA remains the primary target. Establishments and employees are auxiliary inputs only, and 2025 actual release is not required to generate current estimates.

| status | target | target_years | prediction_origin_count | target_origin_combinations | annual_2025_rows | quarterly_2025_rows | monthly_2025_rows | strict_vintage_track | sensitivity_track | production_use | official_statistics_claim | generated_at |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| annual_quarterly_multi_origin | GVA | [2022, 2023, 2024, 2025] | 18 | 72 | 3811 | 15244 | 45732 | limited_by_release_metadata | generated | False | False | 2026-07-18T16:27:50+09:00 |

## 2. 목표 불변 선언

| PRIMARY_TARGET | PRIMARY_OUTPUT_FREQUENCIES | PRIMARY_TARGET_YEARS | PRIMARY_SPATIAL_UNIT | PRIMARY_INDUSTRY_UNIT | ACTUAL_RELEASE_REQUIRED_FOR_EXECUTION | PRODUCTION_USE | OFFICIAL_STATISTICS_CLAIM |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Gross Value Added | ['annual', 'quarterly', 'monthly'] | [2022, 2023, 2024, 2025] | stable sigungu where available | stable KSIC sector/detail where available | False | False | False |

## 3. Target Year와 Prediction Origin

| target_year | target_role | actual_role | actual_release_required_for_execution | confirmatory_role |
| --- | --- | --- | --- | --- |
| 2022 | historical_pseudo_real_time | outer_evaluation_only | false | false |
| 2023 | historical_pseudo_real_time | outer_evaluation_only | false | false |
| 2024 | historical_pseudo_real_time | outer_evaluation_if_available | false | false_development_outer |
| 2025 | current_pre_release_estimate | unused_or_unavailable | false | false |

## 4. 정보 기준시점

| origin_id | origin_label | origin_month | origin_day | origin_kind | strict_track_allowed |
| --- | --- | --- | --- | --- | --- |
| O0 | previous_year_end_forecast | 12 | 31 | one_year_ahead | Y |
| O1 | first_quarter_nowcast | 3 | 31 | quarterly_nowcast | Y |
| O2 | second_quarter_nowcast | 6 | 30 | quarterly_nowcast | Y |
| O3 | third_quarter_nowcast | 9 | 30 | quarterly_nowcast | Y |
| O4 | year_end_nowcast | 12 | 31 | year_end_nowcast | Y |
| O5 | pre_release_final_nowcast | 12 | 31 | pre_release_sensitivity | N_release_date_missing |
| O_M01 | monthly_origin_01 | 1 | 31 | monthly_nowcast | Y |
| O_M02 | monthly_origin_02 | 2 | 28 | monthly_nowcast | Y |
| O_M03 | monthly_origin_03 | 3 | 31 | monthly_nowcast | Y |
| O_M04 | monthly_origin_04 | 4 | 30 | monthly_nowcast | Y |
| O_M05 | monthly_origin_05 | 5 | 31 | monthly_nowcast | Y |
| O_M06 | monthly_origin_06 | 6 | 30 | monthly_nowcast | Y |

## 5. Source Availability

| source_id | source_role | target_track | row_count | min_observation_year | max_observation_year | availability_confidence | use_rule | primary_target |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sigungu_annual_rolling_backtest.csv | annual_gva_outer_evaluation | VA_nominal | 11732 | 2020 | 2023 | D_current_snapshot | sensitivity_backtest | Y |
| sigungu_annual_gva_forecasts.csv | annual_gva_pre_release_estimate | VA_nominal | 11103 | 2023 | 2025 | D_current_snapshot | current_estimate | Y |
| sigungu_quarterly_gva_forecasts.csv | quarterly_gva_pre_release_estimate | VA_nominal | 45732 | 2023 | 2025 | D_current_snapshot | current_estimate | Y |
| sigungu_quarterly_gva_estimates.csv | quarterly_gva_anchor_history | VA_nominal | 65584 | 2019 | 2023 | D_current_snapshot | sensitivity_history | Y |
| detailed_industry_quarterly_estimates.csv | manufacturing_detail_quarterly_proxy | VA_nominal | 53656 | 2022 | 2025 | C_bounded | sensitivity_detail | N_auxiliary |
| service_detail_quarterly_estimates.csv | service_detail_quarterly_proxy | VA_nominal | 1632564 | 2019 | 2025 | D_current_snapshot | sensitivity_detail | N_auxiliary |
| kepco_sigungu_electricity_long.csv | electricity_auxiliary | auxiliary | 148616 | 2025 | 2026 | D_current_snapshot | current_or_future_only | N_auxiliary |
| expanded_manufacturing_sigungu_ksic.csv | establishment_employee_auxiliary | auxiliary | 92634 |  |  | D_current_snapshot | auxiliary_not_target | N_auxiliary |

## 6. Vintage 및 Revision

| source_id | vintage_id | retrieval_date | revision_policy | historical_backdate_allowed |
| --- | --- | --- | --- | --- |
| sigungu_annual_rolling_backtest.csv | sigungu_annual_rolling_backtest.csv:current_snapshot |  | latest_revised_sensitivity | N |
| sigungu_annual_gva_forecasts.csv | sigungu_annual_gva_forecasts.csv:current_snapshot |  | latest_revised_sensitivity | N |
| sigungu_quarterly_gva_forecasts.csv | sigungu_quarterly_gva_forecasts.csv:current_snapshot |  | latest_revised_sensitivity | N |
| sigungu_quarterly_gva_estimates.csv | sigungu_quarterly_gva_estimates.csv:current_snapshot |  | latest_revised_sensitivity | N |
| detailed_industry_quarterly_estimates.csv | detailed_industry_quarterly_estimates.csv:current_snapshot |  | bounded_sensitivity | bounded_only |
| service_detail_quarterly_estimates.csv | service_detail_quarterly_estimates.csv:current_snapshot |  | latest_revised_sensitivity | N |
| kepco_sigungu_electricity_long.csv | kepco_sigungu_electricity_long.csv:current_snapshot |  | latest_revised_sensitivity | N |
| expanded_manufacturing_sigungu_ksic.csv | expanded_manufacturing_sigungu_ksic.csv:current_snapshot |  | latest_revised_sensitivity | N |

## 7. Stable Region

| stable_region_count | spatial_unit | status |
| --- | --- | --- |
| 237 | sigungu | stable_current_crosswalk |

## 8. Stable Industry

| stable_industry_count | industry_unit | status |
| --- | --- | --- |
| 16 | KSIC sector | stable_current_sector_codes |

## 9. 총부가가치 Anchor

| source_id | source_role | target_track | row_count | min_observation_year | max_observation_year | availability_confidence | use_rule | primary_target |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sigungu_annual_rolling_backtest.csv | annual_gva_outer_evaluation | VA_nominal | 11732 | 2020 | 2023 | D_current_snapshot | sensitivity_backtest | Y |
| sigungu_annual_gva_forecasts.csv | annual_gva_pre_release_estimate | VA_nominal | 11103 | 2023 | 2025 | D_current_snapshot | current_estimate | Y |
| sigungu_quarterly_gva_forecasts.csv | quarterly_gva_pre_release_estimate | VA_nominal | 45732 | 2023 | 2025 | D_current_snapshot | current_estimate | Y |
| sigungu_quarterly_gva_estimates.csv | quarterly_gva_anchor_history | VA_nominal | 65584 | 2019 | 2023 | D_current_snapshot | sensitivity_history | Y |

## 10. Target-Origin Grid

| target_year | origin_id | prediction_origin | target_period | origin_kind | actual_hidden_until_evaluation | target_actual_as_feature |
| --- | --- | --- | --- | --- | --- | --- |
| 2022 | O0 | 2021-12-31 | 2022 | one_year_ahead | Y | prohibited |
| 2022 | O1 | 2022-03-31 | 2022 | quarterly_nowcast | Y | prohibited |
| 2022 | O2 | 2022-06-30 | 2022 | quarterly_nowcast | Y | prohibited |
| 2022 | O3 | 2022-09-30 | 2022 | quarterly_nowcast | Y | prohibited |
| 2022 | O4 | 2022-12-31 | 2022 | year_end_nowcast | Y | prohibited |
| 2022 | O5 | 2022-12-31 | 2022 | pre_release_sensitivity | Y | prohibited |
| 2022 | O_M01 | 2022-01-31 | 2022 | monthly_nowcast | Y | prohibited |
| 2022 | O_M02 | 2022-02-28 | 2022 | monthly_nowcast | Y | prohibited |
| 2022 | O_M03 | 2022-03-31 | 2022 | monthly_nowcast | Y | prohibited |
| 2022 | O_M04 | 2022-04-30 | 2022 | monthly_nowcast | Y | prohibited |
| 2022 | O_M05 | 2022-05-31 | 2022 | monthly_nowcast | Y | prohibited |
| 2022 | O_M06 | 2022-06-30 | 2022 | monthly_nowcast | Y | prohibited |

## 11. As-of Dataset

| as_of_dataset_id | target_year | prediction_origin | source_vintages | row_count | feature_count | content_hash | strict_track_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ASOF_2022_O0 | 2022 | 2021-12-31 | sigungu_annual_rolling_backtest.csv:allowed_sensitivity;sigungu_annual_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_estimates.csv:allowed_sensitivity;detailed_industry_quarterly_estimates.csv:allowed_sensitivity;service_detail_quarterly_estimates.csv:allowed_sensitivity;kepco_sigungu_electricity_long.csv:blocked_historical_strict;expanded_manufacturing_sigungu_ksic.csv:blocked_historical_strict | 8 | 6 | 97373556af1939ef1a5a6a7882693b3c40dbb82349c0d8332c9920a7e7192c72 | limited_by_release_metadata |
| ASOF_2022_O1 | 2022 | 2022-03-31 | sigungu_annual_rolling_backtest.csv:allowed_sensitivity;sigungu_annual_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_estimates.csv:allowed_sensitivity;detailed_industry_quarterly_estimates.csv:allowed_sensitivity;service_detail_quarterly_estimates.csv:allowed_sensitivity;kepco_sigungu_electricity_long.csv:blocked_historical_strict;expanded_manufacturing_sigungu_ksic.csv:blocked_historical_strict | 8 | 6 | 97373556af1939ef1a5a6a7882693b3c40dbb82349c0d8332c9920a7e7192c72 | limited_by_release_metadata |
| ASOF_2022_O2 | 2022 | 2022-06-30 | sigungu_annual_rolling_backtest.csv:allowed_sensitivity;sigungu_annual_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_estimates.csv:allowed_sensitivity;detailed_industry_quarterly_estimates.csv:allowed_sensitivity;service_detail_quarterly_estimates.csv:allowed_sensitivity;kepco_sigungu_electricity_long.csv:blocked_historical_strict;expanded_manufacturing_sigungu_ksic.csv:blocked_historical_strict | 8 | 6 | 97373556af1939ef1a5a6a7882693b3c40dbb82349c0d8332c9920a7e7192c72 | limited_by_release_metadata |
| ASOF_2022_O3 | 2022 | 2022-09-30 | sigungu_annual_rolling_backtest.csv:allowed_sensitivity;sigungu_annual_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_estimates.csv:allowed_sensitivity;detailed_industry_quarterly_estimates.csv:allowed_sensitivity;service_detail_quarterly_estimates.csv:allowed_sensitivity;kepco_sigungu_electricity_long.csv:blocked_historical_strict;expanded_manufacturing_sigungu_ksic.csv:blocked_historical_strict | 8 | 6 | 97373556af1939ef1a5a6a7882693b3c40dbb82349c0d8332c9920a7e7192c72 | limited_by_release_metadata |
| ASOF_2022_O4 | 2022 | 2022-12-31 | sigungu_annual_rolling_backtest.csv:allowed_sensitivity;sigungu_annual_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_estimates.csv:allowed_sensitivity;detailed_industry_quarterly_estimates.csv:allowed_sensitivity;service_detail_quarterly_estimates.csv:allowed_sensitivity;kepco_sigungu_electricity_long.csv:blocked_historical_strict;expanded_manufacturing_sigungu_ksic.csv:blocked_historical_strict | 8 | 6 | 97373556af1939ef1a5a6a7882693b3c40dbb82349c0d8332c9920a7e7192c72 | limited_by_release_metadata |
| ASOF_2022_O5 | 2022 | 2022-12-31 | sigungu_annual_rolling_backtest.csv:allowed_sensitivity;sigungu_annual_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_estimates.csv:allowed_sensitivity;detailed_industry_quarterly_estimates.csv:allowed_sensitivity;service_detail_quarterly_estimates.csv:allowed_sensitivity;kepco_sigungu_electricity_long.csv:blocked_historical_strict;expanded_manufacturing_sigungu_ksic.csv:blocked_historical_strict | 8 | 6 | 97373556af1939ef1a5a6a7882693b3c40dbb82349c0d8332c9920a7e7192c72 | limited_by_release_metadata |
| ASOF_2022_O_M01 | 2022 | 2022-01-31 | sigungu_annual_rolling_backtest.csv:allowed_sensitivity;sigungu_annual_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_estimates.csv:allowed_sensitivity;detailed_industry_quarterly_estimates.csv:allowed_sensitivity;service_detail_quarterly_estimates.csv:allowed_sensitivity;kepco_sigungu_electricity_long.csv:blocked_historical_strict;expanded_manufacturing_sigungu_ksic.csv:blocked_historical_strict | 8 | 6 | 97373556af1939ef1a5a6a7882693b3c40dbb82349c0d8332c9920a7e7192c72 | limited_by_release_metadata |
| ASOF_2022_O_M02 | 2022 | 2022-02-28 | sigungu_annual_rolling_backtest.csv:allowed_sensitivity;sigungu_annual_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_estimates.csv:allowed_sensitivity;detailed_industry_quarterly_estimates.csv:allowed_sensitivity;service_detail_quarterly_estimates.csv:allowed_sensitivity;kepco_sigungu_electricity_long.csv:blocked_historical_strict;expanded_manufacturing_sigungu_ksic.csv:blocked_historical_strict | 8 | 6 | 97373556af1939ef1a5a6a7882693b3c40dbb82349c0d8332c9920a7e7192c72 | limited_by_release_metadata |
| ASOF_2022_O_M03 | 2022 | 2022-03-31 | sigungu_annual_rolling_backtest.csv:allowed_sensitivity;sigungu_annual_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_estimates.csv:allowed_sensitivity;detailed_industry_quarterly_estimates.csv:allowed_sensitivity;service_detail_quarterly_estimates.csv:allowed_sensitivity;kepco_sigungu_electricity_long.csv:blocked_historical_strict;expanded_manufacturing_sigungu_ksic.csv:blocked_historical_strict | 8 | 6 | 97373556af1939ef1a5a6a7882693b3c40dbb82349c0d8332c9920a7e7192c72 | limited_by_release_metadata |
| ASOF_2022_O_M04 | 2022 | 2022-04-30 | sigungu_annual_rolling_backtest.csv:allowed_sensitivity;sigungu_annual_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_estimates.csv:allowed_sensitivity;detailed_industry_quarterly_estimates.csv:allowed_sensitivity;service_detail_quarterly_estimates.csv:allowed_sensitivity;kepco_sigungu_electricity_long.csv:blocked_historical_strict;expanded_manufacturing_sigungu_ksic.csv:blocked_historical_strict | 8 | 6 | 97373556af1939ef1a5a6a7882693b3c40dbb82349c0d8332c9920a7e7192c72 | limited_by_release_metadata |
| ASOF_2022_O_M05 | 2022 | 2022-05-31 | sigungu_annual_rolling_backtest.csv:allowed_sensitivity;sigungu_annual_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_estimates.csv:allowed_sensitivity;detailed_industry_quarterly_estimates.csv:allowed_sensitivity;service_detail_quarterly_estimates.csv:allowed_sensitivity;kepco_sigungu_electricity_long.csv:blocked_historical_strict;expanded_manufacturing_sigungu_ksic.csv:blocked_historical_strict | 8 | 6 | 97373556af1939ef1a5a6a7882693b3c40dbb82349c0d8332c9920a7e7192c72 | limited_by_release_metadata |
| ASOF_2022_O_M06 | 2022 | 2022-06-30 | sigungu_annual_rolling_backtest.csv:allowed_sensitivity;sigungu_annual_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_forecasts.csv:allowed_sensitivity;sigungu_quarterly_gva_estimates.csv:allowed_sensitivity;detailed_industry_quarterly_estimates.csv:allowed_sensitivity;service_detail_quarterly_estimates.csv:allowed_sensitivity;kepco_sigungu_electricity_long.csv:blocked_historical_strict;expanded_manufacturing_sigungu_ksic.csv:blocked_historical_strict | 8 | 6 | 97373556af1939ef1a5a6a7882693b3c40dbb82349c0d8332c9920a7e7192c72 | limited_by_release_metadata |

## 12. Leakage Audit

Current snapshots are not backdated into strict historical origins. They are retained only in sensitivity/current-estimate tracks.

| target_year | origin_id | future_feature_rows | target_actual_feature_rows | current_snapshot_backdated_rows | leakage_status |
| --- | --- | --- | --- | --- | --- |
| 2022 | O0 | 0 | 0 | 2 | sensitivity_only_current_snapshot_blocked_from_strict |
| 2022 | O1 | 0 | 0 | 2 | sensitivity_only_current_snapshot_blocked_from_strict |
| 2022 | O2 | 0 | 0 | 2 | sensitivity_only_current_snapshot_blocked_from_strict |
| 2022 | O3 | 0 | 0 | 2 | sensitivity_only_current_snapshot_blocked_from_strict |
| 2022 | O4 | 0 | 0 | 2 | sensitivity_only_current_snapshot_blocked_from_strict |
| 2022 | O5 | 0 | 0 | 2 | sensitivity_only_current_snapshot_blocked_from_strict |
| 2022 | O_M01 | 0 | 0 | 2 | sensitivity_only_current_snapshot_blocked_from_strict |
| 2022 | O_M02 | 0 | 0 | 2 | sensitivity_only_current_snapshot_blocked_from_strict |
| 2022 | O_M03 | 0 | 0 | 2 | sensitivity_only_current_snapshot_blocked_from_strict |
| 2022 | O_M04 | 0 | 0 | 2 | sensitivity_only_current_snapshot_blocked_from_strict |
| 2022 | O_M05 | 0 | 0 | 2 | sensitivity_only_current_snapshot_blocked_from_strict |
| 2022 | O_M06 | 0 | 0 | 2 | sensitivity_only_current_snapshot_blocked_from_strict |

## 13. Annual Baseline

| target_year | origin_id | n | wmape | mae | rmsle | median_ape | p90_ape | actual_sum | prediction_sum | evaluation_status | model_id | model_family |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | O0 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | B3_historical_parent_share_baseline | annual_baseline |
| 2022 | O1 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | B3_historical_parent_share_baseline | annual_baseline |
| 2022 | O2 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | B3_historical_parent_share_baseline | annual_baseline |
| 2022 | O3 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | B3_historical_parent_share_baseline | annual_baseline |
| 2022 | O4 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | B3_historical_parent_share_baseline | annual_baseline |
| 2022 | O5 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | B3_historical_parent_share_baseline | annual_baseline |
| 2022 | O_M01 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | B3_historical_parent_share_baseline | annual_baseline |
| 2022 | O_M02 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | B3_historical_parent_share_baseline | annual_baseline |
| 2022 | O_M03 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | B3_historical_parent_share_baseline | annual_baseline |
| 2022 | O_M04 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | B3_historical_parent_share_baseline | annual_baseline |
| 2022 | O_M05 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | B3_historical_parent_share_baseline | annual_baseline |
| 2022 | O_M06 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | B3_historical_parent_share_baseline | annual_baseline |

## 14. Direct GVA Model

| target_year | origin_id | n | wmape | mae | rmsle | median_ape | p90_ape | actual_sum | prediction_sum | evaluation_status | model_id | model_family | result_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | O0 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | direct_gva_model_not_promoted | direct_gva | not_trained_release_limited |
| 2022 | O1 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | direct_gva_model_not_promoted | direct_gva | not_trained_release_limited |
| 2022 | O2 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | direct_gva_model_not_promoted | direct_gva | not_trained_release_limited |
| 2022 | O3 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | direct_gva_model_not_promoted | direct_gva | not_trained_release_limited |
| 2022 | O4 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | direct_gva_model_not_promoted | direct_gva | not_trained_release_limited |
| 2022 | O5 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | direct_gva_model_not_promoted | direct_gva | not_trained_release_limited |
| 2022 | O_M01 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | direct_gva_model_not_promoted | direct_gva | not_trained_release_limited |
| 2022 | O_M02 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | direct_gva_model_not_promoted | direct_gva | not_trained_release_limited |
| 2022 | O_M03 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | direct_gva_model_not_promoted | direct_gva | not_trained_release_limited |
| 2022 | O_M04 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | direct_gva_model_not_promoted | direct_gva | not_trained_release_limited |
| 2022 | O_M05 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | direct_gva_model_not_promoted | direct_gva | not_trained_release_limited |
| 2022 | O_M06 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | direct_gva_model_not_promoted | direct_gva | not_trained_release_limited |

## 15. Productivity Model

| target_year | origin_id | n | wmape | mae | rmsle | median_ape | p90_ape | actual_sum | prediction_sum | evaluation_status | model_id | model_family | result_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | O0 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | productivity_model_not_promoted | productivity | auxiliary_only |
| 2022 | O1 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | productivity_model_not_promoted | productivity | auxiliary_only |
| 2022 | O2 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | productivity_model_not_promoted | productivity | auxiliary_only |
| 2022 | O3 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | productivity_model_not_promoted | productivity | auxiliary_only |
| 2022 | O4 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | productivity_model_not_promoted | productivity | auxiliary_only |
| 2022 | O5 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | productivity_model_not_promoted | productivity | auxiliary_only |
| 2022 | O_M01 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | productivity_model_not_promoted | productivity | auxiliary_only |
| 2022 | O_M02 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | productivity_model_not_promoted | productivity | auxiliary_only |
| 2022 | O_M03 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | productivity_model_not_promoted | productivity | auxiliary_only |
| 2022 | O_M04 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | productivity_model_not_promoted | productivity | auxiliary_only |
| 2022 | O_M05 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | productivity_model_not_promoted | productivity | auxiliary_only |
| 2022 | O_M06 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | productivity_model_not_promoted | productivity | auxiliary_only |

## 16. Parent-share Model

| target_year | origin_id | n | wmape | mae | rmsle | median_ape | p90_ape | actual_sum | prediction_sum | evaluation_status | model_id | model_family | result_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | O0 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | parent_share_baseline | parent_share | active_baseline |
| 2022 | O1 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | parent_share_baseline | parent_share | active_baseline |
| 2022 | O2 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | parent_share_baseline | parent_share | active_baseline |
| 2022 | O3 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | parent_share_baseline | parent_share | active_baseline |
| 2022 | O4 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | parent_share_baseline | parent_share | active_baseline |
| 2022 | O5 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | parent_share_baseline | parent_share | active_baseline |
| 2022 | O_M01 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | parent_share_baseline | parent_share | active_baseline |
| 2022 | O_M02 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | parent_share_baseline | parent_share | active_baseline |
| 2022 | O_M03 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | parent_share_baseline | parent_share | active_baseline |
| 2022 | O_M04 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | parent_share_baseline | parent_share | active_baseline |
| 2022 | O_M05 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | parent_share_baseline | parent_share | active_baseline |
| 2022 | O_M06 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer | parent_share_baseline | parent_share | active_baseline |

## 17. Proxy Correction

| proxy_correction | reason |
| --- | --- |
| not_promoted | origin-specific proxy release matrix incomplete |

## 18. High-frequency Activity Index

| sigungu_code | sector_code | year | month | quarter | monthly_share | temporal_method |
| --- | --- | --- | --- | --- | --- | --- |
| 32 | A00 | 2025 | 1 | 1 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator |
| 32 | A00 | 2025 | 2 | 1 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator |
| 32 | A00 | 2025 | 3 | 1 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator |
| 32 | A00 | 2025 | 4 | 2 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator |
| 32 | A00 | 2025 | 5 | 2 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator |
| 32 | A00 | 2025 | 6 | 2 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator |
| 32 | A00 | 2025 | 7 | 3 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator |
| 32 | A00 | 2025 | 8 | 3 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator |
| 32 | A00 | 2025 | 9 | 3 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator |
| 32 | A00 | 2025 | 10 | 4 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator |
| 32 | A00 | 2025 | 11 | 4 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator |
| 32 | A00 | 2025 | 12 | 4 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator |

## 19. Temporal Disaggregation

| constraint | max_abs_diff | status |
| --- | --- | --- |
| month_sum_equals_quarter | 3.725290298461914e-09 | pass |
| quarter_sum_equals_annual | 7.450580596923828e-09 | diagnostic_no_hard_parent |

## 20. 2022 Multi-origin 결과

| target_year | origin_id | prediction_origin | source_region | sigungu_code | sigungu_name | sector_code | sector_name | price_track | model_id | prediction_value | actual_value | evaluation_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | O0 | 2021-12-31 | 강원특별자치도 | 32010 | 춘천시 | A00 | 농업, 임업 및 어업 | VA_nominal | B3_historical_parent_share_baseline | 140588.536463 | 136327.0 | evaluated_outer |
| 2022 | O0 | 2021-12-31 | 강원특별자치도 | 32010 | 춘천시 | B00 | 광업 | VA_nominal | B3_historical_parent_share_baseline | 11146.797001 | 8682.0 | evaluated_outer |
| 2022 | O0 | 2021-12-31 | 강원특별자치도 | 32010 | 춘천시 | C00 | 제조업 | VA_nominal | B3_historical_parent_share_baseline | 622293.721254 | 652799.0 | evaluated_outer |
| 2022 | O0 | 2021-12-31 | 강원특별자치도 | 32010 | 춘천시 | D00 | 전기, 가스, 증기 및 공기 조절 공급업 | VA_nominal | B3_historical_parent_share_baseline | 139119.305136 | 147084.0 | evaluated_outer |
| 2022 | O0 | 2021-12-31 | 강원특별자치도 | 32010 | 춘천시 | ERS | 문화 및 기타서비스업 | VA_nominal | B3_historical_parent_share_baseline | 527501.713629 | 512126.0 | evaluated_outer |
| 2022 | O0 | 2021-12-31 | 강원특별자치도 | 32010 | 춘천시 | F00 | 건설업 | VA_nominal | B3_historical_parent_share_baseline | 587104.929152 | 498440.0 | evaluated_outer |
| 2022 | O0 | 2021-12-31 | 강원특별자치도 | 32010 | 춘천시 | G00 | 도매 및 소매업 | VA_nominal | B3_historical_parent_share_baseline | 467451.830421 | 455257.0 | evaluated_outer |
| 2022 | O0 | 2021-12-31 | 강원특별자치도 | 32010 | 춘천시 | H00 | 운수 및 창고업 | VA_nominal | B3_historical_parent_share_baseline | 399144.485092 | 412880.0 | evaluated_outer |
| 2022 | O0 | 2021-12-31 | 강원특별자치도 | 32010 | 춘천시 | I00 | 숙박 및 음식점업 | VA_nominal | B3_historical_parent_share_baseline | 363637.729035 | 319426.0 | evaluated_outer |
| 2022 | O0 | 2021-12-31 | 강원특별자치도 | 32010 | 춘천시 | J00 | 정보통신업 | VA_nominal | B3_historical_parent_share_baseline | 233037.469784 | 218086.0 | evaluated_outer |
| 2022 | O0 | 2021-12-31 | 강원특별자치도 | 32010 | 춘천시 | K00 | 금융 및 보험업 | VA_nominal | B3_historical_parent_share_baseline | 421074.582014 | 429150.0 | evaluated_outer |
| 2022 | O0 | 2021-12-31 | 강원특별자치도 | 32010 | 춘천시 | L00 | 부동산업 | VA_nominal | B3_historical_parent_share_baseline | 811237.469607 | 658709.0 | evaluated_outer |

## 21. 2023 Multi-origin 결과

| target_year | origin_id | prediction_origin | source_region | sigungu_code | sigungu_name | sector_code | sector_name | price_track | model_id | prediction_value | actual_value | evaluation_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2023 | O0 | 2022-12-31 | 경기도 | 002 | 수원시 | A00 | 농업, 임업 및 어업 | VA_nominal | B3_historical_parent_share_baseline | 14212.754357 | 13214.0 | evaluated_outer |
| 2023 | O0 | 2022-12-31 | 경기도 | 002 | 수원시 | B00 | 광업 | VA_nominal | B3_historical_parent_share_baseline | 146.653794 | 64.0 | evaluated_outer |
| 2023 | O0 | 2022-12-31 | 경기도 | 002 | 수원시 | C00 | 제조업 | VA_nominal | B3_historical_parent_share_baseline | 8094785.18706 | 8084369.0 | evaluated_outer |
| 2023 | O0 | 2022-12-31 | 경기도 | 002 | 수원시 | D00 | 전기, 가스, 증기 및 공기 조절 공급업 | VA_nominal | B3_historical_parent_share_baseline | 40039.730052 | 46266.0 | evaluated_outer |
| 2023 | O0 | 2022-12-31 | 경기도 | 002 | 수원시 | ERS | 문화 및 기타서비스업 | VA_nominal | B3_historical_parent_share_baseline | 1227457.913241 | 1334954.0 | evaluated_outer |
| 2023 | O0 | 2022-12-31 | 경기도 | 002 | 수원시 | F00 | 건설업 | VA_nominal | B3_historical_parent_share_baseline | 2164785.78803 | 1559587.0 | evaluated_outer |
| 2023 | O0 | 2022-12-31 | 경기도 | 002 | 수원시 | G00 | 도매 및 소매업 | VA_nominal | B3_historical_parent_share_baseline | 2914997.30763 | 2867673.0 | evaluated_outer |
| 2023 | O0 | 2022-12-31 | 경기도 | 002 | 수원시 | H00 | 운수 및 창고업 | VA_nominal | B3_historical_parent_share_baseline | 1022536.171732 | 1061513.0 | evaluated_outer |
| 2023 | O0 | 2022-12-31 | 경기도 | 002 | 수원시 | I00 | 숙박 및 음식점업 | VA_nominal | B3_historical_parent_share_baseline | 1116810.385146 | 1068027.0 | evaluated_outer |
| 2023 | O0 | 2022-12-31 | 경기도 | 002 | 수원시 | J00 | 정보통신업 | VA_nominal | B3_historical_parent_share_baseline | 870473.065574 | 869535.0 | evaluated_outer |
| 2023 | O0 | 2022-12-31 | 경기도 | 002 | 수원시 | K00 | 금융 및 보험업 | VA_nominal | B3_historical_parent_share_baseline | 2620165.627199 | 2779630.0 | evaluated_outer |
| 2023 | O0 | 2022-12-31 | 경기도 | 002 | 수원시 | L00 | 부동산업 | VA_nominal | B3_historical_parent_share_baseline | 3156370.978001 | 3094725.0 | evaluated_outer |

## 22. 2024 Multi-origin 결과

2024 local annual actual coverage is limited, so 2024 is not promoted to confirmatory evidence.

| target_year | origin_id | prediction_origin | source_region | sigungu_code | sigungu_name | sector_code | sector_name | price_track | model_id | prediction_value | actual_value | evaluation_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2024 | O0 | 2023-12-31 |  |  |  |  |  |  |  |  |  | pending_actual_or_no_backtest_rows |
| 2024 | O1 | 2024-03-31 |  |  |  |  |  |  |  |  |  | pending_actual_or_no_backtest_rows |
| 2024 | O2 | 2024-06-30 |  |  |  |  |  |  |  |  |  | pending_actual_or_no_backtest_rows |
| 2024 | O3 | 2024-09-30 |  |  |  |  |  |  |  |  |  | pending_actual_or_no_backtest_rows |
| 2024 | O4 | 2024-12-31 |  |  |  |  |  |  |  |  |  | pending_actual_or_no_backtest_rows |
| 2024 | O5 | 2024-12-31 |  |  |  |  |  |  |  |  |  | pending_actual_or_no_backtest_rows |
| 2024 | O_M01 | 2024-01-31 |  |  |  |  |  |  |  |  |  | pending_actual_or_no_backtest_rows |
| 2024 | O_M02 | 2024-02-28 |  |  |  |  |  |  |  |  |  | pending_actual_or_no_backtest_rows |
| 2024 | O_M03 | 2024-03-31 |  |  |  |  |  |  |  |  |  | pending_actual_or_no_backtest_rows |
| 2024 | O_M04 | 2024-04-30 |  |  |  |  |  |  |  |  |  | pending_actual_or_no_backtest_rows |
| 2024 | O_M05 | 2024-05-31 |  |  |  |  |  |  |  |  |  | pending_actual_or_no_backtest_rows |
| 2024 | O_M06 | 2024-06-30 |  |  |  |  |  |  |  |  |  | pending_actual_or_no_backtest_rows |

## 23. Origin별 정확도

| target_year | origin_id | n | wmape | mae | rmsle | median_ape | p90_ape | actual_sum | prediction_sum | evaluation_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | O0 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer |
| 2022 | O1 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer |
| 2022 | O2 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer |
| 2022 | O3 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer |
| 2022 | O4 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer |
| 2022 | O5 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer |
| 2022 | O_M01 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer |
| 2022 | O_M02 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer |
| 2022 | O_M03 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer |
| 2022 | O_M04 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer |
| 2022 | O_M05 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer |
| 2022 | O_M06 | 3550 | 0.09712282457331847 | 55459.140597253805 | 0.30280972775054615 | 0.07324928479308596 | 0.34082935774291534 | 2027123387.1665812 | 2092014218.1060982 | evaluated_outer |

## 24. Forecast Revision

| target_year | origin_id | prediction_origin | sigungu_code | sector_code | prediction_value | revision_from_previous_origin | evaluation_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | O0 | 2021-12-31 | 001001 | A00 | 12567.685923 |  | evaluated_outer |
| 2022 | O_M01 | 2022-01-31 | 001001 | A00 | 12567.685923 | 0.0 | evaluated_outer |
| 2022 | O_M02 | 2022-02-28 | 001001 | A00 | 12567.685923 | 0.0 | evaluated_outer |
| 2022 | O1 | 2022-03-31 | 001001 | A00 | 12567.685923 | 0.0 | evaluated_outer |
| 2022 | O_M03 | 2022-03-31 | 001001 | A00 | 12567.685923 | 0.0 | evaluated_outer |
| 2022 | O_M04 | 2022-04-30 | 001001 | A00 | 12567.685923 | 0.0 | evaluated_outer |
| 2022 | O_M05 | 2022-05-31 | 001001 | A00 | 12567.685923 | 0.0 | evaluated_outer |
| 2022 | O2 | 2022-06-30 | 001001 | A00 | 12567.685923 | 0.0 | evaluated_outer |
| 2022 | O_M06 | 2022-06-30 | 001001 | A00 | 12567.685923 | 0.0 | evaluated_outer |
| 2022 | O_M07 | 2022-07-31 | 001001 | A00 | 12567.685923 | 0.0 | evaluated_outer |
| 2022 | O_M08 | 2022-08-31 | 001001 | A00 | 12567.685923 | 0.0 | evaluated_outer |
| 2022 | O3 | 2022-09-30 | 001001 | A00 | 12567.685923 | 0.0 | evaluated_outer |

## 25. Source Ablation

| ablation_id | source_group | status |
| --- | --- | --- |
| S0 | historical_gva | registered_not_reselected_on_outer_actual |
| S1 | establishments_employees | registered_not_reselected_on_outer_actual |
| S2 | population_employment | registered_not_reselected_on_outer_actual |
| S3 | electricity | registered_not_reselected_on_outer_actual |
| S4 | factory_industrial_complex | registered_not_reselected_on_outer_actual |
| S5 | production_exports | registered_not_reselected_on_outer_actual |
| S6 | building_logistics_sales | registered_not_reselected_on_outer_actual |
| S7 | all_eligible | registered_not_reselected_on_outer_actual |

## 26. Support Router

| policy_id | support_classes | default_route | not_estimable_rule | final_status |
| --- | --- | --- | --- | --- |
| P12_GVA_SUPPORT_ROUTER_V1 | ['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8'] | parent_share_or_conservative_baseline | no GVA anchor and no valid parent/proxy mapping | annual_quarterly_multi_origin |

## 27. Reconciliation

| scope | constraint | distortion_status |
| --- | --- | --- |
| time | month_sum_equals_quarter | pass_by_construction_equal_share |
| region | sigungu_sum_equals_sido | diagnostic_existing_parent_consistency_files |
| industry | detail_sum_equals_parent | diagnostic_existing_detail_allocation_files |

## 28. 불확실성

| target_year | origin_group | interval_status | reason |
| --- | --- | --- | --- |
| 2022 | early | not_calibrated_primary | multi-origin conformal requires stable strict vintage track |
| 2022 | mid | not_calibrated_primary | multi-origin conformal requires stable strict vintage track |
| 2022 | late | not_calibrated_primary | multi-origin conformal requires stable strict vintage track |
| 2022 | pre_release | not_calibrated_primary | multi-origin conformal requires stable strict vintage track |
| 2023 | early | not_calibrated_primary | multi-origin conformal requires stable strict vintage track |
| 2023 | mid | not_calibrated_primary | multi-origin conformal requires stable strict vintage track |
| 2023 | late | not_calibrated_primary | multi-origin conformal requires stable strict vintage track |
| 2023 | pre_release | not_calibrated_primary | multi-origin conformal requires stable strict vintage track |
| 2024 | early | not_calibrated_primary | multi-origin conformal requires stable strict vintage track |
| 2024 | mid | not_calibrated_primary | multi-origin conformal requires stable strict vintage track |
| 2024 | late | not_calibrated_primary | multi-origin conformal requires stable strict vintage track |
| 2024 | pre_release | not_calibrated_primary | multi-origin conformal requires stable strict vintage track |

## 29. 2025 연간 추정

| source_region | parent_area_code | sigungu_code | sigungu_name | sector_code | sector_name | year | predicted_annual_gva | actual_annual_gva | method | benchmark_status | annual_source_status | target_period | prediction_origin | price_track | estimate_role | actual_used | estimate_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | A00 | 농업, 임업 및 어업 | 2025 | 1211246.022086 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2025 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | B00 | 광업 | 2025 | 305618.965553 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2025 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | C00 | 제조업 | 2025 | 2404785.572095 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2025 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | D00 | 전기, 가스, 증기 및 공기 조절 공급업 | 2025 | 562266.567175 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2025 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | ERS | 문화 및 기타서비스업 | 2025 | 1277494.0583819998 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2025 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | F00 | 건설업 | 2025 | 1516444.677319 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2025 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | G00 | 도매 및 소매업 | 2025 | 1311214.749708 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2025 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | H00 | 운수 및 창고업 | 2025 | 1211505.520284 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2025 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | I00 | 숙박 및 음식점업 | 2025 | 1097707.128738 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2025 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | J00 | 정보통신업 | 2025 | 484245.232783 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2025 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | K00 | 금융 및 보험업 | 2025 | 1092423.269598 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2025 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | L00 | 부동산업 | 2025 | 1483502.7448439999 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2025 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |

## 30. 2025 분기 추정

| source_region | parent_area_code | sigungu_code | sigungu_name | sector_code | sector_name | year | quarter | period | predicted_gva | actual_quarterly_gva | parent_predicted_gva | last_observed_share | share_base_year | share_base_sigungu_gva | share_base_parent_gva | method | parent_method | benchmark_status | target_period | prediction_origin | price_track | estimate_role | actual_used | estimate_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | A00 | 농업, 임업 및 어업 | 2025 | 1 | 2025Q1 | 238228.195139 |  | 476626.35367 | 0.499821701643 | 2022 | 432412.34384 | 865133.191334 | last observed same-quarter sigungu-to-parent share applied to parent rolling quarterly forecast | national quarterly GDP share | out_of_sample_forecast | 2025Q1 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | A00 | 농업, 임업 및 어업 | 2025 | 2 | 2025Q2 | 290311.361158 |  | 580935.897459 | 0.499730456369 | 2022 | 532448.25744 | 1065470.896668 | last observed same-quarter sigungu-to-parent share applied to parent rolling quarterly forecast | national quarterly GDP share | out_of_sample_forecast | 2025Q2 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | A00 | 농업, 임업 및 어업 | 2025 | 3 | 2025Q3 | 313064.957387 |  | 626549.247821 | 0.499665363059 | 2022 | 571646.79757 | 1144059.284138 | last observed same-quarter sigungu-to-parent share applied to parent rolling quarterly forecast | national quarterly GDP share | out_of_sample_forecast | 2025Q3 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | A00 | 농업, 임업 및 어업 | 2025 | 4 | 2025Q4 | 369641.508402 |  | 739832.973216 | 0.499628323938 | 2022 | 755086.601149 | 1511296.627857 | last observed same-quarter sigungu-to-parent share applied to parent rolling quarterly forecast | national quarterly GDP share | out_of_sample_forecast | 2025Q4 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | B00 | 광업 | 2025 | 1 | 2025Q1 | 71059.701281 |  | 142019.377394 | 0.500352153243 | 2022 | 151960.410189 | 303706.917626 | last observed same-quarter sigungu-to-parent share applied to parent rolling quarterly forecast | regional production index | out_of_sample_forecast | 2025Q1 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | B00 | 광업 | 2025 | 2 | 2025Q2 | 79992.408931 |  | 159819.649763 | 0.500516732767 | 2022 | 171690.731206 | 343026.955876 | last observed same-quarter sigungu-to-parent share applied to parent rolling quarterly forecast | regional production index | out_of_sample_forecast | 2025Q2 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | B00 | 광업 | 2025 | 3 | 2025Q3 | 76656.134856 |  | 153120.622527 | 0.50062580462 | 2022 | 159795.147629 | 319190.793112 | last observed same-quarter sigungu-to-parent share applied to parent rolling quarterly forecast | regional production index | out_of_sample_forecast | 2025Q3 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | B00 | 광업 | 2025 | 4 | 2025Q4 | 77910.720485 |  | 155608.832643 | 0.500683149934 | 2022 | 177028.710975 | 353574.333385 | last observed same-quarter sigungu-to-parent share applied to parent rolling quarterly forecast | regional production index | out_of_sample_forecast | 2025Q4 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | C00 | 제조업 | 2025 | 1 | 2025Q1 | 565251.580297 |  | 1130809.229588 | 0.499864668157 | 2022 | 1223525.200669 | 2447712.908335 | last observed same-quarter sigungu-to-parent share applied to parent rolling quarterly forecast | regional production index | out_of_sample_forecast | 2025Q1 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | C00 | 제조업 | 2025 | 2 | 2025Q2 | 632197.2512 |  | 1264892.590494 | 0.499803110518 | 2022 | 1307516.344692 | 2616062.839899 | last observed same-quarter sigungu-to-parent share applied to parent rolling quarterly forecast | regional production index | out_of_sample_forecast | 2025Q2 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | C00 | 제조업 | 2025 | 3 | 2025Q3 | 610204.222552 |  | 1220989.189135 | 0.499762182976 | 2022 | 1239310.888502 | 2479801.254914 | last observed same-quarter sigungu-to-parent share applied to parent rolling quarterly forecast | regional production index | out_of_sample_forecast | 2025Q3 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | C00 | 제조업 | 2025 | 4 | 2025Q4 | 597132.518046 |  | 1194884.464003 | 0.499740800082 | 2022 | 1356226.566136 | 2713859.996849 | last observed same-quarter sigungu-to-parent share applied to parent rolling quarterly forecast | regional production index | out_of_sample_forecast | 2025Q4 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated |

## 31. 2025 월별 추정

Monthly GVA is a temporal allocation from quarterly estimates, not an observed monthly official statistic.

| source_region | parent_area_code | sigungu_code | sigungu_name | sector_code | sector_name | year | month | quarter | period | estimated_gva | quarterly_parent_gva | monthly_share | temporal_method | prediction_origin | price_track | actual_used |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | A00 | 농업, 임업 및 어업 | 2025 | 1 | 1 | 2025M01 | 79409.39837966666 | 238228.195139 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator | 2026-07-18 | VA_nominal | N |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | A00 | 농업, 임업 및 어업 | 2025 | 2 | 1 | 2025M02 | 79409.39837966666 | 238228.195139 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator | 2026-07-18 | VA_nominal | N |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | A00 | 농업, 임업 및 어업 | 2025 | 3 | 1 | 2025M03 | 79409.39837966666 | 238228.195139 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator | 2026-07-18 | VA_nominal | N |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | A00 | 농업, 임업 및 어업 | 2025 | 4 | 2 | 2025M04 | 96770.45371933334 | 290311.361158 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator | 2026-07-18 | VA_nominal | N |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | A00 | 농업, 임업 및 어업 | 2025 | 5 | 2 | 2025M05 | 96770.45371933334 | 290311.361158 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator | 2026-07-18 | VA_nominal | N |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | A00 | 농업, 임업 및 어업 | 2025 | 6 | 2 | 2025M06 | 96770.45371933334 | 290311.361158 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator | 2026-07-18 | VA_nominal | N |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | A00 | 농업, 임업 및 어업 | 2025 | 7 | 3 | 2025M07 | 104354.98579566665 | 313064.957387 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator | 2026-07-18 | VA_nominal | N |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | A00 | 농업, 임업 및 어업 | 2025 | 8 | 3 | 2025M08 | 104354.98579566665 | 313064.957387 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator | 2026-07-18 | VA_nominal | N |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | A00 | 농업, 임업 및 어업 | 2025 | 9 | 3 | 2025M09 | 104354.98579566665 | 313064.957387 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator | 2026-07-18 | VA_nominal | N |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | A00 | 농업, 임업 및 어업 | 2025 | 10 | 4 | 2025M10 | 123213.836134 | 369641.508402 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator | 2026-07-18 | VA_nominal | N |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | A00 | 농업, 임업 및 어업 | 2025 | 11 | 4 | 2025M11 | 123213.836134 | 369641.508402 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator | 2026-07-18 | VA_nominal | N |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | A00 | 농업, 임업 및 어업 | 2025 | 12 | 4 | 2025M12 | 123213.836134 | 369641.508402 | 0.3333333333333333 | equal_monthly_share_within_quarter_pending_monthly_indicator | 2026-07-18 | VA_nominal | N |

## 32. 2026 현재시점 Nowcast

| source_region | parent_area_code | sigungu_code | sigungu_name | sector_code | sector_name | year | predicted_annual_gva | actual_annual_gva | method | benchmark_status | annual_source_status | target_period | prediction_origin | price_track | estimate_role | actual_used | estimate_status | nowcast_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | A00 | 농업, 임업 및 어업 | 2026 | 1211246.022086 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2026 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated | carry_forward_from_2025_pre_release_estimate |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | B00 | 광업 | 2026 | 305618.965553 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2026 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated | carry_forward_from_2025_pre_release_estimate |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | C00 | 제조업 | 2026 | 2404785.572095 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2026 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated | carry_forward_from_2025_pre_release_estimate |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | D00 | 전기, 가스, 증기 및 공기 조절 공급업 | 2026 | 562266.567175 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2026 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated | carry_forward_from_2025_pre_release_estimate |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | ERS | 문화 및 기타서비스업 | 2026 | 1277494.0583819998 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2026 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated | carry_forward_from_2025_pre_release_estimate |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | F00 | 건설업 | 2026 | 1516444.677319 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2026 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated | carry_forward_from_2025_pre_release_estimate |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | G00 | 도매 및 소매업 | 2026 | 1311214.749708 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2026 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated | carry_forward_from_2025_pre_release_estimate |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | H00 | 운수 및 창고업 | 2026 | 1211505.520284 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2026 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated | carry_forward_from_2025_pre_release_estimate |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | I00 | 숙박 및 음식점업 | 2026 | 1097707.128738 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2026 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated | carry_forward_from_2025_pre_release_estimate |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | J00 | 정보통신업 | 2026 | 484245.232783 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2026 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated | carry_forward_from_2025_pre_release_estimate |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | K00 | 금융 및 보험업 | 2026 | 1092423.269598 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2026 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated | carry_forward_from_2025_pre_release_estimate |
| 강원특별자치도 | 32 | 32 | 강원특별자치도 | L00 | 부동산업 | 2026 | 1483502.7448439999 |  | sum of quarterly out-of-sample forecasts | out_of_sample_forecast | reconciled_from_quarterly_estimates | 2026 | 2026-07-18 | VA_nominal | current_pre_release_estimate | N | estimated | carry_forward_from_2025_pre_release_estimate |

## 33. Risk Queue

| risk_id | risk | effect |
| --- | --- | --- |
| R1 | historical release dates incomplete | Strict vintage track limited; sensitivity track used |
| R2 | 2024 actual incomplete in local annual rolling backtest | 2024 multi-origin evaluation pending/limited |
| R3 | monthly indicator vintage incomplete | monthly GVA uses equal-share fallback |
| R4 | 2025 detailed GVA actual unavailable | 2025 estimates are pre-release estimates, not validated actual performance |

## 34. Not-estimable

| scope | cell_count | status |
| --- | --- | --- |
| G8 | 0 | no_forced_numeric_estimate_detected_in_generated_2025_outputs |

## 35. 한계

| limit_id | description |
| --- | --- |
| release_metadata | Strict historical vintage track is limited because exact release dates are incomplete. |
| monthly_actual | Monthly GVA is allocated from quarterly estimates, not observed official monthly GVA. |
| 2025_actual | 2025 detailed GVA actual is unavailable and unused. |

## 36. 최종 결론

The final estimates use transparent origin-specific baselines and allocation policies because strict historical vintage evidence remains incomplete.

| claim | status | reason |
| --- | --- | --- |
| primary_target | GVA_preserved | establishments/employees remain auxiliary |
| complex_model_advantage | not_claimed | strict vintage evidence incomplete; baseline remains transparent policy |
| 2025_outputs | generated_pre_release | annual, quarterly, monthly estimates generated without 2025 actual |
| official_statistics | not_claimed | production and official-statistics use remain false |
