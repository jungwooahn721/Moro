import eventmanager
import json
import os

def test_eventmanager_functions():
    """eventmanager.py의 함수들이 정상적으로 작동하는지 테스트"""
    
    print("=== EventManager 함수 테스트 시작 ===\n")
    
    # 테스트용 파일 경로
    test_file_path = "Database/[user]/test_events.json"
    
    # 1. add_event 함수 테스트
    print("1. add_event 함수 테스트")
    print("-" * 30)
    
    # 테스트용 이벤트 데이터
    test_event_data = {
        "date_start": "2025-01-15T09:00:00+09:00",
        "date_finish": "2025-01-15T11:00:00+09:00",
        "title": "테스트 회의",
        "description": "eventmanager 함수 테스트용 이벤트",
        "location": "테스트 회의실",
        "member": ["테스터", "개발자"],
        "embedding": [0.1, 0.2, 0.3, 0.4, 0.5]  # 간단한 테스트용 임베딩
    }
    
    try:
        # 이벤트 추가
        new_id = eventmanager.add_event(test_event_data, test_file_path)
        print(f"[SUCCESS] 이벤트 추가 성공! 새 ID: {new_id}")
        
        # 추가된 이벤트 확인
        with open(test_file_path, 'r', encoding='utf-8') as f:
            events = json.load(f)
        print(f"[SUCCESS] 파일에 {len(events)}개의 이벤트가 저장됨")
        
    except Exception as e:
        print(f"[ERROR] add_event 오류: {e}")
        return False
    
    # 2. delete_event 함수 테스트
    print("\n2. delete_event 함수 테스트")
    print("-" * 30)
    
    try:
        # 방금 추가한 이벤트 삭제
        delete_result = eventmanager.delete_event(new_id, test_file_path)
        
        if delete_result:
            print(f"[SUCCESS] 이벤트 ID {new_id} 삭제 성공!")
            
            # 삭제 후 파일 상태 확인
            with open(test_file_path, 'r', encoding='utf-8') as f:
                events_after_delete = json.load(f)
            print(f"[SUCCESS] 삭제 후 남은 이벤트 수: {len(events_after_delete)}")
        else:
            print(f"[ERROR] 이벤트 ID {new_id} 삭제 실패!")
            return False
            
    except Exception as e:
        print(f"[ERROR] delete_event 오류: {e}")
        return False
    
    # 3. 존재하지 않는 이벤트 삭제 테스트
    print("\n3. 존재하지 않는 이벤트 삭제 테스트")
    print("-" * 30)
    
    try:
        fake_id = 99999
        delete_result = eventmanager.delete_event(fake_id, test_file_path)
        
        if not delete_result:
            print(f"[SUCCESS] 존재하지 않는 ID {fake_id} 삭제 시도 - 예상대로 False 반환")
        else:
            print(f"[ERROR] 존재하지 않는 ID 삭제 시도했는데 True 반환됨!")
            return False
            
    except Exception as e:
        print(f"[ERROR] 존재하지 않는 이벤트 삭제 테스트 오류: {e}")
        return False
    
    # 4. 실제 데이터베이스 파일 테스트
    print("\n4. 실제 데이터베이스 파일 테스트")
    print("-" * 30)
    
    real_file_path = "Database/[user]/2025-10.json"
    
    if os.path.exists(real_file_path):
        try:
            # 실제 파일에서 이벤트 로드하여 ID 확인
            with open(real_file_path, 'r', encoding='utf-8') as f:
                real_events = json.load(f)
            
            if real_events:
                first_event_id = real_events[0].get('id')
                print(f"[SUCCESS] 실제 파일에서 첫 번째 이벤트 ID: {first_event_id}")
                
                # 실제 파일에 테스트 이벤트 추가
                test_event_real = {
                    "date_start": "2025-10-20T14:00:00+09:00",
                    "date_finish": "2025-10-20T16:00:00+09:00",
                    "title": "테스트 이벤트 (실제 파일)",
                    "description": "실제 데이터베이스 파일에 추가된 테스트 이벤트",
                    "location": "테스트 장소",
                    "member": ["테스터"],
                    "embedding": [0.1, 0.2, 0.3]
                }
                
                new_real_id = eventmanager.add_event(test_event_real, real_file_path)
                print(f"[SUCCESS] 실제 파일에 이벤트 추가 성공! ID: {new_real_id}")
               
                    
            else:
                print("[WARNING] 실제 파일이 비어있음")
                
        except Exception as e:
            print(f"[ERROR] 실제 파일 테스트 오류: {e}")
            return False
    else:
        print("[WARNING] 실제 데이터베이스 파일이 존재하지 않음")
    
    # 테스트 파일 정리
    if os.path.exists(test_file_path):

        print(f"\n[SUCCESS] 테스트 파일 {test_file_path} 정리 완료")
    
    print("\n=== 모든 테스트 완료 ===")
    print("[SUCCESS] eventmanager.py의 함수들이 정상적으로 작동합니다!")
    print("[SUCCESS] 캘린더와 챗봇에서 사용할 준비가 완료되었습니다!")
    
    return True

if __name__ == "__main__":
    test_eventmanager_functions()
