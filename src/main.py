import sys
import os
import threading
import uvicorn
import multiprocessing

from shellsense.ui.interface import main as run_ui
from shellsense.web.server import app

def start_server():
    # Run FastAPI web server on port 8000
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="error")
    server = uvicorn.Server(config)
    server.run()

if __name__ == '__main__':
    # Required for multiprocessing in PyInstaller bundles on Windows
    multiprocessing.freeze_support()
    
    # Redirect stdout and stderr to a log file to avoid crashes in windowed mode
    if getattr(sys, 'frozen', False):
        log_dir = os.path.dirname(sys.executable)
    else:
        log_dir = os.path.dirname(os.path.abspath(__file__))
    
    log_file_path = os.path.join(log_dir, "app_startup.log")
    log_file = open(log_file_path, "a")
    sys.stdout = log_file
    sys.stderr = log_file

    # Start the web server in a background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Start the PyQt UI
    run_ui()
