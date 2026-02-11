# Availability Data Excel Agent - Technical Report

## 1. Overview
This project is a high-accuracy, dependability-focused AI Agent designed to answer natural language questions about weekly Employee Availability Excel reports. Unlike standard chatbots, this agent uses a **Code Generation Architecture** to ensure mathematical precision and transparency.

## 2. Architecture & Tools
We prioritized **Determinism** (getting the same correct answer every time) over creativity.

### Technology Stack
-   **LLM Engine**: `gemini-3.0-flash-preview` (Fast, High Reasoning capability).
-   **Backend**: Python (3.12+).
-   **Data Processing**: `pandas` (The gold standard for tabular data manipulation).
-   **Frontend**: `Streamlit` (For a clean, interactive Web UI).
-   **Resilience**: `tenacity` (For auto-retrying API calls on rate limits).
-   **Matching**: `fuzzywuzzy` (For understanding "Delhi" means "Delhi-NCR").
-   **Environment**: Secured via `.env` for API keys.

### The "Text-to-Pandas" Approach
Instead of asking the AI to "read" the Excel file (which is prone to hallucinations on large data), we ask the AI to **write Python code**.
-   **User**: "How many people in Mumbai?"
-   **AI**: Generates `df[df['location']=='Mumbai']['id'].nunique()`
-   **System**: Executes this code on the actual data to get the **exact result**.

## 3. Data Flow Pipeline
1.  **Ingestion**:
    -   User uploads `AvailabilityTracker_16102025.xlsx`.
    -   System auto-detects the date (`2025-10-16`) from the filename.
    -   Data is loaded into a Pandas DataFrame (`df`).
    -   **Sanitization**: Column headers are standardized (snake_case) to prevent "KeyError".
2.  **Context Construction**:
    -   The system extracts the **Schema** (Column Names + Types).
    -   It extracts **Unique Values** for key columns (Location, Designation, Status) to help the LLM understand valid filters.
3.  **Prompt Engineering (The "Brain")**:
    -   The User Question + Schema + Valid Values are sent to Gemini.
4.  **Code Generation & Execution**:
    -   Gemini returns Python code.
    -   System executes it in a **Sandboxed Environment**.
5.  **Output**:
    -   Result is displayed to the user along with a **Verification Explanation**.

## 4. Prompting Techniques Used
We utilized several advanced Prompt Engineering techniques to ensure reliability:

### A. Role Prompting
> *"You are an expert Python Data Analyst. Your goal is to answer questions by writing EFFICIENT and ACCURATE pandas code."*
-   Sets the behavior and strictness level.

### B. Few-Shot Prompting (The "Golden Library")
We feed the model reliable examples of "Question -> Code" pairs in the prompt.
-   *Why?* It teaches the model *how* to handle specific logic (e.g., "Non-Billable" = Status 'Available' OR Deployment 'Non-Billable').
-   *Result:* Consistent answers for complex business logic.

### C. Chain-of-Thought (Explanation Field)
We explicitly ask the model to generate an `explanation` variable:
> *"Describe EXACTLY how to verify this in Excel: 'Filter Column X by Y, then Count Z'."*
-   *Why?* This forces the model to "think" about its logic, reducing errors, and builds **User Trust**.

### D. Self-Correction Loop
If the generated code fails (e.g., Syntax Error), the error is fed *back* to the LLM:
> *"The previous code failed with error X. Fix it."*
-   The agent auto-heals without the user knowing.

## 5. Verification & Reliability Mechanisms
We implemented specific "Guardrails" to handle real-world messiness:

### 1. Ambiguity Handling (The "Breakdown" Logic)
-   **Problem**: User asks for "Delhi". Data has "Delhi" and "Delhi CEC".
-   **Solution**: The prompt instructs: *"If a filter matches MULTIPLE distinct values, return a Breakdown."*
-   **Result**:
    ```text
    Total: 130
    - Delhi: 128
    - Delhi CEC: 2
    ```

### 2. Scope Enforcement
-   **Problem**: Users asking "What is the capital of France?"
-   **Solution**: A "Relevance Check" rule in the system prompt.
-   **Result**: Polite refusal to answer off-topic questions.

### 3. Rate Limit Handling
-   **Problem**: API Quotas ("Resource Exhausted").
-   **Solution**: Used `@retry` decorator to automatically wait and retry (Exponential Backoff) if the API is busy.

## 6. How to Run
1.  **Start**: Double-click `run_agent.bat`.
2.  **Access**: Open `http://localhost:8501`.
3.  **Share**: Setup `ngrok` (as per Walkthrough) to share with friends.
