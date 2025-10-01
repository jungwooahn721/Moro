import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from RAG import embed_event

def delete_event(event_id: int, file_path: str) -> bool:
    """
    Delete an event by ID from the specified JSON file.
    
    Args:
        event_id (int): The ID of the event to delete
        file_path (str): The path to the JSON file
        
    Returns:
        bool: True if event was found and deleted, False otherwise
    """
    if not os.path.exists(file_path):
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        events = json.load(f)
    
    # Find and remove the event with the specified ID
    original_count = len(events)
    events = [event for event in events if event.get('id') != event_id]
    
    if len(events) < original_count:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        return True
    return False

def add_event(event_data: Dict[str, Any], file_path: str) -> int:
    """
    Add a new event to the specified JSON file.
    
    Args:
        event_data (Dict[str, Any]): The event data to add
        file_path (str): The path to the JSON file
        
    Returns:
        int: The ID of the newly created event
    """
    # Load existing events or create empty list
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            events = json.load(f)
    else:
        events = []
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Generate new ID
    if not events:
        new_id = 1
    else:
        new_id = max(event.get('id', 0) for event in events) + 1
    
    # Create new event with the generated ID
    new_event = event_data.copy()
    new_event['id'] = new_id
    new_event = embed_event(new_event)
    # Add the new event to the list
    events.append(new_event)
    
    # Save the updated events
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    
    return new_id


# =============== 개별 파일(각 ID별 1파일) 유틸 ===============
def _parse_id_from_filename(filename: str) -> int | None:
    """파일명이 12.json, 0016.json 같은 형태일 때 숫자 ID를 추출.
    일치하지 않으면 None 반환.
    """
    m = re.fullmatch(r"0*(\d+)\.json", filename)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def list_existing_ids(user_dir: str) -> Set[int]:
    """`Database/[user]` 폴더 내 개별 이벤트 파일명에서 존재하는 정수 ID 집합 반환."""
    base = Path(user_dir)
    if not base.exists():
        return set()
    ids: Set[int] = set()
    for p in base.glob("*.json"):
        event_id = _parse_id_from_filename(p.name)
        if event_id is not None:
            ids.add(event_id)
    return ids


def find_missing_ids(user_dir: str, start_id: int | None = None, end_id: int | None = None) -> List[int]:
    """
    폴더 내 존재하는 ID들을 기준으로 빠진 ID 리스트를 반환.
    - start_id/end_id 미지정 시, 1부터 현재 존재하는 최대 ID까지 범위를 사용.
    """
    existing = list_existing_ids(user_dir)
    if not existing:
        return []

    min_id = min(existing) if start_id is None else start_id
    max_id = max(existing) if end_id is None else end_id
    if max_id < min_id:
        return []
    return [i for i in range(min_id, max_id + 1) if i not in existing]


def _format_id_filename(event_id: int, pad: int = 4) -> str:
    """ID를 파일명으로 변환 (기본 4자리 zero-pad)."""
    return f"{event_id:0{pad}d}.json"


def _make_placeholder_event(event_id: int) -> Dict[str, Any]:
    """필수 스키마를 만족하는 기본 이벤트 플레이스홀더를 생성."""
    return {
        "id": event_id,
        "date_start": "",
        "date_finish": "",
        "title": "",
        "description": "",
        "location": "",
        "member": [],
    }


def add_missing_event_files(user_dir: str = "Database/[user]", zero_pad: int = 4) -> List[Tuple[int, str]]:
    """
    `user_dir`에서 누락된 정수 ID를 찾아 개별 이벤트 파일을 생성.
    - 파일명은 zero-pad된 `<id>.json` 형식으로 저장 (기본 4자리)
    - 생성된 파일들의 (id, 경로) 리스트를 반환
    - 원본 파일은 건드리지 않음
    """
    base = Path(user_dir)
    base.mkdir(parents=True, exist_ok=True)

    missing = find_missing_ids(user_dir)
    created: List[Tuple[int, str]] = []
    for event_id in missing:
        event = _make_placeholder_event(event_id)
        # 필요 시 임베딩 필드 생성
        try:
            event = embed_event(event)
        except Exception:
            # 임베딩 실패해도 파일은 생성
            pass
        out_path = base / _format_id_filename(event_id, pad=zero_pad)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(event, f, ensure_ascii=False, indent=2)
        created.append((event_id, str(out_path)))



def update_event(event_id: int, updates: Dict[str, Any], file_path: str, recompute_embedding: bool = True) -> bool:
    """
    월별 JSON 배열 파일(file_path)에서 id가 event_id인 이벤트의 필드를 수정합니다.
    - updates에 있는 키만 갱신합니다.
    - recompute_embedding=True이면 수정 후 임베딩을 재계산합니다.
    반환: 수정 성공 시 True, 대상이 없으면 False.
    """
    if not os.path.exists(file_path):
        return False
    with open(file_path, 'r', encoding='utf-8') as f:
        events = json.load(f)

    found = False
    for idx, ev in enumerate(events):
        if ev.get('id') == event_id:
            # 필드 업데이트
            for k, v in updates.items():
                ev[k] = v
            if recompute_embedding:
                try:
                    ev = embed_event(ev)
                except Exception:
                    pass
            events[idx] = ev
            found = True
            break

    if not found:
        return False

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    return True


def update_event_file(user_dir: str, event_id: int, updates: Dict[str, Any], zero_pad: int = 4, recompute_embedding: bool = True) -> bool:
    """
    개별 이벤트 파일(Database/[user]/<id>.json 또는 zero-pad 파일)을 찾아 수정합니다.
    - updates 반영 후 필요 시 임베딩 재계산.
    반환: 수정 성공 시 True, 파일이 없으면 False.
    """
    base = Path(user_dir)
    padded = base / f"{event_id:0{zero_pad}d}.json"
    plain = base / f"{event_id}.json"
    target = padded if padded.exists() else plain
    if not target.exists():
        return False

    with target.open('r', encoding='utf-8') as f:
        event = json.load(f)

    for k, v in updates.items():
        event[k] = v

    if recompute_embedding:
        try:
            event = embed_event(event)
        except Exception:
            pass

    with target.open('w', encoding='utf-8') as f:
        json.dump(event, f, ensure_ascii=False, indent=2)
    return True


# =============== [user] 폴더용 단일 파일 기반 편의 함수 3종 ===============
def delete_event_in_user(event_id: int, user_dir: str = "Database/[user]", zero_pad: int = 4) -> bool:
    """
    Database/[user] 폴더에서 해당 ID의 이벤트 파일을 삭제합니다.
    - zero-pad 파일(예: 0016.json) 우선, 없으면 16.json 시도
    반환: 삭제 성공 시 True
    """
    base = Path(user_dir)
    padded = base / f"{event_id:0{zero_pad}d}.json"
    plain = base / f"{event_id}.json"
    target = padded if padded.exists() else plain
    if not target.exists():
        return False
    try:
        target.unlink()
        return True
    except Exception:
        return False


def update_event_in_user(event_id: int, updates: Dict[str, Any], user_dir: str = "Database/[user]", zero_pad: int = 4, recompute_embedding: bool = True) -> bool:
    """
    Database/[user] 폴더의 개별 이벤트 파일을 수정합니다.
    내부적으로 update_event_file을 호출합니다.
    """
    return update_event_file(user_dir, event_id, updates, zero_pad=zero_pad, recompute_embedding=recompute_embedding)


def _smallest_missing_positive(ids: Set[int]) -> int:
    """존재하는 정수 집합에서 가장 작은 누락된 양의 정수를 찾습니다 (1부터 시작)."""
    if not ids:
        return 1
    candidate = 1
    while candidate in ids:
        candidate += 1
    return candidate


def add_event_in_user(event_data: Dict[str, Any], recompute_embedding: bool = True, user_dir: str = "Database/[user]", zero_pad: int = 4) -> int:
    """
    Database/[user] 폴더에 "없는 아이디"로 자동 배정하여 단일 파일을 생성합니다.
    - 가장 작은 누락된 양의 정수 ID를 선택
    - 파일명은 zero-pad된 <id>.json
    - 생성된 ID를 반환
    """
    base = Path(user_dir)
    base.mkdir(parents=True, exist_ok=True)

    existing_ids = list_existing_ids(user_dir)
    new_id = _smallest_missing_positive(existing_ids)

    new_event = event_data.copy()
    new_event['id'] = new_id

    if recompute_embedding:
        try:
            new_event = embed_event(new_event)
        except Exception:
            pass

    out_path = base / f"{new_id:0{zero_pad}d}.json"
    with out_path.open('w', encoding='utf-8') as f:
        json.dump(new_event, f, ensure_ascii=False, indent=2)

    return new_id


