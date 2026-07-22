# Phase56 주택 공시가격 Parquet 변환

## 결론

- 공공데이터포털 주택 공시가격 2025년 ZIP을 다운로드한 뒤, ZIP 내부 CSV를 직접 streaming하여 Parquet/Zstd로 변환했다.
- 전체 CSV를 별도 압축해제하지 않았고, 변환 검증 후 원본 ZIP은 삭제했다.
- 전체 행수: 15,580,435행
- 고양·포항 추출 행수: 495,846행
- 원본 ZIP 크기: 144.2MB
- 전체 Parquet 크기: 82.9MB
- 고양·포항 Parquet 크기: 2.3MB
- 원자료의 `시군구` 표기는 `고양덕양구`, `포항남구`처럼 “시”가 생략되어 있어 이 표기로 추출했다.

## 지역별 추출 행수

| 지역 | 행수 |
| --- | ---: |
| 경기도 고양덕양구 | 160,732 |
| 경기도 고양일산동구 | 78,684 |
| 경기도 고양일산서구 | 91,377 |
| 경상북도 포항남구 | 66,875 |
| 경상북도 포항북구 | 98,178 |

## 산출 파일

- `data/processed/phase56_housing_price/molit_public_housing_price_2025.parquet`
- `data/processed/phase56_housing_price/molit_public_housing_price_2025_goyang_pohang.parquet`
- `data/processed/phase56_housing_price/molit_public_housing_price_2025_manifest.json`