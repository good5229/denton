# 잔여 취약 중분류 보강자료 레지스트리

## 목적

Phase88 최종 레지스트리에서 남은 6개 취약 중분류에 대해, 추가 오차 축소에 필요한 무료·공개 자료 후보를 정리했다. 이번 단계는 수치를 억지로 더 낮추는 실험이 아니라, 다음 실험에서 실제로 투입할 수 있는 자료 후보를 선별하는 단계다.

## 운영 전략

모든 산업을 개별 특화모델로 만들지 않는다. 전 산업 공통 기준을 먼저 유지하고, 실제 중분류 GVA와의 격차가 큰 산업만 원인군별로 묶어 처리한다.

| 원인군 | 대상 | 필요한 신호 | 적용 방식 |
| --- | --- | --- | --- |
| 생산시설형 | 제조업·기계수리 | 공장·설비·제조시설 규모 | 공장등록·제조시설면적·중분류 제조업 구조 결합 |
| 계약·공사형 | 건설·엔지니어링 | 계약액·수주·착공·기성 | 건축허가와 엔지니어링 수주/기술인력 자료 결합 |
| 거래·자산형 | 부동산·금융 | 거래금액·자산·연면적 | 공시가격·연면적·거래·중개업소 지표 결합 |
| 이동·물량형 | 운수·창고 | 승객·화물·창고·항만 물동량 | 여객·창고·항만 신호를 중분류별로 분리 |
| 공공·비영리형 | 협회·복지·환경정화 | 예산·회원·시설정원·처리량 | 비영리 공시·복지시설·환경처리 실적 결합 |
| 디지털·콘텐츠형 | 방송·정보서비스 | 방송매출·콘텐츠·서버·플랫폼 규모 | 방송사업자 재산상황과 정보서비스 사업장 규모 결합 |

## 남은 취약 중분류

| 지역 | 상위산업 | 코드 | 산업 | 실제 억원 | 추정 억원 | 오차 억원 | 오차 % | 필요 자료 |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| 고양시 | ERS | 94 | 협회·단체 | 991.0 | 1,792.6 | 801.6 | 80.9 | 비영리단체·협회 활동규모, 단체 예산·종사자·회원수 |
| 고양시 | J00 | 60 | 방송업 | 954.7 | 386.5 | 568.3 | 59.5 | 방송·콘텐츠 사업장 규모, 방송매출·제작인력·채널/송출시설 |
| 포항시 | MN0 | 72 | 건축기술 엔지니어링 및 기타 과학기술 서비스업 | 2,535.3 | 3,673.9 | 1,138.5 | 44.9 | 전문서비스 임금총액, 용역·설계·엔지니어링 계약액 |
| 포항시 | C00 | 34 | 산업용 기계 및 장비 수리업 | 503.9 | 13.3 | 490.6 | 97.4 | 정비·수리 물량, 수리업 매출, 기계장비 정비시설 규모 |
| 포항시 | ERS | 39 | 환경 정화 및 복원업 | 34.8 | 14.2 | 20.6 | 59.2 | 환경정화 처리량, 복원사업 계약액, 폐기물·오염처리 실적 |
| 포항시 | J00 | 63 | 정보서비스업 | 3.9 | 13.8 | 9.9 | 250.5 | 정보서비스 사업장 규모, 서버·데이터센터·플랫폼 매출 |


## 로컬 보유자료 점검

| 자료ID | 존재 | 설명 | 상태 | 경로 |
| --- | --- | --- | --- | --- |
| building_use_area | True | 건축물 용도별 연면적·건수 | local_available | data/processed/partial_stats_phase51_realestate_legal_dong_use_features.csv |
| building_permit_events | True | 건축 인허가·착공·사용승인 이벤트 | local_available | data/processed/partial_stats_phase52_building_permit_legal_dong_monthly.csv |
| pohang_business_survey | True | 포항 2024 사업체조사 중분류 매출·종사자·사업체수 | local_available | data/processed/partial_stats_phase43_pohang_gu_sales_cv_detail.csv |
| pohang_factory_mapping | True | 포항 공장 업종 매핑 | local_available | data/processed/partial_stats_phase43_pohang_factory_industry_mapping.csv |
| kosis_manufacturing_mining | True | KOSIS 제조·광업 중분류 사업체·종사자·부가가치 | local_available | data/processed/business_employment_feature_table.csv |
| phase88_registry | True | 현재 중분류 정확도 레지스트리 | local_available | data/processed/phase88_current_industry_accuracy_registry/phase88_current_middle_industry_accuracy_registry.csv |


## 무료 공개자료 후보

| 지역 | 코드 | 산업 | 후보 자료 | 무료 여부 | 수집 상태 | 적합도 | 기대 신호 | URL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 포항시 | 72 | 건축기술 엔지니어링 및 기타 과학기술 서비스업 | ETIS 엔지니어링종합정보시스템 | 무료 조회 후보 | web_query_or_manual_export | 핵심 후보 | 엔지니어링 사업자 신고, 수주실적, 매출실적, 임금실태 | https://www.etis.or.kr/webs/cmp/report_new.jsp |
| 고양시 | 94 | 협회·단체 | 공익법인/비영리단체 공시·등록 자료 | 무료 후보 | needs_discovery | 핵심 후보 | 단체 예산·수입·회원·종사자 규모 | manual_search_required |
| 고양시 | 60 | 방송업 | 방송미디어통신위원회_방송사업자 재산상황 공표 현황 | 무료 파일데이터 | candidate_download | 핵심 후보 | 방송사업자 매출·손익·자산 규모 | https://www.data.go.kr/data/15030809/fileData.do |
| 포항시 | 34 | 산업용 기계 및 장비 수리업 | 기계설비·정비업 사업자/수리실적 자료 | 무료 후보 | needs_discovery | 핵심 후보 | 정비 건수, 정비 대상 설비, 수리 매출 | manual_search_required |
| 포항시 | 39 | 환경 정화 및 복원업 | 환경부/한국환경공단 환경정화·복원 또는 오염처리 실적 | 무료 후보 | needs_discovery | 핵심 후보 | 환경정화 처리량, 복원사업 계약액, 오염처리 실적 | manual_search_required |
| 포항시 | 63 | 정보서비스업 | 정보서비스·데이터센터·플랫폼 사업자 자료 | 무료 후보 | needs_discovery | 핵심 후보 | 서버·데이터센터·플랫폼 매출 또는 사업장 규모 | manual_search_required |
| 포항시 | 72 | 건축기술 엔지니어링 및 기타 과학기술 서비스업 | 전국건설업체정보표준데이터 | 무료 API | api_application_required | 보조 | 건설 관련 업체 소재지·업종·공시 정보 | https://www.data.go.kr/data/15129444/standard.do?recommendDataYn=Y |
| 고양시 | 94 | 협회·단체 | 근로복지공단 고용·산재보험 가입 사업장 현황 | 무료 | candidate_download_or_api | 보조 | 협회·단체/기타 개인서비스 사업장·가입자 규모 | https://www.data.go.kr/data/15129538/fileData.do |
| 포항시 | 63 | 정보서비스업 | 근로복지공단 고용·산재보험 가입 사업장 현황 | 무료 | candidate_download_or_api | 보조 | 정보통신업 사업장·가입자 규모 | https://www.data.go.kr/data/15129538/fileData.do |
| 포항시 | 34 | 산업용 기계 및 장비 수리업 | 포항 공장 업종 매핑 | 로컬 수집 완료 | local_available_but_sparse | 부족 | 산업용 기계·장비 수리업 공장/사업체 존재 | local:data/processed/partial_stats_phase43_pohang_factory_industry_mapping.csv |


## 수집 우선순위

1. 고양 방송업: 방송사업자 재산상황 공표 자료가 가장 직접적이다. 방송사업자별 매출·손익·자산을 지역 또는 사업자 소재지와 연결할 수 있는지 확인한다.
2. 포항 건축·엔지니어링 서비스업: ETIS의 엔지니어링 사업자, 수주실적, 매출실적, 임금실태 메뉴가 가장 직접적이다. 자동 수집이 어려우면 수동 export 가능성을 확인한다.
3. 포항 산업용 기계 수리업: 현재 로컬 공장 매핑은 C34 직접 행이 희소하다. 수리업 매출·정비물량·정비시설 자료가 새로 필요하다.
4. 고양 협회·단체: 비영리단체 활동규모나 예산/회원/종사자 자료가 필요하다. 일반 사업체 수로는 과대 배분이 남는다.
5. 포항 정보서비스업·환경정화복원업: 실제 GVA가 작아 일반 활동지표가 쉽게 과대 배분된다. 서버·데이터센터·플랫폼 규모, 환경정화 처리량·계약액 같은 직접 물량자료가 필요하다.

## 판정

현재 보유자료만으로 추가 실험을 강행하면 임의 상한·하한에 가까워질 위험이 크다. 다음 실험은 위 후보 중 실제 파일/API 수집이 가능한 자료를 확보한 뒤, 개별 중분류의 실제 GVA 대비 오차가 줄어드는 경우에만 채택한다. 성능 표기는 항상 실제 GVA, 추정 GVA, 오차금액, 오차율을 함께 사용한다.
