import os
from dotenv import load_dotenv
import google.generativeai as genai

# --- Load Environment Variables & Configure Gemini ---
load_dotenv() # Searches for .env in current dir or parent dirs
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def configure_gemini():
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        print("Gemini API configured.")
        return True
    else:
        print("WARNING: GEMINI_API_KEY not found. LLM calls will use fallback/fail.")
        return False

IS_GEMINI_CONFIGURED = configure_gemini()

# --- Constants for Scenarios ---
ACME_BUDGET_STRUCTURAL_DESIGN = 5000.0
COMPANY_B_COST_STRUCTURAL_DESIGN = 3602.0
COMPANY_F_COST_STRUCTURAL_DESIGN = 4900.0
ITEM_NAME = "structural design"
MAX_NEGOTIATION_ROUNDS = 3 # Rounds 0, 1, 2