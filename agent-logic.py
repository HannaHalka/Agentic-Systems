import datetime
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.graph import StateGraph, START, END


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

    issue_id: str
    repo_context: str


def ask_model(messages):
    model_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=TOOLS,
        tool_choice="auto"
    )
    response = model_response.choices[0].message
    messages.append(response)

    if response.tool_calls:
        for tool_call in response.tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            function_result = execute_function(function_name, arguments, client)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": function_result
            })

    final_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )
    return [final_response.choices[0].message]


async def init_with_context(state):
    context = get_context(state["issue_id"])
    return {"repo_context": context,
            "messages": [
                {"role": "system", "content": """You are an AI assistant that can interact with issues raised in a public GitHub repository.
                You can read issues and the repository code. When users give you an issue id and ask questions about the 
                issue, use the available functions to interact with the GitHub repository and answer the questions."""},
                {"role": "user", "content": state["issue_id"]},
                {"role": "tool", "content": context}
            ]}


async def basic_info(state):
    info = get_basic_info(state["issue_id"])
    info["messages"] = {"role": "tool", "content": f"{info}"}
    return info


async def issue_type(state):
    message = [{"role": "user", "content": """"Classify the issue into one of the following 5 categories:
    1. bug
    2. feature request
    3. question
    4. documentation
    5. duplicate
    Explain your reasoning citing specific content from the issue or linked issues."""}]
    response = ask_model(state["messages"] + message)
    return {"messages": message + response}


async def similar_issues(state):
    message = [{"role": "user", "content": """"For the given issue, find up to 3 likely duplicate or closely related issues.
    Explain the relationship between the given issue and the selected issues."""}]
    response = ask_model(state["messages"] + message)
    return {"messages": message + response}


async def related_code(state):
    message = [{"role": "user", "content": """"For the given bug report, identify the most probable area of the codebase affected. 
    Use the issue text plus repository search."""}]
    response = ask_model(state["messages"] + message)
    return {"messages": message + response}


async def history(state):
    message = [{"role": "user", "content": """"For the given issue, summarize its current state, outstanding questions, and what decision is needed to move it forward"""}]
    response = ask_model(state["messages"] + message)
    return {"messages": message + response}


def compile_final_message(state):
    message = [{"role": "user",
               "content": """"Analyze the chat from start to finish.
               Produce a triage report on the GitHub issue based on the chat contents."""}]
    response = ask_model(state["messages"] + message)
    return response[0]


def history_cond(state):
    q1 = [{"role": "user", "content": """"Is the given issue currently open? Return only the bool output."""}]
    q2 = [{"role": "user", "content": """"Was the given issue opened over 6 months ago? Return only the bool output."""}]

    response1 = ask_model(state["messages"] + q1)
    response2 = ask_model(state["messages"] + q2)

    if response1[0].content.lower() == "true" and response2[0].content.lower() == "true":
        return "history"
    else:
        return "similar_issues"


def related_code_cond(state):
    q = [{"role": "user", "content": """"Is the given issue a bug report? Return only the bool output."""}]

    response1 = ask_model(state["messages"] + q)

    if response1[0].content.lower() == "true":
        return "related_code"
    else:
        return "compile_final_message"


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
graph.add_edge("history", "similar_issues")
graph.add_edge("similar_issues", "issue_type")
graph.add_conditional_edges("issue_type", related_code_cond)
graph.add_edge("related_code", "compile_final_message")
graph.add_edge("compile_final_message", END)

app = graph.compile()
issue_id = "SOME_ID"
initial_state: AgentState = {"issue_id": issue_id}
final_state = app.ainvoke(initial_state)
print(f"Final Result: {final_state['final_message']}")
