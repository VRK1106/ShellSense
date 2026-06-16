import os
import re

def get_last_downloaded_file():
    user_profile = os.path.expanduser('~')
    search_dirs = [
        os.path.join(user_profile, 'Downloads'),
        os.path.join(user_profile, 'Desktop'),
        os.path.join(user_profile, 'Documents')
    ]
    
    ignored_extensions = ('.crdownload', '.tmp', '.part', '.download')
    
    files = []
    for d in search_dirs:
        if not os.path.exists(d):
            continue
        try:
            for f in os.listdir(d):
                filepath = os.path.join(d, f)
                if os.path.isfile(filepath):
                    _, ext = os.path.splitext(f)
                    if ext.lower() not in ignored_extensions:
                        files.append(filepath)
        except Exception:
            continue
            
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
        return True, "Error: No downloaded files found in search directories"
        
    filename = os.path.basename(filepath)
    
    if open_match:
        return True, f"Opened File: {filepath}|{filename}"
    else:
        return True, f"Copied File: {filepath}|{filename}"
