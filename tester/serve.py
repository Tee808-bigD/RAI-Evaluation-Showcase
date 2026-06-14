#!/usr/bin/env python3
import http.server
import socketserver
import os
from pathlib import Path

PORT = 8000
HANDLER = http.server.SimpleHTTPRequestHandler

try:
    os.chdir(Path(__file__).parent)
    with socketserver.TCPServer(("", PORT), HANDLER) as httpd:
        print(f"\n[✓] Server started on http://localhost:{PORT}")
        print(f"[→] Open http://localhost:{PORT}/STANDALONE.html in your browser")
        print(f"[→] Press Ctrl+C to stop\n")
        httpd.serve_forever()
except KeyboardInterrupt:
    print("\n[✓] Server stopped")
except OSError as e:
    print(f"[ERROR] Port {PORT} already in use. Try: python3 serve.py --port 8001")
