# Multi-Agent System for Construction Contract Negotiation

This project simulates a multi-agent system where a primary company (ACME) negotiates contracts for various construction items with several contractor companies. The simulation involves a Reverse Dutch Auction phase followed by a Monotonic Concession Negotiation phase. Agents' reasoning is powered by the Gemini LLM.

This README provides instructions on how to set up and run the two main parts of this project:
1.  The main simulation driven by `environment.py`.
2.  The LangGraph bonus task demonstrating a specific negotiation scenario.

## Prerequisites

Before running either solution, ensure you have the following:

1.  **Python**: Python 3.8 or higher is recommended.
2.  **Git**: To clone the repository (if applicable).
3.  **Gemini API Key**: You need a valid Gemini API key.
    * This key should be associated with a Google Cloud Project where billing is enabled to avoid free-tier rate limits.
    * Store your API key in a file named `.env` in the root directory of this project. The file should have one line:
        ```
        GEMINI_API_KEY=YOUR_ACTUAL_GEMINI_API_KEY
        ```
4.  **Project Files**: Ensure all project files are present, including:
    * `base.py`
    * `communication.py`
    * `environment.py`
    * `game.cfg`
    * `config-ACME-project.cfg`
    * `config-companies.cfg`
    * `logging_conf.yaml`
    * `.env` (with your API key)
    * `agents/` directory containing:
        * `__init__.py`
        * `student_agent.py` (the version with Gemini LLM calls)
    * `langgraph_bonus/` directory (for the bonus task) containing:
        * `__init__.py`
        * `config.py`
        * `graph.py`
        * `llm_calls.py`
        * `main.py`
        * `nodes.py`
        * `state.py`

## Setup: Virtual Environment and Dependencies

It is highly recommended to use a Python virtual environment to manage dependencies and avoid conflicts with system-wide packages.

1.  **Create a Virtual Environment**:
    Open your terminal or command prompt in the root directory of the project and run:
    ```bash
    python -m venv venv
    ```

2.  **Activate the Virtual Environment**:
    * **Windows (cmd.exe)**:
        ```bash
        venv\Scripts\activate.bat
        ```
    * **Windows (PowerShell)**:
        ```bash
        .\venv\Scripts\Activate.ps1
        ```
        (If you encounter an execution policy error in PowerShell, you might need to run `Set-ExecutionPolicy Unrestricted -Scope Process` first).
    * **macOS and Linux (bash/zsh)**:
        ```bash
        source venv/bin/activate
        ```
    Your terminal prompt should now indicate that the `(venv)` is active.

3.  **Install Required Packages**:
    Create a `requirements.txt` file in the root of your project with the following content:

    ```txt
    # requirements.txt
    google-generativeai
    python-dotenv
    PyYAML
    scipy
    langgraph
    # langchain-google-genai # Only if directly used; current setup uses google-generativeai
    typing_inspect
    typing_extensions
    ```
    Then, with your virtual environment active, install these packages:
    ```bash
    pip install -r requirements.txt
    ```

## Running Solution 1: Main Simulation (`environment.py`)

This solution runs the full simulation involving all construction items, auctions, and negotiations as driven by the `BuildingEnvironment`.

1.  **Ensure Prerequisites and Setup** are completed (virtual environment active, packages installed, `.env` file ready).
2.  **Navigate to Project Root Directory**:
    If you are not already there, `cd` into the root directory where `environment.py` is located.
3.  **Run the Simulation**:
    ```bash
    python environment.py
    ```
4.  **Output**:
    * The console will display printouts from the environment, showing the progress of auction and negotiation rounds for each item.
    * It will also show messages from the `student_agent.py` indicating when Gemini API calls are made and their responses (e.g., "Calling Gemini for...", "LLM RESPONSE (Actual for...)").
    * At the end of the simulation, a summary of all LLM interactions will be printed to the console, and a file named `llm_interactions_log.jsonl` will be created in the root directory containing these detailed logs. This is handled by the modifications made to `environment.py` to process `llm_interactions_log` from `agents.student_agent`.

## Running Solution 2: LangGraph Bonus Task (`langgraph_bonus/main.py`)

This solution runs specific negotiation scenarios for a single construction item ("structural design") using the LangGraph framework.

1.  **Ensure Prerequisites and Setup** are completed (virtual environment active, packages installed, `.env` file ready in the project root).
2.  **Run the LangGraph Scenarios**:
    Execute the `main.py` script:
    ```bash
    python -m langgraph_bonus.main
    ```
    *(Alternatively, if you are in the project root directory and `langgraph_bonus` is a Python package there, you could try `python -m langgraph_bonus.main`)*
3.  **Output**:
    * The console will display printouts specific to the LangGraph execution, including which agent is taking a turn and the LLM calls being made within the LangGraph nodes.
    * The final state of each scenario (e.g., winning company and price) will be printed.
    * A log file named `langgraph_bonus_llm_interactions.jsonl` will be created containing the LLM interactions for the LangGraph scenarios.
