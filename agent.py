from RAG.parsing_with_criteria import parse_with_criteria
from RAG.parsing_with_content import parse_with_content
from openai import OpenAI
import os
import json
from dotenv import load_dotenv

load_dotenv()

class Agent:
    def __init__(self):
        self.tools = [{
            "type": "function",
            "function": {
                "name": "parse_with_criteria",
                "description": "날짜, 요일, 시간, 타임윈도우 등 기준으로 이벤트를 필터링합니다",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "criteria": {
                            "type": "object",
                            "description": "이벤트 필터링 기준",
                            "properties": {
                                "date": {
                                    "type": "string",
                                    "description": "특정 날짜의 이벤트만 포함 (YYYY-MM-DD 형식)",
                                    "example": "2025-09-15"
                                },
                                "weekday": {
                                    "type": "integer",
                                    "description": "요일 기준 필터 (0=월요일, 1=화요일, ..., 6=일요일)",
                                    "minimum": 0,
                                    "maximum": 6,
                                    "example": 4
                                },
                                "hour": {
                                    "type": "string",
                                    "description": "시작 시각 기준 필터 (HH 또는 HH:MM 형식)",
                                    "example": "14:00"
                                },
                                "time_window_hours": {
                                    "type": "number",
                                    "description": "기준 시간으로부터 ±N시간 범위의 이벤트만 포함",
                                    "example": 48
                                },
                                "reference_time": {
                                    "type": "string",
                                    "description": "time_window_hours나 nearest_n의 기준 시간 (ISO 8601 형식)",
                                    "example": "2025-09-15T12:00:00+09:00"
                                },
                                "nearest_n": {
                                    "type": "integer",
                                    "description": "기준 시간에 가장 가까운 N개의 이벤트만 포함",
                                    "minimum": 1,
                                    "example": 5
                                },
                                "sort_by": {
                                    "type": "string",
                                    "description": "정렬 방식",
                                    "enum": ["nearest", "start"],
                                    "example": "nearest"
                                }
                            },
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "parse_with_content",
                "description": "텍스트 내용으로 이벤트를 검색합니다. 제목, 설명, 장소, 멤버 필드를 통합하여 유사도 검색을 수행합니다",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "검색할 텍스트 쿼리",
                            "example": "회의"
                            
                        },
                        "criteria": {
                            "type": "object",
                            "description": "검색 전에 적용할 필터링 기준 (parse_with_criteria와 동일한 구조)",
                            "properties": {
                                "date": {"type": "string", "description": "특정 날짜 (YYYY-MM-DD)"},
                                "weekday": {"type": "integer", "description": "요일 (0-6)"},
                                "hour": {"type": "string", "description": "시작 시각 (HH:MM)"},
                                "time_window_hours": {"type": "number", "description": "시간 윈도우 (시간)"},
                                "reference_time": {"type": "string", "description": "기준 시간 (ISO 8601)"},
                                "nearest_n": {"type": "integer", "description": "가장 가까운 N개"},
                                "sort_by": {"type": "string", "enum": ["nearest", "start"], "description": "정렬 방식"}
                            },
                            "required": ["query"]
                        },
                        "k": {
                            "type": "integer",
                            "description": "반환할 최대 결과 수",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50
                        }
                    },
                    "required": ["query"]
                }
            }
        }]
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def __call__(self, query: str):
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": query}],
            tools=self.tools,
            tool_choice="auto",
        )

        msg = response.choices[0].message
        if msg.tool_calls:
            tool_results = []
            for tool_call in msg.tool_calls:
                fn_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                if fn_name == "parse_with_criteria":
                    result = parse_with_criteria(**args)
                elif fn_name == "parse_with_content":
                    result = parse_with_content(**args)
                else:
                    result = {"error": "Unknown function"}

                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })

            follow_up = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": "query"},
                    msg,
                    *tool_results
                ]
            )
            return(follow_up.choices[0].message.content)
        else:
            return(msg.content)

agent = Agent()
print(agent("수요일 일정 알려줘."))