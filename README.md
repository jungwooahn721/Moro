## 데이터 포맷
- 경로: `Database/[user]/YYYY-MM.json`
- 각 이벤트 필드:
  - `id`: 정수
  - `date_start` / `date_finish`: ISO 8601(+09:00)
  - `title`, `description`, `location`, `member`

## 주요 모듈
- `RAG/parsing_with_criteria.py`: 날짜/요일/시간/타임 윈도우 기준으로 “조건에 맞는 이벤트”를 반환
- `RAG/parsing_with_content.py`:
  - 이벤트 텍스트 합성(`title+description+location+member`) → 임베딩 계산 → JSON 저장
  - 저장된 JSON에서 기준(criteria)로 선별한 뒤, 그 집합으로 Chroma 인덱스를 생성하여 유사도 검색

## RAG 클래스(API)
`RAG/__init__.py`
- `parse_with_criteria(events, criteria)`
  - 기준에 “맞는” 이벤트 리스트 반환
- `parse_with_content(query, criteria=None, k=10, vector_dir="RAG/VectorDB/[user]")`
  - `embed_events`로 저장된 임베딩 JSON을 불러와 criteria로 선별 후 인덱싱/검색
  - 검색 결과는 전체 이벤트(JSON) 리스트로 반환
- `embed_events(events, vector_dir="RAG/VectorDB/[user]")`
  - 각 이벤트를 임베딩하여 `{event, text, embedding}` 형태로 JSON 파일(`event_{id}.json`) 저장

### 기준(criteria)
- `date` (str): 특정 날짜의 이벤트만 포함합니다. 형식 `YYYY-MM-DD`.
  - 예: `{ "date": "2025-10-31" }`
- `weekday` (int|str): 요일 기준 필터. 정수 0~6은 월~일, 한글 '월'~'일' 지원.
  - 예: `{ "weekday": 4 }` 또는 `{ "weekday": "금" }`
- `hour` (int|str): 시작 시각 기준. `HH` 또는 `HH:MM`.
  - 예: `{ "hour": "21:00" }`, `{ "hour": 9 }`
- `time_window_hours` (float|int): 기준 시간(`reference_time`) ±N시간 범위 이벤트만 포함.
  - 예: `{ "time_window_hours": 48, "reference_time": dt }`
- `reference_time` (datetime): `time_window_hours`/`nearest_n` 기준 시각(KST 권장).
- `nearest_n` (int): 기준 시각에 가장 가까운 N개만 포함.
- `sort_by` (str): 반환 정렬. `nearest`(기준 시각 거리순), `start`(시작 시각 오름차순).


## 사용 예시
```python
from RAG.parsing_with_content import embed_events, parse_with_content
from RAG.parsing_with_criteria import parse_with_criteria

# 1) 임베딩 저장
embed_events(events, vector_dir="RAG/VectorDB/[user]")

# 2) 기준 필터 (조건에 맞는 이벤트 반환)
matched = parse_with_criteria(events, {"time_window_hours": 48, "reference_time": some_kst_dt})

# 3) 콘텐츠 유사도 검색 (선별+인덱싱+검색)
results = parse_with_content("회의", criteria={"weekday": 4}, k=5, vector_dir="RAG/VectorDB/[user]")
```

