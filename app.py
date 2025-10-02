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

@app.route('/api/sync/google', methods=['POST'])
def sync_google_calendar():
    """구글 캘린더 동기화"""
    try:
        from eventmanager import sync_with_google_calendar
        
        data = request.json or {}
        sync_direction = data.get('direction', 'both')  # 'to_google', 'from_google', 'both'
        
        result = sync_with_google_calendar(sync_direction=sync_direction)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': '구글 캘린더 동기화가 완료되었습니다.',
                'details': result['details']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
            
    except Exception as e:
        return jsonify({'error': f'구글 캘린더 동기화 중 오류가 발생했습니다: {str(e)}'}), 500

@app.route('/api/process/audio', methods=['POST'])
def process_audio():
    """음성 데이터 처리"""
    try:
        from multimedia_processor import MultimediaProcessor
        
        if 'audio' not in request.files:
            return jsonify({'error': '음성 파일이 제공되지 않았습니다.'}), 400
        
        audio_file = request.files['audio']
        audio_format = request.form.get('format', 'webm')
        
        processor = MultimediaProcessor()
        result = processor.process_audio(audio_file.read(), audio_format)
        
        if result['success']:
            return jsonify({
                'success': True,
                'transcript': result['transcript'],
                'formatted_message': processor.format_for_agent(result)
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
            
    except Exception as e:
        return jsonify({'error': f'음성 처리 중 오류가 발생했습니다: {str(e)}'}), 500

@app.route('/api/process/image', methods=['POST'])
def process_image():
    """이미지 데이터 처리"""
    try:
        from multimedia_processor import MultimediaProcessor
        
        if 'image' not in request.files:
            return jsonify({'error': '이미지 파일이 제공되지 않았습니다.'}), 400
        
        image_file = request.files['image']
        image_format = request.form.get('format', 'png')
        
        processor = MultimediaProcessor()
        result = processor.process_image(image_file.read(), image_format)
        
        if result['success']:
            return jsonify({
                'success': True,
                'analysis': result['analysis'],
                'formatted_message': processor.format_for_agent(result)
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
            
    except Exception as e:
        return jsonify({'error': f'이미지 처리 중 오류가 발생했습니다: {str(e)}'}), 500

@app.route('/api/process/mixed', methods=['POST'])
def process_mixed_content():
    """혼합 콘텐츠 처리 (텍스트 + 멀티미디어)"""
    try:
        from multimedia_processor import MultimediaProcessor
        
        data = request.form
        text = data.get('text', '')
        
        audio_data = None
        image_data = None
        
        if 'audio' in request.files:
            audio_data = request.files['audio'].read()
        
        if 'image' in request.files:
            image_data = request.files['image'].read()
        
        processor = MultimediaProcessor()
        result = processor.process_mixed_content(text, audio_data, image_data)
        
        if result['success']:
            return jsonify({
                'success': True,
                'formatted_message': result['final_message'],
                'processed_content': result['processed_content']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
            
    except Exception as e:
        return jsonify({'error': f'혼합 콘텐츠 처리 중 오류가 발생했습니다: {str(e)}'}), 500

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
