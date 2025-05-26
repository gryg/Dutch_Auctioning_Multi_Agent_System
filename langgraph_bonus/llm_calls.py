import json
import google.generativeai as genai
from .config import IS_GEMINI_CONFIGURED 

# --- Global Log for LLM Interactions ---
langgraph_llm_interactions_log = []

def call_gemini_llm_for_langgraph(agent_name: str, system_prompt: str, user_prompt: str):
    global langgraph_llm_interactions_log # ensure the global list is the one being modified
    log_entry = {
        "agent_name": agent_name,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "llm_response": None
    }

    if not IS_GEMINI_CONFIGURED:
        error_response = {"reasoning": "LLM call skipped: API key not configured.", "error": "API key missing"}
        if "ACME" in agent_name: error_response["negotiation_offer"] = 0.0
        else: error_response["counter_offer"] = float('inf')
        log_entry["llm_response"] = error_response
        langgraph_llm_interactions_log.append(log_entry)
        return error_response

    try:
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash-latest',
            generation_config={"temperature": 0.0, "response_mime_type": "application/json"},
            system_instruction=system_prompt
        )
        print(f"\n--- Calling Gemini for LangGraph Agent: {agent_name} ---")
        response = model.generate_content(user_prompt)
        
        response_text = ""
        if response.parts:
            response_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))
        elif hasattr(response, 'text'): 
            response_text = response.text
            
        if not response_text and hasattr(response, 'candidates') and response.candidates and \
           hasattr(response.candidates[0], 'content') and response.candidates[0].content.parts:
             response_text = "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, 'text'))
        
        if not response_text: 
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                raise ValueError(f"LLM call blocked for {agent_name}. Reason: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason}")
            raise ValueError(f"LLM returned empty or unreadable response content for {agent_name}.")

        parsed_json = json.loads(response_text)
        print(f"LLM Response for {agent_name}:\n{json.dumps(parsed_json, indent=2)}")
        log_entry["llm_response"] = parsed_json
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from LLM response for {agent_name}: {e}")
        raw_text_for_error = response_text if 'response_text' in locals() and response_text else "Raw response text not available or empty."
        print(f"LLM raw response text was: {raw_text_for_error}")
        parsed_json = {"reasoning": f"Error decoding LLM JSON response: {e}. Raw: {raw_text_for_error}", "error": str(e)}
        log_entry["llm_response"] = parsed_json
    except Exception as e:
        print(f"Error calling Gemini for {agent_name}: {e}")
        parsed_json = {"reasoning": f"Error in LLM call: {e}", "error": str(e)}
        log_entry["llm_response"] = parsed_json
        
    langgraph_llm_interactions_log.append(log_entry)
    return parsed_json