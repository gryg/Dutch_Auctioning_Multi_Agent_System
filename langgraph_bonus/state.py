from typing import List, Dict, Any, Optional, TypedDict

class NegotiationMessageRecord(TypedDict):
    round: int
    actor: str 
    acme_offers: Optional[Dict[str, float]] 
    company_name: Optional[str]
    company_response_to_acme: Optional[float]
    acme_offer_received: Optional[float]

class NegotiationState(TypedDict):
    current_item: str
    negotiation_round: int
    max_negotiation_rounds: int
    acme_agent_name: str
    active_companies: List[Dict[str, Any]] 
    acme_current_offers_for_round: Dict[str, float] 
    company_current_responses_for_round: Dict[str, float] 
    history: List[NegotiationMessageRecord]
    negotiation_complete: bool
    final_agreement_price: Optional[float]
    winning_company: Optional[str]
    next_actor_in_round: Optional[str] 
    companies_acted_this_round: List[str]