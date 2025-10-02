from RAG.parsing_with_criteria import parse_with_criteria
from datetime import datetime

print('=== 10월 일요일 일정 검색 테스트 ===')

# 먼저 10월 모든 일정 확인
print('1. 10월 모든 일정:')
all_october = parse_with_criteria(criteria={'month': 10})
print(f'   총 {len(all_october)}개 일정')

for event in all_october:
    date_str = event.get('date_start', '')
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        weekday_names = ['월', '화', '수', '목', '금', '토', '일']
        print(f'   ID: {event.get("id")} | {dt.strftime("%Y-%m-%d %H:%M")} ({weekday_names[dt.weekday()]}요일) | {event.get("title")}')
    except Exception as e:
        print(f'   날짜 파싱 오류: {date_str} - {e}')

print('\n2. 10월 일요일 일정 (문자열):')
result = parse_with_criteria(criteria={'month': 10, 'weekday': '일'})
print(f'   검색 결과 개수: {len(result)}')

for event in result:
    print(f'   ID: {event.get("id")} | 제목: {event.get("title")} | 시작: {event.get("date_start")}')

print('\n3. 10월 일요일 일정 (숫자):')
result2 = parse_with_criteria(criteria={'month': 10, 'weekday': 6})
print(f'   검색 결과 개수: {len(result2)}')

for event in result2:
    print(f'   ID: {event.get("id")} | 제목: {event.get("title")} | 시작: {event.get("date_start")}')
