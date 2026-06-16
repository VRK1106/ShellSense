import os
import json
import re
import ctypes
from ctypes import wintypes
import win32clipboard
import win32con

class DROPFILES(ctypes.Structure):
    _fields_ = [
        ("pFiles", wintypes.DWORD),
        ("pt", wintypes.POINT),
        ("fNC", wintypes.BOOL),
        ("fWide", wintypes.BOOL)
    ]

# Define kernel32 prototypes to prevent pointer truncation on 64-bit Windows
kernel32 = ctypes.windll.kernel32

kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = ctypes.c_void_p

kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalLock.restype = ctypes.c_void_p

kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.restype = wintypes.BOOL

def copy_file_to_clipboard(filepath: str):
    abs_path = os.path.abspath(filepath)
    # Unicode file list double-null terminated
    files_str = abs_path + "\0\0"
    files_data = files_str.encode("utf-16-le")
    
    offset = ctypes.sizeof(DROPFILES)
    
    dropfiles = DROPFILES()
    dropfiles.pFiles = offset
    dropfiles.pt = wintypes.POINT(0, 0)
    dropfiles.fNC = False
    dropfiles.fWide = True
    
    data = bytes(dropfiles) + files_data
    
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        hGlobal = kernel32.GlobalAlloc(win32con.GMEM_MOVEABLE, len(data))
        if not hGlobal:
            raise OSError("GlobalAlloc failed to allocate memory.")
        pGlobal = kernel32.GlobalLock(hGlobal)
        if not pGlobal:
            raise OSError("GlobalLock failed to lock memory.")
        try:
            ctypes.memmove(pGlobal, data, len(data))
        finally:
            kernel32.GlobalUnlock(hGlobal)
        win32clipboard.SetClipboardData(win32con.CF_HDROP, hGlobal)
    finally:
        win32clipboard.CloseClipboard()

def load_file_shortcuts():
    from shellsense.core.config import FILE_SHORTCUTS_PATH
    shortcuts_path = FILE_SHORTCUTS_PATH
    
    if not os.path.exists(shortcuts_path):
        default_shortcuts = {
            "resume": "C:\\Users\\example\\Documents\\resume.pdf",
            "notes": "D:\\notes.txt"
        }
        try:
            with open(shortcuts_path, 'w', encoding='utf-8') as f:
                json.dump(default_shortcuts, f, indent=4)
        except Exception:
            return default_shortcuts
        return default_shortcuts
        
    try:
        with open(shortcuts_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def evaluate_file_shortcuts(query: str):
    q = query.lower().strip()
    
    # Supported commands:
    # "copy file [alias]"
    # "copy path [alias]"
    # "open file [alias]" / "open [alias]"
    
    action = "open"
    clean_q = q
    
    if q.startswith("copy file "):
        action = "copy_file"
        clean_q = q[10:]
    elif q.startswith("copy path "):
        action = "copy_path"
        clean_q = q[10:]
    elif q.startswith("open file "):
        action = "open"
        clean_q = q[10:]
    elif q.startswith("open "):
        action = "open"
        clean_q = q[5:]
    else:
        # Check exact key lookup without prefix to be user-friendly
        pass
        
    clean_q = clean_q.strip()
    norm_q = re.sub(r'[^a-z0-9]', '', clean_q)
    if not norm_q:
        return False, None
        
    shortcuts = load_file_shortcuts()
    if not shortcuts:
        return False, None
        
    norm_shortcuts = {}
    for k, v in shortcuts.items():
        norm_k = re.sub(r'[^a-z0-9]', '', k.lower())
        norm_shortcuts[norm_k] = (k, v)
        
    # If no action prefix used, only match if it is an exact shortcut alias
    if q == clean_q and norm_q not in norm_shortcuts:
        return False, None
        
    matched_norm_key = None
    
    # 1. Exact match
    if norm_q in norm_shortcuts:
        matched_norm_key = norm_q
        
    # 2. Substring match
    if not matched_norm_key:
        matches = []
        for norm_key in norm_shortcuts:
            if norm_q in norm_key or norm_key in norm_q:
                matches.append(norm_key)
        if len(matches) == 1:
            matched_norm_key = matches[0]
        elif len(matches) > 1:
            keys_str = ", ".join(f"'{norm_shortcuts[m][0]}'" for m in matches)
            return True, f"Error: Multiple matches found ({keys_str}). Please be more specific."
            
    # 3. Fuzzy match
    if not matched_norm_key:
        import difflib
        best_match = None
        highest_ratio = 0.0
        for norm_key in norm_shortcuts:
            ratio = difflib.SequenceMatcher(None, norm_q, norm_key).ratio()
            if ratio > highest_ratio:
                highest_ratio = ratio
                best_match = norm_key
        if highest_ratio >= 0.75 and best_match:
            matched_norm_key = best_match
            
    if not matched_norm_key:
        return False, None
        
    orig_key, filepath = norm_shortcuts[matched_norm_key]
    
    # Validate file existence
    if not os.path.exists(filepath):
        return True, f"Error: File not found at {filepath}"
        
    if action == "copy_file":
        return True, f"Copied File: {filepath}|{orig_key}"
    elif action == "copy_path":
        return True, f"Copied Path: {filepath}|{orig_key}"
    else:
        return True, f"Opened File: {filepath}|{orig_key}"
