from RAG.parsing_with_criteria import parse_with_criteria
from RAG.parsing_with_content import parse_with_content
from openai import OpenAI
import os
import json
from dotenv import load_dotenv

load_dotenv()

class Agent:
    def __init__(self):
        self.tools = json.load(open("tools.json"))
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