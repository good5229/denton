# 공공데이터 기반 시군구 외부 Feature 수집

## 목적

시군구 ML 재개 조건인 신규 직접 설명변수 확보를 위해 무료 공공데이터 후보를 실제 취득 가능성 기준으로 점검했다.

## 실제 확보

| Source | 상태 | 산출물 |
| --- | --- | --- |
| KEPCO 시군구별 전력사용량 | 월별 XLSX 다운로드 및 정규화 완료 | `kepco_sigungu_electricity_long.csv`, `kepco_sigungu_electricity_wide.csv` |
| KICOX 공장등록 현황 통계정보 | XLSX 다운로드 성공, 본문 시트는 제목만 존재 | `kicox_factory_registration_schema_probe.csv` |
| MOLIT 건축인허가 기본개요 | 메타데이터/필드 확인, 본체 파일은 외부 HUB 대용량 제공 구조 | `public_feature_source_inventory.csv` |

- 전력 long rows: 148,616
- 전력 wide rows: 3,664
- 공장등록 workbook sheets: 28

## Source Inventory

| 우선순위 | source_id | 상태 | 대상 산업 | URL |
| ---: | --- | --- | --- | --- |
| 1 | kepco_sigungu_electricity_sales | collected_from_provider_board | C00,D00,E00,all | https://www.data.go.kr/data/3069444/fileData.do?recommendDataYn=Y |
| 2 | molit_building_permit_basic | metadata_collected_source_file_not_directly_exposed | F00,L00 | https://www.data.go.kr/data/15044695/fileData.do?recommendDataYn=Y |
| 3 | kicox_factory_registration_stats | schema_probe_downloaded_empty_workbook | B00,C00 | https://www.data.go.kr/data/3041646/fileData.do |
| 4 | kicox_national_industrial_complex_trends | candidate_not_collected | C00 | https://www.data.go.kr/data/3042071/fileData.do |
| 5 | niier_livestock_aquaculture_inventory | candidate_not_collected | A00 | https://www.data.go.kr/data/15091204/fileData.do?recommendDataYn=Y |

## 전력 Feature

전력 파일은 KEPCO 공식 게시판의 월별 XLSX에서 수집했다. 각 파일은 해당 연도 1월부터 source month까지의 누적 월별 표를 포함하므로, 동일 관측월이 여러 source file에 존재할 때는 가장 최신 source file을 채택했다.

주요 feature 후보:

- `electricity_contract_kwh_산업용`
- `electricity_contract_kwh_일반용`
- `electricity_contract_kwh_total`
- `electricity_use_industry_kwh_total`
- `industrial_contract_electricity_share`

공표지연은 보수적으로 2개월을 가정해 `first_eligible_period`를 부여했다.

## 건축 Feature 상태

건축인허가 기본개요는 시군구코드, 법정동코드, 대지면적, 건축면적, 연면적, 주용도코드, 실제착공일, 건축허가일, 사용승인일을 포함하는 것으로 확인했다. 다만 공공데이터포털 파일 다운로드 응답에는 직접 파일 ID가 노출되지 않고, 원천은 건축HUB 대용량 제공 페이지로 연결된다.

따라서 다음 구현은 건축HUB 대용량 파일 또는 Open-API 신청/키 방식 확인 후 `sigungu × permit/start month × main_use` 집계로 진행해야 한다.

## 공장등록 Feature 상태

공장등록 XLSX 파일은 다운로드됐지만, 현재 파일의 각 시트는 제목 행만 포함한다. 포털 설명에도 대용량 문제로 FactoryOn 원 사이트 이용을 권장한다고 되어 있으므로, 다음 단계는 FactoryOn 자료실 또는 관련 세부 파일데이터(`시도별 업종별`, `공장면적`)를 별도로 수집하는 것이다.

## ML 재개 판단

이번 단계에서 전력사용량은 실제 시군구 월간 feature로 즉시 사용 가능하다. 건축 인허가는 필드 적합성은 높지만 본체 수집 경로가 남아 있어 아직 ML 재개 조건의 두 번째 직접 feature로 확정하기는 이르다.
