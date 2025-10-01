from RAG.parsing_with_criteria import parse_with_criteria
from RAG.parsing_with_content import parse_with_content
from eventmanager import delete_event_in_user, update_event_in_user, add_event_in_user
from openai import OpenAI
import os
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class Agent:
    def __init__(self):
        self.tools = json.load(open("tools.json", encoding="utf-8"))
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def __call__(self, query: str):
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": query},
                {"role": "system", "content": f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
            ],
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
                    if result:
                        result = "".join([f"{k}: {v}\n" for k, v in result[0].items() if k != "embedding"])
                elif fn_name == "parse_with_content":
                    result = parse_with_content(**args)
                    if result:
                        result = "".join([f"{k}: {v}\n" for k, v in result[0].items() if k != "embedding"])
                elif fn_name == "delete_event_in_user":
                    result = delete_event_in_user(**args)
                elif fn_name == "update_event_in_user":
                    result = update_event_in_user(**args)
                elif fn_name == "add_event_in_user":
                    result = add_event_in_user(**args)
                else:
                    result = {"error": "Unknown function"}

                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })

            follow_up = self.client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "user", "content": "query"},
                    msg,
                    *tool_results
                ]
            )
            return(follow_up.choices[0].message.content)
        else:
            return(msg.content)

#agent = Agent()
#print(agent("set math midterm tomorrow."))