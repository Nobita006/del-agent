import re
from datetime import datetime
import os

def parse_date_from_filename(filename, filepath=None):
    """
    Extracts date from filename in format 'Name_DDMMYYYY.xlsx'.
    Returns datetime object from filename if possible.
    If not, and filepath is provided, returns file modification date.
    Otherwise returns None.
    """
    # Look for 8 digits pattern at the end of the name (before extension)
    match = re.search(r'_(\d{8})\.', filename)
    if match:
        date_str = match.group(1)
        try:
            return datetime.strptime(date_str, "%d%m%Y").date()
        except ValueError:
            pass
            
    # Fallback to file modification time if filepath is provided
    if filepath and os.path.exists(filepath):
        timestamp = os.path.getmtime(filepath)
        return datetime.fromtimestamp(timestamp).date()
        
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
            path = os.path.join(directory, f)
            date = parse_date_from_filename(f, filepath=path)
            if date:
                files.append({'file': f, 'date': date, 'path': path})
    
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
            path = os.path.join(directory, f)
            # Pass path for fallback date
            date = parse_date_from_filename(f, filepath=path)
            if date:
                files.append({'file': f, 'date': date, 'path': path})
    
    # Sort files
    if files:
        files.sort(key=lambda x: x['date'], reverse=True)
    return files
