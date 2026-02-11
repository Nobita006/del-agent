import re
from datetime import datetime
import os

def parse_date_from_filename(filename):
    """
    Extracts date from filename in format 'Name_DDMMYYYY.xlsx'.
    Returns datetime object or None.
    """
    # Look for 8 digits pattern at the end of the name (before extension)
    match = re.search(r'_(\d{8})\.', filename)
    if match:
        date_str = match.group(1)
        try:
            return datetime.strptime(date_str, "%d%m%Y").date()
        except ValueError:
            return None
    return None

def get_latest_file(directory, pattern="*.xlsx"):
    """
    Scans directory for files matching pattern, parses dates, 
    and returns the file with the latest date.
    """
    files = []
    if not os.path.exists(directory):
        return None
        
    for f in os.listdir(directory):
        if f.endswith(".xlsx") or f.endswith(".xls"):
            date = parse_date_from_filename(f)
            if date:
                files.append({'file': f, 'date': date, 'path': os.path.join(directory, f)})
    
    if not files:
        return None
        
    # Sort by date descending
    files.sort(key=lambda x: x['date'], reverse=True)
    return files[0]

def get_all_files(directory):
    """
    Scans directory and returns ALL valid excel files with dates, sorted descending.
    """
    files = []
    if not os.path.exists(directory):
        return []
        
    for f in os.listdir(directory):
        if f.endswith(".xlsx") or f.endswith(".xls"):
            date = parse_date_from_filename(f)
            if date:
                files.append({'file': f, 'date': date, 'path': os.path.join(directory, f)})
    
    files.sort(key=lambda x: x['date'], reverse=True)
    return files
