from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class MathState(TypedDict):
    num1: float
    num2: float
    sum_result: float
    final_result: float

def add_numbers(state: MathState) -> MathState:
    state["sum_result"] = state["num1"] + state["num2"]
    return state
def multiply_result(state: MathState) -> MathState:
    # state["final_result"] = state["sum_result"] * 2
    return {"final_result": state["sum_result"] * 2}

graph = StateGraph(MathState)
graph.add_node("add", add_numbers)
graph.add_node("multiply", multiply_result)
graph.add_edge(START, "add")
graph.add_edge("add", "multiply")
graph.add_edge("multiply", END)

app = graph.compile()
initial_state: MathState = {"num1": 5, "num2": 3, "sum_result": 0, "final_result": 0}
final_state = app.invoke(initial_state)
print(f"Final Result: {final_state['final_result']}")  # Output: 16