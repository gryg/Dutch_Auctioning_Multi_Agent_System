import json
from typing import Dict, Any
from .state import NegotiationState 
from .llm_calls import call_gemini_llm_for_langgraph 
from .config import ACME_BUDGET_STRUCTURAL_DESIGN 

# Definition of acme_agent_node
def acme_agent_node(state: NegotiationState) -> Dict[str, Any]:
    print(f"\n--- ACME's Turn (Round {state['negotiation_round']}) ---")
    acme_name = state["acme_agent_name"]
    current_round = state["negotiation_round"]
    item_name = state["current_item"]
    new_acme_offers_this_round = {}
    round_history_entry_offers = {}

    for company_info in state["active_companies"]:
        partner_agent_name = company_info["name"]
        auction_agreed_price = company_info["auction_price"]
        
        your_previous_offer_to_partner = 0.0
        partner_previous_counter_offer = 0.0

        temp_prev_offer_acme = 0.0
        for record in reversed(state["history"]): 
            if record["round"] < current_round:
                if record["actor"] == acme_name and record["acme_offers"] and partner_agent_name in record["acme_offers"]:
                    temp_prev_offer_acme = record["acme_offers"][partner_agent_name]
                    break 
        your_previous_offer_to_partner = temp_prev_offer_acme

        temp_prev_counter_partner = 0.0
        for record in reversed(state["history"]): 
            if record["round"] < current_round:
                if record["actor"] == partner_agent_name and record["company_response_to_acme"] is not None:
                    temp_prev_counter_partner = record["company_response_to_acme"]
                    break 
        partner_previous_counter_offer = temp_prev_counter_partner
        
        if current_round == 0: 
            your_previous_offer_to_partner = 0.0
            partner_previous_counter_offer = 0.0
        
        system_prompt = f"""
You are {acme_name}, in 'Monotonic Concession Negotiation' for "{item_name}" with Company {partner_agent_name}.
Primary goal: complete item. Secondary: save money.
Partner accepted auction at {auction_agreed_price:.2f}. Your max budget for item: {ACME_BUDGET_STRUCTURAL_DESIGN:.2f}.

Rules (Initiator):
- Max {state['max_negotiation_rounds']} rounds (0 to {state['max_negotiation_rounds']-1}).
- Your offers must be >= previous offer (monotonic increase/stagnation).
- Agreement if: partner counter <= your current offer OR your current offer >= partner's previous counter.
Decide your offer.
        """
        user_prompt = f"""
Negotiation Status ({item_name} with {partner_agent_name}):
- Round: {current_round} (max {state['max_negotiation_rounds']-1})
- Your budget for item: {ACME_BUDGET_STRUCTURAL_DESIGN:.2f}
- Partner's auction acceptance price: {auction_agreed_price:.2f}
- Your previous offer to {partner_agent_name}: {your_previous_offer_to_partner:.2f}
- {partner_agent_name}'s previous counter-offer: {partner_previous_counter_offer:.2f}
- Estimated other negotiators for this item: {len(state['active_companies']) -1}

Task:
Think step by step.
1. New offer must be >= {your_previous_offer_to_partner:.2f}.
2. Strategy: Start below {auction_agreed_price:.2f}.
   - If {partner_previous_counter_offer:.2f} > 0 & new offer >= {partner_previous_counter_offer:.2f}, agreement possible.
   - Round 0: Offer significantly below {auction_agreed_price:.2f} (e.g., 70-80%).
3. Offer should ideally not exceed {auction_agreed_price:.2f}.
4. Final round ({state['max_negotiation_rounds']-1}) is critical.
Output JSON: {{"reasoning": "...", "negotiation_offer": <float>}}
        """

        llm_response = call_gemini_llm_for_langgraph(f"{acme_name}_negotiating_with_{partner_agent_name}", system_prompt, user_prompt)
        
        offer = auction_agreed_price 
        if "error" not in llm_response and "negotiation_offer" in llm_response and isinstance(llm_response["negotiation_offer"],(int,float)):
            offer = float(llm_response["negotiation_offer"])
        
        if current_round > 0 and offer < your_previous_offer_to_partner: offer = your_previous_offer_to_partner
        if current_round == 0 and (offer <= 0 or offer > auction_agreed_price * 0.95): offer = auction_agreed_price * 0.7 
        if offer > auction_agreed_price : offer = auction_agreed_price
        if offer <= 0 and auction_agreed_price > 0: offer = auction_agreed_price * 0.1
        elif offer <=0 : offer = 1.0

        new_acme_offers_this_round[partner_agent_name] = offer
        round_history_entry_offers[partner_agent_name] = offer

    updated_history = state["history"] + [{
        "round": current_round, "actor": acme_name, "acme_offers": round_history_entry_offers,
        "company_name": None, "company_response_to_acme": None, "acme_offer_received": None
    }]
    
    return {
        "acme_current_offers_for_round": new_acme_offers_this_round,
        "history": updated_history,
        "companies_acted_this_round": [], 
        "next_actor_in_round": state["active_companies"][0]["name"] if state["active_companies"] else None
    }

# Definition of company_agent_node 
def company_agent_node(state: NegotiationState) -> Dict[str, Any]:
    company_name_to_act = state["next_actor_in_round"]
    if not company_name_to_act: 
        print("ERROR: Company agent node called without a company to act.")
        return {"negotiation_complete": True, "winning_company": None, "final_agreement_price": None} 
        
    print(f"\n--- {company_name_to_act}'s Turn (Round {state['negotiation_round']}) ---")
    
    company_info = next((c for c in state["active_companies"] if c["name"] == company_name_to_act), None)
    if not company_info:
        print(f"ERROR: Company info not found for {company_name_to_act}")
        return {"negotiation_complete": True, "winning_company": None, "final_agreement_price": None}

    acme_offer_to_this_company = state["acme_current_offers_for_round"].get(company_name_to_act, 0.0)
    current_round = state["negotiation_round"]
    item_name = state["current_item"]
    
    previous_counter_offer_by_company = company_info["auction_price"] 
    temp_prev_counter = company_info["auction_price"] 
    for record in reversed(state["history"]):
        if record["round"] < current_round:
            if record["actor"] == company_name_to_act and record["company_response_to_acme"] is not None:
                temp_prev_counter = record["company_response_to_acme"]
                break
    previous_counter_offer_by_company = temp_prev_counter
    
    if current_round == 0: 
        previous_counter_offer_by_company = company_info["auction_price"]

    system_prompt = f"""
You are Contractor Company {company_name_to_act}. You are in 'Monotonic Concession Negotiation' for "{item_name}" with ACME.
Primary goal: win >=1 contract. Secondary: profit (counter_offer - cost).
Your cost for "{item_name}": {company_info['cost']:.2f}. Initial auction price was {company_info['auction_price']:.2f}.

Rules (Responder):
- Max {state['max_negotiation_rounds']} rounds (0 to {state['max_negotiation_rounds']-1}).
- Your counter-offers must be <= previous counter (implicitly {previous_counter_offer_by_company:.2f} if no prior actual counter this negotiation).
- Agreement if: your counter <= ACME's current offer OR ACME's next offer >= your current counter.
- {len(state['active_companies'])} companies (incl. you) are negotiating for this item.
Decide your counter-offer.
    """
    user_prompt = f"""
Negotiation Status ({item_name} for Co. {company_name_to_act}):
- Round: {current_round} (max {state['max_negotiation_rounds']-1})
- ACME's Current Offer: {acme_offer_to_this_company:.2f}
- Your Implicit Previous Counter-Offer (or actual if not R0): {previous_counter_offer_by_company:.2f}
- Your Cost for "{item_name}": {company_info['cost']:.2f}
- Auction Price for "{item_name}": {company_info['auction_price']:.2f}
- Contracts Won by You: {company_info['contracts_won']}
- Total Competitors (incl. you) for this item: {len(state['active_companies'])}

Task:
Think step by step.
1. Counter-offer MUST be >= {company_info['cost']:.2f}.
2. Counter-offer MUST be <= {previous_counter_offer_by_company:.2f} (monotonic concession).
3. Strategy:
    - If {acme_offer_to_this_company:.2f} >= {company_info['cost']:.2f}:
        - To accept: counter_offer = {acme_offer_to_this_company:.2f}. (Strong if {company_info['contracts_won']}==0 or {len(state['active_companies'])}>1).
        - Else, counter_offer < {previous_counter_offer_by_company:.2f} but >= {acme_offer_to_this_company:.2f} (or slightly higher).
    - If {acme_offer_to_this_company:.2f} < {company_info['cost']:.2f}: Cannot accept. Counter_offer >= {company_info['cost']:.2f}. Concede from {previous_counter_offer_by_company:.2f} if possible.
4. Final round ({state['max_negotiation_rounds']-1}): Strongly consider accepting if ACME's offer >= cost. Else, best possible counter.
Output JSON: {{"reasoning": "...", "counter_offer": <float>}}
    """

    llm_response = call_gemini_llm_for_langgraph(company_name_to_act, system_prompt, user_prompt)

    counter_offer = previous_counter_offer_by_company 
    if "error" not in llm_response and "counter_offer" in llm_response and isinstance(llm_response["counter_offer"],(int,float)):
        counter_offer = float(llm_response["counter_offer"])

    if counter_offer < company_info['cost']: counter_offer = company_info['cost']
    if (current_round > 0 and counter_offer > previous_counter_offer_by_company) or \
       (current_round == 0 and counter_offer > company_info["auction_price"]): 
        counter_offer = previous_counter_offer_by_company if current_round > 0 else company_info["auction_price"]
    
    updated_company_responses = state.get("company_current_responses_for_round", {}).copy() 
    updated_company_responses[company_name_to_act] = counter_offer
    
    updated_history = state["history"] + [{
        "round": current_round, "actor": company_name_to_act, "acme_offers": None,
        "company_name": company_name_to_act, "company_response_to_acme": counter_offer, 
        "acme_offer_received": acme_offer_to_this_company
    }]
    
    updated_companies_acted = state["companies_acted_this_round"] + [company_name_to_act]
    
    next_actor = None
    current_company_index = -1
    for idx, c_info in enumerate(state["active_companies"]):
        if c_info["name"] == company_name_to_act:
            current_company_index = idx
            break
    
    if current_company_index != -1 and current_company_index + 1 < len(state["active_companies"]):
        next_actor = state["active_companies"][current_company_index + 1]["name"]
    
    return {
        "company_current_responses_for_round": updated_company_responses,
        "history": updated_history,
        "companies_acted_this_round": updated_companies_acted,
        "next_actor_in_round": next_actor 
    }

# Definition of negotiation_manager_node (copied from previous response)
def negotiation_manager_node(state: NegotiationState) -> Dict[str, Any]:
    current_round = state["negotiation_round"]
    print(f"\n--- Negotiation Manager (Processing Results for Round {current_round}) ---")

    potential_agreements = [] 
    acme_offers_k = state["acme_current_offers_for_round"]
    company_responses_k = state["company_current_responses_for_round"]
    acme_name = state["acme_agent_name"]

    for company_info in state["active_companies"]:
        comp_name = company_info["name"]
        i_kc = acme_offers_k.get(comp_name)
        p_kc = company_responses_k.get(comp_name)

        if i_kc is None or p_kc is None: 
            print(f"Note: Missing offer/response for {comp_name} in round {current_round}. Skipping agreement check for this pair this round.")
            continue

        p_k_minus_1_c = None
        if current_round > 0:
            for record in reversed(state["history"]):
                 if record["round"] < current_round: 
                    if record["actor"] == comp_name and record["company_response_to_acme"] is not None:
                        p_k_minus_1_c = record["company_response_to_acme"]
                        break
        
        if p_kc <= i_kc: 
            potential_agreements.append({"company": comp_name, "price": p_kc, "reason": f"Company accepted ACME's offer of {i_kc:.2f}"})
            print(f"Potential Agreement (C accepts A): {comp_name} accepts {p_kc:.2f} (ACME offered {i_kc:.2f})")
        elif current_round > 0 and p_k_minus_1_c is not None and i_kc >= p_k_minus_1_c: 
            potential_agreements.append({"company": comp_name, "price": i_kc, "reason": f"ACME accepted company's previous counter of {p_k_minus_1_c:.2f} with new offer {i_kc:.2f}"})
            print(f"Potential Agreement (A accepts C_prev): ACME accepts {i_kc:.2f} (Company prev countered {p_k_minus_1_c:.2f})")
        
        i_k_minus_1_c = 0.0
        if current_round > 0:
            for record in reversed(state["history"]):
                if record["round"] < current_round and record["actor"] == acme_name and record["acme_offers"] and comp_name in record["acme_offers"]:
                    i_k_minus_1_c = record["acme_offers"][comp_name]
                    break
            if i_kc < i_k_minus_1_c:
                 print(f"MONOTONICITY WARNING (ACME): For {comp_name}, offer {i_kc:.2f} < previous {i_k_minus_1_c:.2f}")

        p_k_minus_1_c_for_comp_check = company_info["auction_price"] 
        if current_round > 0: 
            found_prev_counter = False
            for record in reversed(state["history"]):
                if record["round"] < current_round and record["actor"] == comp_name and record["company_response_to_acme"] is not None:
                    p_k_minus_1_c_for_comp_check = record["company_response_to_acme"]
                    found_prev_counter = True
                    break
            if found_prev_counter and p_kc > p_k_minus_1_c_for_comp_check:
                 print(f"MONOTONICITY WARNING ({comp_name}): Counter {p_kc:.2f} > previous {p_k_minus_1_c_for_comp_check:.2f}")
        elif current_round == 0 and p_kc > company_info["auction_price"]: 
            print(f"MONOTONICITY WARNING ({comp_name}): First counter {p_kc:.2f} > auction price {company_info['auction_price']:.2f}")


    if potential_agreements:
        best_agreement = min(potential_agreements, key=lambda x: x["price"])
        print(f"Negotiation SUCCESSFUL in round {current_round}! Winner: {best_agreement['company']} at {best_agreement['price']:.2f} ({best_agreement['reason']})")
        return {
            "negotiation_complete": True,
            "winning_company": best_agreement["company"],
            "final_agreement_price": best_agreement["price"],
            "next_actor_in_round": None 
        }

    if current_round + 1 >= state["max_negotiation_rounds"]:
        print(f"Negotiation FAILED: Max rounds ({state['max_negotiation_rounds']}) reached without agreement.")
        return {"negotiation_complete": True, "winning_company": None, "final_agreement_price": None, "next_actor_in_round": None} 

    print(f"No agreement in round {current_round}. Proceeding to round {current_round + 1}.")
    return {
        "negotiation_round": current_round + 1,
        "acme_current_offers_for_round": {}, 
        "company_current_responses_for_round": {}, 
        "companies_acted_this_round": [],
        "next_actor_in_round": None 
    }