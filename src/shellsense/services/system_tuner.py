import os
import re
import shutil
import winreg

def get_startup_apps():
    apps = []
    
    # 1. HKCU Registry
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
        i = 0
        while True:
            try:
                name, val, _ = winreg.EnumValue(key, i)
                apps.append({"name": name, "command": val, "source": "HKCU Registry"})
                i += 1
            except OSError:
                break
        winreg.CloseKey(key)
    except Exception:
        pass
        
    # 2. HKLM Registry
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
        i = 0
        while True:
            try:
                name, val, _ = winreg.EnumValue(key, i)
                apps.append({"name": name, "command": val, "source": "HKLM Registry"})
                i += 1
            except OSError:
                break
        winreg.CloseKey(key)
    except Exception:
        pass

    # 3. Startup folders
    user_startup = os.path.join(os.environ.get('APPDATA', ''), 'Microsoft\\Windows\\Start Menu\\Programs\\Startup')
    common_startup = os.path.join(os.environ.get('ProgramData', 'C:\\ProgramData'), 'Microsoft\\Windows\\Start Menu\\Programs\\Startup')
    
    for folder, source in [(user_startup, "User Startup Folder"), (common_startup, "Common Startup Folder")]:
        if os.path.exists(folder):
            try:
                for f in os.listdir(folder):
                    if f.lower() == 'desktop.ini':
                        continue
                    filepath = os.path.join(folder, f)
                    if os.path.isfile(filepath):
                        apps.append({"name": f, "command": filepath, "source": source})
            except Exception:
                pass
                
    return apps

def disable_startup_app(app_name: str):
    apps = get_startup_apps()
    norm_target = re.sub(r'[^a-z0-9]', '', app_name.lower())
    
    # Find matching apps
    matches = []
    for a in apps:
        norm_name = re.sub(r'[^a-z0-9]', '', a["name"].lower())
        if norm_target in norm_name or norm_name in norm_target:
            matches.append(a)
            
    if not matches:
        return f"Error: Could not find any startup app matching '{app_name}'"
        
    if len(matches) > 1:
        names_str = ", ".join(f"'{m['name']}' ({m['source']})" for m in matches)
        return f"Error: Multiple matches found ({names_str}). Please be more specific."
        
    app = matches[0]
    source = app["source"]
    name = app["name"]
    command = app["command"]
    
    if source == "HKCU Registry":
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, name)
            winreg.CloseKey(key)
            return f"Disabled '{name}' from startup successfully."
        except Exception as e:
            return f"Error disabling registry key: {e}"
            
    elif source == "HKLM Registry":
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, name)
            winreg.CloseKey(key)
            return f"Disabled '{name}' from startup successfully."
        except PermissionError:
            return f"Error: Disabling '{name}' from HKLM Registry requires administrator privileges."
        except Exception as e:
            return f"Error disabling registry key: {e}"
            
    elif source in ("User Startup Folder", "Common Startup Folder"):
        try:
            os.remove(command)
            return f"Disabled '{name}' from startup by removing shortcut."
        except PermissionError:
            return f"Error: Disabling '{name}' requires administrator privileges."
        except Exception as e:
            return f"Error removing shortcut: {e}"
            
    return f"Error: Unknown startup source '{source}'"

def clean_temp_files():
    temp_dirs = []
    user_temp = os.environ.get('TEMP')
    if user_temp and os.path.exists(user_temp):
        temp_dirs.append(user_temp)
    system_temp = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp')
    if os.path.exists(system_temp):
        temp_dirs.append(system_temp)
        
    freed_bytes = 0
    deleted_files = 0
    deleted_dirs = 0
    
    for d in temp_dirs:
        try:
            items = os.listdir(d)
        except Exception:
            continue
            
        for item in items:
            item_path = os.path.join(d, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    size = os.path.getsize(item_path)
                    os.unlink(item_path)
                    freed_bytes += size
                    deleted_files += 1
                elif os.path.isdir(item_path):
                    # Calculate directory size
                    dir_size = 0
                    for root, dirs, files in os.walk(item_path):
                        for f in files:
                            fp = os.path.join(root, f)
                            try:
                                dir_size += os.path.getsize(fp)
                            except Exception:
                                pass
                    shutil.rmtree(item_path)
                    freed_bytes += dir_size
                    deleted_dirs += 1
            except Exception:
                pass
                
    freed_mb = freed_bytes / (1024 * 1024)
    return f"Cleaned {deleted_files} files and {deleted_dirs} folders. Freed {freed_mb:.2f} MB of space."

def evaluate_system_tuner(query: str):
    q = query.lower().strip()
    
    # 1. Clean temp files
    if q in ("clean my temp files", "clean temp files", "clean temp", "clean temp cache", "free temp space"):
        return True, clean_temp_files()
        
    # 2. Show startup apps
    if q in ("show my startup apps", "show startup apps", "list startup apps", "list startup", "get startup apps"):
        apps = get_startup_apps()
        if not apps:
            return True, "Startup Apps: No active startup apps found."
        
        # Format HTML list
        html = (
            "<div style='line-height: 1.4; font-family: \"Segoe UI\", sans-serif; color: #00bcd4;'>"
            "<b style='color: #ffffff; font-size: 17px;'>🚀 Active Windows Startup Apps:</b><br>"
        )
        for a in apps:
            name_clean = a["name"].replace(".lnk", "")
            html += f"<span style='color: #ffffff;'>•</span> <b>{name_clean}</b> <span style='color: #888888; font-size: 11px;'>({a['source']})</span><br>"
        html += "</div>"
        return True, html
        
    # 3. Disable startup app
    disable_match = re.match(r'^disable\s+(.+?)\s+from\s+startup$', q)
    if not disable_match:
        disable_match = re.match(r'^disable\s+startup\s+(.+?)$', q)
    if not disable_match:
        disable_match = re.match(r'^remove\s+(.+?)\s+from\s+startup$', q)
        
    if disable_match:
        target_app = disable_match.group(1).strip()
        return True, disable_startup_app(target_app)
        
    return False, None
