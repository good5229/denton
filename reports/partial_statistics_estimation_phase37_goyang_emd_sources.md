# Phase 37: 고양시 현행 행정동 산업·월 자료 수집과 교차검증

## 결론

무료 공식 자료만으로 고양시 **현행 44개 행정동**에 대해 산업별 월간 변동을 구분하는 입력자료를 실제 수집했다. Phase 36의 2015년 39개 동 고정배분보다 분명한 개선이다. 다만 이번 산출물은 GVA가 아니라 **GVA 배분에 투입할 사업체 활동 프록시**다.

- `I00 숙박·음식점`, `S00 개인서비스`: 다음 GVA 배분 실험의 주 공간·시간 프록시로 사용할 수 있다.
- `Q00 보건·사회복지`, `R00 예술·스포츠·여가`: 보조 프록시로 사용할 수 있다.
- `G00 도소매`: 대규모점포만으로는 전체 도소매를 대표하지 못하므로 단독 사용을 기각한다.
- `P00 교육`: 고양시 제공 학원·교습소 스냅샷으로 현행 공간구조는 개선할 수 있지만, 과거 월별 변화는 아직 없다.
- `H00 운수`, `M00 전문서비스`, `N00 사업지원`: 이번 무료 인허가 묶음으로는 직접 보강되지 않았다.

따라서 “고양 행정동×산업×월 GVA”를 곧바로 관측했다고 주장할 수는 없지만, **I/S를 중심으로 Phase 36의 동일 월간 프로필 결함을 제거한 재배분 실험**은 진행할 수 있다.

## 수집한 공식 무료 자료

| 자료 | 범위·기준 | 역할 | 인증 |
| --- | --- | --- | --- |
| [고양시 생활지도](https://www.goyang.go.kr/bigdata/lvlhmap/map.do) 행정동 GeoJSON | 현행 44개 동, 행정동 코드, EPSG:5179 | 공간경계와 좌표 결합 | 불필요 |
| [고양시 주민등록인구](https://www.data.go.kr/data/3070908/fileData.do) | 2024년 말 44개 동, 인구·세대 | 현행 동 목록 및 보조 규모변수 | 불필요 |
| [LOCALDATA](https://www.localdata.go.kr/portal/portalDataGuide.do?menuNo=30002) 인허가 19종 | 고양시 기관코드 3940000, 개·폐업일과 좌표 | 2021-01~2026-06 월별 인허가 stock/flow | 불필요 |
| [고양시 생활지도](https://www.goyang.go.kr/bigdata/lvlhmap/map.do) 학원·교습소 | 2026-06 스냅샷 | P00 현행 공간구조 | 불필요 |
| [고양시 사업체조사 DB](https://www.goyang.go.kr/bigdata/bsnes/bsnes.do?selected=2) / KOSIS | 2021~2023 구×KSIC 대분류 사업체·종사자 actual | 공간·연간 교차검증 및 향후 마진 | KOSIS OpenAPI 키 사용 |

모든 수집자료는 무료다. 카드사·통신사 유료 데이터와 과거 `NABIS_contest/civil_data`는 사용하지 않았다. 기존 KOSIS 키 외에 새로 필요한 API 키는 없다.

## 만들어진 자료

- `partial_stats_phase37_goyang_emd_current.csv`: 44개 현행 행정동 코드·구·2024 인구·세대
- `partial_stats_phase37_goyang_emd_industry_monthly_proxy.csv`: 44동×5산업×66개월 = 14,520행
- `partial_stats_phase37_goyang_emd_education_snapshot.csv`: 2026-06 학원·교습소 현행 공간분포
- `partial_stats_phase37_goyang_gu_industry_annual_actual.csv`: 2021~2023 고양시/3개 구×19산업 사업체·종사자 actual 456행
- `partial_stats_phase37_goyang_source_audit.csv`: 인허가 19종별 좌표·시점·해시 감사
- `partial_stats_phase37_goyang_source_manifest.csv`: 원천 28개 파일의 크기와 SHA-256
- `partial_stats_phase37_goyang_spatial_cross_validation.csv`: 구 공간비중 교차검증
- `partial_stats_phase37_goyang_temporal_cross_validation.csv`: 연간 증감률 교차검증
- `partial_stats_phase37_goyang_common_proxy_audit.csv`: 산업 간 동일 공간프록시 검사
- `partial_stats_phase37_goyang_sector_use_gate.csv`: 산업별 사용 판정

월별 프록시의 세 지표는 월말 영업 인허가 stock, 당월 신규 인허가, 당월 폐업이다. 이는 전체 사업체 수나 매출이 아니며, 업종별 인허가 제도에 포함된 사업체 활동만 측정한다.

## 수집 품질

LOCALDATA 19종은 66,160개 인허가 기록을 현재 행정동에 공간결합했다. 원천 행 대비 행정동 좌표 매칭률은 업종별 80.0~100.0%이며, 일반음식점 94.96%, 휴게음식점 96.35%, 미용업 94.45%다. 모든 동·산업 월 패널에서 다음 항등식이 성립했다.

`당월 stock = 전월 stock + 당월 신규 - 당월 폐업`

고양시 교육 스냅샷은 강좌 행을 기관명·주소로 중복 제거했다. 학원 2,148개 중 1,886개(87.80%), 교습소 1,125개 중 958개(85.16%)가 행정동 코드와 결합됐다. 이 값은 월간 시계열이 아니라 2026-06 공간 스냅샷이다.

## 공간 교차검증

2021~2023년 각 12월 인허가 stock의 3개 구 비중을 KOSIS 구×산업 실제 사업체 비중과 비교했다.

| 산업 | 구 비중 MAE | 평균 상관 | actual 대비 인허가 범위 | 판정 |
| --- | ---: | ---: | ---: | --- |
| I00 숙박·음식점 | 0.51%p | 0.999 | 106.4% | Strong |
| S00 개인서비스 | 0.52%p | 1.000 | 41.0% | Strong |
| Q00 보건·사회복지 | 2.16%p | 0.990 | 53.7% | Supplementary |
| R00 예술·스포츠·여가 | 4.32%p | 0.921 | 42.7% | Supplementary |
| G00 도소매 | 8.12%p | -0.354 | 0.18% | Reject as standalone |

인허가 범위가 100%를 넘는 I00은 하나의 사업체가 복수 인허가를 보유할 수 있고 KOSIS 사업체 정의와 인허가 단위가 다르기 때문이다. 따라서 수준을 직접 대입하지 않고 **동별 상대비중과 월별 변화**만 사용해야 한다.

## 시간 교차검증

2022~2023년 10개 산업·연도 비교 중 8개는 인허가 stock과 KOSIS 실제 사업체수의 증감 방향이 일치했다. I00은 2022년에 프록시 +1.48%, actual -0.22%로 방향이 달랐고, G00도 2022년에 방향이 달랐다. R00의 2023년 성장률 오차는 4.75%p였다.

이 결과는 인허가 월변동을 그대로 GVA 성장률로 사용할 근거가 아니라, Denton 배분 시 움직임을 제공하는 제한적 indicator로 쓸 근거다. 월간 actual이 없으므로 직접 월별 정확도는 아직 검증되지 않았다.

## 공통 프록시 재발 여부의 엄격 검사

Phase 36의 결함은 같은 구·산업 안 모든 동이 동일한 정규화 월간 프로필을 물려받았다는 점이었다. 이번에는 다음을 별도로 검사했다.

1. 66개 월 각각에서 5개 산업의 동별 공간비중 10쌍을 전수 비교했다.
2. 총 660개 산업쌍·월 중 완전히 동일한 공간비중은 **0개**였다.
3. 산업 간 공간비중의 최대 상관은 0.880으로 1에 근접하지 않았다.
4. I/Q/R/S는 44개 동 모두 서로 다른 66개월 stock 프로필을 가졌다. G00은 자료 자체가 76개 대규모점포뿐이어서 44개 동 중 23개만 비영(非零)이며 단독 프록시로 기각했다.
5. KOSIS 구 actual의 `3개 구 합 = 고양시 합계` 오차는 전 산업·연도에서 0이었다.

즉, 이번 자료에는 “하나의 공통 사업체 프록시를 모든 산업 또는 동에 복제”한 문제는 없다. 다만 서로 다른 인허가 업종을 같은 산업 대분류로 합산한 것이므로, 산업 내부 구성비 변화와 중복 인허가는 다음 단계에서 민감도 분석해야 한다.

## 다음 GVA 실험에 적용하는 방법

Phase 38에서는 자료의 강도에 따라 다르게 적용하는 것이 안전하다.

1. 고양시 산업별 연간 GVA와 분기 총량을 상위 마진으로 둔다.
2. KOSIS 3개 구×산업 사업체·종사자 actual로 연간 공간 마진을 만든다.
3. I00·S00은 행정동 인허가 stock/flow로 구 내부의 동 비중과 월 움직임을 갱신한다.
4. Q00·R00은 인구·시설자료와 결합한 앙상블만 시험하고 단일 인허가 결과도 함께 제시한다.
5. P00은 2026-06 학원·교습소를 현행 공간비중에만 쓰고, 동별 월변동 주장은 보류한다.
6. G00은 다른 도소매 전수성 자료가 들어오기 전까지 Phase 36 방식보다 개선됐다고 판정하지 않는다.
7. 매 단계에서 월→분기, 동→구, 구→고양시, 분기→연간을 각각 재조정하고 잔차를 공개한다.
8. 2021~2022로 가중치를 정하고 2023 KOSIS 구×산업 actual을 숨긴 시공간 holdout으로 사용한다. 보존식 통과와 예측 정확도 통과를 분리한다.

핵심 한계는 검증 actual이 구 수준이라는 점이다. 구 교차검증이 강한 I/S도 **행정동 actual 정확도가 입증된 것은 아니다**. 공모전에서는 “행정동 경제활동 추정지수” 또는 “GVA 배분 추정치”로 명명하고, 공식 통계나 관측 GVA로 표현하면 안 된다.

## 재현

```bash
.venv/bin/python scripts/collect_phase37_goyang_emd_sources.py
.venv/bin/python scripts/discover_phase37_goyang_kosis.py
.venv/bin/python scripts/collect_phase37_goyang_kosis_actuals.py
.venv/bin/python scripts/verify_phase37_goyang_emd_sources.py
.venv/bin/pytest -q tests/test_partial_statistics_phase37_goyang_sources.py
```

