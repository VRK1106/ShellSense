import sys
import os
import threading
import uvicorn
import multiprocessing

from src.shellsense.ui.interface import main as run_ui
from src.shellsense.web.server import app

def start_server():
    # Run FastAPI web server on port 8000
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="error")
    server = uvicorn.Server(config)
    server.run()

if __name__ == '__main__':
    # Required for multiprocessing in PyInstaller bundles on Windows
    multiprocessing.freeze_support()
    
    # Redirect stdout and stderr to a log file to avoid crashes in windowed mode
    log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_startup.log")
    log_file = open(log_file_path, "a")
    sys.stdout = log_file
    sys.stderr = log_file

    # Add src to python path for imports if needed
    src_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
    if src_root not in sys.path:
        sys.path.insert(0, src_root)
        
    # Start the web server in a background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Start the PyQt UI
    run_ui()
