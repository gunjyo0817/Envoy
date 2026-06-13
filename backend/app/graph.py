from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.state import ProcurementState
from app.agents.search import search_node
from app.agents.extract import extract_node
from app.agents.analyst import analyst_node, confirm_candidate_node
from app.agents.negotiate import (
    make_offer_node, decide_offer_node, seller_turn_node,
    make_counter_node, decide_counter_node,
)
from app.agents.coordinate import plan_meetup_node, confirm_meetup_node, seller_time_turn_node


def _after_confirm(state: ProcurementState) -> str:
    if state["status"] == "failed":
        return END
    return "make_offer"


def _after_make_offer(state: ProcurementState) -> str:
    return END if state["status"] == "failed" else "decide_offer"


def _after_decide_offer(state: ProcurementState) -> str:
    if state["status"] == "awaiting_seller":
        return "seller_turn"
    if state["status"] == "failed":
        return END
    return "make_offer"  # skip → next candidate


def _after_seller_turn(state: ProcurementState) -> str:
    if state["status"] == "coordinating":
        return "plan_meetup"
    if state["status"] == "failed":
        return END
    thread = state.get("negotiation_thread") or []
    if thread and thread[-1]["role"] == "seller":
        return "make_counter"   # seller countered → round 2
    return "make_offer"         # rejected → next candidate


def _after_decide_counter(state: ProcurementState) -> str:
    if state["status"] == "coordinating":
        return "plan_meetup"
    return "make_offer"  # walked away → try next candidate


def _after_confirm_meetup(state: ProcurementState) -> str:
    if state["status"] == "awaiting_seller":
        return "seller_time_turn"
    if state["status"] == "done":
        return END
    if state["status"] == "failed":
        return END
    return "plan_meetup"  # plain reschedule


def _after_seller_time_turn(state: ProcurementState) -> str:
    return "confirm_meetup"


def build_graph() -> tuple:
    builder = StateGraph(ProcurementState)
    builder.add_node("search", search_node)
    builder.add_node("extract", extract_node)
    builder.add_node("analyst", analyst_node)
    builder.add_node("confirm_candidate", confirm_candidate_node)
    builder.add_node("make_offer", make_offer_node)
    builder.add_node("decide_offer", decide_offer_node)
    builder.add_node("seller_turn", seller_turn_node)
    builder.add_node("make_counter", make_counter_node)
    builder.add_node("decide_counter", decide_counter_node)
    builder.add_node("plan_meetup", plan_meetup_node)
    builder.add_node("confirm_meetup", confirm_meetup_node)
    builder.add_node("seller_time_turn", seller_time_turn_node)

    builder.set_entry_point("search")
    builder.add_edge("search", "extract")
    builder.add_edge("extract", "analyst")
    builder.add_edge("analyst", "confirm_candidate")
    builder.add_conditional_edges(
        "confirm_candidate",
        _after_confirm,
        {"make_offer": "make_offer", END: END},
    )
    builder.add_conditional_edges(
        "make_offer",
        _after_make_offer,
        {"decide_offer": "decide_offer", END: END},
    )
    builder.add_conditional_edges(
        "decide_offer",
        _after_decide_offer,
        {"seller_turn": "seller_turn", "make_offer": "make_offer", END: END},
    )
    builder.add_conditional_edges(
        "seller_turn",
        _after_seller_turn,
        {"make_offer": "make_offer", "make_counter": "make_counter",
         "plan_meetup": "plan_meetup", END: END},
    )
    builder.add_edge("make_counter", "decide_counter")
    builder.add_conditional_edges(
        "decide_counter",
        _after_decide_counter,
        {"make_offer": "make_offer", "plan_meetup": "plan_meetup"},
    )
    builder.add_edge("plan_meetup", "confirm_meetup")
    builder.add_conditional_edges(
        "confirm_meetup",
        _after_confirm_meetup,
        {"seller_time_turn": "seller_time_turn", "plan_meetup": "plan_meetup", END: END},
    )
    builder.add_edge("seller_time_turn", "confirm_meetup")

    # All three human checkpoints use dynamic interrupt() inside their nodes,
    # so no static interrupt_before is needed — resume is uniformly
    # Command(resume=choice).
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)
    return graph, memory


_graph, _memory = build_graph()


def get_graph():
    return _graph
