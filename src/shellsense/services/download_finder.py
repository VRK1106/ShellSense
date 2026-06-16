import os
import re

def get_last_downloaded_file():
    downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
    if not os.path.exists(downloads_path):
        return None
        
    ignored_extensions = ('.crdownload', '.tmp', '.part', '.download')
    
    files = []
    try:
        for f in os.listdir(downloads_path):
            filepath = os.path.join(downloads_path, f)
            if os.path.isfile(filepath):
                _, ext = os.path.splitext(f)
                if ext.lower() not in ignored_extensions:
                    files.append(filepath)
    except Exception:
        return None
                
    if not files:
        return None
        
    try:
        files.sort(key=os.path.getmtime, reverse=True)
        return files[0]
    except Exception:
        return None

def evaluate_last_download(query: str):
    q = query.lower().strip()
    
    # Match "open last download", "open last downloaded file", etc.
    open_match = re.match(r'^open\s+last\s+download(ed)?(\s+file)?$', q)
    # Match "copy last download", "copy last downloaded file", etc.
    copy_match = re.match(r'^copy\s+last\s+download(ed)?(\s+file)?$', q)
    
    if not open_match and not copy_match:
        return False, None
        
    filepath = get_last_downloaded_file()
    if not filepath:
        return True, "Error: No downloaded files found in Downloads folder"
        
    filename = os.path.basename(filepath)
    
    if open_match:
        return True, f"Opened File: {filepath}|{filename}"
    else:
        return True, f"Copied File: {filepath}|{filename}"
