import os
import re

def get_last_downloaded_file():
    # 1. First, try reading Windows Recent Files folder (.lnk shortcuts)
    recent_dir = os.path.join(os.environ.get('APPDATA', ''), 'Microsoft\\Windows\\Recent')
    if os.path.exists(recent_dir):
        try:
            import win32com.client
            files = [os.path.join(recent_dir, f) for f in os.listdir(recent_dir) if f.endswith('.lnk')]
            files.sort(key=os.path.getmtime, reverse=True)
            
            shell = win32com.client.Dispatch("WScript.Shell")
            ignored_exts = ('.crdownload', '.tmp', '.part', '.download', '.lnk', '.log', '.git', '.py', '.json')
            ignored_paths = ['\\appdata\\', '\\.git\\', '\\commandgenerator\\']
            
            for lnk in files:
                try:
                    shortcut = shell.CreateShortCut(lnk)
                    target = shortcut.Targetpath
                    if target and os.path.exists(target) and not os.path.isdir(target):
                        # Filter out system, temp, code, and project files
                        _, ext = os.path.splitext(target)
                        if ext.lower() in ignored_exts:
                            continue
                        path_lower = target.lower()
                        if any(p in path_lower for p in ignored_paths):
                            continue
                        return target
                except Exception:
                    pass
        except Exception:
            pass

    # 2. Fallback: Scan standard folders (Downloads, Desktop, Documents)
    user_profile = os.path.expanduser('~')
    search_dirs = [
        os.path.join(user_profile, 'Downloads'),
        os.path.join(user_profile, 'Desktop'),
        os.path.join(user_profile, 'Documents')
    ]
    
    ignored_extensions = ('.crdownload', '.tmp', '.part', '.download')
    fallback_files = []
    
    for d in search_dirs:
        if not os.path.exists(d):
            continue
        try:
            for f in os.listdir(d):
                filepath = os.path.join(d, f)
                if os.path.isfile(filepath):
                    _, ext = os.path.splitext(f)
                    if ext.lower() not in ignored_extensions:
                        fallback_files.append(filepath)
        except Exception:
            continue
            
    if not fallback_files:
        return None
        
    try:
        fallback_files.sort(key=os.path.getmtime, reverse=True)
        return fallback_files[0]
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
