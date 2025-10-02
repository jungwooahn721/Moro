# 구글 캘린더 API 설정 가이드

## 1. Google Cloud Console 설정

### 1.1 프로젝트 생성
1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. 프로젝트 이름: `Moro Calendar Sync` (또는 원하는 이름)

### 1.2 Calendar API 활성화
1. 왼쪽 메뉴에서 "API 및 서비스" > "라이브러리" 선택
2. "Google Calendar API" 검색
3. "사용" 버튼 클릭하여 API 활성화

### 1.3 인증 정보 생성
1. "API 및 서비스" > "사용자 인증 정보" 선택
2. "사용자 인증 정보 만들기" > "OAuth 클라이언트 ID" 선택
3. 애플리케이션 유형: "데스크톱 애플리케이션"
4. 이름: `Moro Calendar Sync`
5. "만들기" 클릭
6. JSON 파일 다운로드 (`credentials.json`)

## 2. 파일 배치

### 2.1 credentials.json 파일 배치
```
Moro-backend/
├── credentials.json  ← 여기에 배치
├── google_calendar_sync.py
├── eventmanager.py
└── ...
```

### 2.2 필요한 라이브러리 설치
```bash
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
```

## 3. 첫 실행 및 인증

### 3.1 첫 동기화 실행
1. Flask 앱 실행: `python app.py`
2. 웹 브라우저에서 `http://localhost:5000` 접속
3. AI 채팅 패널에서 구글 캘린더 동기화 버튼 클릭
4. 브라우저가 열리면서 Google 로그인 요청
5. Google 계정으로 로그인 및 권한 승인

### 3.2 토큰 파일 생성
- 첫 인증 후 `token.pickle` 파일이 자동 생성됩니다
- 이 파일은 인증 정보를 저장하므로 안전하게 보관하세요

## 4. 동기화 기능

### 4.1 양방향 동기화
- **로컬 → 구글**: 로컬 JSON 파일의 일정을 구글 캘린더에 업로드
- **구글 → 로컬**: 구글 캘린더의 일정을 로컬 JSON 파일에 다운로드
- **양방향**: 두 방향 모두 동시에 동기화

### 4.2 AI 명령어로 동기화
```
"구글 캘린더와 동기화해줘"
"구글 캘린더에서 일정 가져와줘"
"로컬 일정을 구글 캘린더에 업로드해줘"
```

### 4.3 수동 동기화
- 웹 인터페이스의 구글 캘린더 동기화 버튼 클릭
- API 엔드포인트: `POST /api/sync/google`

## 5. 동기화 매핑

### 5.1 필드 매핑
| 로컬 JSON | 구글 캘린더 |
|-----------|-------------|
| title | summary |
| description | description |
| location | location |
| date_start | start.dateTime |
| date_finish | end.dateTime |
| member | attendees |
| id | extendedProperties.private.local_id |

### 5.2 시간대 설정
- 모든 일정은 `Asia/Seoul` 시간대로 설정됩니다
- 구글 캘린더에서 다른 시간대로 설정된 일정도 한국 시간으로 변환됩니다

## 6. 문제 해결

### 6.1 인증 오류
- `credentials.json` 파일이 올바른 위치에 있는지 확인
- Google Cloud Console에서 OAuth 클라이언트 ID가 올바르게 설정되었는지 확인

### 6.2 권한 오류
- Google 계정에서 캘린더 접근 권한이 있는지 확인
- API 할당량이 초과되지 않았는지 확인

### 6.3 동기화 오류
- 네트워크 연결 상태 확인
- 로그에서 구체적인 오류 메시지 확인

## 7. 보안 주의사항

### 7.1 파일 보안
- `credentials.json`과 `token.pickle` 파일을 안전하게 보관
- 이 파일들을 Git에 커밋하지 마세요
- `.gitignore`에 추가:
  ```
  credentials.json
  token.pickle
  ```

### 7.2 권한 관리
- 최소한의 필요한 권한만 요청
- 정기적으로 앱 권한을 검토하고 불필요한 권한은 제거

## 8. 고급 설정

### 8.1 특정 캘린더 사용
```python
# google_calendar_sync.py에서 수정
self.calendar_id = 'your-calendar-id@gmail.com'  # 기본 캘린더 대신 특정 캘린더 사용
```

### 8.2 동기화 방향 설정
```python
# API 호출 시 direction 파라미터 설정
{
    "direction": "to_google"    # 로컬 → 구글만
    "direction": "from_google"  # 구글 → 로컬만
    "direction": "both"         # 양방향 (기본값)
}
```

이제 구글 캘린더와 완전한 양방향 동기화가 가능합니다! 🎉
