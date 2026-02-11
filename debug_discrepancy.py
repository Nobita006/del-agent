import pandas as pd
from src.utils import get_latest_file

def debug_data():
    # Load Data
    latest = get_latest_file("data")
    if not latest:
        # Fallback to current dir if not found in data
        latest = get_latest_file(".")
    
    if not latest:
        print("No file found in 'data' or '.'")
        return

    print(f"Loading: {latest['path']}")
    df = pd.read_excel(latest['path'], sheet_name="Availability Tracker")
    
    # Standardize
    df.columns = [str(col).strip().lower().replace(" ", "_").replace("-", "_").replace("/", "_").replace(".", "") for col in df.columns]
    rename_map = {
        "emplo+a514+a1+a1:n18": "employee_id",
        "rm_name": "reporting_manager",
        "lwd": "last_working_day"
    }
    df.rename(columns=rename_map, inplace=True)
    
    # 1. Filter: Designation == 'Consultant'
    consultants = df[df['designation'] == 'Consultant']
    
    # 2. Filter: Location contains 'Delhi'
    delhi_consultants = consultants[consultants['office_location'].str.contains('Delhi', case=False, na=False)]
    
    print(f"Total Consultants: {len(consultants)}")
    print(f"Consultants in 'Delhi' (Partial Match): {len(delhi_consultants)}")
    print(f"Unique IDs in 'Delhi' (Partial Match): {delhi_consultants['employee_id'].nunique()}")
    
    # Check unique locations found
    print("\nUnique Locations matched by 'Delhi':")
    locations = delhi_consultants['office_location'].unique()
    print(locations)
    
    for loc in locations:
        count = len(delhi_consultants[delhi_consultants['office_location'] == loc])
        print(f"  - {loc}: {count}")
    
    # Check if any duplicates
    if len(delhi_consultants) != delhi_consultants['employee_id'].nunique():
        print("\nWARNING: Duplicates found!")
        print(delhi_consultants[delhi_consultants.duplicated(subset=['employee_id'], keep=False)])

if __name__ == "__main__":
    debug_data()
