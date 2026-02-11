import pandas as pd
import os
import google.generativeai as genai
from .utils import get_latest_file, get_all_files
from .prompts import SYSTEM_PROMPT, ERROR_PROMPT, get_few_shot_examples
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import google.api_core.exceptions

load_dotenv()

class ExcelAgent:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.df = None
        self.schema_str = ""
        self.values_str = ""
        self.report_date = None
        self.latest_date = None
        self.date_range = []
        self.chat_history = []  # List of {"role": "user/assistant", "content": "..."}
        
        # Setup Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("WARNING: GEMINI_API_KEY not found in .env")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash') 

    def load_data(self):
        """
        Loads ALL Excel files from data directory, adds 'report_date', and concatenates.
        """
        all_files = get_all_files(self.data_dir)
        # Fallback to current dir if data_dir is empty checking
        if not all_files:
            all_files = get_all_files(".")
        
        if not all_files:
            return "No Excel files found."
            
        dfs = []
        self.date_range = []
        
        try:
            for file_info in all_files:
                f_path = file_info['path']
                r_date = file_info['date']
                self.date_range.append(r_date)
                
                # Read
                temp_df = pd.read_excel(f_path, sheet_name="Availability Tracker")
                
                # Standardize Headers
                temp_df.columns = [
                    str(col).strip().lower()
                    .replace(" ", "_").replace("-", "_").replace("/", "_").replace(".", "")
                    for col in temp_df.columns
                ]
                
                # Renaming bad headers
                rename_map = {
                    "emplo+a514+a1+a1:n18": "employee_id",
                    "rm_name": "reporting_manager",
                    "lwd": "last_working_day"
                }
                temp_df.rename(columns=rename_map, inplace=True)
                
                # Add Report Date
                temp_df['report_date'] = pd.to_datetime(r_date)
                
                # Parse internal dates
                if 'date_of_joining' in temp_df.columns:
                    temp_df['date_of_joining'] = pd.to_datetime(temp_df['date_of_joining'], errors='coerce')
                
                dfs.append(temp_df)
            
            # Concat
            self.df = pd.concat(dfs, ignore_index=True)
            self.report_date = max(self.date_range) # Set to latest for default
            
            self._prepare_context()
            self.chat_history = [] 
            
            return f"Loaded {len(all_files)} files. Date Range: {min(self.date_range)} to {max(self.date_range)}."
            
        except Exception as e:
            return f"Error loading data: {str(e)}"

    def _prepare_context(self):
        """
        Creates schema and values strings for the prompt.
        """
        if self.df is None:
            return

        # Schema
        self.schema_str = "\n".join([f"- {col}: {dtype}" for col, dtype in self.df.dtypes.items()])

        # Unique values for important categorical columns
        key_cols = ['office_location', 'category', 'deployment_status', 'status', 'spine_current_status', 'designation']
        values_list = []
        
        # Add available dates
        if self.date_range:
            dates = sorted([d.strftime('%Y-%m-%d') for d in self.date_range], reverse=True)
            values_list.append(f"AVAILABLE REPORT DATES (YYYY-MM-DD): {dates}")
            values_list.append(f"LATEST REPORT DATE: {max(dates)}")

        for col in key_cols:
            if col in self.df.columns:
                uniques = self.df[col].dropna().unique().tolist()
                # Limit to top 20 to avoid token overflow
                if len(uniques) > 20: 
                    uniques = uniques[:20] + ["..."]
                values_list.append(f"{col}: {uniques}")
        self.values_str = "\n".join(values_list)

    def _format_chat_history(self):
        """Format chat history for the prompt."""
        history_str = ""
        # Keep last 10 messages to avoid overflow
        for msg in self.chat_history[-10:]:
            history_str += f"{msg['role'].title()}: {msg['content']}\n"
        return history_str if history_str else "No previous chat history."

    @retry(
        retry=retry_if_exception_type(google.api_core.exceptions.ResourceExhausted),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=4, max=30)
    )
    def generate_code(self, question):
        """
        Generates pandas code using LLM.
        """
        few_shot = get_few_shot_examples(question)
        history_str = self._format_chat_history()
        
        prompt = SYSTEM_PROMPT.format(
            schema_context=self.schema_str,
            values_context=self.values_str,
            chat_history=history_str,
            few_shot_examples=few_shot,
            user_question=question
        )
        
        response = self.model.generate_content(prompt)
        code = response.text.strip()
        
        # Clean markdown
        if code.startswith("```python"):
            code = code.replace("```python", "").replace("```", "")
        elif code.startswith("```"):
            code = code.replace("```", "")
            
        return code.strip()

    def execute_code(self, code):
        """
        Executes the generated code in a safe local environment.
        """
        # Sandbox variables
        import matplotlib.pyplot as plt
        import plotly.express as px
        
        local_vars = {
            "df": self.df, 
            "pd": pd,
            "plt": plt,
            "px": px,
            "result": None,
            "explanation": None
        }
        
        try:
            exec(code, {}, local_vars)
            return local_vars.get("result", "No result found"), local_vars.get("explanation", "No explanation provided.")
        except Exception as e:
            return f"Error: {str(e)}", None

    def run(self, question):
        """
        Full pipeline: Generate -> Execute -> Retry.
        Returns a dictionary with 'result' and 'explanation'.
        """
        if self.df is None:
            return {"result": "Data not loaded.", "explanation": ""}
            
        print(f"Generating code for: {question}")
        
        try:
            code = self.generate_code(question)
        except Exception as e:
            print(f"Generation failed: {e}")
            return {"result": "âš ï¸  **Server Busy / Rate Limit Hit**.\nPlease wait 30 seconds and try again.", "explanation": f"API Error: {str(e)}"}

        print(f"Generated Code:\n{code}")
        
        result, explanation = self.execute_code(code)
        
        # Simple Retry Logic
        if str(result).startswith("Error:"):
            print("Code failed. Retrying...")
            # Re-generate with error context
            history_str = self._format_chat_history()
            full_prompt = f"{SYSTEM_PROMPT.format(schema_context=self.schema_str, values_context=self.values_str, chat_history=history_str, few_shot_examples='', user_question=question)}\n\nUser: The previous code failed: {result}. Fix it."
            
            response = self.model.generate_content(full_prompt)
            code = response.text.replace("```python", "").replace("```", "").strip()
            print(f"Retried Code:\n{code}")
            result, explanation = self.execute_code(code)
            
        # Update History
        self.chat_history.append({"role": "user", "content": question})
        self.chat_history.append({"role": "assistant", "content": str(result)})
        
        return {"result": result, "explanation": explanation}
