from langgraph.graph import StateGraph, END
from .state import NegotiationState # Relative import
from .nodes import acme_agent_node, company_agent_node, negotiation_manager_node # Relative import

def build_negotiation_graph() -> StateGraph:
    graph_builder = StateGraph(NegotiationState)

    graph_builder.add_node("acme_turn", acme_agent_node)
    graph_builder.add_node("company_turn", company_agent_node)
    graph_builder.add_node("process_round_results", negotiation_manager_node)

    graph_builder.set_entry_point("acme_turn")

    def route_after_acme(state: NegotiationState) -> str:
        if state.get("next_actor_in_round") and state["active_companies"]:
            return "company_turn"
        else:
            return "process_round_results"

    graph_builder.add_conditional_edges(
        "acme_turn",
        route_after_acme,
        {"company_turn": "company_turn", "process_round_results": "process_round_results"}
    )

    def route_after_company(state: NegotiationState) -> str:
        if state.get("next_actor_in_round"): # Next company in the list
            return "company_turn"
        else: # All companies in this round have responded
            return "process_round_results"

    graph_builder.add_conditional_edges(
        "company_turn",
        route_after_company,
        {"company_turn": "company_turn", "process_round_results": "process_round_results"}
    )

    def route_after_processing_results(state: NegotiationState) -> str:
        if state.get("negotiation_complete"):
            return END
        else: # Continue to next round, ACME's turn
            return "acme_turn"

    graph_builder.add_conditional_edges(
        "process_round_results",
        route_after_processing_results,
        {END: END, "acme_turn": "acme_turn"}
    )
    
    return graph_builder.compile()

app = build_negotiation_graph()