# Phase135 고양시 스포츠·영화 레이어 활동강도 감사

## 목적

Phase134에서 추가 수집한 고양시 무료 포털 레이어가 단순 시설 수를 넘어 GVA 배분에 쓸 만한 강도 변수를 갖는지 확인했다. 이 단계는 예측값을 바꾸지 않고, 정밀화·공간배분 후보성과 strict flash 부적격성을 분리한다.

## 레이어별 활동강도 변수

| layer id | layer name | reference period | row count | leader count | building area ㎡ | member capacity | intensity score | strict flash 2023 | use track |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LYR0106 | 체육도장업 | 202607 | 617 | 285.00 | 148,858.00 | 150.00 | 29.01 | N | precision_spatial_structure |
| LYR0107 | 체력단련장업 | 202607 | 475 | 399.00 | 404,561.00 | 0.00 | 25.07 | N | precision_spatial_structure |
| LYR0099 | 골프연습장업 | 202607 | 404 | 31.00 | 420,347.00 | 0.00 | 22.42 | N | precision_spatial_structure |
| LYR0101 | 당구장업 | 202607 | 715 | 0.00 | 285,924.00 | 10.00 | 21.54 | N | precision_spatial_structure |
| LYR0103 | 수영장업 | 202607 | 42 | 37.00 | 17,387.00 | 0.00 | 17.16 | N | precision_spatial_structure |
| LYR0105 | 썰매장업 | 202607 | 15 | 0.00 | 117,135.00 | 0.00 | 14.44 | N | precision_spatial_structure |
| LYR0100 | 골프장 | 202607 | 6 | 0.00 | 28,490.00 | 0.00 | 12.20 | N | precision_spatial_structure |
| LYR0104 | 승마장업 | 202607 | 1 | 2.00 | 4,446.00 | 0.00 | 10.19 | N | precision_spatial_structure |
| LYR0102 | 빙상장업 | 202607 | 9 | 5.00 | 0.00 | 0.00 | 4.09 | N | precision_spatial_structure |
| LYR0084 | 영화상영관 |  | 0 | 0.00 | 0.00 | 0.00 | 0.00 | N | precision_spatial_structure |

## GVA 잔여오차와 시설강도 비교

| parent code | middle code | middle label | actual gva 억원 | phase133 error 억원 | phase133 error rate % | row count | member capacity | building area ㎡ | facility gva scale 억원 per row | error 억원 per row | diagnosis |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ERS | 91 | 스포츠·오락 서비스업 | 4,365.64 | 731.16 | 16.75 | 2,284 | 160.00 | 1,427,148.00 | 1.91 | 0.32 | 현재 snapshot 구조축: 2023 속보에는 부적격 |
| J00 | 59 | 영상·오디오 제작업 | 1,467.02 | 219.93 | 14.99 | 0 | 0.00 | 0.00 |  |  | 현재 snapshot 구조축: 2023 속보에는 부적격 |

## 포털 레이어와 고용보험 세부업종 결합 가능성

| parent code | middle code | middle label | portal layer rows | portal member capacity | portal building area ㎡ | comwel active rows | comwel active workers | actual gva 억원 | remaining error 억원 | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ERS | 91 | 스포츠·오락 서비스업 | 2,284 | 160.00 | 1,427,148.00 | 672 | 2,034.00 | 4,365.64 | 731.16 | 시설 강도+고용보험을 함께 써야 함 |
| J00 | 59 | 영상·오디오 제작업 | 0 | 0.00 | 0.00 | 752 | 2,522.00 | 1,467.02 | 219.93 | 관객·매출 외부 API 필요 |

## 판정

1. ERS91 스포츠·오락은 고양시 포털 레이어에서 2,284개 시설 행, 759명 지도자수, 1,427,148㎡ 건축물연면적, 160명 회원모집총인원을 확인했다. 따라서 정밀화·행정동 공간배분 구조축으로는 기존 단순 시설 수보다 낫다.
2. 하지만 기준년월이 202607이므로 2023년 Q+1개월 strict flash에는 사용할 수 없다. Phase132 기준상 과거 as-of archive나 변동분 공표달력이 없으면 속보 성능으로 주장하면 안 된다.
3. J59 영상·오디오 쪽 영화상영관 레이어는 0행으로 내려와, 이 경로만으로는 금액격차 220억원을 설명하기 어렵다. KOBIS 지역 관객·매출 또는 고양시 영상산업 기업/제작지원 자료가 필요하다.
4. 다음 모델 개선은 `ERS91 공간배분/정밀화 구조축`에는 포털 레이어를 붙이고, `연·분기·월 GVA 금액 예측`에는 KOPIS/KOBIS 관객·매출 API를 붙이는 2트랙으로 가야 한다.
