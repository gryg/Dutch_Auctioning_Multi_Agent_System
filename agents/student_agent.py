# Standard library imports
import json
import os
from typing import List, Dict, Any, Optional

# Third-party imports
from dotenv import load_dotenv
import google.generativeai as genai

from agents import HouseOwnerAgent, CompanyAgent 
from communication import NegotiationMessage   

# The following import was in the original student_agent.py stub.
# It does not seem to be used by MyACMEAgent or MyCompanyAgent directly.
# from scipy.stats._multivariate import special_ortho_group_frozen # [cite: 91]


# --- Load Environment Variables ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Configure Gemini API ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("WARNING: GEMINI_API_KEY not found in .env file. LLM calls will be skipped, and agents will use fallback logic.")

# --- Global Log for Prompts and Responses ---
llm_interactions_log = []

# --- Gemini LLM Call Function ---
def call_gemini_llm(agent_name: str, agent_role: str, interaction_stage: str, item_name: str, round_num: int, system_prompt: str, user_prompt: str):
    """
    Makes a call to the Gemini LLM and returns the parsed JSON response.
    Logs the interaction.
    """
    global llm_interactions_log
    
    log_entry = {
        "agent_name": agent_name,
        "agent_role": agent_role,
        "interaction_stage": interaction_stage,
        "item_name": item_name,
        "round_num": round_num,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "llm_response": None
    }

    if not GEMINI_API_KEY:
        print(f"LLM SKIPPED (NO API KEY) for {agent_name} ({agent_role}), Item: {item_name}, Round: {round_num}")
        # Fallback response structure if API key is missing
        error_response = {"reasoning": "LLM call skipped: API key not configured.", "error": "API key missing"}
        if interaction_stage == "Auction":
            if agent_role == "ACME": error_response["proposed_budget"] = 0.0 
            else: error_response["decision_to_bid"] = False
        elif interaction_stage == "Negotiation":
            if agent_role == "ACME": error_response["negotiation_offer"] = 0.0
            else: error_response["counter_offer"] = float('inf') 
        
        log_entry["llm_response"] = error_response
        llm_interactions_log.append(log_entry)
        return error_response

    try:
        print(f"Calling Gemini for {agent_name} ({agent_role}), Item: {item_name}, Round: {round_num}...")
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash-preview-05-20',
            generation_config={
                "temperature": 0.0,
                "response_mime_type": "application/json"
            },
            system_instruction=system_prompt
        )
        
        response = model.generate_content(user_prompt)
        
        response_text = ""
        if response.parts:
            response_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))
        elif hasattr(response, 'text'): # Fallback for simpler response structures
            response_text = response.text
            
        if not response_text: # Handle cases where the response might be empty or in an unexpected format
            print(f"Warning: Empty response text from LLM for {agent_name}. Full response: {response}")
            # Try to inspect response.candidates or other attributes if text is empty
            if response.candidates and response.candidates[0].content.parts:
                 response_text = "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, 'text'))
            if not response_text:
                 raise ValueError("LLM returned empty or unreadable response content.")


        parsed_json = json.loads(response_text)
        print(f"LLM RESPONSE (Actual for {agent_name}):\n{json.dumps(parsed_json, indent=2)}")

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from LLM response for {agent_name}: {e}")
        raw_text = response_text if 'response_text' in locals() else "Raw response text not available."
        print(f"LLM raw response text was: {raw_text}")
        parsed_json = {"reasoning": f"Error decoding LLM JSON response: {e}. Raw: {raw_text}", "error": str(e)}
    except Exception as e:
        print(f"Error calling Gemini API for {agent_name}: {e}")
        # More detailed error logging if possible
        # For example, some API errors might have a 'response' attribute with more details
        # error_details = str(e)
        # if hasattr(e, 'response') and e.response:
        #     try:
        #         error_details += f" - API Response: {e.response.text}"
        #     except: pass # Ignore if can't get response text
        parsed_json = {"reasoning": f"Error in LLM call: {e}", "error": str(e)}

    log_entry["llm_response"] = parsed_json
    llm_interactions_log.append(log_entry)
    return parsed_json


class MyACMEAgent(HouseOwnerAgent):
    def __init__(self, role: str, budget_list: List[Dict[str, Any]]):
        super(MyACMEAgent, self).__init__(role, budget_list)
        self.previous_auction_offers: Dict[str, float] = {} 
        self.negotiation_states: Dict[str, Dict[str, Dict]] = {} 
        self.auction_round_responders: Dict[str, List[str]] = {} 

    def propose_item_budget(self, auction_item: str, auction_round: int) -> float:
        item_budget_for_acme = self.budget_dict.get(auction_item, 0.0)
        previous_offer_for_item = self.previous_auction_offers.get(auction_item, 0.0)
        responding_agents_previous_round = self.auction_round_responders.get(auction_item, [])

        system_prompt = f"""
You are ACME, a company building its new headquarters. You are currently in the 'Reverse Dutch Auction' phase for contracting construction tasks.
Your primary goal is to complete all construction items for the headquarters. Your secondary goal is to save as much money as possible from your overall budget.
Your per-item budgets are: {json.dumps(self.budget_dict, indent=2)}

Auction Rules:
- You propose a price. This is a reverse Dutch auction: start low, raise price in subsequent rounds if no bids.
- Max 3 auction rounds (0, 1, 2) per item. Failure if no bids after 3 rounds.
- If your offer in round N for an item was X, your offer in round N+1 must be > X if no one bid.
- Successful bidders proceed to negotiation.
Decide the price for the current item and round.
        """
        user_prompt = f"""
Current Auction Status:
- Item: "{auction_item}", Round: {auction_round} (max 2)
- Your Budget for "{auction_item}": {item_budget_for_acme:.2f}
- Your Previous Offer for "{auction_item}": {previous_offer_for_item:.2f}
- Responders in Previous Round for "{auction_item}": {responding_agents_previous_round}

Task:
Think step by step.
1. Round 0: Make a low initial offer (e.g., 50-70% of budget).
2. Round > 0 & no prior responders for this item: MUST increase offer significantly (must be > previous_offer_for_item).
3. Last round (2) & no prior responders: Offer attractively, possibly near budget, to avoid item failure.
4. New offer should not exceed your budget {item_budget_for_acme:.2f}.

Output JSON: {{"reasoning": "...", "proposed_budget": <float>}}
        """

        llm_response = call_gemini_llm(self.name, "ACME", "Auction", auction_item, auction_round, system_prompt, user_prompt)
        
        proposed_budget = item_budget_for_acme * 0.7 # Fallback if LLM fails
        if "error" not in llm_response and "proposed_budget" in llm_response and isinstance(llm_response["proposed_budget"], (int, float)):
            proposed_budget = float(llm_response["proposed_budget"])
        
        # Enforce constraints post-LLM
        is_first_offer_attempt = (previous_offer_for_item == 0.0) # More robust check
        no_responders_last_time = not responding_agents_previous_round

        if not is_first_offer_attempt and no_responders_last_time: # Must increase if not first offer and no one responded
            if proposed_budget <= previous_offer_for_item:
                proposed_budget = previous_offer_for_item * 1.15 # Enforce significant increase
        
        if proposed_budget > item_budget_for_acme: proposed_budget = item_budget_for_acme
        if proposed_budget <= 0 and item_budget_for_acme > 0: proposed_budget = item_budget_for_acme * 0.1 # Ensure positive sensible offer
        elif proposed_budget <= 0 : proposed_budget = 1.0 # Absolute fallback for 0 budget items

        self.previous_auction_offers[auction_item] = proposed_budget
        self.auction_round_responders.pop(auction_item, None) # Clear for current round's responses
        return proposed_budget

    def notify_auction_round_result(self, auction_item: str, auction_round: int, responding_agents: List[str]):
        self.auction_round_responders[auction_item] = responding_agents
        print(f"ACME ({self.name}) notified: Auction for {auction_item}, rnd {auction_round}. Responders: {responding_agents}")

    def provide_negotiation_offer(self, negotiation_item: str, partner_agent_name: str, negotiation_round: int) -> float:
        item_budget_for_acme = self.budget_dict.get(negotiation_item, 0.0)
        
        if negotiation_item not in self.negotiation_states: self.negotiation_states[negotiation_item] = {}
        if partner_agent_name not in self.negotiation_states[negotiation_item]:
            auction_agreed_price_for_this_partner = self.previous_auction_offers.get(negotiation_item, item_budget_for_acme)
            self.negotiation_states[negotiation_item][partner_agent_name] = {
                "previous_offer_acme": 0.0,
                "partner_previous_counter_offer": 0.0,
                "auction_agreed_price": auction_agreed_price_for_this_partner
            }
            
        state = self.negotiation_states[negotiation_item][partner_agent_name]
        prev_acme_offer = state["previous_offer_acme"]
        prev_partner_counter = state["partner_previous_counter_offer"]
        auction_price = state["auction_agreed_price"]
        
        other_negotiators_count = max(0, len(self.negotiation_states[negotiation_item].keys()) - 1)

        system_prompt = f"""
You are ACME, in 'Monotonic Concession Negotiation' for "{negotiation_item}" with Company {partner_agent_name}.
Primary goal: complete item. Secondary: save money.
Partner accepted auction at {auction_price:.2f}. Your max budget for item: {item_budget_for_acme:.2f}.

Rules (Initiator):
- Max 3 rounds (0, 1, 2).
- Your offers must be >= previous offer (monotonic increase/stagnation).
- Agreement if: partner counter <= your current offer OR your current offer >= partner's previous counter.
Decide your offer.
        """
        user_prompt = f"""
Negotiation Status ({negotiation_item} with {partner_agent_name}):
- Round: {negotiation_round} (max 2)
- Your budget for item: {item_budget_for_acme:.2f}
- Partner's auction acceptance price: {auction_price:.2f}
- Your previous offer to partner: {prev_acme_offer:.2f}
- Partner's previous counter-offer: {prev_partner_counter:.2f}
- Estimated other negotiators for this item: {other_negotiators_count}

Task:
Think step by step.
1. New offer must be >= {prev_acme_offer:.2f}.
2. Strategy: Start below {auction_price:.2f}.
   - If {prev_partner_counter:.2f} > 0 & new offer >= {prev_partner_counter:.2f}, agreement possible.
   - Round 0: Offer significantly below {auction_price:.2f} (e.g., 70-80%).
3. Offer should ideally not exceed {auction_price:.2f}.
4. Final round (2) is critical.
Output JSON: {{"reasoning": "...", "negotiation_offer": <float>}}
        """
        llm_response = call_gemini_llm(self.name, "ACME", "Negotiation", negotiation_item, negotiation_round, system_prompt, user_prompt)

        offer = auction_price # Fallback
        if "error" not in llm_response and "negotiation_offer" in llm_response and isinstance(llm_response["negotiation_offer"],(int,float)):
            offer = float(llm_response["negotiation_offer"])
        
        if negotiation_round > 0 and offer < prev_acme_offer: offer = prev_acme_offer
        if negotiation_round == 0 and (offer <= 0 or offer > auction_price * 0.9): offer = auction_price * 0.7
        if offer > auction_price : offer = auction_price
        if offer <= 0 and auction_price > 0 : offer = auction_price * 0.1
        elif offer <=0 : offer = 1.0


        state["previous_offer_acme"] = offer
        return offer

    def notify_partner_response(self, response_msg: NegotiationMessage) -> None:
        item, partner_name, offer = response_msg.negotiation_item, response_msg.sender, response_msg.offer
        if item not in self.negotiation_states: self.negotiation_states[item] = {}
        if partner_name not in self.negotiation_states[item]: # Should be init by provide_negotiation_offer
             self.negotiation_states[item][partner_name] = {
                "previous_offer_acme": 0.0, 
                "partner_previous_counter_offer": 0.0,
                "auction_agreed_price": self.previous_auction_offers.get(item, self.budget_dict.get(item,0.0))
            }
        self.negotiation_states[item][partner_name]["partner_previous_counter_offer"] = offer
        print(f"ACME ({self.name}) notified: Partner {partner_name} response for {item} is {offer:.2f}")

    def notify_negotiation_winner(self, negotiation_item: str, winning_agent_name: str, winning_offer: float) -> None:
        print(f"ACME ({self.name}) notified: Nego for {negotiation_item} won by {winning_agent_name} at {winning_offer:.2f}")
        if negotiation_item in self.negotiation_states:
            # Keep state for learning, or mark as completed. For simplicity, can remove.
            # self.negotiation_states[negotiation_item].clear() # Or del specific partner if needed
            pass


class MyCompanyAgent(CompanyAgent):
    def __init__(self, role: str, specialties: List[Dict[str, Any]]):
        super(MyCompanyAgent, self).__init__(role, specialties)
        self.contracts_won_count: int = 0
        self.negotiation_competitors: Dict[str, int] = {}
        self.previous_negotiation_counter_offers: Dict[str, float] = {}
        self.auction_agreed_prices: Dict[str, float] = {}

    def _get_cost_for_item(self, item_name: str) -> Optional[float]:
        return self.specialties.get(item_name)

    def decide_bid(self, auction_item: str, auction_round: int, acme_proposed_price: float) -> bool:
        your_cost = self._get_cost_for_item(auction_item)
        if your_cost is None: return False # Cannot bid if not a specialty

        system_prompt = f"""
You are Contractor Company {self.name} ({self.role}). You are in a 'Reverse Dutch Auction' by ACME.
Primary goal: win >=1 contract. Secondary: maximize profit (offer - cost).
Your specialties & costs: {json.dumps(self.specialties)}

Auction Rules:
- ACME proposes price. Bid if item is your specialty & price >= your cost.
- Successful bid leads to negotiation. Max 3 auction rounds (0,1,2).
Decide whether to bid.
        """
        user_prompt = f"""
Auction Status for Company {self.name} ({self.role}):
- Item: "{auction_item}", Round: {auction_round} (max 2)
- ACME's Proposed Price for "{auction_item}": {acme_proposed_price:.2f}
- Your Cost for "{auction_item}": {your_cost:.2f}
- Contracts Won by You: {self.contracts_won_count}

Task:
Think step by step.
1. Bid only if {acme_proposed_price:.2f} >= {your_cost:.2f}.
2. Goals: If {self.contracts_won_count} == 0, strong incentive to bid if price >= cost. Good profit is also a factor.
3. Round consideration: Early round (0) + acceptable offer = secure negotiation. Late round (2) + acceptable offer = crucial bid.
Output JSON: {{"reasoning": "...", "decision_to_bid": <true_or_false>}}
        """
        llm_response = call_gemini_llm(self.name, f"Company {self.role}", "Auction", auction_item, auction_round, system_prompt, user_prompt)

        decision = False # Fallback
        if "error" not in llm_response and "decision_to_bid" in llm_response and isinstance(llm_response["decision_to_bid"], bool):
            decision = bool(llm_response["decision_to_bid"])
        
        if your_cost is not None and acme_proposed_price < your_cost: # Enforce cannot bid below cost
            decision = False
        
        if decision: self.auction_agreed_prices[auction_item] = acme_proposed_price
        return decision

    def notify_won_auction(self, auction_item: str, auction_round: int, num_selected: int):
        self.negotiation_competitors[auction_item] = num_selected
        # auction_agreed_prices should have been set if agent decided to bid
        print(f"Company {self.name} notified: Won auction for {auction_item} (rnd {auction_round}). Num selected: {num_selected}. Agreed price: {self.auction_agreed_prices.get(auction_item, 'N/A')}")

    def respond_to_offer(self, initiator_msg: NegotiationMessage) -> float:
        item, acme_offer, round_num = initiator_msg.negotiation_item, initiator_msg.offer, initiator_msg.round
        your_cost = self._get_cost_for_item(item)
        if your_cost is None: return acme_offer * 2.0 # Problem: Should not happen

        auction_price = self.auction_agreed_prices.get(item, your_cost * 1.1) # Fallback
        prev_counter = self.previous_negotiation_counter_offers.get(item, auction_price) # First "previous" is auction price
        num_comps = self.negotiation_competitors.get(item, 1)

        system_prompt = f"""
You are Contractor Company {self.name} ({self.role}), in 'Monotonic Concession Negotiation' for "{item}" with ACME.
Primary goal: win >=1 contract. Secondary: profit (counter_offer - cost).
Your cost for "{item}": {your_cost:.2f}. Initial auction price was {auction_price:.2f}.

Rules (Responder):
- Max 3 rounds (0,1,2).
- Your counter-offers must be <= previous counter (currently {prev_counter:.2f}).
- Agreement if: your counter <= ACME's current offer OR ACME's next offer >= your current counter.
- {num_comps} companies (incl. you) are negotiating for this item.
Decide your counter-offer.
        """
        user_prompt = f"""
Negotiation Status ({item} for Co. {self.name}):
- Round: {round_num} (max 2)
- ACME's Current Offer: {acme_offer:.2f}
- Your Implicit Previous Counter-Offer: {prev_counter:.2f}
- Your Cost for "{item}": {your_cost:.2f}
- Auction Price for "{item}": {auction_price:.2f}
- Contracts Won by You: {self.contracts_won_count}
- Total Competitors (incl. you) for this item: {num_comps}

Task:
Think step by step.
1. Counter-offer MUST be >= {your_cost:.2f}.
2. Counter-offer MUST be <= {prev_counter:.2f} (monotonic concession).
3. Strategy:
    - If {acme_offer:.2f} >= {your_cost:.2f}:
        - To accept: counter_offer = {acme_offer:.2f}. (Strong if {self.contracts_won_count}==0 or {num_comps}>1).
        - Else, counter_offer < {prev_counter:.2f} but >= {acme_offer:.2f} (or slightly higher).
    - If {acme_offer:.2f} < {your_cost:.2f}: Cannot accept. Counter_offer >= {your_cost:.2f}. Concede from {prev_counter:.2f} if possible.
4. Final round (2): Strongly consider accepting if ACME's offer >= cost. Else, best possible counter.
Output JSON: {{"reasoning": "...", "counter_offer": <float>}}
        """
        llm_response = call_gemini_llm(self.name, f"Company {self.role}", "Negotiation", item, round_num, system_prompt, user_prompt)
        
        counter_offer = prev_counter # Fallback
        if "error" not in llm_response and "counter_offer" in llm_response and isinstance(llm_response["counter_offer"], (int,float)):
            counter_offer = float(llm_response["counter_offer"])

        if counter_offer < your_cost: counter_offer = your_cost
        # Ensure monotonic concession (for rounds > 0, or if current counter > initial auction price)
        if (round_num > 0 and counter_offer > prev_counter) or \
           (round_num == 0 and counter_offer > auction_price) :
            counter_offer = prev_counter if round_num > 0 else auction_price
        
        self.previous_negotiation_counter_offers[item] = counter_offer
        return counter_offer

    def notify_contract_assigned(self, construction_item: str, price: float) -> None:
        self.contracts_won_count += 1
        print(f"Company {self.name} notified: Contract ASSIGNED for {construction_item} at {price:.2f}. Total: {self.contracts_won_count}")
        # Clean up state for this item
        self.negotiation_competitors.pop(construction_item, None)
        self.previous_negotiation_counter_offers.pop(construction_item, None)
        # self.auction_agreed_prices.pop(construction_item, None) # Optionally keep for record

    def notify_negotiation_lost(self, construction_item: str) -> None:
        print(f"Company {self.name} notified: Negotiation LOST for {construction_item}")
        self.negotiation_competitors.pop(construction_item, None)
        self.previous_negotiation_counter_offers.pop(construction_item, None)

