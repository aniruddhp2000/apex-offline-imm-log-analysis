import os
import sys
import socket
import webbrowser
import uvicorn

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

def main():
    # Clear PYTHONPATH and PYTHONHOME to prevent conflict with Python 2.7 site-packages
    os.environ.pop("PYTHONPATH", None)
    os.environ.pop("PYTHONHOME", None)
    
    port = find_available_port(8000)
    print(f"Selected available port: {port}")
    
    # Auto-open browser
    url = f"http://localhost:{port}/"
    print(f"Opening browser on {url} ...")
    
    # Open browser
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Failed to open browser automatically: {e}")
        
    print(f"Launching Uvicorn server on {url} ...")
    
    # Run uvicorn programmatically, reload backend, exclude rules changes
    uvicorn.run(
        "backend.app:app",
        host="127.0.0.1",
        port=port,
        reload=True,
        reload_dirs=["backend"],
        reload_excludes=["*rules.json", "*parser_config.json"]
    )

if __name__ == "__main__":
    main()
