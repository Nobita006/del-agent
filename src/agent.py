import pandas as pd
import os
import google.generativeai as genai
from .utils import get_latest_file
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
        self.chat_history = []  # List of {"role": "user/assistant", "content": "..."}
        
        # Setup Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("WARNING: GEMINI_API_KEY not found in .env")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-3-flash-preview') 

    def load_data(self):
        """
        Loads the latest Excel file, standardizes columns, and prepares schema.
        """
        # For now, we look in current dir for testing, or data_dir
        # The user seems to have file in root.
        root_file = get_latest_file(".")
        data_file = get_latest_file(self.data_dir)
        
        latest = root_file if root_file else data_file
        
        if not latest:
            return "No Excel file found."
            
        try:
            file_path = latest['path']
            self.report_date = latest['date']
            
            # Read specific sheet
            self.df = pd.read_excel(file_path, sheet_name="Availability Tracker")
            
            # Standardize Headers: Snake Case
            # e.g. "Office Location" -> "office_location"
            self.df.columns = [
                str(col).strip().lower()
                .replace(" ", "_").replace("-", "_").replace("/", "_").replace(".", "")
                for col in self.df.columns
            ]
            
            # Specific Mappings for bad headers
            rename_map = {
                "emplo+a514+a1+a1:n18": "employee_id",
                "rm_name": "reporting_manager",
                "lwd": "last_working_day"
            }
            self.df.rename(columns=rename_map, inplace=True)
            
            # Parse Dates
            if 'date_of_joining' in self.df.columns:
                self.df['date_of_joining'] = pd.to_datetime(self.df['date_of_joining'], errors='coerce')
                
            self._prepare_context()
            self.chat_history = [] # Reset history on new file load
            return f"Loaded data from {latest['file']} (Date: {self.report_date})"
            
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
        local_vars = {
            "df": self.df, 
            "pd": pd, 
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
        code = self.generate_code(question)
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
