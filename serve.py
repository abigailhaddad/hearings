#!/usr/bin/env python3
import http.server
import socketserver
import socket
import webbrowser
from pathlib import Path

def find_free_port(start_port=8000, max_attempts=100):
    """Find a free port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            # Try to bind to the port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            # Port is in use, try next one
            continue
    
    raise RuntimeError(f"Could not find free port in range {start_port}-{start_port + max_attempts}")

def main():
    # Find a free port
    port = find_free_port()
    
    # Change to the script directory
    script_dir = Path(__file__).parent
    
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=script_dir, **kwargs)
        
        def log_message(self, format, *args):
            # Custom logging
            print(f"[{self.log_date_time_string()}] {format % args}")
    
    print(f"🌐 YouTube-Congress Matcher Viewer")
    print(f"=" * 40)
    print(f"📁 Serving from: {script_dir}")
    print(f"🚀 Starting server on port {port}...")
    
    with socketserver.TCPServer(("", port), Handler) as httpd:
        url = f"http://localhost:{port}/viewer.html"
        print(f"✅ Server running at: {url}")
        print(f"\n📊 Available files:")
        print(f"   - viewer.html (main interface)")
        print(f"   - youtube_congress_matches.csv (data)")
        print(f"   - youtube_congress_matches.json (raw data)")
        
        print(f"\n🌐 Opening browser...")
        webbrowser.open(url)
        
        print(f"\n⌨️  Press Ctrl+C to stop the server")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print(f"\n\n👋 Server stopped")

if __name__ == "__main__":
    main()