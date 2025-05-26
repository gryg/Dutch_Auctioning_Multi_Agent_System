# langgraph_bonus/main.py
import json
from .config import ITEM_NAME, MAX_NEGOTIATION_ROUNDS, COMPANY_B_COST_STRUCTURAL_DESIGN, COMPANY_F_COST_STRUCTURAL_DESIGN # Relative
from .state import NegotiationState 
from .graph import app 
from .llm_calls import langgraph_llm_interactions_log 


def run_scenario(scenario_name: str, initial_state: NegotiationState):
    print(f"\n\n--- RUNNING SCENARIO: {scenario_name} ---")
    final_state_result = None
    for s_output in app.stream(initial_state, {"recursion_limit": 25}):
        node_name = list(s_output.keys())[0]
        # print(f"\nOutput from node: {node_name}") # Verbose state printing
        # print(json.dumps(s_output[node_name], indent=2, default=str))
        final_state_result = s_output[node_name]
    
    print(f"\n--- FINAL STATE for {scenario_name} ---")
    if final_state_result:
        print(f"Negotiation Complete: {final_state_result.get('negotiation_complete')}")
        if final_state_result.get('winning_company'):
            print(f"Winning Company: {final_state_result['winning_company']} at Price: {final_state_result.get('final_agreement_price'):.2f}")
        else:
            print("No agreement reached or negotiation ended prematurely.")
        print(f"Total rounds processed (state): {final_state_result.get('negotiation_round')}")
        # print("Full history:") # For detailed debugging
        # for h_entry in final_state_result.get("history",[]):
        # print(json.dumps(h_entry, indent=2))
    else:
        print("Scenario did not produce a final state from stream.")
    return final_state_result

if __name__ == "__main__":
    # --- Scenario 1: ACME and a single company (Company B) ---
    initial_state_s1: NegotiationState = {
        "current_item": ITEM_NAME,
        "negotiation_round": 0,
        "max_negotiation_rounds": MAX_NEGOTIATION_ROUNDS,
        "acme_agent_name": "ACME_LG_S1",
        "active_companies": [
            {"name": "Company_B_LG_S1", "cost": COMPANY_B_COST_STRUCTURAL_DESIGN, "contracts_won": 0, "auction_price": 4000.0}
        ],
        "acme_current_offers_for_round": {}, "company_current_responses_for_round": {}, "history": [],
        "negotiation_complete": False, "final_agreement_price": None, "winning_company": None,
        "next_actor_in_round": None, "companies_acted_this_round": []
    }
    final_state_s1 = run_scenario("ACME_vs_CompanyB", initial_state_s1)

    # --- Scenario 2: ACME and two companies (Company B and Company F) ---
    initial_state_s2: NegotiationState = {
        "current_item": ITEM_NAME,
        "negotiation_round": 0,
        "max_negotiation_rounds": MAX_NEGOTIATION_ROUNDS,
        "acme_agent_name": "ACME_LG_S2",
        "active_companies": [
            {"name": "Company_B_LG_S2", "cost": COMPANY_B_COST_STRUCTURAL_DESIGN, "contracts_won": 0, "auction_price": 4000.0},
            {"name": "Company_F_LG_S2", "cost": COMPANY_F_COST_STRUCTURAL_DESIGN, "contracts_won": 1, "auction_price": 4950.0}
        ],
        "acme_current_offers_for_round": {}, "company_current_responses_for_round": {}, "history": [],
        "negotiation_complete": False, "final_agreement_price": None, "winning_company": None,
        "next_actor_in_round": None, "companies_acted_this_round": []
    }
    final_state_s2 = run_scenario("ACME_vs_CompanyB_and_CompanyF", initial_state_s2)

    # --- Save LangGraph LLM Logs ---
    print("\n\n--- LangGraph LLM Interaction Logs ---")
    if langgraph_llm_interactions_log:
        log_file_name_lg = "langgraph_bonus_llm_interactions.jsonl" # Save in current dir
        try:
            with open(log_file_name_lg, "w") as f:
                for entry in langgraph_llm_interactions_log:
                    f.write(json.dumps(entry) + "\n")
            print(f"LangGraph LLM interaction logs saved to {log_file_name_lg}")
        except IOError as e:
            print(f"Error saving LangGraph LLM logs: {e}")
    else:
        print("No LangGraph LLM interactions were logged.")