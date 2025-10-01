#!/usr/bin/env python3
"""
테스트 스니펫: parsing_with_criteria.py 사용 예시
"""

import json
from datetime import datetime, timezone, timedelta
from RAG.parsing_with_criteria import parse_with_criteria, filter_out_by_criteria
from RAG.parsing_with_content import embed_events, parse_with_content

# 타임존 설정
KST = timezone(timedelta(hours=9))

def load_test_data():
    """테스트용 데이터 로드"""
    import os
    import glob
    
    events = []
    data_dir = 'Database/[user]'
    
    # Database/[user] 폴더의 모든 JSON 파일 찾기
    try:
        # 직접 폴더 내용 확인
        if os.path.exists(data_dir):
            all_files = os.listdir(data_dir)
            json_files = [os.path.join(data_dir, f) for f in all_files if f.endswith('.json') and not f.startswith('event_')]
        else:
            json_files = []
    except Exception as e:
        print(f"폴더 접근 오류: {e}")
        json_files = []
    
    if not json_files:
        print(f"{data_dir} 폴더에 JSON 파일이 없습니다. 폴더 존재 여부: {os.path.exists(data_dir)}")
        if os.path.exists(data_dir):
            print(f"폴더 내용: {os.listdir(data_dir)}")
        return events
    
    # 모든 JSON 파일을 반복문으로 로드
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                file_events = json.load(f)
                events.extend(file_events)
                print(f"로드됨: {json_file} ({len(file_events)}개 이벤트)")
        except FileNotFoundError:
            print(f"파일을 찾을 수 없습니다: {json_file}")
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류 {json_file}: {e}")
        except Exception as e:
            print(f"오류 발생 {json_file}: {e}")
    
    print(f"총 {len(events)}개 이벤트 로드 완료")
    return events

def test_basic_filtering():
    """기본 필터링 테스트"""
    print("=== 기본 필터링 테스트 ===")
    events = load_test_data()
    
    if not events:
        print("테스트 데이터가 없습니다.")
        return
    
    print(f"전체 이벤트 수: {len(events)}")
    
    # 특정 날짜 필터링 (2025-09-30 포함)
    filtered = parse_with_criteria(events, {"date": "2025-09-30"})
    print(f"2025-09-30 이벤트 수: {len(filtered)}")
    
    # 금요일 필터링 (금요일 포함)
    filtered = parse_with_criteria(events, {"weekday": 4})  # 4 = 금요일
    print(f"금요일 이벤트 수: {len(filtered)}")
    
    # 특정 시간 필터링 (21:00 포함)
    filtered = parse_with_criteria(events, {"hour": "21:00"})
    print(f"21:00 이벤트 수: {len(filtered)}")

def test_advanced_filtering():
    """고급 필터링 테스트"""
    print("\n=== 고급 필터링 테스트 ===")
    events = load_test_data()
    
    if not events:
        print("테스트 데이터가 없습니다.")
        return
    
    # 복합 조건: 2025년 10월의 금요일 21시 이벤트 포함
    filtered = parse_with_criteria(events, {
        "date": "2025-10-31",  # 10월 31일
        "weekday": 4,          # 금요일
        "hour": "21:00"        # 21시
    })
    print(f"복합 조건에 맞는 이벤트 수: {len(filtered)}")

def test_time_window_filtering():
    """타임 윈도우 필터링 테스트"""
    print("\n=== 타임 윈도우 필터링 테스트 ===")
    events = load_test_data()
    
    if not events:
        print("테스트 데이터가 없습니다.")
        return
    
    # 특정 기준 시간에서 ±12시간 범위의 이벤트 포함
    reference_time = datetime(2025, 10, 15, 12, 0, tzinfo=KST)
    filtered = parse_with_criteria(events, {
        "time_window_hours": 12,
        "reference_time": reference_time
    })
    print(f"기준 시간({reference_time})에서 ±12시간 범위 이벤트 수: {len(filtered)}")
    
    # 가장 가까운 5개 포함
    filtered = parse_with_criteria(events, {
        "nearest_n": 5,
        "reference_time": reference_time,
        "sort_by": "nearest"
    })
    print(f"기준 시간에서 가장 가까운 5개 이벤트 수: {len(filtered)}")
    
    # 결과 출력 (처음 3개만)
    print("선택된 이벤트들 (처음 3개):")
    for i, event in enumerate(filtered[:3]):
        start_dt = datetime.fromisoformat(event['date_start'])
        time_diff = abs((start_dt - reference_time).total_seconds()) / 3600
        print(f"  {i+1}. {event['title']} - {event['date_start']} (거리: {time_diff:.1f}시간)")

def test_sorting():
    """정렬 테스트"""
    print("\n=== 정렬 테스트 ===")
    events = load_test_data()
    
    if not events:
        print("테스트 데이터가 없습니다.")
        return
    
    # 시작 시간순 정렬
    filtered = parse_with_criteria(events, {"date": "2025-09-01"}, sort_by="start")
    print("2025-09-01이 아닌 이벤트들 (시작 시간순):")
    for i, event in enumerate(filtered[:3]):
        print(f"  {i+1}. {event['title']} - {event['date_start']}")


def test_content_search_basic():
    """콘텐츠 임베딩 검색 - 기본 쿼리"""
    print("\n=== 콘텐츠 검색: 기본 ===")
    events = load_test_data()
    if not events:
        print("테스트 데이터가 없습니다.")
        return
    
    # Embed events to individual files
    print("이벤트들을 개별 벡터DB로 저장 중...")
    embed_events(events)
    
    # Search with no criteria
    print("검색 중...")
    results = parse_with_content("디자인", k=5)
    print(f"\"디자인\" 매칭 결과: {len(results)}건")
    for i, ev in enumerate(results[:3]):
        print(f"  {i+1}. {ev.get('title')} | {ev.get('location')}")


def test_content_search_with_criteria():
    """콘텐츠 임베딩 검색 - criteria 적용"""
    print("\n=== 콘텐츠 검색: criteria 적용 ===")
    events = load_test_data()
    if not events:
        print("테스트 데이터가 없습니다.")
        return
    
    # Search with criteria filter
    criteria = {
        "time_window_hours": 128,
        "reference_time": datetime(2025, 10, 15, 12, 0, tzinfo=KST)
    }
    
    print("조건에 맞는 이벤트들을 검색 중...")
    results = parse_with_content("회의", criteria=criteria, k=5)
    print(f"criteria+\"회의\" 결과: {len(results)}건")
    for i, ev in enumerate(results[:3]):
        print(f"  {i+1}. {ev.get('title')} | {ev.get('date_start')}")

def main():
    """메인 테스트 함수"""
    print("parsing_with_criteria.py 테스트 시작\n")
    
    try:
        test_basic_filtering()
        test_advanced_filtering()
        test_time_window_filtering()
        test_sorting()
        test_content_search_basic()
        test_content_search_with_criteria()
        
        print("\n=== 모든 테스트 완료 ===")
        
    except Exception as e:
        print(f"테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
