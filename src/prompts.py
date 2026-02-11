from fuzzywuzzy import process

SYSTEM_PROMPT = """
You are an expert Python Data Analyst. Your goal is to answer questions by writing EFFICIENT and ACCURATE pandas code.

You have access to a pandas DataFrame named `df`.
The dataframe contains employee availability and project allocation data.

## Rules:
1. **Return ONLY Python code**. No markdown, no explanations, no `print()` unless asked.
2. **Output Variables**:
   - `result`: The final answer (number, list, or string).
   - `explanation`: A string describing EXACTLY how to verify this in Excel.
     - Format: "Filter Column X by 'Value', then Count/Sum Column Y."
     - Example: "Filter 'Office Location' by 'Delhi', then filter 'Deployment Status' by 'Non-Billable'. Count the rows."
3. **Role Distinction**:
   - if User asks for "Consultant", they mean EXACLTY `designation == 'Consultant'`. DO NOT include 'Senior Consultant'.
   - If User asks for "Senior Consultant", match exactly.
   - If user asks for "All Consultants", match string "Consultant".
4. **Dates**: If asked about current month/status, assume the data is already filtered for the latest report date.
5. **Memory**: use the provided conversation history to resolve "them", "it", "previous", etc.

## Schema:
{schema_context}

## Valid Values for Key Columns:
{values_context}

## Chat History:
{chat_history}

## Similar Past Examples (Few-Shot):
{few_shot_examples}

## Question:
{user_question}

## Constraints:
- If counting people, always use `df['employee_id'].nunique()` if `employee_id` exists, otherwise `len(df)`.
- Drop duplicates if necessary.
"""

ERROR_PROMPT = """
The previous code failed with this error:
{error_message}

Fix the code. Return ONLY the fixed Python code.
"""

# Golden Queries Library (Question -> Code pattern)
# These are "known good" patterns for this specific excel structure
GOLDEN_QUERIES = [
    {
        "q": "How many non-billable people are in Delhi?",
        "code": "df_filtered = df[(df['office_location'].str.contains('Delhi', case=False, na=False)) & (df['deployment_status'] == 'NON BILLABLE')]\nresult = df_filtered['employee_id'].nunique()\nexplanation = \"Filter 'Office Location' for 'Delhi' (matches Delhi, Delhi-NCR) and 'Deployment Status' for 'NON BILLABLE'. Count unique Employee IDs.\""
    },
    {
        "q": "List all people in Mumbai office",
        "code": "result = df[df['office_location'] == 'Mumbai']['employee_name'].tolist()\nexplanation = \"Filter 'Office Location' for 'Mumbai'. List the 'Employee Name' column.\""
    },
    {
        "q": "What is the bench strength?",
        "code": "result = df[df['spine_current_status'] == 'Available']['employee_id'].nunique()\nexplanation = \"Filter 'sPInE Current status' for 'Available'. Count unique Employee IDs.\""
    },
    {
        "q": "Count of interns",
        "code": "result = df[df['category'] == 'INTERN']['employee_id'].nunique()\nexplanation = \"Filter 'Category' for 'INTERN'. Count unique Employee IDs.\""
    },
    {
        "q": "How many Consultants vs Senior Consultants?",
        "code": "consultants = df[df['designation'] == 'Consultant']['employee_id'].nunique()\nsniors = df[df['designation'] == 'Senior Consultant']['employee_id'].nunique()\nresult = {'Consultant': consultants, 'Senior Consultant': sniors}\nexplanation = \"Filter 'Designation' exactly for 'Consultant' vs 'Senior Consultant'. Count unique Employee IDs for each.\""
    }
]

def get_few_shot_examples(user_question, k=3):
    """
    Returns the top k most similar golden queries formatted as a string.
    """
    questions = [g['q'] for g in GOLDEN_QUERIES]
    
    # Check for empty questions list to avoid extraction error
    if not questions:
        return "No examples available."

    matches = process.extract(user_question, questions, limit=k)
    
    examples_str = ""
    for match_q, score in matches:
        if score > 50: # Only include relevant ones
            # Find the code for this question
            match_code = next(g['code'] for g in GOLDEN_QUERIES if g['q'] == match_q)
            examples_str += f"Q: {match_q}\nA:\n```python\n{match_code}\n```\n\n"
            
    return examples_str if examples_str else "No similar examples found."
