"""
ReAct Agent with tools.json 도구들
"""
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from RAG.parsing_with_criteria import parse_with_criteria
from RAG.parsing_with_content import parse_with_content, embed_event
from eventmanager import delete_event_in_user, update_event_in_user, add_event_in_user
import os
import json
from datetime import datetime

class ReactAgent:
    def __init__(self):
        """ReAct Agent 초기화"""
        # OpenAI 모델 초기화
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # 도구들 정의
        self.tools = self._create_tools()
        
        # 메모리 설정 (최근 10개 대화 기억)
        self.memory = ConversationBufferWindowMemory(
            k=10,
            memory_key="chat_history",
            return_messages=True
        )
        
        # ReAct 프롬프트 템플릿
        self.prompt = PromptTemplate(
            template="""You are a calendar assistant. Use tools only for calendar-related tasks.
default year is 2025
Available tools:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

RULES:
- For greetings or non-calendar questions: skip Action and go directly to Final Answer
- For calendar tasks: use appropriate tools from the list
- When no tool is needed: skip Action and go directly to Final Answer
- Always respond in Korean
- If you cannot find the information after 3 attempts, provide a helpful response and stop
- Do not repeat the same action multiple times

Examples:
- Greeting: "안녕하세요" → Thought: This is a greeting → Final Answer: 안녕하세요! 일정 관리에 도움이 필요하시면 말씀해 주세요.
- Calendar task: "오늘 일정 보여줘" → Thought: Need to search today's events → Action: parse_with_criteria → Action Input: {{"date": "2024-10-02"}}

Begin!

Question: {input}
Thought: {agent_scratchpad}""",
            input_variables=["input", "agent_scratchpad", "tools", "tool_names"]
        )
        
        # ReAct Agent 생성
        self.agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        # Agent Executor 생성
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10,
            max_execution_time=30
        )
        
        # Database 폴더의 모든 파일에 대해 embedding 필드 생성
        self._update_all_embeddings()

    def _create_tools(self):
        """tools.json의 도구들을 LangChain Tool로 변환"""
        tools = []
        
        # parse_with_criteria 도구
        def parse_with_criteria_wrapper(criteria_str):
            try:
                criteria = json.loads(criteria_str) if criteria_str else None
                result = parse_with_criteria(criteria=criteria)
                if result:
                    # embedding 필드가 없으면 생성
                    for event in result:
                        if 'embedding' not in event:
                            try:
                                event = embed_event(event)
                            except:
                                pass
                    return self._format_events(result)
                return "일정을 찾을 수 없습니다."
            except Exception as e:
                return f"검색 중 오류가 발생했습니다: {str(e)}"
        
        tools.append(Tool(
            name="parse_with_criteria",
            description="날짜, 요일, 시간, 타임윈도우 등 기준으로 이벤트를 필터링합니다. criteria는 JSON 문자열로 전달하세요.",
            func=parse_with_criteria_wrapper
        ))
        
        # parse_with_content 도구
        def parse_with_content_wrapper(query, criteria_str=None, k=10):
            try:
                criteria = json.loads(criteria_str) if criteria_str else None
                result = parse_with_content(query=query, criteria=criteria, k=k)
                if result:
                    # embedding 필드가 없으면 생성
                    for event in result:
                        if 'embedding' not in event:
                            try:
                                event = embed_event(event)
                            except:
                                pass
                    return self._format_events(result)
                return "일정을 찾을 수 없습니다."
            except Exception as e:
                return f"검색 중 오류가 발생했습니다: {str(e)}"
        
        tools.append(Tool(
            name="parse_with_content",
            description="텍스트 내용으로 이벤트를 검색합니다. query는 필수, criteria는 JSON 문자열로 전달하세요.",
            func=parse_with_content_wrapper
        ))
        
        # delete_event_in_user 도구
        def delete_event_wrapper(event_id):
            try:
                result = delete_event_in_user(event_id=int(event_id))
                if result:
                    return f"일정(ID: {event_id})이 성공적으로 삭제되었습니다. [CALENDAR_REFRESH]"
                else:
                    return f"일정(ID: {event_id})을 찾을 수 없어 삭제에 실패했습니다."
            except Exception as e:
                return f"삭제 중 오류가 발생했습니다: {str(e)}"
        
        tools.append(Tool(
            name="delete_event_in_user",
            description="ID로 이벤트를 삭제합니다.",
            func=delete_event_wrapper
        ))
        
        # update_event_in_user 도구
        def update_event_wrapper(event_id, updates_str):
            try:
                updates = json.loads(updates_str)
                result = update_event_in_user(event_id=int(event_id), event_data=updates)
                if result:
                    return f"일정(ID: {event_id})이 성공적으로 수정되었습니다. [CALENDAR_REFRESH]"
                else:
                    return f"일정(ID: {event_id})을 찾을 수 없어 수정에 실패했습니다."
            except Exception as e:
                return f"수정 중 오류가 발생했습니다: {str(e)}"
        
        tools.append(Tool(
            name="update_event_in_user",
            description="ID로 이벤트를 수정합니다. updates는 JSON 문자열로 전달하세요.",
            func=update_event_wrapper
        ))
        
        # add_event_in_user 도구
        def add_event_wrapper(event_data_str):
            try:
                event_data = json.loads(event_data_str)
                
                # 필수 필드 검증
                required_fields = ['title', 'date_start', 'date_finish']
                missing_fields = [field for field in required_fields if not event_data.get(field)]
                
                if missing_fields:
                    return f"필수 필드가 누락되었습니다: {', '.join(missing_fields)}. 제목, 시작 날짜, 종료 날짜를 모두 포함해 주세요."
                
                result = add_event_in_user(event_data=event_data)
                if result:
                    return f"새로운 일정 '{event_data.get('title')}'이 성공적으로 추가되었습니다. [CALENDAR_REFRESH]"
                else:
                    return f"일정 추가에 실패했습니다."
            except Exception as e:
                return f"추가 중 오류가 발생했습니다: {str(e)}"
        
        tools.append(Tool(
            name="add_event_in_user",
            description="새로운 이벤트를 추가합니다. event_data는 JSON 문자열로 전달하세요.",
            func=add_event_wrapper
        ))
        
        return tools

    def _format_events(self, events):
        """이벤트 목록을 ID와 함께 사용자 친화적인 형식으로 포맷합니다."""
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

    def __call__(self, query: str) -> str:
        """사용자 쿼리를 처리하고 응답을 반환합니다."""
        try:
            # Agent 실행
            result = self.agent_executor.invoke({
                "input": query
            })
            return result["output"]
        except Exception as e:
            return f"오류가 발생했습니다: {str(e)}"

    def clear_memory(self):
        """대화 메모리를 초기화합니다."""
        self.memory.clear()

    def get_memory(self):
        """현재 메모리 상태를 반환합니다."""
        return self.memory.chat_memory.messages

    def add_message_to_memory(self, message: str, is_user: bool = True):
        """메모리에 메시지를 수동으로 추가합니다."""
        if is_user:
            self.memory.chat_memory.add_user_message(message)
        else:
            self.memory.chat_memory.add_ai_message(message)
