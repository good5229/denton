# 전국 GRDP/GVA 추정 검증 대시보드

## 실행

정적 파일 구조이므로 `dashboard/index.html`을 브라우저로 열면 된다. 데이터 fetch를 쓰지 않고 `dashboard/data/dashboard_data.js`를 직접 로드하므로 로컬 파일 열기에서도 동작한다.

데이터를 다시 만들려면:

```bash
.venv/bin/python dashboard/prepare_dashboard_data.py
```

## 포함 범위

- 지역: 17개 시도 + 229개 시군구/통합시 단위
- 추정 기간: 2021~2025년
- 업종: 전국 검증 산출물의 15개 경제활동 업종군
- 시도 total: 추정 GRDP와 공식 시도 GRDP actual 비교
- 시군구 total: 추정 GVA + 시도 순생산물세·기타항목 배분형 GRDP 추정
- 시군구 actual: 2021~2023년 공개 GVA 중심. 2024~2025년 시군구 actual은 미공표/미확보 구간으로 추정값만 표시
- 지도 이동 좌표: 17개 시도 + 229개 시군구/통합시 전부 행정청사 좌표 적용

## 주요 원천

- `nationwide/outputs/sido_quarterly_grdp_validation.csv`
- `nationwide/outputs/operating_point_sido_grdp_validation.csv`
- `nationwide/outputs/sido_activity_quarterly_validation.csv`
- `nationwide/outputs/sigungu_industry_quarterly_predictions.csv`
- `nationwide/outputs/annual_sigungu_gva_normalized.csv`
- `nationwide/outputs/sido_other_npt_quarterly_predictions.csv`
- `nationwide/outputs/hard_region_indicator_route_rolling_gate_grdp_detail.csv`
- `nationwide/outputs/hard_region_activity_diagnostics.csv`
- `data/processed/admin_center_coordinates/esri_local_government_offices_2025.csv`

## 해석 주의

시도 단위는 GRDP actual과 직접 비교할 수 있다. 반면 시군구는 공개 actual이 보통 GVA이므로, 화면에서는 `GRDP형 추정`과 `실제 GVA`를 분리해 보여준다. 둘을 같은 official GRDP 검증값처럼 해석하면 안 된다.

인천·울산·세종·대구·충북은 5개년 검증에서 상대적으로 어려운 지역이므로, 모달에 `recursive_no_target_actual` 트랙의 `1분기+1개월` 운영시점 기준 취약 업종 TOP 5를 표시한다. 표에는 주요 원인, 필요 직접자료, 개선/보강 방향을 함께 표시한다. 이는 예측 실패 원인을 설명하기 위한 진단이며, Q1~Q2 보조 성과와는 별도다. 모든 운영시점에서 독립 보조지표를 자동 채택한다는 뜻은 아니다.

지역 검색 후 지도는 행정청사 좌표로 이동한다. 현재 인천광역시와 인천 10개 군구는 공공데이터포털 원천을 우선 적용하고, 나머지 지역은 ESRI Korea 공개 관공서 레이어의 행정안전부 주소 기반 지오코딩 좌표를 적용한다.

경기도 청사및출장소 현황 CSV가 `data/raw/admin_center_coordinates/gyeonggi_office_branch_15057551.csv`에 저장되면 경기도 및 경기도 시군청 좌표는 더 직접적인 지역 원천으로 자동 반영된다. 현재는 전국 커버리지를 위해 ESRI Korea 공개 관공서 레이어를 사용한다.

ESRI/MOIS 좌표는 공개 조회 가능한 레이어에서 수집했으나, 원천 메타데이터의 사용권 표기는 `All rights reserved by Korean Ministry of Interior and Safety`다. 따라서 외부 재배포·상업적 이용 가능 범위는 원천 사용조건을 별도 확인해야 한다. 원자료 기준일은 2016.12, 서비스 갱신 표기는 2025.02다.
