"""
구글 캘린더 API와의 양방향 동기화 모듈
"""
import os
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle

# 구글 캘린더 API 스코프
SCOPES = ['https://www.googleapis.com/auth/calendar']

class GoogleCalendarSync:
    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.pickle'):
        """
        구글 캘린더 동기화 클래스 초기화
        
        Args:
            credentials_file: 구글 클라우드 콘솔에서 다운로드한 credentials.json 파일 경로
            token_file: 인증 토큰을 저장할 파일 경로
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.calendar_id = 'primary'  # 기본 캘린더 사용
        
    def authenticate(self):
        """구글 캘린더 API 인증"""
        creds = None
        
        # 기존 토큰 파일이 있으면 로드
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # 유효한 인증 정보가 없으면 새로 생성
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(f"credentials.json 파일을 찾을 수 없습니다: {self.credentials_file}")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=8080)
            
            # 토큰 저장
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('calendar', 'v3', credentials=creds)
        return True
    
    def _convert_to_google_event(self, local_event: Dict[str, Any]) -> Dict[str, Any]:
        """로컬 이벤트를 구글 캘린더 이벤트 형식으로 변환"""
        google_event = {
            'summary': local_event.get('title', ''),
            'description': local_event.get('description', ''),
            'location': local_event.get('location', ''),
            'start': {
                'dateTime': local_event.get('date_start', ''),
                'timeZone': 'Asia/Seoul'
            },
            'end': {
                'dateTime': local_event.get('date_finish', local_event.get('date_start', '')),
                'timeZone': 'Asia/Seoul'
            }
        }
        
        # 참석자 정보 추가
        if local_event.get('member'):
            attendees = []
            if isinstance(local_event['member'], list):
                for member in local_event['member']:
                    attendees.append({'email': member})
            else:
                attendees.append({'email': local_event['member']})
            google_event['attendees'] = attendees
        
        # 로컬 ID를 확장 속성에 저장 (동기화용)
        google_event['extendedProperties'] = {
            'private': {
                'local_id': str(local_event.get('id', ''))
            }
        }
        
        return google_event
    
    def _convert_from_google_event(self, google_event: Dict[str, Any]) -> Dict[str, Any]:
        """구글 캘린더 이벤트를 로컬 이벤트 형식으로 변환"""
        local_event = {
            'id': int(google_event.get('extendedProperties', {}).get('private', {}).get('local_id', 0)) or int(str(uuid.uuid4().int)[:8]),
            'title': google_event.get('summary', ''),
            'description': google_event.get('description', ''),
            'location': google_event.get('location', ''),
            'date_start': google_event.get('start', {}).get('dateTime', ''),
            'date_finish': google_event.get('end', {}).get('dateTime', ''),
            'google_event_id': google_event.get('id', ''),
            'member': []
        }
        
        # 참석자 정보 처리
        if google_event.get('attendees'):
            local_event['member'] = [attendee.get('email', '') for attendee in google_event['attendees']]
        
        return local_event
    
    def sync_to_google(self, local_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """로컬 이벤트를 구글 캘린더에 동기화"""
        if not self.service:
            raise Exception("구글 캘린더 API가 인증되지 않았습니다. authenticate()를 먼저 호출하세요.")
        
        results = {
            'created': 0,
            'updated': 0,
            'errors': []
        }
        
        try:
            # 기존 구글 캘린더 이벤트 가져오기
            existing_events = self.get_google_events()
            existing_by_local_id = {event.get('extendedProperties', {}).get('private', {}).get('local_id'): event 
                                  for event in existing_events if event.get('extendedProperties', {}).get('private', {}).get('local_id')}
            
            for local_event in local_events:
                try:
                    local_id = str(local_event.get('id', ''))
                    google_event = self._convert_to_google_event(local_event)
                    
                    if local_id in existing_by_local_id:
                        # 기존 이벤트 업데이트
                        google_event_id = existing_by_local_id[local_id]['id']
                        self.service.events().update(
                            calendarId=self.calendar_id,
                            eventId=google_event_id,
                            body=google_event
                        ).execute()
                        results['updated'] += 1
                    else:
                        # 새 이벤트 생성
                        self.service.events().insert(
                            calendarId=self.calendar_id,
                            body=google_event
                        ).execute()
                        results['created'] += 1
                        
                except Exception as e:
                    results['errors'].append(f"이벤트 {local_event.get('title', 'Unknown')} 동기화 실패: {str(e)}")
            
        except HttpError as e:
            results['errors'].append(f"구글 캘린더 API 오류: {str(e)}")
        
        return results
    
    def get_google_events(self, max_results: int = 1000) -> List[Dict[str, Any]]:
        """구글 캘린더에서 이벤트 가져오기"""
        if not self.service:
            raise Exception("구글 캘린더 API가 인증되지 않았습니다. authenticate()를 먼저 호출하세요.")
        
        try:
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
        except HttpError as e:
            raise Exception(f"구글 캘린더 이벤트 조회 실패: {str(e)}")
    
    def sync_from_google(self, local_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """구글 캘린더에서 로컬로 이벤트 동기화"""
        if not self.service:
            raise Exception("구글 캘린더 API가 인증되지 않았습니다. authenticate()를 먼저 호출하세요.")
        
        results = {
            'created': 0,
            'updated': 0,
            'errors': []
        }
        
        try:
            google_events = self.get_google_events()
            local_by_id = {event['id']: event for event in local_events}
            
            for google_event in google_events:
                try:
                    local_event = self._convert_from_google_event(google_event)
                    local_id = local_event['id']
                    
                    if local_id in local_by_id:
                        # 기존 로컬 이벤트 업데이트
                        local_by_id[local_id].update(local_event)
                        results['updated'] += 1
                    else:
                        # 새 로컬 이벤트 생성
                        local_events.append(local_event)
                        results['created'] += 1
                        
                except Exception as e:
                    results['errors'].append(f"구글 이벤트 {google_event.get('summary', 'Unknown')} 동기화 실패: {str(e)}")
            
        except Exception as e:
            results['errors'].append(f"구글 캘린더 동기화 실패: {str(e)}")
        
        return results
    
    def delete_google_event(self, google_event_id: str) -> bool:
        """구글 캘린더에서 이벤트 삭제"""
        if not self.service:
            raise Exception("구글 캘린더 API가 인증되지 않았습니다. authenticate()를 먼저 호출하세요.")
        
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=google_event_id
            ).execute()
            return True
        except HttpError as e:
            print(f"구글 캘린더 이벤트 삭제 실패: {str(e)}")
            return False
