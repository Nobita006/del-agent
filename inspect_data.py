import pandas as pd
import os

FILE_PATH = "AvailabilityTracker_16102025.xlsx"

def inspect_excel():
    if not os.path.exists(FILE_PATH):
        print(f"Error: {FILE_PATH} not found.")
        return

    print(f"--- Inspecting {FILE_PATH} ---\n")
    
    try:
        xl = pd.ExcelFile(FILE_PATH)
        print(f"Sheet Names: {xl.sheet_names}")
        
        target_sheet = "Availability Tracker"
        if target_sheet not in xl.sheet_names:
            print(f"WARNING: '{target_sheet}' sheet not found! Using first sheet: '{xl.sheet_names[0]}'")
            target_sheet = xl.sheet_names[0]
            
        df = pd.read_excel(FILE_PATH, sheet_name=target_sheet)
        
        print(f"\n--- Sheet: {target_sheet} ---")
        print(f"Shape: {df.shape}")
        print("\nColumns & Types:")
        print(df.dtypes)
        
        print("\n--- Sample Data (First 3 rows) ---")
        print(df.head(3).to_markdown(index=False))
        
        print("\n--- Unique Values in Categorical-looking Columns ---")
        potential_categoricals = [col for col in df.columns if df[col].dtype == 'object' and df[col].nunique() < 50]
        for col in potential_categoricals:
            print(f"\nColumn: {col}")
            print(df[col].unique()[:10]) # Show first 10 unique
            
    except Exception as e:
        print(f"Error reading excel: {e}")

if __name__ == "__main__":
    inspect_excel()
