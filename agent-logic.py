# def chat_with_questions_api(user_message, client):
#     """Have a conversation with GPT-4o that can call your Questions API"""
#
#     messages = [
#         {
#             "role": "system",
#             "content": """You are an AI assistant that can interact with a Q&A REST API for managing questions.
#             You can create, read, and update questions. When users ask you to perform operations on questions,
#             use the available functions to interact with the API. Ask for clarification if not enough information is available.
#
#             Note: This system doesn't support DELETE operations for questions because in distributed systems,
#             deletes are typically avoided to maintain data consistency and audit trails."""
#         },
#         {"role": "user", "content": user_message}
#     ]
#
#     logger.info(f"User: {user_message}")
#
#     response = openai.chat.completions.create(
#         model="gpt-4o",
#         messages=messages,
#         tools=QUESTION_FUNCTIONS,
#         tool_choice="auto"
#     )
#
#     message = response.choices[0].message
#     messages.append(message)
#
#     if message.tool_calls:
#         logger.info("\nGPT-4o is calling functions...")
#
#         for tool_call in message.tool_calls:
#             function_name = tool_call.function.name
#             arguments = json.loads(tool_call.function.arguments)
#
#             logger.info(f"Function: {function_name}")
#             logger.info(f"Arguments: {json.dumps(arguments, indent=2)}")
#
#             function_result = execute_function(function_name, arguments, client)
#             logger.info(f"API Response: {function_result}")
#
#             messages.append({
#                 "role": "tool",
#                 "tool_call_id": tool_call.id,
#                 "content": function_result
#             })
#
#         final_response = openai.chat.completions.create(
#             model="gpt-4o",
#             messages=messages
#         )
#
#         logger.info(f"\nGPT-4o: {final_response.choices[0].message.content}")
#     else:
#         logger.info(f"\nGPT-4o: {message.content}")
import datetime
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.graph import StateGraph, START, END


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

    issue_id: str
    repo_context: str

    issue_title: str
    issue_text: str
    is_open: bool
    issue_opened: str
    issue_closed: str
    issue_type: str

    similar_issues: list[{str, str}]
    history: str
    related_code: str

    final_message: str


async def init_with_context(state):
    context = get_context(state["issue_id"])
    return {"repo_context": context,
            "messages": [
                ("system", """You are an AI assistant that can interact with issues raised in a public GitHub repository.
                You can read issues and the repository code. When users give you an issue by id, use the available
                functions to produce a triage report on this issue."""),
                ("user", state["issue_id"]),
                ("tool", context)
            ]}


async def basic_info(state):
    info = get_basic_info(state["issue_id"])
    info["messages"] = ("tool", f"{info}")
    return info


async def issue_type(state):
    return {"issue_type": decide_issue_type(state)}


async def similar_issues(state):
    return {"similar_issues": get_similar_issues(state)}


async def related_code(state):
    return {"related_code": get_related_code(state)}


async def history(state):
    return {"history": get_history(state)}


def compile_final_message(state):
    return {"final_message": ""}


def history_cond(state):
    if state["is_open"] and datetime(state["issue_opened"]) - datetime.datetime.now() >= 6m:
        return "history"
    else:
        return "issue_type"


def related_code_cond(state):
    if state["issue_type"] == "bug":
        return "related_code"
    else:
        return "similar_issues"


graph = StateGraph(AgentState)

graph.add_node("init_with_context", init_with_context)
graph.add_node("basic_info", basic_info)
graph.add_node("issue_type", issue_type)
graph.add_node("similar_issues", similar_issues)
graph.add_node("related_code", related_code)
graph.add_node("history", history)
graph.add_node("compile_final_message", compile_final_message)

graph.add_edge(START, "init_with_context")
graph.add_edge("init_with_context", "basic_info")
graph.add_conditional_edges("basic_info", history_cond)
graph.add_edge("history", "issue_type")
graph.add_conditional_edges("issue_type", related_code_cond)
graph.add_edge("related_code", "similar_issues")
graph.add_edge("similar_issues", "compile_final_message")
graph.add_edge("compile_final_message", END)

app = graph.compile()
issue_id = "SOME_ID"
initial_state: AgentState = {"issue_id": issue_id}
final_state = app.ainvoke(initial_state)
print(f"Final Result: {final_state['final_message']}")  # Output: 16