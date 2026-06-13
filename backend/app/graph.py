from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.state import ProcurementState
from app.agents.search import search_node
from app.agents.extract import extract_node
from app.agents.analyst import analyst_node, confirm_candidate_node
from app.agents.negotiate import negotiate_node
from app.agents.coordinate import coordinate_node


def _after_confirm(state: ProcurementState) -> str:
    if state["status"] == "failed":
        return END
    return "negotiate"


def _should_continue_negotiating(state: ProcurementState) -> str:
    if state["status"] == "failed":
        return END
    if state["status"] == "coordinating":
        return "coordinate"
    return "negotiate"


def build_graph() -> tuple:
    builder = StateGraph(ProcurementState)
    builder.add_node("search", search_node)
    builder.add_node("extract", extract_node)
    builder.add_node("analyst", analyst_node)
    builder.add_node("confirm_candidate", confirm_candidate_node)
    builder.add_node("negotiate", negotiate_node)
    builder.add_node("coordinate", coordinate_node)

    builder.set_entry_point("search")
    builder.add_edge("search", "extract")
    builder.add_edge("extract", "analyst")
    builder.add_edge("analyst", "confirm_candidate")
    builder.add_conditional_edges(
        "confirm_candidate",
        _after_confirm,
        {"negotiate": "negotiate", END: END},
    )
    builder.add_conditional_edges(
        "negotiate",
        _should_continue_negotiating,
        {"negotiate": "negotiate", "coordinate": "coordinate", END: END},
    )
    builder.add_edge("coordinate", END)

    # All three human checkpoints use dynamic interrupt() inside their nodes,
    # so no static interrupt_before is needed — resume is uniformly
    # Command(resume=choice).
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)
    return graph, memory


_graph, _memory = build_graph()


def get_graph():
    return _graph
