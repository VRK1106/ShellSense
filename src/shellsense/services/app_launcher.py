import os
import glob
import shutil
import subprocess
from shellsense.core.logger import logger

class AppLauncher:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AppLauncher, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.shortcuts = {}
        self.scan_and_index()
        self._initialized = True

    def scan_and_index(self):
        """Scans Start Menu and Desktop folders for shortcuts (.lnk files)."""
        logger.info("Scanning system for application shortcuts...")
        self.shortcuts.clear()
        
        # Define directories to scan
        directories = []
        
        # 1. User Start Menu
        user_menu = os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs')
        if os.path.exists(user_menu):
            directories.append(user_menu)
            
        # 2. System Start Menu
        system_menu = os.path.join(os.environ.get('ALLUSERSPROFILE', 'C:\\ProgramData'), 'Microsoft', 'Windows', 'Start Menu', 'Programs')
        if os.path.exists(system_menu):
            directories.append(system_menu)
            
        # 3. User Desktop
        user_desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        if os.path.exists(user_desktop):
            directories.append(user_desktop)
            
        # 4. Public Desktop
        public_desktop = r'C:\Users\Public\Desktop'
        if os.path.exists(public_desktop):
            directories.append(public_desktop)
            
        # Scan recursively
        for directory in directories:
            try:
                # Find all .lnk files recursively
                lnk_pattern = os.path.join(directory, '**', '*.lnk')
                for path in glob.glob(lnk_pattern, recursive=True):
                    filename = os.path.basename(path)
                    name_without_ext = os.path.splitext(filename)[0]
                    clean_name = name_without_ext.lower().strip()
                    # Keep the first one found or prioritize user shortcuts
                    if clean_name not in self.shortcuts:
                        self.shortcuts[clean_name] = path
            except Exception as e:
                logger.error(f"Error scanning directory {directory}: {e}")
                
        logger.info(f"Indexed {len(self.shortcuts)} unique application shortcuts.")

    def clean_query(self, query: str) -> str:
        """Strips action verbs and suffixes from the user command to isolate the app name."""
        import re
        q = query.lower().strip()
        
        # Remove common introductory phrases
        q = re.sub(r'^(please|can you|could you|i want to|i need to|go ahead and)\s+', '', q)
        
        # Remove action verbs
        q = re.sub(r'^(open|launch|start|run|execute|bring up|show|display|get)\s+', '', q)
        
        # Remove common modifiers
        q = re.sub(r'^(the|default|a|an)\s+', '', q)
        q = re.sub(r'^(the|default|a|an)\s+', '', q)
        
        # Remove common suffixes
        q = re.sub(r'\s+(app|application|please|now)$', '', q)
        q = re.sub(r'\s+(app|application|please|now)\s*[?!.]$', '', q)
        
        return q.strip().rstrip("?!. ")

    def resolve_app_path(self, query: str):
        """
        Resolves an application query to a shortcut path or an executable path.
        Returns path if resolved, else None.
        """
        target = self.clean_query(query)
        if not target:
            return None

        # Common alias mapping for command-line executables or shortcut variations
        aliases = {
            "calculator": "calc",
            "calc": "calc",
            "cmd": "cmd",
            "command prompt": "cmd",
            "terminal": "cmd",
            "powershell": "powershell",
            "paint": "mspaint",
            "mspaint": "mspaint",
            "word": "winword",
            "excel": "excel",
            "powerpoint": "powerpnt",
            "vscode": "code",
            "vs code": "code",
            "registry editor": "regedit",
            "task manager": "taskmgr",
            "taskmgr": "taskmgr"
        }
        if target in aliases:
            target = aliases[target]

        # 1. Look for exact match in shortcuts
        if target in self.shortcuts:
            logger.info(f"Exact shortcut match found for '{target}': {self.shortcuts[target]}")
            return self.shortcuts[target]

        # 2. Look for word boundary or substring match in shortcuts
        matches = []
        for name, path in self.shortcuts.items():
            if name.startswith(target + " ") or name.endswith(" " + target) or (" " + target + " " in name):
                matches.append((1, len(name), path))
            elif target in name:
                matches.append((2, len(name), path))

        if matches:
            # Sort by rank priority (1 is better), then by name length (shorter is more specific)
            matches.sort(key=lambda x: (x[0], x[1]))
            best_match_path = matches[0][2]
            logger.info(f"Best substring shortcut match found for '{target}': {best_match_path}")
            return best_match_path

        # 3. Check system PATH for executable (e.g. 'notepad', 'calc')
        executable_path = shutil.which(target) or shutil.which(target + ".exe")
        if executable_path:
            logger.info(f"System PATH match found for '{target}': {executable_path}")
            return executable_path

        logger.warning(f"Could not resolve application for query: '{query}' (cleaned: '{target}')")
        return None

    def launch(self, query: str) -> bool:
        """
        Resolves and launches the requested application.
        Returns True on success, False if app was not found/resolved.
        """
        path = self.resolve_app_path(query)
        if not path:
            return False

        try:
            logger.info(f"Launching application at path: {path}")
            os.startfile(path)
            return True
        except Exception as e:
            logger.error(f"Failed to launch application at {path}: {e}")
            # Fallback to subprocess if startfile fails
            try:
                subprocess.Popen([path], shell=True)
                return True
            except Exception as e2:
                logger.error(f"Fallback subprocess launch also failed: {e2}")
                return False
