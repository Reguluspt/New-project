import os
import sys
import argparse
from pathlib import Path

# Add project root directory to sys.path so we can import from src and api
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from api import create_app

app = create_app()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Flask API server")
    parser.add_argument("--port", type=int, default=int(os.getenv("FLASK_PORT", "5000")))
    parser.add_argument("--host", default=os.getenv("FLASK_HOST", "0.0.0.0"))
    parser.add_argument("--debug", action="store_true", default=os.getenv("FLASK_DEBUG", "false").lower() in ("1", "true", "yes"))
    args = parser.parse_args()

    app.run(host=args.host, port=args.port, debug=args.debug)
