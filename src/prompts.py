from fuzzywuzzy import process

SYSTEM_PROMPT = """
You are an expert Python Data Analyst. Your goal is to answer questions by writing EFFICIENT and ACCURATE pandas code.

You have access to a pandas DataFrame named `df`.
The dataframe contains employee availability and project allocation data.

## Rules:
1. **Return ONLY Python code**. No markdown, no explanations, no `print()` unless asked.
2. **Relevance Check**:
   - if the question is NOT related to the dataframe (e.g. "What is 2+2?", "Capital of France?", "Write a poem"), return:
     `result = "I can only answer questions about the provided Employee/Availability data."`
     `explanation = "Question is outside the scope of the provided dataset."`
   - If the question asks for a column NOT in the **Schema**, return:
     `result = "I cannot answer this as the data does not contain that information."`
     `explanation = "The available columns are: [List of similar columns]."`
3. **Output Variables**:
   - `result`: The final answer.
     - **CHARTS**: If asked to plot/chart, use `import matplotlib.pyplot as plt`. Create a figure `fig, ax = plt.subplots()`. Plot data. Assign `result = fig`.
     - **LISTS/TABLES**: If asked to list details, `result` must be a `pd.DataFrame` or `list`.
     - **AMBIGUITY**: If a filter matches MULTIPLE distinct values (e.g. 'Bengaluru' and 'Bengaluru Eco space'), `result` MUST show the breakdown.
       - Logic: Find ALL matches, count, reindex.
       - Example: "Total: 101\n- Bengaluru: 101\n- Bengaluru Eco space: 0"
   - `explanation`: A string describing EXACTLY how to verify this in Excel.
     - **Format**: "Step 1: Filter Column 'X' to select values [A, B]. Step 2: ... "
     - Example: "Filter 'Office Location' to select BOTH 'Bengaluru' and 'Bengaluru Eco space'. Then filter 'Designation' to 'Analyst'."
4. **Role Distinction**:
   - if User asks for "Consultant", they mean EXACLTY `designation == 'Consultant'`. DO NOT include 'Senior Consultant'.
   - If User asks for "Senior Consultant", match exactly.
   - If user asks for "All Consultants", match string "Consultant".
5. **Dates & History**:
   - The dataframe contains multiple reports distinguished by `report_date` (datetime).
   - **Default Behavior**: If the user asks about "current" status or gives no date, filter `df` to the **LATEST REPORT DATE**.
     - Code: `latest_date = df['report_date'].max(); df_latest = df[df['report_date'] == latest_date]`
   - **History/Comparison**: If user asks for "history", "trend", "previous", or specific dates:
     - Use `report_date` column to filter specific slices.
     - Example: "Compare 2025-10-16 vs 2025-10-09".
6. **Memory**: use the provided conversation history to resolve "them", "it", "previous", etc.

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
        "q": "How many consultants in Delhi?",
        "code": "term = 'Delhi'\n# 1. Identify ALL matching locations first\nall_locs = df[df['office_location'].str.contains(term, case=False, na=False)]['office_location'].unique()\n\n# 2. Filter for Consultant\nconsultants = df[df['designation'] == 'Consultant']\n\n# 3. Filter for Location in that set\nmatches = consultants[consultants['office_location'].isin(all_locs)]\n\n# 4. Breakdown with Zeros (reindex)\nbreakdown = matches['office_location'].value_counts().reindex(all_locs, fill_value=0)\n\nif len(all_locs) > 1:\n    breakdown_str = '\\n'.join([f'- {k}: {v}' for k,v in breakdown.items()])\n    result = f\"Total: {len(matches)}\\n{breakdown_str}\"\n    explanation = f\"Step 1: Identify locations matching '{term}': {', '.join(all_locs)}. Step 2: Filter 'Designation' to 'Consultant'. Step 3: Count unique IDs for each location.\"\nelse:\n    result = len(matches)\n    explanation = f\"Filter 'Designation' to 'Consultant' and 'Office Location' to '{term}'.\""
    },
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
    },
    {
        "q": "Compare the number of consultants last week vs this week",
        "code": "# Get sorted unique dates\ndates = sorted(df['report_date'].unique())\nif len(dates) < 2:\n    result = \"Not enough historical data to compare.\"\n    explanation = \"Need at least 2 report dates.\"\nelse:\n    latest = dates[-1]\n    previous = dates[-2]\n    \n    # Filter for Consultant\n    cons_latest = df[(df['report_date'] == latest) & (df['designation'] == 'Consultant')]['employee_id'].nunique()\n    cons_prev = df[(df['report_date'] == previous) & (df['designation'] == 'Consultant')]['employee_id'].nunique()\n    \n    diff = cons_latest - cons_prev\n    result = f\"Latest ({latest.date()}): {cons_latest}\\nPrevious ({previous.date()}): {cons_prev}\\nChange: {diff:+}\"\n    explanation = f\"Filter 'report_date' for {latest.date()} vs {previous.date()}. Count unique 'employee_id' for 'Consultant' in each.\""
    },
    {
        "q": "Show a bar chart of consultants by location",
        "code": "import matplotlib.pyplot as plt\n\n# Filter\ndf_cons = df[df['designation'] == 'Consultant']\ncounts = df_cons['office_location'].value_counts()\n\n# Plot\nfig, ax = plt.subplots(figsize=(10, 6))\ncounts.plot(kind='bar', ax=ax, color='skyblue')\nax.set_title('Consultants by Location')\nax.set_ylabel('Count')\nplt.tight_layout()\n\nresult = fig\nexplanation = \"Filter 'Designation' to 'Consultant'. Group by 'Office Location' and count. Plot values.\""
    },
    {
        "q": "List all consultants in Mumbai",
        "code": "result = df[(df['designation'] == 'Consultant') & (df['office_location'].str.contains('Mumbai', case=False, na=False))][['employee_id', 'employee_name', 'email_id', 'office_location']]\nexplanation = \"Filter 'Designation' to 'Consultant' and 'Office Location' to 'Mumbai'. Return relevant columns.\""
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
