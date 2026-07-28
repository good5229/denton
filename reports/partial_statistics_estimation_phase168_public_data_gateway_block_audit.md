# Phase168 공공데이터포털 API Gateway 403 진단

## 목적

Phase166~167에서 새로 활용신청한 조달청·심평원·환경공단·행안부 API가 모두 `Forbidden`으로 응답했다. 단순히 신규 API의 승인 미반영인지, 아니면 현재 공공데이터포털 API gateway 접근 전체가 막힌 것인지 구분하기 위해 기존에 수집 성공 이력이 있는 RTMS API를 대조 호출했다.

## 대조 결과

| 점검 대상 | endpoint | 키/프로토콜 조합 | 결과 |
| --- | --- | --- | --- |
| RTMS 아파트 매매 실거래 | `apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev` | `http × decoding_urlencode` | 403 Forbidden |
| RTMS 아파트 매매 실거래 | 동일 | `http × encoding_raw` | 403 Forbidden |
| RTMS 아파트 매매 실거래 | 동일 | `https × decoding_urlencode` | 403 Forbidden |
| RTMS 아파트 매매 실거래 | 동일 | `https × encoding_raw` | 403 Forbidden |

## 판정

현재 실패는 조달청 사용자정보·비급여·폐기물·물류 등 특정 신규 API만의 문제가 아니라, `apis.data.go.kr` gateway 전체 접근 문제일 가능성이 높다. 같은 공공데이터포털 키로 과거 RTMS 자료를 수집한 산출물이 이미 존재하므로, 현재 원인은 다음 중 하나일 수 있다.

1. 공공데이터포털 인증키 상태 변경 또는 재발급 필요
2. 새로 신청한 서비스가 현재 사용 중인 인증키에 연결되지 않음
3. 개발계정 트래픽/일시 차단/공공데이터포털 gateway 정책 문제
4. 현재 실행 환경 IP에 대한 gateway 차단

## 모델링 영향

이번 단계에서 신규 공공데이터포털 API를 총부가가치(GVA) 추정모형에 반영하면 안 된다. 실제 행을 받지 못했고, `Forbidden` 상태이므로 활동자료의 존재만으로 성능 개선을 주장할 수 없다.

다만 이미 로컬에 보유한 자료는 계속 사용할 수 있다.

- RTMS 2020~2023 실거래/전월세 캐시
- 조달청 입찰공고 Phase122 캐시
- 해수부/해양수산통계 포항항 물동량 캐시
- 경기버스 자동수집 자료
- KOBIS 수집 가능 자료
- 건축HUB/공장/전력 등 기존 구조자료

## 사용자가 확인할 사항

공공데이터포털 마이페이지에서 다음을 확인해야 한다.

1. 현재 `.env`에 넣은 공공데이터포털 키가 “활성” 상태인지
2. 새로 신청한 API들이 동일 키에 연결되어 “승인” 상태인지
3. 일일 트래픽 초과 또는 제한 안내가 있는지
4. 필요하면 공공데이터포털 인증키를 재발급해 `DATA_GO_KR_DECODING`, `DATA_GO_KR_ENCODING`에 반영

## 로컬 재현용 점검 명령

키 값을 출력하지 않는 점검 스크립트:

```bash
.venv/bin/python scripts/probe_phase166_newly_approved_activity_apis.py
.venv/bin/python scripts/probe_phase167_remaining_activity_apis.py
```

정상 상태라면 최소한 일부 API가 `ok_items` 또는 `ok_empty_or_needs_params`로 바뀌어야 한다. 계속 `Forbidden`이면 키/승인/gateway 문제로 보고 공공데이터포털 쪽 확인이 필요하다.

## 다음 진행

공공데이터포털 gateway가 복구되기 전까지는 신규 API 기반 개선은 보류한다. 대신 다음 실험은 로컬에 이미 수집된 캐시 자료를 이용해, 고양·포항의 남은 고오차 업종에 대해 보수적 조합 가중과 외부 검증 가능한 자료만 사용하는 방향으로 진행한다.
