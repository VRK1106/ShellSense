import sys
import os

# For local development: run the exact same main file that PyInstaller uses
if __name__ == '__main__':
    src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    from src.main import start_server, run_ui
    import threading
    import multiprocessing
    
    multiprocessing.freeze_support()
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    run_ui()
