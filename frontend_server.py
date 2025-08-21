"""
Simple HTTP server to serve the frontend
Run this to serve the frontend on http://localhost:3000
"""

import http.server
import socketserver
import os
import sys

# Change to the frontend directory
frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend')
os.chdir(frontend_dir)

PORT = 3000

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers to allow API calls
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        # Handle preflight requests
        self.send_response(200)
        self.end_headers()

if __name__ == "__main__":
    print(f"Starting Frontend Server...")
    print(f"Frontend will be available at: http://localhost:{PORT}")
    print(f"Make sure your API server is running on http://localhost:8000")
    print("Press Ctrl+C to stop the server")
    
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down the server...")
            httpd.shutdown()
