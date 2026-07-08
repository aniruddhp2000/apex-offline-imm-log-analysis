import os
import sys
import socket
import webbrowser
import threading
import time
import uvicorn

# In PyInstaller frozen mode, stdout and stderr can be invalid (e.g. running as windowed mode)
# So we reroute them to prevent crashes.
if sys.executable.endswith("pythonw.exe") or getattr(sys, 'frozen', False):
    sys.stdout = open(os.devnull, "w")
    sys.stderr = open(os.devnull, "w")

# Import the FastAPI app directly so PyInstaller bundles it properly
from backend.app import app

def find_available_port(start_port=8000):
    port = start_port
    while port < 65535:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                port += 1
    raise RuntimeError("No available ports found.")

def open_browser(url):
    # Wait a tiny bit for the server to spin up
    time.sleep(1.5)
    try:
        webbrowser.open(url)
    except Exception:
        pass

def main():
    # Clear PYTHONPATH and PYTHONHOME to prevent conflict with other Pythons
    os.environ.pop("PYTHONPATH", None)
    os.environ.pop("PYTHONHOME", None)
    
    port = find_available_port(8000)
    url = f"http://localhost:{port}/"
    
    # Launch browser in background thread
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()
    
    # Run uvicorn natively (no string import, no reload in frozen mode)
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level="error"
    )

if __name__ == "__main__":
    main()
