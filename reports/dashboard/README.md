# Dashboard

정적 HTML 대시보드다. 원천 CSV는 `data/processed/` 아래의 CP949 CSV를 직접 읽는다.

로컬 브라우저 보안 정책 때문에 파일을 더블클릭하면 CSV fetch가 막힐 수 있다. 저장소 루트에서 아래 명령으로 서버를 띄운 뒤 접속한다.

```bash
python3 -m http.server 8000
```

접속 URL:

```text
http://localhost:8000/reports/dashboard/
```

현재 표시 범위:

- 시도: 연도별 롤링 예측 vs 실제, 분기별 예측. 전국 분기는 경제활동별 GDP 실측치와 비교
- 시군구: 연도별 벤치마크 제약 진단, 분기별 추정값
- 읍면동: 예측값이 아니라 자료 후보 인벤토리

산업군 필터의 `전체`는 선택 지역과 기간 안에서 산업별 예측/실제 행을 합산한 비교 시계열이다. 서울 자치구 연간 총량은 `scripts/collect_seoul_district_grdp.py`로 `DT_201012_D040028`를 수집하면 `seoul_district_grdp_annual.csv`로 보강된다.

월간 예측값은 아직 생성하지 않았으므로 UI에서 안내 메시지만 표시한다.
