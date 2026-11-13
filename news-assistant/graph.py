from langgraph.graph import END, START, StateGraph

from agents.notifier_agent import notifier_agent
from agents.research_agent import research_agent
from agents.summarizer_agent import summarizer_agent
from state import NewsState


def check_error(state: NewsState) -> str:
    return "stop" if state.get("error") else "continue"


def build_graph():
    graph = StateGraph(NewsState)

    graph.add_node("research", research_agent)
    graph.add_node("summarizer", summarizer_agent)
    graph.add_node("notifier", notifier_agent)

    graph.add_edge(START, "research")
    graph.add_conditional_edges("research", check_error, {"continue": "summarizer", "stop": END})
    graph.add_conditional_edges("summarizer", check_error, {"continue": "notifier", "stop": END})
    graph.add_edge("notifier", END)

    return graph.compile()
