// 전역 변수
let currentDate = new Date();
let events = [];
let isModalOpen = false;
let isUploading = false; // 이미지 업로드 중복 방지

// DOM 요소들
const calendarGrid = document.getElementById('calendarGrid');
const currentMonthElement = document.getElementById('currentMonth');
const prevMonthBtn = document.getElementById('prevMonth');
const nextMonthBtn = document.getElementById('nextMonth');
const todayEventsElement = document.getElementById('todayEvents');
const chatbotMessages = document.getElementById('chatbotMessages');
const chatInput = document.getElementById('chatInput');
const sendButton = document.getElementById('sendButton');
const eventModal = document.getElementById('eventModal');
const eventForm = document.getElementById('eventForm');

// 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeCalendar();
    initializeChatbot();
    loadEvents();
    setupEventListeners();
});

// 캘린더 초기화
function initializeCalendar() {
    renderCalendar();
    updateTodayEvents();
}

// 챗봇 초기화
function initializeChatbot() {
    // 엔터키로 메시지 전송
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // 전송 버튼 클릭
    sendButton.addEventListener('click', sendMessage);
    
    // 이미지 업로드 이벤트 리스너
    document.getElementById('imageUpload').addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            addUserMessage(`📷 사진 업로드: ${file.name}`);
            uploadImageAndCreateEvent(file);
        }
    });
}

// 이벤트 리스너 설정
function setupEventListeners() {
    // 캘린더 네비게이션
    prevMonthBtn.addEventListener('click', function() {
        currentDate.setMonth(currentDate.getMonth() - 1);
        renderCalendar();
    });
    
    nextMonthBtn.addEventListener('click', function() {
        currentDate.setMonth(currentDate.getMonth() + 1);
        renderCalendar();
    });
    
    // 모달 관련
    document.getElementById('cancelEvent').addEventListener('click', closeModal);
    document.querySelector('.modal-close').addEventListener('click', closeModal);
    document.getElementById('saveEvent').addEventListener('click', saveEvent);
    
    // 모달 외부 클릭으로 닫기
    eventModal.addEventListener('click', function(e) {
        if (e.target === eventModal) {
            closeModal();
        }
    });
}

// 캘린더 렌더링
function renderCalendar() {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    
    // 월 표시 업데이트
    currentMonthElement.textContent = `${year}년 ${month + 1}월`;
    
    // 달의 첫 날과 마지막 날
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay());
    
    // 그리드 초기화
    calendarGrid.innerHTML = '';
    
    // 요일 헤더
    const dayNames = ['일', '월', '화', '수', '목', '금', '토'];
    dayNames.forEach(day => {
        const dayHeader = document.createElement('div');
        dayHeader.className = 'calendar-day-header';
        dayHeader.textContent = day;
        dayHeader.style.background = '#f8f9fa';
        dayHeader.style.fontWeight = 'bold';
        dayHeader.style.textAlign = 'center';
        dayHeader.style.padding = '10px';
        calendarGrid.appendChild(dayHeader);
    });
    
    // 날짜 셀들
    const today = new Date();
    for (let i = 0; i < 42; i++) {
        const cellDate = new Date(startDate);
        cellDate.setDate(startDate.getDate() + i);
        
        const dayElement = document.createElement('div');
        dayElement.className = 'calendar-day';
        dayElement.innerHTML = `
            <div class="day-number">${cellDate.getDate()}</div>
            <div class="day-events"></div>
        `;
        
        // 다른 달의 날짜 스타일링
        if (cellDate.getMonth() !== month) {
            dayElement.classList.add('other-month');
        }
        
        // 오늘 날짜 스타일링
        if (cellDate.toDateString() === today.toDateString()) {
            dayElement.classList.add('today');
        }
        
        // 해당 날짜의 이벤트 표시 (timeblock 형식)
        const dayEvents = getEventsForDate(cellDate);
        if (dayEvents.length > 0) {
            dayElement.classList.add('has-events');
            const eventsContainer = dayElement.querySelector('.day-events');
            eventsContainer.innerHTML = ''; // 기존 내용 초기화
            
                dayEvents.forEach(event => {
                    const eventBlock = document.createElement('div');
                    eventBlock.className = 'event-block';
                    eventBlock.textContent = event.title;
                    eventBlock.dataset.eventId = event.id; // 이벤트 ID 저장
                    
                    // Unix Timestamp 또는 ISO 형식 모두 지원
                    let startTime, endTime;
                    if (event.start_timestamp && event.end_timestamp) {
                        startTime = formatUnixTime(event.start_timestamp);
                        endTime = formatUnixTime(event.end_timestamp);
                    } else if (event.start && event.end && event.start.iso && event.end.iso) {
                        startTime = formatTime(event.start.iso);
                        endTime = formatTime(event.end.iso);
                    } else {
                        startTime = '시간 미정';
                        endTime = '시간 미정';
                    }
                    
                    eventBlock.title = `${event.title}\n${startTime} - ${endTime}`;
                    
                    // 우클릭 이벤트 추가
                    eventBlock.addEventListener('contextmenu', function(e) {
                        e.preventDefault();
                        showEventContextMenu(e, event.id, event.title);
                    });
                    
                    eventsContainer.appendChild(eventBlock);
                });
        }
        
        // 날짜 클릭 이벤트
        dayElement.addEventListener('click', function() {
            selectDate(cellDate);
        });
        
        calendarGrid.appendChild(dayElement);
    }
}

// 특정 날짜의 이벤트 가져오기 (Asia/Seoul 타임존 고려)
function getEventsForDate(date) {
    const dateStr = formatDate(date);
    return events.filter(event => {
        let eventDate;
        if (event.start_timestamp) {
            // Unix Timestamp를 Asia/Seoul 타임존으로 변환하여 날짜만 비교
            eventDate = new Date(event.start_timestamp * 1000);
            const eventDateStr = eventDate.toLocaleDateString('en-CA', {timeZone: 'Asia/Seoul'});
            const targetDateStr = date.toLocaleDateString('en-CA', {timeZone: 'Asia/Seoul'});
            return eventDateStr === targetDateStr;
        } else if (event.start && event.start.iso) {
            eventDate = new Date(event.start.iso);
            return formatDate(eventDate) === dateStr;
        } else {
            return false;
        }
    });
}

// 오늘의 일정 업데이트 (Asia/Seoul 타임존 고려)
function updateTodayEvents() {
    // Asia/Seoul 타임존의 오늘 날짜 사용
    const today = new Date();
    const seoulToday = new Date(today.toLocaleString("en-US", {timeZone: "Asia/Seoul"}));
    const todayEvents = getEventsForDate(seoulToday);
    
    todayEventsElement.innerHTML = '';
    
    if (todayEvents.length === 0) {
        todayEventsElement.innerHTML = '<p style="color: #999; font-style: italic;">오늘 예정된 일정이 없습니다.</p>';
        return;
    }
    
    todayEvents.forEach(event => {
        const eventElement = document.createElement('div');
        eventElement.className = 'event-item';
        
        // Unix Timestamp 또는 ISO 형식 모두 지원
        let startTime;
        if (event.start_timestamp) {
            startTime = formatUnixTime(event.start_timestamp);
        } else if (event.start && event.start.iso) {
            startTime = formatTime(event.start.iso);
        } else {
            startTime = '시간 미정';
        }
        
        eventElement.innerHTML = `
            <div class="event-time">${startTime}</div>
            <div class="event-title">${event.title}</div>
        `;
        todayEventsElement.appendChild(eventElement);
    });
}

// 날짜 선택
function selectDate(date) {
    // 날짜 선택 시 일정 등록 모달 열기
    openEventModal(date);
}

// 이벤트 모달 열기
function openEventModal(selectedDate = null) {
    isModalOpen = true;
    eventModal.classList.add('show');
    
    if (selectedDate) {
        document.getElementById('eventDate').value = formatDate(selectedDate);
    } else {
        document.getElementById('eventDate').value = formatDate(new Date());
    }
    
    // 폼 초기화
    eventForm.reset();
}

// 이벤트 모달 닫기
function closeModal() {
    isModalOpen = false;
    eventModal.classList.remove('show');
}

// 이벤트 저장
async function saveEvent() {
    const formData = {
        title: document.getElementById('eventTitle').value,
        date: document.getElementById('eventDate').value,
        startTime: document.getElementById('eventStartTime').value,
        endTime: document.getElementById('eventEndTime').value,
        location: document.getElementById('eventLocation').value,
        attendees: document.getElementById('eventAttendees').value,
        notes: document.getElementById('eventNotes').value
    };
    
    if (!formData.title || !formData.date || !formData.startTime || !formData.endTime) {
        alert('필수 항목을 모두 입력해주세요.');
        return;
    }
    
    try {
        // 자연어로 변환하여 API 호출
        const naturalLanguage = `${formData.title}을 ${formData.date} ${formData.startTime}부터 ${formData.endTime}까지 ${formData.location ? formData.location + '에서 ' : ''}${formData.attendees ? formData.attendees + '와 함께 ' : ''}일정 등록해줘`;
        
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(naturalLanguage)
        });
        
        const result = await response.json();
        
        if (result.status === 'created') {
            addBotMessage('일정이 성공적으로 등록되었습니다!');
            closeModal();
            loadEvents(); // 이벤트 목록 새로고침
        } else {
            addBotMessage('일정 등록 중 오류가 발생했습니다.');
        }
    } catch (error) {
        console.error('Error:', error);
        addBotMessage('일정 등록 중 오류가 발생했습니다.');
    }
}

// 메시지 전송
async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;
    
    // 사용자 메시지 표시
    addUserMessage(message);
    chatInput.value = '';
    
    // 로딩 표시
    const loadingMessage = addBotMessage('🤖 자연어를 분석하고 일정을 등록하는 중...', true);
    
    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({user_input: message})
        });
        
        const result = await response.json();
        
        // 로딩 메시지 제거
        loadingMessage.remove();
        
        // 응답 표시
        if (result.status === 'created') {
            addBotMessage(result.message || '일정이 성공적으로 등록되었습니다!');
            // 캘린더와 오늘의 일정 업데이트
            loadEvents();
            updateTodayEvents();
        } else if (result.status === 'found') {
            if (result.events && result.events.length > 0) {
                let responseText = '🔍 검색된 일정:\n\n';
                result.events.forEach((event, index) => {
                    let startTime = '시간 미정';
                    if (event.start_timestamp) {
                        startTime = formatUnixTime(event.start_timestamp);
                    } else if (event.start && event.start.iso) {
                        startTime = formatTime(event.start.iso);
                    }
                    responseText += `${index + 1}. ${event.title || event.summary}\n   🕐 ${startTime}\n   📍 ${event.location || '장소 미정'}\n\n`;
                });
                addBotMessage(responseText);
            } else {
                addBotMessage('검색된 일정이 없습니다.');
            }
        } else if (result.status === 'chat') {
            addBotMessage(result.message);
        } else if (result.status === 'error') {
            addBotMessage(`❌ ${result.message}`);
        } else {
            addBotMessage(result.message || '처리되었습니다.');
        }
    } catch (error) {
        loadingMessage.remove();
        console.error('Error:', error);
        addBotMessage('죄송합니다. 오류가 발생했습니다. 다시 시도해주세요.');
    }
}

// RAG 검색
async function performRAGSearch(query) {
    try {
        const response = await fetch(`/rag_search?query=${encodeURIComponent(query)}`);
        const result = await response.json();
        
        if (result.results && result.results.length > 0) {
            let responseText = `RAG 검색 결과 (${result.results.length}개):\n\n`;
            result.results.forEach((event, index) => {
                responseText += `${index + 1}. ${event.title || event.summary || '제목 없음'}\n`;
                if (event.start && event.start.iso) {
                    const eventDate = new Date(event.start.iso);
                    responseText += `   📅 ${eventDate.toLocaleDateString('ko-KR')} ${eventDate.toLocaleTimeString('ko-KR', {hour: '2-digit', minute: '2-digit'})}\n`;
                }
                if (event.location) {
                    responseText += `   📍 ${event.location}\n`;
                }
                if (event.attendees && event.attendees.length > 0) {
                    responseText += `   👥 참석자: ${event.attendees.join(', ')}\n`;
                }
                if (event.members && event.members.length > 0) {
                    responseText += `   👥 참석자: ${event.members.join(', ')}\n`;
                }
                if (event.notes) {
                    responseText += `   📝 ${event.notes}\n`;
                }
                responseText += '\n';
            });
            addBotMessage(responseText);
        } else {
            addBotMessage('RAG 검색 결과가 없습니다.');
        }
    } catch (error) {
        console.error('RAG Search Error:', error);
        addBotMessage('RAG 검색 중 오류가 발생했습니다.');
    }
}

// 빠른 액션 처리 (제거됨 - 자연어 입력으로 통합)

// 사용자 메시지 추가
function addUserMessage(message) {
    const messageElement = document.createElement('div');
    messageElement.className = 'message user-message';
    messageElement.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-user"></i>
        </div>
        <div class="message-content">${message}</div>
    `;
    chatbotMessages.appendChild(messageElement);
    scrollToBottom();
}

// 봇 메시지 추가
function addBotMessage(message, isLoading = false) {
    const messageElement = document.createElement('div');
    messageElement.className = 'message bot-message';
    
    if (isLoading) {
        messageElement.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="loading-text">${message}</div>
                <div class="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
    } else {
        messageElement.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">${message.replace(/\n/g, '<br>')}</div>
        `;
    }
    
    chatbotMessages.appendChild(messageElement);
    scrollToBottom();
    return messageElement;
}

// 스크롤을 맨 아래로
function scrollToBottom() {
    chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
}

// 이벤트 로드 (서버에서)
async function loadEvents() {
    try {
        const response = await fetch('/events');
        const data = await response.json();
        events = data.events || [];
        
        // 로컬 스토리지에도 백업
        localStorage.setItem('calendarEvents', JSON.stringify(events));
        
        renderCalendar();
        updateTodayEvents();
    } catch (error) {
        console.error('이벤트 로드 실패:', error);
        // 로컬 스토리지에서 폴백
        const savedEvents = localStorage.getItem('calendarEvents');
        if (savedEvents) {
            events = JSON.parse(savedEvents);
            renderCalendar();
            updateTodayEvents();
        }
    }
}

// 이벤트 저장 (로컬 스토리지에)
function saveEvents() {
    localStorage.setItem('calendarEvents', JSON.stringify(events));
}

// 이미지 업로드 및 OCR 일정 등록
async function uploadImageAndCreateEvent(file) {
    // 중복 업로드 방지
    if (isUploading) {
        addBotMessage('이미 사진을 처리 중입니다. 잠시만 기다려주세요.');
        return;
    }
    
    isUploading = true;
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/upload_image', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            // Unix Timestamp 또는 ISO 형식 모두 지원
            let timeDisplay;
            if (result.event.start_timestamp) {
                timeDisplay = formatUnixTimestamp(result.event.start_timestamp);
            } else if (result.event.start && result.event.start.iso) {
                timeDisplay = new Date(result.event.start.iso).toLocaleString('ko-KR');
            } else {
                timeDisplay = '시간 미정';
            }
            
            addBotMessage(`📷 사진에서 일정을 성공적으로 추출했습니다!\n\n제목: ${result.event.title}\n시간: ${timeDisplay}\n장소: ${result.event.location || '없음'}`);
            loadEvents(); // 이벤트 목록 새로고침
            updateTodayEvents(); // 오늘의 일정 업데이트
        } else {
            // 상세한 에러 메시지 표시
            addBotMessage(`❌ 사진 처리 실패: ${result.message}`);
        }
    } catch (error) {
        console.error('사진 업로드 오류:', error);
        // 네트워크 오류나 기타 예외 상황
        addBotMessage(`❌ 사진 업로드 중 오류가 발생했습니다: ${error.message}`);
    } finally {
        isUploading = false;
    }
}

// 유틸리티 함수들
function formatDate(date) {
    return date.toISOString().split('T')[0];
}

function formatTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString('ko-KR', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false 
    });
}

// Unix Timestamp를 사람이 읽기 좋은 형식으로 변환 (Asia/Seoul 타임존)
function formatUnixTimestamp(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString('ko-KR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
        timeZone: 'Asia/Seoul'
    });
}

// Unix Timestamp를 간단한 시간 형식으로 변환 (Asia/Seoul 타임존)
function formatUnixTime(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString('ko-KR', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: true,
        timeZone: 'Asia/Seoul'
    });
}

// 컨텍스트 메뉴 표시
function showEventContextMenu(event, eventId, eventTitle) {
    // 기존 컨텍스트 메뉴 제거
    const existingMenu = document.getElementById('eventContextMenu');
    if (existingMenu) {
        existingMenu.remove();
    }
    
    // 컨텍스트 메뉴 생성
    const contextMenu = document.createElement('div');
    contextMenu.id = 'eventContextMenu';
    contextMenu.style.cssText = `
        position: fixed;
        top: ${event.clientY}px;
        left: ${event.clientX}px;
        background: #2a2a2a;
        border: 1px solid #444;
        border-radius: 6px;
        padding: 8px 0;
        z-index: 1000;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        min-width: 120px;
    `;
    
    // 삭제 버튼 추가
    const deleteButton = document.createElement('div');
    deleteButton.textContent = '삭제';
    deleteButton.style.cssText = `
        padding: 8px 16px;
        color: #ff6b6b;
        cursor: pointer;
        transition: background 0.2s;
    `;
    deleteButton.addEventListener('mouseenter', function() {
        this.style.background = '#444';
    });
    deleteButton.addEventListener('mouseleave', function() {
        this.style.background = 'transparent';
    });
    deleteButton.addEventListener('click', function() {
        deleteEvent(eventId, eventTitle);
        contextMenu.remove();
    });
    
    contextMenu.appendChild(deleteButton);
    document.body.appendChild(contextMenu);
    
    // 다른 곳 클릭 시 메뉴 닫기
    const closeMenu = (e) => {
        if (!contextMenu.contains(e.target)) {
            contextMenu.remove();
            document.removeEventListener('click', closeMenu);
        }
    };
    
    setTimeout(() => {
        document.addEventListener('click', closeMenu);
    }, 100);
}

// 일정 삭제
async function deleteEvent(eventId, eventTitle) {
    if (!confirm(`"${eventTitle}" 일정을 삭제하시겠습니까?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/delete_event/${eventId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            addBotMessage(`✅ "${eventTitle}" 일정이 삭제되었습니다.`);
            loadEvents(); // 이벤트 목록 새로고침
            renderCalendar(); // 캘린더 다시 렌더링
            updateTodayEvents(); // 오늘의 일정 업데이트
        } else {
            addBotMessage(`❌ 일정 삭제 중 오류가 발생했습니다: ${result.message || '알 수 없는 오류'}`);
        }
    } catch (error) {
        console.error('일정 삭제 오류:', error);
        addBotMessage(`❌ 일정 삭제 중 오류가 발생했습니다: ${error.message}`);
    }
}

// 페이지 로드 시 초기화
window.addEventListener('load', function() {
    // 오늘 날짜로 캘린더 초기화
    currentDate = new Date();
    renderCalendar();
    loadEvents();
    updateTodayEvents();
    
    // 이벤트 리스너 등록
    document.getElementById('prevMonth').addEventListener('click', function() {
        currentDate.setMonth(currentDate.getMonth() - 1);
        renderCalendar();
    });
    
    document.getElementById('nextMonth').addEventListener('click', function() {
        currentDate.setMonth(currentDate.getMonth() + 1);
        renderCalendar();
    });
    
    document.getElementById('sendButton').addEventListener('click', sendMessage);
    document.getElementById('chatInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    // 카메라 버튼 (이미지 업로드)
    document.getElementById('cameraButton').addEventListener('click', function() {
        document.getElementById('imageUpload').click();
    });
    
    // 이미지 업로드
    document.getElementById('imageUpload').addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            uploadImageAndCreateEvent(e.target.files[0]);
        }
    });
    
    // 모달 이벤트
    document.getElementById('cancelEvent').addEventListener('click', closeEventModal);
    document.querySelector('.modal-close').addEventListener('click', closeEventModal);
    document.getElementById('saveEvent').addEventListener('click', saveEvent);
    
    // 모달 외부 클릭 시 닫기
    document.getElementById('eventModal').addEventListener('click', function(e) {
        if (e.target === this) {
            closeEventModal();
        }
    });
    
});
