# Phase192 제조업 중분류 직접 활동자료 후보 맵

## 목적

Phase188~190의 결론은 분명하다. 제조업 산업생산지수는 시간배분에는 핵심이지만 중분류 금액오차를 직접 줄이지 못하고, 공장등록 current snapshot 단순 혼합도 운영 채택에는 불안정하다. Phase192는 잔여 제조업 고오차 중분류를 대상으로 무료 공개자료/API 후보를 정리해 다음 수집·실험 순서를 고정한다.

## 후보 자료

| source_id | source_name | url | related_notice | free_or_key | coverage | target_use | candidate_ksic | temporal_role | priority | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| KICOX_FACTORY_PRODUCTION_API | 한국산업단지공단_공장등록생산정보조회서비스 | https://www.data.go.kr/en/data/15100060/standard.do | https://www.data.go.kr/bbs/ntc/selectNotice.do?originId=NOTICE_0000000004062 | 무료 / 공공데이터포털 활용신청 필요 가능 | 전국 공장, 생산품, 업종코드, 회사명, 주소 등 | 고양·포항 제조업 중분류/소분류 생산품 텍스트 매핑, 공장 current snapshot 보완 | C10,C13,C14,C18,C21,C23,C25,C27,C28,C29,C34 등 | 정밀화 중심; history가 없으면 속보성 불가 | A | 현재 file snapshot보다 검색조건/응답 업종코드가 좋아 중분류·소분류 매핑 보강 가능 |
| KICOX_FACTORY_LOT_API | 한국산업단지공단_공장등록필지정보조회서비스 | https://www.data.go.kr/data/15087615/openapi.do |  | 무료 / 개발계정 1,000건 | 공장 기본 및 필지정보 | 공장면적·필지 기반 제조시설 규모 보정, 읍면동 공간배분 보강 | C23,C24,C25,C28,C29 등 면적 민감 업종 | 정밀화 중심; 실시간 current snapshot | A | 포항 금속·비금속·전기장비의 공장 규모 차이를 current snapshot보다 세밀하게 파악할 후보 |
| MOLIT_INDUSTRIAL_LOCATION_WFS | 국토교통부_산업입지도(WMS/WFS) | https://www.data.go.kr/data/15056776/openapi.do |  | 무료 / VWorld 연계 | 전국 산업단지 경계, 용도지역, 시설용지, 유치업종 | 포항 철강산단·고양 제조입지 공간제약, 읍면동 제조업 공간배분 보강 | C00 전체, 특히 C24,C25,C28 | 공간 정밀화; 시간 직접 지표 아님 | A | 공장 주소 매칭이 약한 경우 산업단지 경계와 유치업종으로 공간분포를 보강 가능 |
| MOTIE_STEEL_TREND_FILE | 산업통상부_철강산업 동향 | https://www.data.go.kr/data/3039950/fileData.do?recommendDataYn=Y |  | 무료 파일데이터 | 전국 철강산업 생산·수출입·소비 등 연간 동향 | 포항 C24 1차 금속 제조업의 시간/전국 경기 보조지표 | C24 | 연간 정밀화 보조; 지역 직접자료 아님 | B | 포항 지역성은 약하지만 철강산업 경기 방향 보정 후보 |
| LOCALDATA_FOOD_ADDITIVE_MFG | 행정안전부_식품_식품첨가물제조업 조회서비스 | https://www.data.go.kr/data/15155162/openapi.do |  | 무료 / 개발계정 10,000건 | 전국 식품첨가물 제조업 인허가 info/history | 고양 C10 식료품 제조업 세부 활동자료 | C10 | history 엔드포인트 활용 시 월/분기 인허가 stock 가능 | B | C10 전체는 아니지만 식품 제조 하위 일부의 월별 변화를 직접 반영 가능 |
| MFDS_DRUG_PRODUCT_PERMISSION | 식품의약품안전처_의약품 제품 허가정보 | https://www.data.go.kr/data/15095677/openapi.do |  | 무료 / 개발계정 10,000건 | 의약품 품목, 제조원, 허가일자, 업체명 등 | 고양 C21 의료용 물질 및 의약품 제조업 활동자료 | C21 | 허가일자 기반 정밀화·일부 속보 가능 | B | 고양 C21 오차가 커서 제품허가/제조원 기반 보조지표가 필요 |
| LOCALDATA_MEDICAL_DEVICE_REPAIR | 행정안전부_건강_의료기기수리업 조회서비스 | https://www.data.go.kr/data/15154913/openapi.do |  | 무료 / 개발계정 10,000건 | 전국 의료기기 수리업 인허가 info/history | 고양 C27 및 수리성 업종 보조, 포항 C34와 직접 대응 여부 점검 | C27,C34 일부 | history 엔드포인트 활용 시 월/분기 stock 가능 | B | 의료정밀·수리업 계열의 사업장 변화를 포착할 수 있는 직접 인허가 자료 |
| LOCALDATA_ELEVATOR_MANUFACTURERS_IMPORTERS | 행정안전부_기타_승강기제조및수입업체 조회서비스 | https://www.data.go.kr/data/15155100/openapi.do?recommendDataYn=Y |  | 무료 / 개발계정 10,000건 | 전국 승강기 제조/수입업체 인허가 info/history | 포항 C28 전기장비·C29 기계장비 중 일부 설비업체 보조 | C28,C29 | history 엔드포인트 활용 시 월/분기 stock 가능 | C | 범위는 좁지만 포항 전기장비 고오차 원인 진단 보조 가능 |
| LOCALDATA_ELEVATOR_MAINTENANCE | 행정안전부_기타_승강기유지관리업체 조회서비스 | https://www.data.go.kr/data/15155095/openapi.do |  | 무료 / 개발계정 10,000건 | 전국 승강기 유지관리업체 인허가 info/history | 포항 C34 산업용 기계 및 장비 수리업의 유지관리 성격 보조 | C34 일부 | history 엔드포인트 활용 시 월/분기 stock 가능 | C | C34 전체에는 좁지만 유지보수 활동자료로 공장생산 지표 한계를 보완 |

## 중분류별 라우팅 계획

| city | middle_code | middle_name | phase188_2024_error_eok | first_sources | experiment | expected_gain |
| --- | --- | --- | --- | --- | --- | --- |
| 포항시 | C28 | 전기장비 제조업 | 5,638 | KICOX_FACTORY_PRODUCTION_API; KICOX_FACTORY_LOT_API; LOCALDATA_ELEVATOR_MANUFACTURERS_IMPORTERS | 생산품 텍스트에서 전기·배전·제어·케이블 키워드 추출 + 공장규모 가중 | current snapshot만으로는 불안정, 제품/업종코드 세분화가 핵심 |
| 포항시 | C25 | 금속가공제품 제조업 | 1,921 | KICOX_FACTORY_PRODUCTION_API; KICOX_FACTORY_LOT_API; MOLIT_INDUSTRIAL_LOCATION_WFS | 철강산단 입지 + 금속가공 생산품 키워드 + 제조시설면적 | C24와 C25 경계 혼동 완화 |
| 포항시 | C23 | 비금속 광물제품 제조업 | 1,622 | KICOX_FACTORY_PRODUCTION_API; KICOX_FACTORY_LOT_API | 레미콘·시멘트·석재·내화물 생산품 키워드와 면적/용지 가중 | 건설수요와 공장규모 보조가 필요 |
| 포항시 | C34 | 산업용 기계 및 장비 수리업 | 1,209 | KICOX_FACTORY_PRODUCTION_API; LOCALDATA_ELEVATOR_MAINTENANCE; LOCALDATA_MEDICAL_DEVICE_REPAIR | 수리·정비·유지관리 키워드와 인허가 history stock 결합 | 공장생산 지표 대신 정비서비스성 활동자료 필요 |
| 고양시 | C13 | 섬유제품 제조업 | 205 | KICOX_FACTORY_PRODUCTION_API; KICOX_FACTORY_LOT_API | 원단·섬유·봉제 생산품 키워드와 제조시설면적 가중 | Phase190에서 제조시설면적 후보가 일부 개선 |
| 고양시 | C21 | 의료용 물질 및 의약품 제조업 | 168 | MFDS_DRUG_PRODUCT_PERMISSION; KICOX_FACTORY_PRODUCTION_API | 의약품 허가 제조원/허가일자 + 공장등록 의약품 생산품 매칭 | 공장수보다 제품허가 활동자료가 직접적 |
| 고양시 | C29 | 기타 기계 및 장비 제조업 | 331 | KICOX_FACTORY_PRODUCTION_API; KICOX_FACTORY_LOT_API; LOCALDATA_ELEVATOR_MANUFACTURERS_IMPORTERS | 기계·장비 생산품 키워드 세분화 + 공장규모 | C28/C29/C34 경계 재분류 필요 |

## 우선순위

1. **한국산업단지공단 공장등록생산정보/필지정보 API**를 먼저 확인한다. 현재 파일 스냅샷보다 업종코드·생산품·필지 조건검색이 좋아 C28/C25/C23/C29/C34 경계 혼동을 줄일 가능성이 가장 크다.
2. 산업입지도 WFS는 시간지표가 아니라 공간제약용이다. 포항 철강산단·산업단지 내 제조업 공간배분에 우선 적용한다.
3. 행안부/MFDS 업종별 인허가 API는 특정 하위 업종만 보완한다. C10·C21·C27·C34처럼 공장등록만으로 부족한 업종에 제한 적용한다.
4. current snapshot 자료는 정밀화 후보로만 사용한다. 속보성 모델에 쓰려면 info가 아니라 history 엔드포인트 또는 공표시점 기준 수집 이력이 필요하다.

## API 키 요청 후보

- 공공데이터포털 기존 key로 사용 가능할 가능성이 높음: KICOX 공장등록생산정보, KICOX 공장등록필지정보, 행안부 표준 인허가 API, MFDS 의약품 제품 허가정보.
- VWorld 계정/key가 필요할 수 있음: 국토교통부 산업입지도 WMS/WFS.

## 상태

```json
{
  "phase": "phase192_manufacturing_direct_source_map",
  "created_at": "2026-07-26T18:55:28+09:00",
  "candidate_sources": 9,
  "routed_middle_industries": 7,
  "next_action": "KICOX production/lot APIs first; then targeted LOCALDATA/MFDS APIs if keys approved"
}
```
