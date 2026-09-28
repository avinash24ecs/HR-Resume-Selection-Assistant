"""One-click Python launcher for HR Resume Selection Assistant."""
import os
import sys
import threading
import time
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

def open_browser():
    time.sleep(1.2)
    print("\n[Browser] Opening http://localhost:5000 ...")
    webbrowser.open("http://localhost:5000")

def main():
    print("=" * 70)
    print("      HR Resume Selection Assistant - Live Server")
    print("=" * 70)

    try:
        from api.index import app
    except ImportError as e:
        print(f"[Error] Missing dependency: {e}")
        print("Please install requirements: pip install -r requirements.txt")
        print("\nOpening standalone interface in browser...")
        html_path = os.path.join(ROOT, "public", "index.html")
        webbrowser.open(f"file://{os.path.abspath(html_path)}")
        return

    threading.Thread(target=open_browser, daemon=True).start()
    port = int(os.getenv("PORT", 5000))
    print(f"\n[Server] Live API listening on http://localhost:{port}")
    print("[Server] Press Ctrl+C to stop the assistant.\n")
    app.run(host="0.0.0.0", port=port, debug=False)

if __name__ == "__main__":
    main()
