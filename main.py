from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import os
import sqlite3
import uuid
from datetime import datetime
import shutil

# Unix Timestamp 변환 유틸리티 함수들
def datetime_to_unix_timestamp(dt: datetime) -> int:
    """datetime 객체를 Unix Timestamp로 변환 (Asia/Seoul 타임존 고려)"""
    import pytz
    
    # Asia/Seoul 타임존 설정
    seoul_tz = pytz.timezone('Asia/Seoul')
    
    # naive datetime이면 Asia/Seoul로 localize
    if dt.tzinfo is None:
        dt = seoul_tz.localize(dt)
    # 다른 타임존이면 Asia/Seoul로 변환
    elif dt.tzinfo != seoul_tz:
        dt = dt.astimezone(seoul_tz)
    
    return int(dt.timestamp())

def unix_timestamp_to_datetime(timestamp: int) -> datetime:
    """Unix Timestamp를 datetime 객체로 변환 (Asia/Seoul 타임존)"""
    import pytz
    
    # UTC에서 Asia/Seoul로 변환
    utc_dt = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
    seoul_tz = pytz.timezone('Asia/Seoul')
    return utc_dt.astimezone(seoul_tz)

def parse_date_with_year_fallback(date_str: str, time_str: str = None) -> datetime:
    """날짜 문자열을 파싱하고 연도가 없으면 현재 연도 적용"""
    from datetime import datetime
    import re
    
    current_year = datetime.now().year
    
    # 연도가 포함된 경우
    if re.search(r'\d{4}년', date_str) or re.search(r'\d{4}-\d{2}-\d{2}', date_str):
        # 이미 연도가 있는 경우 그대로 파싱
        if '년' in date_str:
            # "2025년 10월 1일" 형식
            year_match = re.search(r'(\d{4})년', date_str)
            month_match = re.search(r'(\d{1,2})월', date_str)
            day_match = re.search(r'(\d{1,2})일', date_str)
            
            if year_match and month_match and day_match:
                year = int(year_match.group(1))
                month = int(month_match.group(1))
                day = int(day_match.group(1))
                
                if time_str:
                    time_parts = time_str.split(':')
                    hour = int(time_parts[0])
                    minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                    return datetime(year, month, day, hour, minute)
                else:
                    return datetime(year, month, day)
    else:
        # 연도가 없는 경우 현재 연도 적용
        if '월' in date_str and '일' in date_str:
            month_match = re.search(r'(\d{1,2})월', date_str)
            day_match = re.search(r'(\d{1,2})일', date_str)
            
            if month_match and day_match:
                month = int(month_match.group(1))
                day = int(day_match.group(1))
                
                if time_str:
                    time_parts = time_str.split(':')
                    hour = int(time_parts[0])
                    minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                    return datetime(current_year, month, day, hour, minute)
                else:
                    return datetime(current_year, month, day)
    
    # 파싱 실패 시 현재 시간 반환
    return datetime.now()

def format_unix_timestamp_for_display(timestamp: int) -> str:
    """Unix Timestamp를 사람이 읽기 좋은 형식으로 변환"""
    dt = unix_timestamp_to_datetime(timestamp)
    return dt.strftime('%Y-%m-%d %H:%M')

# GPT 멀티모달 이미지 분석 기능
def analyze_image_with_gpt(image_data: bytes) -> dict:
    """GPT-4o-mini를 사용하여 이미지에서 일정 정보 추출"""
    if client is None:
        return {"error": "OpenAI API 키가 설정되지 않았습니다."}
    
    try:
        import base64
        
        # 이미지를 base64로 인코딩
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # GPT-4o-mini에 이미지와 프롬프트 전송
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """이미지를 분석하여 일정 정보를 JSON 형식으로 추출해주세요.
다음 JSON 스키마를 정확히 따라주세요:

{
  "title": "일정 제목",
  "start": {"iso": "YYYY-MM-DDTHH:MM:SS", "tz": "Asia/Seoul"},
  "end": {"iso": "YYYY-MM-DDTHH:MM:SS", "tz": "Asia/Seoul"},
  "location": "장소 (없으면 null)",
  "attendees": ["참석자1", "참석자2"],
  "notes": "추가 메모 (없으면 null)"
}

규칙:
1. 시간이 명시되지 않으면 현재 시간 기준으로 추정
2. 종료 시간이 없으면 시작 시간 + 1시간으로 설정
3. 날짜가 없으면 오늘 날짜 사용
4. 연도가 없는 경우 현재 연도(2025)를 자동으로 적용
5. JSON만 반환하고 다른 텍스트는 포함하지 마세요
6. 한국어로 된 일정 정보를 정확히 파싱해주세요
7. 날짜 형식: "10월 1일 오후 6시" → "2025-10-01T18:00:00"로 변환"""
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "이 이미지에서 일정 정보를 추출해주세요."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        
        # JSON 파싱
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        return {"error": f"GPT 이미지 분석 실패: {str(e)}"}

from openai import OpenAI
from googleapiclient.discovery import build
# from google.oauth2.credentials import Credentials   # 실제 OAuth2 토큰 관리 필요

# ---- 기존 RAG 코드 연결 (Moro-backend 기준) ----
try:
    from RAG.parsing_with_content import parse_with_content
    from RAG.parsing_with_criteria import parse_with_criteria
except ImportError:
    # RAG 코드 없는 경우 대비 (테스트용)
    def parse_with_content(query, *args, **kwargs):
        return [{"title": "Mock meeting", "members": ["정우", "운영팀"]}]
    def parse_with_criteria(events, criteria=None, *args, **kwargs):
        return events

app = FastAPI()

# 정적 파일과 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# OpenAI 클라이언트 초기화 (API 키 확인)
try:
    # 환경변수에서 API 키 가져오기
    api_key = os.getenv("OPENAI_API_KEY")
    
    # 환경변수가 없으면 오류 메시지 출력
    if not api_key:
        print("❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   환경변수를 설정하거나 .env 파일을 생성해주세요.")
    
    if api_key:
        client = OpenAI(api_key=api_key)
        print("✅ OpenAI 클라이언트가 성공적으로 초기화되었습니다.")
    else:
        print("❌ OPENAI_API_KEY가 설정되지 않았습니다.")
        client = None
except Exception as e:
    print(f"❌ OpenAI 클라이언트 초기화 실패: {e}")
    client = None

# -------------------------
# JSON Schema 정의
# -------------------------
class EventTime(BaseModel):
    iso: str
    tz: str

class Reminder(BaseModel):
    minutes: int

class Recurrence(BaseModel):
    rrule: str

class Event(BaseModel):
    title: Optional[str] = ""
    start: Optional[EventTime] = None
    end: Optional[EventTime] = None
    # Unix timestamp 필드 추가
    start_timestamp: Optional[int] = None
    end_timestamp: Optional[int] = None
    all_day: bool = False
    location: Optional[str] = ""
    attendees: Optional[List[str]] = []
    recurrence: Optional[Recurrence] = None
    reminders: Optional[List[Reminder]] = []
    notes: Optional[str] = ""
    confidence: float = 0.0
    needs_confirmation: bool = False

class EventRequest(BaseModel):
    intent: str
    event: Event

# -------------------------
# 이벤트 생성/수정을 위한 Pydantic 모델
# -------------------------
class CreateEventRequest(BaseModel):
    title: str
    start_iso: str
    end_iso: str
    start_tz: str = "Asia/Seoul"
    end_tz: str = "Asia/Seoul"
    all_day: bool = False
    location: Optional[str] = None
    attendees: Optional[List[str]] = []
    notes: Optional[str] = None

class UpdateEventRequest(BaseModel):
    title: Optional[str] = None
    start_iso: Optional[str] = None
    end_iso: Optional[str] = None
    start_tz: Optional[str] = None
    end_tz: Optional[str] = None
    all_day: Optional[bool] = None
    location: Optional[str] = None
    attendees: Optional[List[str]] = None
    notes: Optional[str] = None

# -------------------------
# SQLite 데이터베이스 초기화
# -------------------------
def init_database():
    """SQLite 데이터베이스 초기화 및 마이그레이션"""
    import os
    
    conn = sqlite3.connect('events.db')
    cursor = conn.cursor()
    
    # 기존 테이블 구조 확인
    cursor.execute("PRAGMA table_info(events)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # start_timestamp, end_timestamp 컬럼이 없으면 마이그레이션 필요
    if 'start_timestamp' not in columns or 'end_timestamp' not in columns:
        print("🔄 데이터베이스 스키마를 Unix Timestamp 기반으로 마이그레이션합니다...")
        
        # 기존 데이터 백업 (있다면)
        try:
            cursor.execute("SELECT * FROM events")
            old_data = cursor.fetchall()
            print(f"📦 기존 데이터 {len(old_data)}개를 백업합니다...")
        except:
            old_data = []
        
        # 기존 테이블 삭제
        cursor.execute("DROP TABLE IF EXISTS events")
        
        # 새 테이블 생성 (Unix Timestamp 기반)
        cursor.execute('''
            CREATE TABLE events (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                start_timestamp INTEGER NOT NULL,  -- Unix Timestamp
                end_timestamp INTEGER NOT NULL,    -- Unix Timestamp
                all_day BOOLEAN DEFAULT FALSE,
                location TEXT,
                attendees TEXT,  -- JSON 문자열로 저장
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 기존 데이터가 있으면 마이그레이션 (간단한 변환)
        if old_data:
            print("🔄 기존 데이터를 새 형식으로 변환합니다...")
            for row in old_data:
                try:
                    # 기존 데이터 구조에 따라 변환 (간단한 예시)
                    event_id = row[0] if len(row) > 0 else str(uuid.uuid4())
                    title = row[1] if len(row) > 1 else "마이그레이션된 일정"
                    
                    # 현재 시간으로 기본값 설정
                    current_timestamp = int(datetime.now().timestamp())
                    
                    cursor.execute('''
                        INSERT INTO events (id, title, start_timestamp, end_timestamp, 
                                          all_day, location, attendees, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        event_id,
                        title,
                        current_timestamp,
                        current_timestamp + 3600,  # 1시간 후
                        False,
                        row[6] if len(row) > 6 else None,  # location
                        row[7] if len(row) > 7 else '[]',   # attendees
                        row[8] if len(row) > 8 else None   # notes
                    ))
                except Exception as e:
                    print(f"⚠️ 데이터 마이그레이션 중 오류: {e}")
                    continue
        
        print("✅ 데이터베이스 마이그레이션이 완료되었습니다.")
    else:
        print("✅ 데이터베이스 스키마가 이미 최신 상태입니다.")
    
    conn.commit()
    conn.close()

# 데이터베이스 초기화
init_database()

# -------------------------
# 데이터베이스 CRUD 함수들
# -------------------------
def formatUnixTimestamp(timestamp: int) -> str:
    """Unix timestamp를 한국어 형식으로 변환"""
    try:
        import pytz
        seoul_tz = pytz.timezone('Asia/Seoul')
        dt = datetime.fromtimestamp(timestamp, tz=seoul_tz)
        return dt.strftime('%Y년 %m월 %d일 %p %I:%M')
    except:
        return "시간 정보 없음"

def simple_keyword_parsing(user_input: str) -> dict:
    """간단한 키워드 기반 파싱 (API 키 없이 작동)"""
    import re
    from datetime import datetime, timedelta
    import pytz
    
    print(f"🔍 키워드 파싱 시작: '{user_input}'")
    
    seoul_tz = pytz.timezone('Asia/Seoul')
    now = datetime.now(seoul_tz)
    
    # 시간 키워드 매핑
    time_keywords = {
        '내일': 1,
        '모레': 2,
        '다음주': 7,
        '이번주': 0
    }
    
    # 시간 패턴 매칭
    time_patterns = [
        (r'(\d+)시', lambda m: int(m.group(1))),
        (r'(\d+)시\s*(\d+)분', lambda m: int(m.group(1)) + int(m.group(2))/60),
        (r'오전\s*(\d+)시', lambda m: int(m.group(1))),
        (r'오후\s*(\d+)시', lambda m: int(m.group(1)) + 12 if int(m.group(1)) != 12 else 12),
        (r'(\d+)시\s*반', lambda m: int(m.group(1)) + 0.5),
    ]
    
    # 기본값 설정
    days_offset = 0
    hour = 14  # 기본 오후 2시
    minute = 0
    
    # 날짜 키워드 찾기
    for keyword, offset in time_keywords.items():
        if keyword in user_input:
            days_offset = offset
            print(f"📅 날짜 키워드 발견: '{keyword}' -> {offset}일 후")
            break
    
    # 시간 패턴 찾기
    for pattern, extractor in time_patterns:
        match = re.search(pattern, user_input)
        if match:
            hour = extractor(match)
            print(f"🕐 시간 패턴 발견: '{pattern}' -> {hour}시")
            break
    
    # 시간 계산
    target_date = now + timedelta(days=days_offset)
    target_datetime = target_date.replace(hour=int(hour), minute=int((hour % 1) * 60), second=0, microsecond=0)
    
    # 시간이 24시간을 초과하는 경우 처리
    if target_datetime.hour >= 24:
        target_datetime = target_datetime + timedelta(days=1)
        target_datetime = target_datetime.replace(hour=target_datetime.hour - 24)
    
    # Unix timestamp로 변환
    start_timestamp = int(target_datetime.timestamp())
    end_timestamp = start_timestamp + 3600  # 1시간 후
    
    print(f"⏰ 계산된 시간: {target_datetime.strftime('%Y-%m-%d %H:%M')} (timestamp: {start_timestamp})")
    
    # 제목 추출 (스마트한 방법)
    title = user_input
    
    # 시간 관련 키워드 제거
    time_keywords_to_remove = ['내일', '모레', '다음주', '이번주', '오전', '오후', '시', '분']
    for keyword in time_keywords_to_remove:
        title = title.replace(keyword, '')
    
    # 숫자+시 패턴 제거 (예: "12시" -> "")
    title = re.sub(r'\d+시\s*', '', title)
    title = re.sub(r'\d+시\s*\d+분', '', title)
    
    # 장소 키워드 추출 및 제목에서 제거
    location_keywords = ['신촌역', '회의실', '사무실', '카페', '식당', '학교', '집']
    extracted_location = ""
    for loc in location_keywords:
        if loc in title:
            extracted_location = loc
            title = title.replace(loc, '')
            break
    
    # 사람 관련 키워드 제거
    people_keywords = ['친구랑', '친구와', '동료와', '팀과', '선배와', '후배와']
    for keyword in people_keywords:
        title = title.replace(keyword, '')
    
    # 불필요한 단어들 제거
    cleanup_words = ['에서', '와', '과', '랑', '에', '를', '을', '가', '이', '의', '로', '으로']
    for word in cleanup_words:
        title = title.replace(word, ' ')
    
    # 공백 정리
    title = ' '.join(title.split())
    
    # 제목이 비어있으면 기본값 설정
    if not title or len(title.strip()) < 2:
        if extracted_location:
            title = f"{extracted_location} 일정"
        else:
            title = "일정"
    
    # 장소 정보 업데이트
    if extracted_location:
        location = extracted_location
    
    print(f"📝 추출된 제목: '{title}'")
    
    # 장소 추출
    location = ""
    if '회의실' in user_input:
        location = "회의실"
    elif '사무실' in user_input:
        location = "사무실"
    
    print(f"📍 추출된 장소: '{location}'")
    
    try:
        # 이벤트 생성
        saved_event = create_event_from_timestamps(
            title=title,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            location=location,
            attendees=[],
            notes="키워드 기반 파싱으로 생성",
            all_day=False
        )
        
        return {
            "status": "created",
            "message": f"✅ 일정이 등록되었습니다!\n\n📅 {saved_event['title']}\n🕐 {formatUnixTimestamp(saved_event['start_timestamp'])}\n📍 {saved_event.get('location', '장소 미정')}",
            "event": saved_event
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"일정 생성 중 오류가 발생했습니다: {str(e)}"
        }

def create_event_from_timestamps(title: str, start_timestamp: int, end_timestamp: int, 
                                 location: str = "", attendees: list = None, notes: str = "", 
                                 all_day: bool = False) -> dict:
    """Unix timestamp를 직접 받아서 이벤트를 데이터베이스에 저장"""
    conn = sqlite3.connect('events.db')
    cursor = conn.cursor()
    
    event_id = str(uuid.uuid4())
    attendees_json = json.dumps(attendees or [], ensure_ascii=False)
    
    cursor.execute('''
        INSERT INTO events (id, title, start_timestamp, end_timestamp, 
                          all_day, location, attendees, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        event_id,
        title,
        start_timestamp,
        end_timestamp,
        all_day,
        location,
        attendees_json,
        notes
    ))
    
    conn.commit()
    conn.close()
    
    return {
        "id": event_id,
        "title": title,
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
        "location": location,
        "attendees": attendees or [],
        "notes": notes
    }

def create_event_db(event: Event) -> dict:
    """이벤트를 데이터베이스에 저장"""
    conn = sqlite3.connect('events.db')
    cursor = conn.cursor()
    
    event_id = str(uuid.uuid4())
    attendees_json = json.dumps(event.attendees or [], ensure_ascii=False)
    
    # Unix Timestamp로 변환 (Asia/Seoul 타임존 고려)
    start_timestamp = None
    end_timestamp = None
    
    if event.start and event.start.iso:
        try:
            # ISO 문자열을 파싱하고 Asia/Seoul 타임존으로 처리
            start_dt = datetime.fromisoformat(event.start.iso.replace('Z', '+00:00'))
            start_timestamp = datetime_to_unix_timestamp(start_dt)
        except:
            # 현재 시간을 Asia/Seoul 타임존으로 설정
            import pytz
            seoul_tz = pytz.timezone('Asia/Seoul')
            start_timestamp = int(seoul_tz.localize(datetime.now()).timestamp())
    
    if event.end and event.end.iso:
        try:
            # ISO 문자열을 파싱하고 Asia/Seoul 타임존으로 처리
            end_dt = datetime.fromisoformat(event.end.iso.replace('Z', '+00:00'))
            end_timestamp = datetime_to_unix_timestamp(end_dt)
        except:
            # 현재 시간 + 1시간을 Asia/Seoul 타임존으로 설정
            import pytz
            seoul_tz = pytz.timezone('Asia/Seoul')
            end_timestamp = int(seoul_tz.localize(datetime.now()).timestamp()) + 3600
    
    cursor.execute('''
        INSERT INTO events (id, title, start_timestamp, end_timestamp, 
                          all_day, location, attendees, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        event_id,
        event.title,
        start_timestamp,
        end_timestamp,
        event.all_day,
        event.location,
        attendees_json,
        event.notes
    ))
    
    conn.commit()
    conn.close()
    
    return {
        "id": event_id,
        "title": event.title,
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
        "location": event.location,
        "attendees": event.attendees,
        "notes": event.notes
    }

def get_events_db() -> List[dict]:
    """모든 이벤트를 데이터베이스에서 조회"""
    conn = sqlite3.connect('events.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, title, start_timestamp, end_timestamp, 
               all_day, location, attendees, notes, created_at, updated_at
        FROM events 
        ORDER BY start_timestamp ASC
    ''')
    
    events = []
    for row in cursor.fetchall():
        event = {
            "id": row[0],
            "title": row[1],
            "start_timestamp": row[2],
            "end_timestamp": row[3],
            "all_day": bool(row[4]),
            "location": row[5],
            "attendees": json.loads(row[6]) if row[6] else [],
            "notes": row[7],
            "created_at": row[8],
            "updated_at": row[9],
            # 프론트엔드 호환성을 위한 추가 필드
            "start": {
                "iso": unix_timestamp_to_datetime(row[2]).isoformat(),
                "tz": "Asia/Seoul"
            },
            "end": {
                "iso": unix_timestamp_to_datetime(row[3]).isoformat(),
                "tz": "Asia/Seoul"
            }
        }
        events.append(event)
    
    conn.close()
    return events

def get_event_db(event_id: str) -> Optional[dict]:
    """특정 이벤트를 데이터베이스에서 조회"""
    conn = sqlite3.connect('events.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, title, start_timestamp, end_timestamp, 
               all_day, location, attendees, notes, created_at, updated_at
        FROM events 
        WHERE id = ?
    ''', (event_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "title": row[1],
            "start_timestamp": row[2],
            "end_timestamp": row[3],
            "all_day": bool(row[4]),
            "location": row[5],
            "attendees": json.loads(row[6]) if row[6] else [],
            "notes": row[7],
            "created_at": row[8],
            "updated_at": row[9],
            # 프론트엔드 호환성을 위한 추가 필드
            "start": {
                "iso": unix_timestamp_to_datetime(row[2]).isoformat(),
                "tz": "Asia/Seoul"
            },
            "end": {
                "iso": unix_timestamp_to_datetime(row[3]).isoformat(),
                "tz": "Asia/Seoul"
            }
        }
    return None

def update_event_db(event_id: str, event: Event) -> Optional[dict]:
    """이벤트를 데이터베이스에서 업데이트"""
    conn = sqlite3.connect('events.db')
    cursor = conn.cursor()
    
    attendees_json = json.dumps(event.attendees or [], ensure_ascii=False)
    
    # Unix Timestamp로 변환
    start_timestamp = None
    end_timestamp = None
    
    if event.start and event.start.iso:
        try:
            start_dt = datetime.fromisoformat(event.start.iso.replace('Z', '+00:00'))
            start_timestamp = datetime_to_unix_timestamp(start_dt)
        except:
            start_timestamp = int(datetime.now().timestamp())
    
    if event.end and event.end.iso:
        try:
            end_dt = datetime.fromisoformat(event.end.iso.replace('Z', '+00:00'))
            end_timestamp = datetime_to_unix_timestamp(end_dt)
        except:
            end_timestamp = int(datetime.now().timestamp()) + 3600  # 1시간 후
    
    cursor.execute('''
        UPDATE events 
        SET title = ?, start_timestamp = ?, end_timestamp = ?, 
            all_day = ?, location = ?, attendees = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (
        event.title,
        start_timestamp,
        end_timestamp,
        event.all_day,
        event.location,
        attendees_json,
        event.notes,
        event_id
    ))
    
    if cursor.rowcount > 0:
        conn.commit()
        conn.close()
        return get_event_db(event_id)
    
    conn.close()
    return None

def delete_event_db(event_id: str) -> bool:
    """이벤트를 데이터베이스에서 삭제"""
    conn = sqlite3.connect('events.db')
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM events WHERE id = ?', (event_id,))
    
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return deleted

# -------------------------
# 구글 캘린더 API 헬퍼 (mock)
# -------------------------
def get_google_calendar_service(user_token="dummy"):
    # 실제 환경에서는 OAuth2 인증 후 Credentials 사용 필요
    service = build("calendar", "v3")   # credentials=creds
    return service


def create_event_google(event: Event):
    service = get_google_calendar_service()
    body = {
        "summary": event.title,
        "location": event.location,
        "description": event.notes,
        "start": {"dateTime": event.start.iso, "timeZone": event.start.tz},
        "end": {"dateTime": event.end.iso, "timeZone": event.end.tz},
        "attendees": [{"email": a} for a in (event.attendees or [])],
    }
    # 실제 구글 API 호출 예시
    # created_event = service.events().insert(calendarId="primary", body=body).execute()
    created_event = {"id": "mock123", "summary": event.title}  # mock response
    return {"status": "created", "event": created_event}


def search_event_google(event: Event):
    service = get_google_calendar_service()
    # 실제 구글 API 호출 예시
    # events = service.events().list(
    #     calendarId="primary",
    #     timeMin=event.start.iso,
    #     timeMax=event.end.iso,
    #     singleEvents=True,
    #     orderBy="startTime"
    # ).execute()
    events = {"items": [{"id": "mock456", "summary": "Lunch with Prof. Kim"}]}
    return {"status": "found", "events": events["items"]}


# -------------------------
# To-do 기능 (로컬)
# -------------------------
def create_task_local(event: Event):
    task = {"title": event.title, "deadline": getattr(event.start, 'iso', None), "notes": event.notes}
    with open("tasks.json", "a", encoding="utf-8") as f:
        f.write(json.dumps(task, ensure_ascii=False) + "\n")
    return {"status": "task_created", "task": task}


# -------------------------
# OpenAI: 자연어 → JSON 변환
# -------------------------
SYSTEM_PROMPT = """
You are an assistant that converts natural language scheduling requests
into a JSON object with this schema:

{
  "intent": "create_event | update_event | delete_event | search_event | create_task",
  "event": {
    "title": "...",
    "start": {"iso": "...", "tz": "Asia/Seoul"},
    "end": {"iso": "...", "tz": "Asia/Seoul"},
    "all_day": false,
    "location": "...",
    "attendees": ["..."],
    "recurrence": {"rrule": "..."},
    "reminders": [{"minutes": 30}],
    "notes": "...",
    "confidence": 0.0~1.0,
    "needs_confirmation": false
  }
}
Always return valid JSON.
"""

def natural_language_to_event(user_input: str) -> dict:
    if client is None:
        raise Exception("OpenAI API 키가 설정되지 않았습니다.")
    
    # 개선된 시스템 프롬프트 - Unix timestamp 직접 생성
    system_prompt = """
You are an assistant that converts natural language scheduling requests into a JSON object with this schema:

{
  "intent": "create_event",
  "event": {
    "title": "일정 제목",
    "start_timestamp": 1234567890,
    "end_timestamp": 1234567890,
    "location": "장소",
    "attendees": ["참석자1", "참석자2"],
    "notes": "메모",
    "all_day": false
  }
}

Rules:
1. start_timestamp and end_timestamp must be Unix timestamps (seconds since 1970-01-01 00:00:00 UTC)
2. If no year is specified, use current year (2025)
3. If no end time is specified, set end_timestamp = start_timestamp + 3600 (1 hour later)
4. Convert all times to Asia/Seoul timezone before creating timestamps
5. Always return valid JSON with Unix timestamps
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"GPT 자연어 파싱 실패: {e}")
        raise Exception(f"GPT 자연어 파싱 중 오류가 발생했습니다: {str(e)}")


# -------------------------
# FastAPI 라우트들
# -------------------------
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """메인 페이지"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/events")
async def get_events():
    """저장된 이벤트 목록 반환"""
    events = get_events_db()
    return {"events": events}

@app.post("/create_event")
async def create_event(request: CreateEventRequest):
    """새 이벤트 생성"""
    try:
        # Event 객체 생성
        event = Event(
            title=request.title,
            start=EventTime(iso=request.start_iso, tz=request.start_tz),
            end=EventTime(iso=request.end_iso, tz=request.end_tz),
            all_day=request.all_day,
            location=request.location,
            attendees=request.attendees,
            notes=request.notes
        )
        
        # 데이터베이스에 저장
        saved_event = create_event_db(event)
        
        return {
            "status": "success",
            "message": "이벤트가 성공적으로 생성되었습니다.",
            "event": saved_event
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"이벤트 생성 실패: {str(e)}")

@app.get("/get_events")
async def get_all_events():
    """모든 이벤트 조회"""
    events = get_events_db()
    return {"events": events, "count": len(events)}

@app.get("/get_event/{event_id}")
async def get_event(event_id: str):
    """특정 이벤트 조회"""
    event = get_event_db(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="이벤트를 찾을 수 없습니다.")
    return {"event": event}

@app.put("/update_event/{event_id}")
async def update_event(event_id: str, request: UpdateEventRequest):
    """이벤트 수정"""
    try:
        # 기존 이벤트 조회
        existing_event = get_event_db(event_id)
        if not existing_event:
            raise HTTPException(status_code=404, detail="이벤트를 찾을 수 없습니다.")
        
        # 업데이트할 필드만 Event 객체로 생성
        event_data = {
            "title": request.title if request.title is not None else existing_event["title"],
            "start": EventTime(
                iso=request.start_iso if request.start_iso else existing_event["start"]["iso"],
                tz=request.start_tz if request.start_tz else existing_event["start"]["tz"]
            ),
            "end": EventTime(
                iso=request.end_iso if request.end_iso else existing_event["end"]["iso"],
                tz=request.end_tz if request.end_tz else existing_event["end"]["tz"]
            ),
            "all_day": request.all_day if request.all_day is not None else existing_event["all_day"],
            "location": request.location if request.location is not None else existing_event["location"],
            "attendees": request.attendees if request.attendees is not None else existing_event["attendees"],
            "notes": request.notes if request.notes is not None else existing_event["notes"]
        }
        
        event = Event(**event_data)
        
        # 데이터베이스 업데이트
        updated_event = update_event_db(event_id, event)
        
        if updated_event:
            return {
                "status": "success",
                "message": "이벤트가 성공적으로 수정되었습니다.",
                "event": updated_event
            }
        else:
            raise HTTPException(status_code=400, detail="이벤트 수정에 실패했습니다.")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"이벤트 수정 실패: {str(e)}")

@app.delete("/delete_event/{event_id}")
async def delete_event(event_id: str):
    """이벤트 삭제"""
    try:
        deleted = delete_event_db(event_id)
        if deleted:
            return {
                "status": "success",
                "message": "이벤트가 성공적으로 삭제되었습니다."
            }
        else:
            raise HTTPException(status_code=404, detail="이벤트를 찾을 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"이벤트 삭제 실패: {str(e)}")

@app.post("/chat")
async def chat(request: dict):
    """
    사용자 입력(자연어) → JSON 변환 → intent에 따라 처리
    """
    try:
        # JSON body에서 user_input 추출
        user_input = request.get('user_input', str(request))
        
        # OpenAI API 키가 없으면 오류 반환
        if client is None:
            return {
                "status": "error",
                "message": "OpenAI API 키가 설정되지 않았습니다. 자연어 처리를 위해서는 API 키가 필요합니다."
            }
        
        # 자연어 파싱 시도
        try:
            event_json = natural_language_to_event(user_input)
            req = EventRequest(**event_json)
        except Exception as parse_error:
            print(f"GPT 자연어 파싱 실패: {parse_error}")
            return {
                "status": "error",
                "message": f"일정 파싱 중 오류가 발생했습니다: {str(parse_error)}"
            }

        if req.intent == "create_event":
            # 필수 필드 검증
            if not req.event.title or not req.event.start_timestamp:
                return {
                    "status": "error",
                    "message": "일정 제목과 시작 시간이 필요합니다."
                }
            
            # Unix timestamp를 직접 사용하여 데이터베이스에 저장
            try:
                saved_event = create_event_from_timestamps(
                    title=req.event.title,
                    start_timestamp=req.event.start_timestamp,
                    end_timestamp=req.event.end_timestamp or (req.event.start_timestamp + 3600),
                    location=req.event.location or "",
                    attendees=req.event.attendees or [],
                    notes=req.event.notes or "",
                    all_day=req.event.all_day or False
                )
                
                return {
                    "status": "created", 
                    "message": f"✅ 일정이 등록되었습니다!\n\n📅 {saved_event['title']}\n🕐 {formatUnixTimestamp(saved_event['start_timestamp'])}\n📍 {saved_event.get('location', '장소 미정')}",
                    "event": saved_event
                }
            except Exception as db_error:
                print(f"DB 저장 실패: {db_error}")
                return {
                    "status": "error",
                    "message": f"일정 저장 중 오류가 발생했습니다: {str(db_error)}"
                }
                
        elif req.intent == "search_event":
            # 데이터베이스에서 검색
            all_events = get_events_db()
            # 간단한 제목 기반 검색 (향후 개선 가능)
            search_results = []
            if req.event.title:
                search_term = req.event.title.lower()
                for event in all_events:
                    if search_term in event.get("title", "").lower():
                        search_results.append(event)
            
            return {
                "status": "found",
                "events": search_results,
                "message": f"{len(search_results)}개의 일정을 찾았습니다."
            }
        elif req.intent == "create_task":
            return create_task_local(req.event)
        elif req.intent == "update_event":
            return {"status": "update_event not implemented"}
        elif req.intent == "delete_event":
            return {"status": "delete_event not implemented"}
        else:
            # 일반적인 챗봇 응답
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "당신은 일정 관리 챗봇입니다. 사용자의 일정 관련 질문에 도움을 주세요."},
                        {"role": "user", "content": user_input}
                    ],
                    max_tokens=500,
                    temperature=0.7
                )
                
                return {
                    "status": "chat",
                    "message": response.choices[0].message.content
                }
            except Exception as chat_error:
                return {
                    "status": "error",
                    "message": f"챗봇 응답 생성 중 오류가 발생했습니다: {str(chat_error)}"
                }
    except Exception as e:
        print(f"Chat 엔드포인트 오류: {e}")
        return {"status": "error", "message": f"처리 중 오류가 발생했습니다: {str(e)}"}


@app.get("/rag_search")
async def rag_search(query: str):
    """
    RAG 기반 의미 검색
    """
    try:
        # 데이터베이스에서 이벤트 조회
        db_events = get_events_db()
        
        # RAG 검색 수행
        rag_results = parse_with_content(query)
        
        # 데이터베이스 이벤트에서도 검색
        db_matches = []
        query_lower = query.lower()
        for event in db_events:
            if (query_lower in event.get('title', '').lower() or 
                query_lower in event.get('notes', '').lower() or
                query_lower in event.get('location', '').lower()):
                db_matches.append(event)
        
        # 결과 결합
        all_results = rag_results + db_matches
        
        return {"results": all_results, "query": query}
    except Exception as e:
        return {"results": [], "error": str(e), "query": query}

@app.post("/upload_image")
async def upload_image(file: UploadFile = File(...)):
    """
    이미지 업로드 및 GPT 멀티모달을 통한 일정 등록
    """
    try:
        # 파일 타입 확인
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다.")
        
        # 이미지 데이터 읽기
        image_data = await file.read()
        
        # GPT 멀티모달로 일정 정보 추출
        extracted_data = analyze_image_with_gpt(image_data)
        
        if "error" in extracted_data:
            return {
                "status": "error",
                "message": extracted_data["error"]
            }
        
        # 필수 정보 확인
        if not extracted_data.get("start") or not extracted_data.get("end"):
            return {
                "status": "error",
                "message": "이미지에서 시간 정보를 추출할 수 없습니다.",
                "extracted_data": extracted_data
            }
        
        # Event 객체 생성
        event = Event(
            title=extracted_data.get("title", "GPT로 추출된 일정"),
            start=EventTime(
                iso=extracted_data["start"]["iso"],
                tz=extracted_data["start"].get("tz", "Asia/Seoul")
            ),
            end=EventTime(
                iso=extracted_data["end"]["iso"],
                tz=extracted_data["end"].get("tz", "Asia/Seoul")
            ),
            all_day=False,
            location=extracted_data.get("location"),
            attendees=extracted_data.get("attendees", []),
            notes=extracted_data.get("notes")
        )
        
        # 데이터베이스에 저장
        saved_event = create_event_db(event)
        
        return {
            "status": "success",
            "message": "이미지에서 일정을 성공적으로 추출하고 등록했습니다!",
            "event": saved_event,
            "extracted_data": extracted_data
        }
        
    except Exception as e:
        # 상세한 에러 정보를 포함하여 반환
        error_message = str(e)
        if "no column named" in error_message:
            error_message = f"데이터베이스 스키마 오류: {error_message}. 앱을 재시작하면 자동으로 수정됩니다."
        elif "GPT" in error_message:
            error_message = f"AI 분석 오류: {error_message}"
        else:
            error_message = f"서버 오류: {error_message}"
        
        return {
            "status": "error",
            "message": error_message
        }