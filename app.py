from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime, timedelta
from react_agent import ReactAgent
from eventmanager import delete_event_in_user, update_event_in_user, add_event_in_user

app = Flask(__name__)
CORS(app)

# ReAct AI 에이전트 초기화
agent = ReactAgent()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/events')
def get_events():
    """모든 이벤트 조회"""
    try:
        events = []
        user_dir = "Database/[user]"
        if os.path.exists(user_dir):
            for filename in os.listdir(user_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(user_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        event = json.load(f)
                        # embedding 필드 제거 (AI 검색용이므로 프론트엔드에서는 숨김)
                        # embedding 필드 제거 (AI 검색용이므로 프론트엔드에서는 숨김)
                        if 'embedding' in event:
                            del event['embedding']
                        events.append(event)
        return jsonify(events)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/events/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    """이벤트 삭제"""
    try:
        success = delete_event_in_user(event_id)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/events/<int:event_id>', methods=['PUT'])
def update_event(event_id):
    """이벤트 수정"""
    try:
        updates = request.json
        success = update_event_in_user(event_id, updates, recompute_embedding=False)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/events', methods=['POST'])
def create_event():
    """이벤트 생성"""
    try:
        event_data = request.json
        new_id = add_event_in_user(event_data, recompute_embedding=False)
        return jsonify({'success': True, 'id': new_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """AI 채팅"""
    try:
        user_message = request.json.get('message', '')
        if not user_message:
            return jsonify({'error': '메시지가 비어있습니다.'}), 400
        
        response = agent(user_message)
        return jsonify({'response': response})
    except Exception as e:
        print(f"Chat error: {str(e)}")  # 디버깅용
        return jsonify({'error': f'채팅 처리 중 오류가 발생했습니다: {str(e)}'}), 500

@app.route('/api/chat/clear', methods=['POST'])
def clear_chat():
    """채팅 메모리 초기화"""
    try:
        agent.clear_memory()
        return jsonify({'success': True, 'message': '채팅 기록이 초기화되었습니다.'})
    except Exception as e:
        return jsonify({'error': f'메모리 초기화 중 오류가 발생했습니다: {str(e)}'}), 500

@app.route('/api/chat/history', methods=['GET'])
def get_chat_history():
    """채팅 기록 조회"""
    try:
        history = agent.get_memory()
        return jsonify({'history': history})
    except Exception as e:
        return jsonify({'error': f'채팅 기록 조회 중 오류가 발생했습니다: {str(e)}'}), 500

@app.route('/api/events/week/<int:year>/<int:week>')
def get_week_events(year, week):
    """특정 주의 이벤트 조회"""
    try:
        # 주의 시작일 계산
        jan_1 = datetime(year, 1, 1)
        week_start = jan_1 + timedelta(weeks=week-1)
        
        events = []
        user_dir = "Database/[user]"
        if os.path.exists(user_dir):
            for filename in os.listdir(user_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(user_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        event = json.load(f)
                        # embedding 필드 제거 (AI 검색용이므로 프론트엔드에서는 숨김)
                        if 'embedding' in event:
                            del event['embedding']
                        
                        # 날짜 확인
                        if 'date_start' in event and event['date_start']:
                            try:
                                event_date = datetime.fromisoformat(event['date_start'].replace('Z', '+00:00'))
                                if week_start <= event_date < week_start + timedelta(weeks=1):
                                    events.append(event)
                            except:
                                continue
        
        return jsonify(events)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
