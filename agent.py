from RAG.parsing_with_criteria import parse_with_criteria
from RAG.parsing_with_content import parse_with_content, embed_event
from eventmanager import delete_event_in_user, update_event_in_user, add_event_in_user
from openai import OpenAI
import os
import json
import uuid
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class Agent:
    def __init__(self):
        self.tools = json.load(open("tools.json", encoding="utf-8"))
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.plans = {}  # 계획 저장소
        self.history = []  # 대화 히스토리 (system/user/assistant/tool 메시지 누적)
        
        # Database 폴더의 모든 파일에 대해 embedding 필드 생성
        self._update_all_embeddings()

    def _update_all_embeddings(self, user_dir="Database/[user]"):
        """Database 폴더의 모든 JSON 파일에 대해 embedding 필드를 생성합니다."""
        
        if not os.path.exists(user_dir):
            print(f"❌ {user_dir} 폴더가 존재하지 않습니다.")
            return
        
        # 모든 JSON 파일 확인
        json_files = [f for f in os.listdir(user_dir) if f.endswith('.json')]
        print(f"📁 {len(json_files)}개의 JSON 파일을 확인합니다...")
        
        updated_files = []
        error_files = []
        
        for filename in json_files:
            filepath = os.path.join(user_dir, filename)
            
            try:
                # JSON 파일 읽기
                with open(filepath, 'r', encoding='utf-8') as f:
                    event = json.load(f)
                
                # embedding 필드가 있는지 확인
                if 'embedding' not in event or not event['embedding']:
                    print(f"🔄 {filename}: embedding 생성 중...")
                    
                    # 임베딩 생성
                    try:
                        event_with_embedding = embed_event(event)
                        
                        # 파일에 저장
                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump(event_with_embedding, f, ensure_ascii=False, indent=2)
                        
                        updated_files.append(filename)
                        print(f"✅ {filename}: embedding 생성 완료")
                        
                    except Exception as e:
                        print(f"❌ {filename}: embedding 생성 실패 - {str(e)}")
                        error_files.append((filename, str(e)))
                else:
                    print(f"✓ {filename}: embedding 이미 존재")
                    
            except Exception as e:
                print(f"❌ {filename}: 파일 읽기/쓰기 오류 - {str(e)}")
                error_files.append((filename, str(e)))
        
        # 결과 요약
        if updated_files or error_files:
            print("\n" + "="*50)
            print("📊 Database Embedding 업데이트 결과")
            print("="*50)
            print(f"✅ 성공적으로 업데이트된 파일: {len(updated_files)}개")
            if updated_files:
                for filename in updated_files:
                    print(f"   - {filename}")
            
            print(f"❌ 오류가 발생한 파일: {len(error_files)}개")
            if error_files:
                for filename, error in error_files:
                    print(f"   - {filename}: {error}")
            
            print(f"📁 총 처리된 파일: {len(json_files)}개")

    def __call__(self, query: str):
        # 시스템 프롬프트
        sys_msg = {
            "role": "system",
            "content": (
                f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                "You are an intelligent calendar assistant. You MUST use tools to perform actions - never just describe what you will do.\n\n"
                "When user asks to delete events:\n"
                "1. ALWAYS use parse_with_content or parse_with_criteria to find the events first\n"
                "2. ALWAYS use delete_event_in_user with the found event IDs\n"
                "3. Report the actual results\n\n"
                "When user asks to update events:\n"
                "1. ALWAYS find the events first using search tools\n"
                "2. ALWAYS use update_event_in_user with the found event ID\n"
                "3. Report the actual results\n\n"
                "For complex tasks, use create_plan to break down the work, then execute_plan to run each step.\n\n"
                "Remember: Actions require tool calls. Never just say you will do something - actually do it with tools."
            ),
        }

        # 최근 히스토리 10개로 제한
        trimmed_history = self.history[-10:]
        messages = [sys_msg, *trimmed_history, {"role": "user", "content": query}]

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=self.tools,
            tool_choice="auto",
        )

        msg = response.choices[0].message
        if msg.tool_calls:
            tool_results = []
            for tool_call in msg.tool_calls:
                fn_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                if fn_name == "create_plan":
                    result = self._create_plan(args)
                elif fn_name == "execute_plan":
                    result = self._execute_plan(args)
                elif fn_name == "parse_with_criteria":
                    result = parse_with_criteria(**args)
                    if result:
                        result = "".join([f"{k}: {v}\n" for k, v in result[0].items() if k != "embedding"])
                elif fn_name == "parse_with_content":
                    result = parse_with_content(**args)
                    if result:
                        result = "".join([f"{k}: {v}\n" for k, v in result[0].items() if k != "embedding"])
                elif fn_name == "delete_event_in_user":
                    result = delete_event_in_user(**args)
                    if result:
                        result = f"일정(ID: {args.get('event_id')})이 성공적으로 삭제되었습니다."
                    else:
                        result = f"일정(ID: {args.get('event_id')})을 찾을 수 없어 삭제에 실패했습니다."
                elif fn_name == "update_event_in_user":
                    result = update_event_in_user(**args)
                elif fn_name == "add_event_in_user":
                    result = add_event_in_user(**args)
                else:
                    result = {"error": "Unknown function"}

                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

            # 히스토리에 이번 턴의 assistant(도구 호출 지시)와 tool 결과를 반영하여 후속 응답 유도
            follow_messages = [
                sys_msg,
                *trimmed_history,
                {"role": "user", "content": query},
                msg,
                *tool_results,
            ]
            follow_up = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=follow_messages,
            )
            content = follow_up.choices[0].message.content
            
            # 히스토리 업데이트
            self.history.append({"role": "user", "content": query})
            self.history.append({"role": "assistant", "content": content})
            return content
        else:
            content = msg.content
            # 히스토리 업데이트
            self.history.append({"role": "user", "content": query})
            self.history.append({"role": "assistant", "content": content})
            return content

    def _create_plan(self, args):
        """계획을 생성하고 저장합니다."""
        plan_id = str(uuid.uuid4())
        goal = args.get("goal", "")
        steps = args.get("steps", [])
        
        self.plans[plan_id] = {
            "goal": goal,
            "steps": steps,
            "current_step": 0,
            "results": []
        }
        
        return {
            "plan_id": plan_id,
            "message": f"계획이 생성되었습니다. 목표: {goal}",
            "total_steps": len(steps)
        }

    def _execute_plan(self, args):
        """계획을 실행합니다."""
        plan_id = args.get("plan_id")
        current_step = args.get("current_step", 0)
        
        if plan_id not in self.plans:
            return {"error": "계획을 찾을 수 없습니다."}
        
        plan = self.plans[plan_id]
        steps = plan["steps"]
        
        if current_step >= len(steps):
            return {"message": "모든 단계가 완료되었습니다.", "completed": True}
        
        step = steps[current_step]
        function_name = step["function_name"]
        parameters = step["parameters"]
        
        try:
            # 함수 실행
            if function_name == "parse_with_criteria":
                result = parse_with_criteria(**parameters)
                if result:
                    # embedding 필드가 없으면 생성
                    for event in result:
                        if 'embedding' not in event:
                            try:
                                event = embed_event(event)
                            except:
                                pass  # embedding 생성 실패해도 계속 진행
                    result = self._format_events(result)
            elif function_name == "parse_with_content":
                result = parse_with_content(**parameters)
                if result:
                    # embedding 필드가 없으면 생성
                    for event in result:
                        if 'embedding' not in event:
                            try:
                                event = embed_event(event)
                            except:
                                pass  # embedding 생성 실패해도 계속 진행
                    result = self._format_events(result)
            elif function_name == "delete_event_in_user":
                result = delete_event_in_user(**parameters)
            elif function_name == "update_event_in_user":
                result = update_event_in_user(**parameters)
            elif function_name == "add_event_in_user":
                result = add_event_in_user(**parameters)
            else:
                result = {"error": f"Unknown function: {function_name}"}
            
            # 결과 저장
            plan["results"].append({
                "step": current_step,
                "action": step["action"],
                "result": result
            })
            plan["current_step"] = current_step + 1
            
            return {
                "step": current_step,
                "action": step["action"],
                "result": result,
                "next_step": current_step + 1,
                "total_steps": len(steps)
            }
            
        except Exception as e:
            return {"error": f"단계 {current_step} 실행 중 오류: {str(e)}"}

    def _format_events(self, events):
        """이벤트 목록을 사용자 친화적인 형식으로 포맷합니다."""
        if not events:
            return "일정을 찾을 수 없습니다."
        
        formatted = []
        for i, event in enumerate(events, 1):
            event_info = []
            if event.get('title'):
                event_info.append(f"제목: {event['title']}")
            if event.get('date_start'):
                try:
                    start_time = datetime.fromisoformat(event['date_start'].replace('Z', '+00:00'))
                    event_info.append(f"시작: {start_time.strftime('%Y-%m-%d %H:%M')}")
                except:
                    event_info.append(f"시작: {event['date_start']}")
            if event.get('date_finish'):
                try:
                    end_time = datetime.fromisoformat(event['date_finish'].replace('Z', '+00:00'))
                    event_info.append(f"종료: {end_time.strftime('%Y-%m-%d %H:%M')}")
                except:
                    event_info.append(f"종료: {event['date_finish']}")
            if event.get('location'):
                event_info.append(f"장소: {event['location']}")
            if event.get('description'):
                event_info.append(f"설명: {event['description']}")
            if event.get('member'):
                if isinstance(event['member'], list):
                    event_info.append(f"참석자: {', '.join(event['member'])}")
                else:
                    event_info.append(f"참석자: {event['member']}")
            
            formatted.append(f"{i}. {' | '.join(event_info)}")
        
        return "\n".join(formatted)

    def _format_events_with_ids(self, events):
        """이벤트 목록을 ID와 함께 포맷합니다 (삭제/수정용)."""
        if not events:
            return "일정을 찾을 수 없습니다."
        
        formatted = []
        for i, event in enumerate(events, 1):
            event_info = []
            # ID를 맨 앞에 표시
            event_info.append(f"ID: {event.get('id', 'N/A')}")
            if event.get('title'):
                event_info.append(f"제목: {event['title']}")
            if event.get('date_start'):
                try:
                    start_time = datetime.fromisoformat(event['date_start'].replace('Z', '+00:00'))
                    event_info.append(f"시작: {start_time.strftime('%Y-%m-%d %H:%M')}")
                except:
                    event_info.append(f"시작: {event['date_start']}")
            if event.get('date_finish'):
                try:
                    end_time = datetime.fromisoformat(event['date_finish'].replace('Z', '+00:00'))
                    event_info.append(f"종료: {end_time.strftime('%Y-%m-%d %H:%M')}")
                except:
                    event_info.append(f"종료: {event['date_finish']}")
            if event.get('location'):
                event_info.append(f"장소: {event['location']}")
            if event.get('description'):
                event_info.append(f"설명: {event['description']}")
            if event.get('member'):
                if isinstance(event['member'], list):
                    event_info.append(f"참석자: {', '.join(event['member'])}")
                else:
                    event_info.append(f"참석자: {event['member']}")
            
            formatted.append(f"{i}. {' | '.join(event_info)}")
        
        return "\n".join(formatted)

    def _execute_tool_calls_recursively(self, tool_calls, max_depth=5, current_depth=0):
        """도구 호출을 재귀적으로 실행하여 연쇄 작업을 자동화합니다."""
        if current_depth >= max_depth:
            return [], "최대 실행 깊수에 도달했습니다."
        
        results = []
        for tool_call in tool_calls:
            fn_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            if fn_name == "create_plan":
                result = self._create_plan(args)
            elif fn_name == "execute_plan":
                result = self._execute_plan(args)
            elif fn_name == "parse_with_criteria":
                result = parse_with_criteria(**args)
                if result:
                    result = self._format_events_with_ids(result)
            elif fn_name == "parse_with_content":
                result = parse_with_content(**args)
                if result:
                    result = self._format_events_with_ids(result)
            elif fn_name == "delete_event_in_user":
                result = delete_event_in_user(**args)
                if result:
                    result = f"일정(ID: {args.get('event_id')})이 성공적으로 삭제되었습니다."
                else:
                    result = f"일정(ID: {args.get('event_id')})을 찾을 수 없어 삭제에 실패했습니다."
            elif fn_name == "update_event_in_user":
                result = update_event_in_user(**args)
            elif fn_name == "add_event_in_user":
                result = add_event_in_user(**args)
            else:
                result = {"error": "Unknown function"}
            
            results.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False)
            })
        
        return results, None
