from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import AnyMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command
import mistralai
from mistralai.client import Mistral
import json
from github_api import execute_function, GitHubAPI
import operator


api_key = "21Z5Tgmvrd69iu0yfU7ot1QRNOcT7Tcv"
mistral_ai = Mistral(api_key=api_key)
max_tokens = 50

TOOLS = []
tool_filenames = ["get_issue", "get_issue_comments", "list_repository_issues", "search_issues"]
for tool_filename in tool_filenames:
    with open(f'github_tools/{tool_filename}.json') as f:
        d = json.load(f)
        TOOLS.append(d)

client = GitHubAPI()


def ask_model(messages):
    try:
        model_response = mistral_ai.chat.complete(
            model="mistral-large-latest",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=max_tokens
        )
        response = model_response.choices[0].message
        responses = [response]

        if response.tool_calls:
            for tool_call in response.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                decision = interrupt(f"""Do you approve calling the following function?:
        function name: {function_name}
        arguments: {arguments}
    Type "yes" for approval, otherwise stop agent.""")

                if decision.lower() != "yes":
                    return Command(goto=END)

                function_result = execute_function(function_name, arguments, client)

                responses.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": function_result
                })

            final_response = mistral_ai.chat.complete(
                model="mistral-large-latest",
                messages=messages + responses,
                max_tokens=max_tokens
            )
            return responses + [final_response]
        else:
            return responses
    except mistralai.client.errors.SDKError:
        return [{"role": "assistant",
                 "content": "Sorry, cannot help. Ran out of tokens :("}]


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]

    issue_id: str
    repo_owner: str
    repo_name: str

    issue_context: str


def init(state):
    return {"messages": [
                {"role": "system", "content": """You are an AI assistant that can interact with issues raised in a 
                public GitHub repository. You can read issues and the repository code. When users give you an issue and 
                a repository and ask questions about the issue, use the available functions to interact with the GitHub 
                repository and answer the questions."""},
                {"role": "user",
                 "content": f'Issue {state["issue_id"]} in the {state["repo_owner"]}/{state["repo_name"]} repository'}
            ]}


def context(state):
    issue_context = GitHubAPI().get_issue(owner=state["repo_owner"], repo=state["repo_name"],
                                          issue_number=state["issue_id"])
    return {"messages": [{"role": "user",
                          "content": issue_context["data"]["body"]}],
            "issue_context": issue_context["data"]["body"]}


def issue_type(state):
    message = [{"role": "user", "content": """"Classify the issue into one of the following 5 categories:
    1. bug
    2. feature request
    3. question
    4. documentation
    5. duplicate
    Explain your reasoning citing specific content from the issue or linked issues."""}]
    response = ask_model(state["messages"] + message)
    return {"messages": message + response}


def similar_issues(state):
    message = [{"role": "user", "content": """"For the given issue, find up to 3 likely duplicate or closely related issues.
    Explain the relationship between the given issue and the selected issues."""}]
    response = ask_model(state["messages"] + message)
    return {"messages": message + response}


def related_code(state):
    message = [{"role": "user", "content": """"For the given bug report, identify the most probable area of the codebase affected. 
    Use the issue text plus repository search."""}]
    response = ask_model(state["messages"] + message)
    return {"messages": message + response}


def history(state):
    message = [{"role": "user", "content": """"For the given issue, summarize its current state, outstanding questions, and what decision is needed to move it forward"""}]
    response = ask_model(state["messages"] + message)
    return {"messages": message + response}


def compile_final_message(state):
    message = [{"role": "user",
               "content": """"Analyze the chat from start to finish.
               Produce a triage report on the GitHub issue based on the chat contents."""}]
    response = ask_model(state["messages"] + message)
    return response[-1]


def history_cond(state):
    q1 = [{"role": "user", "content": """"Is the given issue currently open? Return only the bool output."""}]
    q2 = [{"role": "user", "content": """"Was the given issue opened over 6 months ago? Return only the bool output."""}]

    response1 = ask_model(state["messages"] + q1)
    response2 = ask_model(state["messages"] + q2)

    if response1[-1]["content"].lower() == "true" and response2[-1]["content"].lower() == "true":
        return "history"
    else:
        return "similar_issues"


def related_code_cond(state):
    q = [{"role": "user", "content": """"Is the given issue a bug report? Return only the bool output."""}]

    response1 = ask_model(state["messages"] + q)

    if response1[-1]["content"].lower() == "true":
        return "related_code"
    else:
        return "compile_final_message"


graph = StateGraph(AgentState)

graph.add_node("init", init)
graph.add_node("context", context)
graph.add_node("issue_type", issue_type)
graph.add_node("similar_issues", similar_issues)
graph.add_node("related_code", related_code)
graph.add_node("history", history)
graph.add_node("compile_final_message", compile_final_message)

graph.add_edge(START, "init")
graph.add_edge("init", "context")
graph.add_conditional_edges("context", history_cond)
graph.add_edge("history", "similar_issues")
graph.add_edge("similar_issues", "issue_type")
graph.add_conditional_edges("issue_type", related_code_cond)
graph.add_edge("related_code", "compile_final_message")
graph.add_edge("compile_final_message", END)

repo_owner = "langchain-ai"
repo_name = "langgraphjs"
issue_id = "2351"
checkpointer = InMemorySaver()
app = graph.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "1"}}

for result in app.stream({"issue_id": issue_id, "repo_owner": repo_owner,
                          "repo_name": repo_name}, config=config):
    print(result)
    if "__interrupt__" in result.keys():
        print(result["__interrupt__"][0].value)
        inp = input()
        final_result = app.invoke(Command(resume=inp), config=config)


# initial_state: AgentState = {"issue_id": issue_id}
# final_state = app.invoke(initial_state)
print(f"Final Result: {final_result['messages'][-1]['content']}")
