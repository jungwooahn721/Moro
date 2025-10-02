// 전역 변수
let currentDate = new Date();
let events = [];
let selectedDate = null;

// DOM 요소들
const calendarGrid = document.getElementById('calendarGrid');
const currentMonthEl = document.getElementById('currentMonth');
const eventsList = document.getElementById('eventsList');
const chatPanel = document.getElementById('chatPanel');
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const eventModal = document.getElementById('eventModal');
const eventForm = document.getElementById('eventForm');

// 이벤트 리스너
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    loadEvents();
    // 주기적 폴링으로 DB 변경 반영 (10초)
    setInterval(loadEvents, 10000);
});

function initializeApp() {
    renderCalendar();
    updateEventsList();
}

function setupEventListeners() {
    // 캘린더 네비게이션
    document.getElementById('prevMonth').addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() - 1);
        renderCalendar();
    });
    
    document.getElementById('nextMonth').addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() + 1);
        renderCalendar();
    });

    // 헤더 버튼들
    document.getElementById('addEventBtn').addEventListener('click', openEventModal);
    document.getElementById('toggleChatBtn').addEventListener('click', toggleChat);
    document.getElementById('closeChatBtn').addEventListener('click', toggleChat);
    
    // 채팅 메모리 관리 버튼들
    document.getElementById('clearChatBtn').addEventListener('click', clearChatHistory);
    document.getElementById('syncGoogleBtn').addEventListener('click', syncGoogleCalendar);
    
    // 멀티미디어 입력 버튼들
    document.getElementById('voiceRecordBtn').addEventListener('click', toggleVoiceRecording);
    document.getElementById('imageUploadBtn').addEventListener('click', () => document.getElementById('imageFileInput').click());
    document.getElementById('imageFileInput').addEventListener('change', handleImageUpload);
    document.getElementById('removeMediaBtn').addEventListener('click', removeMediaPreview);
    
    // 클립보드 이미지 붙여넣기
    document.getElementById('chatInput').addEventListener('paste', handleClipboardPaste);

    // 모달 관련
    document.getElementById('closeModalBtn').addEventListener('click', closeEventModal);
    document.getElementById('cancelBtn').addEventListener('click', closeEventModal);
    eventForm.addEventListener('submit', handleEventSubmit);

    // 채팅
    document.getElementById('sendBtn').addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // 모달 외부 클릭으로 닫기
    eventModal.addEventListener('click', (e) => {
        if (e.target === eventModal) {
            closeEventModal();
        }
    });
}

// 캘린더 렌더링
function renderCalendar() {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    
    // 월 표시 업데이트
    currentMonthEl.textContent = `${year}년 ${month + 1}월`;
    
    // 달력 그리드 초기화
    calendarGrid.innerHTML = '';
    
    // 요일 헤더
    const dayHeaders = ['일', '월', '화', '수', '목', '금', '토'];
    dayHeaders.forEach(day => {
        const dayHeader = document.createElement('div');
        dayHeader.className = 'calendar-day-header';
        dayHeader.textContent = day;
        dayHeader.style.cssText = `
            background: #f7fafc;
            padding: 15px 10px;
            text-align: center;
            font-weight: 600;
            color: #4a5568;
            border-bottom: 2px solid #e2e8f0;
        `;
        calendarGrid.appendChild(dayHeader);
    });
    
    // 첫 번째 날과 마지막 날 계산
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay());
    
    // 6주 표시 (42일)
    for (let i = 0; i < 42; i++) {
        const date = new Date(startDate);
        date.setDate(startDate.getDate() + i);
        
        const dayElement = document.createElement('div');
        dayElement.className = 'calendar-day';
        
        // 다른 월의 날짜인지 확인
        if (date.getMonth() !== month) {
            dayElement.classList.add('other-month');
        }
        
        // 오늘인지 확인
        const today = new Date();
        if (date.toDateString() === today.toDateString()) {
            dayElement.classList.add('today');
        }
        
        // 날짜 번호
        const dayNumber = document.createElement('div');
        dayNumber.className = 'day-number';
        dayNumber.textContent = date.getDate();
        dayElement.appendChild(dayNumber);
        
        // 해당 날짜의 이벤트 표시
        const dayEvents = getEventsForDate(date);
        if (dayEvents.length > 0) {
            dayElement.classList.add('has-events');
            const eventsContainer = document.createElement('div');
            eventsContainer.className = 'day-events';
            
            dayEvents.slice(0, 3).forEach(event => {
                const eventDot = document.createElement('span');
                eventDot.className = 'event-dot';
                eventDot.title = event.title;
                eventsContainer.appendChild(eventDot);
            });
            
            if (dayEvents.length > 3) {
                const moreText = document.createElement('span');
                moreText.textContent = `+${dayEvents.length - 3}`;
                moreText.style.fontSize = '10px';
                moreText.style.color = '#667eea';
                eventsContainer.appendChild(moreText);
            }
            
            dayElement.appendChild(eventsContainer);
        }
        
        // 클릭 이벤트
        dayElement.addEventListener('click', () => {
            selectedDate = date;
            updateEventsList();
        });
        
        calendarGrid.appendChild(dayElement);
    }
}

// 특정 날짜의 이벤트 가져오기
function getEventsForDate(date) {
    return events.filter(event => {
        if (!event.date_start) return false;
        const eventDate = new Date(event.date_start);
        return eventDate.toDateString() === date.toDateString();
    });
}

// 이벤트 목록 업데이트
function updateEventsList() {
    const targetDate = selectedDate || new Date();
    const dayEvents = getEventsForDate(targetDate);
    
    eventsList.innerHTML = '';
    
    if (dayEvents.length === 0) {
        eventsList.innerHTML = '<p style="color: #a0aec0; text-align: center; padding: 20px;">등록된 일정이 없습니다.</p>';
        return;
    }
    
    dayEvents.forEach(event => {
        const eventElement = document.createElement('div');
        eventElement.className = 'event-item';
        eventElement.dataset.eventId = event.id || '';
        eventElement.innerHTML = `
            <div class="event-title">${event.title}</div>
            <div class="event-time">${formatEventTime(event)}</div>
            ${event.location ? `<div class="event-location">📍 ${event.location}</div>` : ''}
            <div style="margin-top:10px; display:flex; gap:8px;">
                <button class="btn btn-secondary btn-edit" data-id="${event.id}">수정</button>
                <button class="btn btn-primary btn-delete" data-id="${event.id}">삭제</button>
            </div>
        `;
        
        eventsList.appendChild(eventElement);
    });
}

// 이벤트 시간 포맷팅
function formatEventTime(event) {
    if (!event.date_start) return '';
    
    const startTime = new Date(event.date_start);
    const endTime = event.date_finish ? new Date(event.date_finish) : null;
    
    let timeStr = startTime.toLocaleTimeString('ko-KR', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
    
    if (endTime) {
        timeStr += ` - ${endTime.toLocaleTimeString('ko-KR', { 
            hour: '2-digit', 
            minute: '2-digit' 
        })}`;
    }
    
    return timeStr;
}

// 이벤트 로드
async function loadEvents() {
    try {
        const response = await fetch('/api/events');
        events = await response.json();
        renderCalendar();
        updateEventsList();
    } catch (error) {
        console.error('이벤트 로드 실패:', error);
        showNotification('이벤트를 불러오는데 실패했습니다.', 'error');
    }
}

// 이벤트 모달 열기
function openEventModal(event = null) {
    const modal = document.getElementById('eventModal');
    const modalTitle = document.getElementById('modalTitle');
    const form = document.getElementById('eventForm');
    
    if (event) {
        modalTitle.textContent = '일정 수정';
        fillEventForm(event);
    } else {
        modalTitle.textContent = '일정 추가';
        form.reset();
        
        // 선택된 날짜가 있으면 기본값으로 설정
        if (selectedDate) {
            const dateStr = selectedDate.toISOString().split('T')[0];
            document.getElementById('eventStartDate').value = dateStr;
            document.getElementById('eventEndDate').value = dateStr;
        }
    }
    
    modal.classList.add('show');
}

// 이벤트 수정
function editEvent(event) {
    openEventModal(event);
}

// 이벤트 폼 채우기
function fillEventForm(event) {
    document.getElementById('eventId').value = event.id || '';
    document.getElementById('eventTitle').value = event.title || '';
    document.getElementById('eventDescription').value = event.description || '';
    document.getElementById('eventLocation').value = event.location || '';
    document.getElementById('eventMembers').value = Array.isArray(event.member) ? event.member.join(', ') : '';
    
    if (event.date_start) {
        const startDate = new Date(event.date_start);
        document.getElementById('eventStartDate').value = startDate.toISOString().split('T')[0];
        document.getElementById('eventStartTime').value = startDate.toTimeString().slice(0, 5);
    }
    
    if (event.date_finish) {
        const endDate = new Date(event.date_finish);
        document.getElementById('eventEndDate').value = endDate.toISOString().split('T')[0];
        document.getElementById('eventEndTime').value = endDate.toTimeString().slice(0, 5);
    }
}

// 이벤트 모달 닫기
function closeEventModal() {
    eventModal.classList.remove('show');
    eventForm.reset();
}

// 이벤트 제출 처리
async function handleEventSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(eventForm);
    const eventId = document.getElementById('eventId').value;
    
    const eventData = {
        title: document.getElementById('eventTitle').value,
        description: document.getElementById('eventDescription').value,
        location: document.getElementById('eventLocation').value,
        member: document.getElementById('eventMembers').value.split(',').map(m => m.trim()).filter(m => m),
        date_start: `${document.getElementById('eventStartDate').value}T${document.getElementById('eventStartTime').value}:00+09:00`,
        date_finish: `${document.getElementById('eventEndDate').value}T${document.getElementById('eventEndTime').value}:00+09:00`
    };
    
    try {
        let response;
        if (eventId) {
            // 수정
            response = await fetch(`/api/events/${eventId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(eventData)
            });
        } else {
            // 생성
            response = await fetch('/api/events', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(eventData)
            });
        }
        
        const result = await response.json();
        
        if (result.success) {
            showNotification(eventId ? '일정이 수정되었습니다.' : '일정이 추가되었습니다.', 'success');
            closeEventModal();
            loadEvents();
        } else {
            throw new Error(result.error || '저장에 실패했습니다.');
        }
    } catch (error) {
        console.error('이벤트 저장 실패:', error);
        showNotification('일정 저장에 실패했습니다.', 'error');
    }
}

// 이벤트 삭제
async function deleteEventById(eventId) {
    if (!eventId) return;
    try {
        const res = await fetch(`/api/events/${eventId}`, { method: 'DELETE' });
        const result = await res.json();
        if (result.success) {
            showNotification('일정이 삭제되었습니다.', 'success');
            await loadEvents();
        } else {
            throw new Error(result.error || '삭제 실패');
        }
    } catch (err) {
        console.error('삭제 실패:', err);
        showNotification('일정 삭제에 실패했습니다.', 'error');
    }
}

// 채팅 토글
function toggleChat() {
    chatPanel.classList.toggle('open');
    if (chatPanel.classList.contains('open')) {
        chatInput.focus();
    }
}

// 메시지 전송
async function sendMessage() {
    const message = chatInput.value.trim();
    
    if (!message && !currentMedia) return;
    
    // 사용자 메시지 표시
    if (message) {
        addMessage(message, 'user');
    }
    chatInput.value = '';
    
    // 로딩 표시
    const loadingId = addMessage('AI가 응답을 생성하고 있습니다...', 'ai', true);
    
    try {
        let response;
        
        if (currentMedia && message) {
            // 텍스트 + 멀티미디어 혼합 전송
            const formData = new FormData();
            formData.append('text', message);
            
            if (currentMedia.type === 'image') {
                formData.append('image', currentMedia.file);
            }
            
            response = await fetch('/api/process/mixed', {
                method: 'POST',
                body: formData
            });
            
            const mixedResult = await response.json();
            if (mixedResult.success) {
                // 처리된 메시지로 AI 채팅 요청
                response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: mixedResult.formatted_message })
                });
            } else {
                addMessage(`멀티미디어 처리 실패: ${mixedResult.error}`, 'ai');
                return;
            }
        } else if (currentMedia) {
            // 멀티미디어만 전송
            if (currentMedia.type === 'image') {
                const formData = new FormData();
                formData.append('image', currentMedia.file);
                formData.append('format', currentMedia.file.type.split('/')[1]);
                
                response = await fetch('/api/process/image', {
                    method: 'POST',
                    body: formData
                });
                
                const imageResult = await response.json();
                if (imageResult.success) {
                    // 처리된 메시지로 AI 채팅 요청
                    response = await fetch('/api/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: imageResult.formatted_message })
                    });
                } else {
                    addMessage(`이미지 처리 실패: ${imageResult.error}`, 'ai');
                    return;
                }
            }
        } else {
            // 텍스트만 전송
            response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message })
            });
        }
        
        const result = await response.json();
        // 로딩 메시지 안전 제거 (성공 시)
        setTimeout(() => {
            const loadingEl = document.getElementById(loadingId);
            if (loadingEl && loadingEl.parentNode) {
                loadingEl.parentNode.removeChild(loadingEl);
            }
        }, 0);

        // AI 응답 표시 (빈 응답 방지)
        const reply = (result && result.response) ? String(result.response) : '응답을 가져오지 못했습니다.';
        addMessage(reply, 'ai');
        
        // 일정 관련 작업이 완료된 경우 캘린더 새로고침
        if (reply.includes('[CALENDAR_REFRESH]')) {
            setTimeout(() => {
                loadEvents();
            }, 500); // 0.5초 후 캘린더 새로고침
        }
        
        // 멀티미디어 미리보기 제거
        if (currentMedia) {
            removeMediaPreview();
        }
    } catch (error) {
        console.error('채팅 실패:', error);
        // 로딩 메시지 안전 제거 (오류 시)
        setTimeout(() => {
            const loadingEl = document.getElementById(loadingId);
            if (loadingEl && loadingEl.parentNode) {
                loadingEl.parentNode.removeChild(loadingEl);
            }
        }, 0);

        addMessage('죄송합니다. 오류가 발생했습니다. 다시 시도해 주세요.', 'ai');
    }
}

// 메시지 추가
function addMessage(content, type, isLoading = false) {
    const messageId = 'msg_' + Date.now();
    const messageEl = document.createElement('div');
    messageEl.id = messageId;
    messageEl.className = `message ${type}-message`;
    
    const contentEl = document.createElement('div');
    contentEl.className = 'message-content';
    
    if (isLoading) {
        contentEl.innerHTML = '<div class="loading"></div> ' + content;
    } else {
        // 계획 관련 메시지인지 확인
        if (content.includes('계획이 생성되었습니다') || content.includes('단계')) {
            contentEl.innerHTML = formatPlanMessage(content);
        } else {
            // 긴 텍스트를 더 잘 표시하기 위해 innerHTML 사용
            contentEl.innerHTML = content.replace(/\n/g, '<br>');
        }
    }
    
    messageEl.appendChild(contentEl);
    chatMessages.appendChild(messageEl);
    
    // 스크롤을 맨 아래로
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageId;
}

// 채팅 기록 초기화
async function clearChatHistory() {
    try {
        const response = await fetch('/api/chat/clear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (result.success) {
            // 채팅 메시지 모두 제거
            chatMessages.innerHTML = '';
            addMessage('채팅 기록이 초기화되었습니다.', 'ai');
        } else {
            addMessage('채팅 기록 초기화에 실패했습니다.', 'ai');
        }
    } catch (error) {
        console.error('채팅 기록 초기화 실패:', error);
        addMessage('채팅 기록 초기화 중 오류가 발생했습니다.', 'ai');
    }
}

// 구글 캘린더 동기화
async function syncGoogleCalendar() {
    try {
        const syncBtn = document.getElementById('syncGoogleBtn');
        const originalText = syncBtn.innerHTML;
        
        // 버튼 비활성화 및 로딩 표시
        syncBtn.disabled = true;
        syncBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        
        const response = await fetch('/api/sync/google', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ direction: 'both' })
        });
        
        const result = await response.json();
        
        if (result.success) {
            addMessage(result.message, 'ai');
            // 캘린더 새로고침
            loadEvents();
        } else {
            addMessage(`동기화 실패: ${result.error}`, 'ai');
        }
        
    } catch (error) {
        console.error('구글 캘린더 동기화 실패:', error);
        addMessage('구글 캘린더 동기화 중 오류가 발생했습니다.', 'ai');
    } finally {
        // 버튼 복원
        const syncBtn = document.getElementById('syncGoogleBtn');
        syncBtn.disabled = false;
        syncBtn.innerHTML = '<i class="fas fa-sync"></i>';
    }
}

// 멀티미디어 처리 관련 변수
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let currentMedia = null;

// 음성 녹음 토글
async function toggleVoiceRecording() {
    if (isRecording) {
        stopVoiceRecording();
    } else {
        await startVoiceRecording();
    }
}

// 음성 녹음 시작
async function startVoiceRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            await processAudio(audioBlob);
            stream.getTracks().forEach(track => track.stop());
        };
        
        mediaRecorder.start();
        isRecording = true;
        
        // UI 업데이트
        document.getElementById('voiceRecording').style.display = 'block';
        document.getElementById('voiceRecordBtn').innerHTML = '<i class="fas fa-stop"></i>';
        document.getElementById('voiceRecordBtn').style.background = '#dc3545';
        
    } catch (error) {
        console.error('음성 녹음 시작 실패:', error);
        addMessage('음성 녹음 권한이 필요합니다.', 'ai');
    }
}

// 음성 녹음 중지
function stopVoiceRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        
        // UI 복원
        document.getElementById('voiceRecording').style.display = 'none';
        document.getElementById('voiceRecordBtn').innerHTML = '<i class="fas fa-microphone"></i>';
        document.getElementById('voiceRecordBtn').style.background = '#6c757d';
    }
}

// 음성 데이터 처리
async function processAudio(audioBlob) {
    try {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'audio.webm');
        formData.append('format', 'webm');
        
        const response = await fetch('/api/process/audio', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            // 음성 전사 결과를 채팅 입력창에 표시
            document.getElementById('chatInput').value = result.transcript;
            // 자동으로 메시지 전송
            sendMessage();
        } else {
            addMessage(`음성 처리 실패: ${result.error}`, 'ai');
        }
        
    } catch (error) {
        console.error('음성 처리 실패:', error);
        addMessage('음성 처리 중 오류가 발생했습니다.', 'ai');
    }
}

// 이미지 업로드 처리
function handleImageUpload(event) {
    const file = event.target.files[0];
    if (file && file.type.startsWith('image/')) {
        processImage(file);
    }
}

// 이미지 데이터 처리
async function processImage(imageFile) {
    try {
        // 이미지 미리보기 표시
        const reader = new FileReader();
        reader.onload = (e) => {
            document.getElementById('previewImage').src = e.target.result;
            document.getElementById('mediaPreview').style.display = 'block';
        };
        reader.readAsDataURL(imageFile);
        
        // 서버로 이미지 전송
        const formData = new FormData();
        formData.append('image', imageFile);
        formData.append('format', imageFile.type.split('/')[1]);
        
        const response = await fetch('/api/process/image', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentMedia = {
                type: 'image',
                file: imageFile,
                analysis: result.analysis,
                formattedMessage: result.formatted_message
            };
            // 이미지 분석 결과를 입력창에 표시하고 자동 전송
            document.getElementById('chatInput').value = `[이미지 분석] ${result.analysis.substring(0, 200)}...`;
            sendMessage();
        } else {
            addMessage(`이미지 처리 실패: ${result.error}`, 'ai');
        }
        
    } catch (error) {
        console.error('이미지 처리 실패:', error);
        addMessage('이미지 처리 중 오류가 발생했습니다.', 'ai');
    }
}

// 클립보드 이미지 붙여넣기 처리
async function handleClipboardPaste(event) {
    const items = event.clipboardData.items;
    
    for (let item of items) {
        if (item.type.startsWith('image/')) {
            event.preventDefault();
            
            const file = item.getAsFile();
            if (file) {
                processImage(file);
            }
            break;
        }
    }
}

// 미디어 미리보기 제거
function removeMediaPreview() {
    document.getElementById('mediaPreview').style.display = 'none';
    document.getElementById('imageFileInput').value = '';
    currentMedia = null;
}

// 채팅 기록 조회
async function loadChatHistory() {
    try {
        const response = await fetch('/api/chat/history');
        const result = await response.json();
        
        if (result.history) {
            // 기존 메시지 제거
            chatMessages.innerHTML = '';
            
            // 히스토리 메시지 추가
            result.history.forEach(msg => {
                if (msg.type === 'human') {
                    addMessage(msg.content, 'user');
                } else if (msg.type === 'ai') {
                    addMessage(msg.content, 'ai');
                }
            });
        }
    } catch (error) {
        console.error('채팅 기록 로드 실패:', error);
    }
}

// 계획 메시지 포맷팅
function formatPlanMessage(content) {
    // 계획 관련 키워드가 포함된 경우 특별한 스타일 적용
    if (content.includes('계획이 생성되었습니다')) {
        return `<div style="background: #e6f3ff; padding: 10px; border-radius: 8px; border-left: 4px solid #1890ff;">
                    <strong>📋 계획 생성됨</strong><br>
                    ${content}
                </div>`;
    } else if (content.includes('단계')) {
        return `<div style="background: #f6ffed; padding: 10px; border-radius: 8px; border-left: 4px solid #52c41a;">
                    <strong>⚡ 실행 중</strong><br>
                    ${content}
                </div>`;
    }
    return content;
}

// 알림 표시
function showNotification(message, type = 'info') {
    // 간단한 알림 구현 (실제로는 더 정교한 알림 시스템을 사용할 수 있음)
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'success' ? '#48bb78' : type === 'error' ? '#f56565' : '#4299e1'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 3000;
        font-weight: 600;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// 이벤트 편집/삭제 버튼 위임 처리
document.addEventListener('click', (e) => {
    const delBtn = e.target.closest('.btn-delete');
    const editBtn = e.target.closest('.btn-edit');
    if (delBtn) {
        const eventId = delBtn.getAttribute('data-id');
        const titleEl = delBtn.closest('.event-item')?.querySelector('.event-title');
        const title = titleEl ? titleEl.textContent : '';
        if (confirm(`"${title}" 일정을 삭제하시겠습니까?`)) {
            deleteEventById(eventId);
        }
        return;
    }
    if (editBtn) {
        const eventId = editBtn.getAttribute('data-id');
        const ev = events.find(e => String(e.id) === String(eventId));
        if (ev) {
            editEvent(ev);
        }
        return;
    }
});
