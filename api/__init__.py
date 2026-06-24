import os
from pathlib import Path
from flask import Flask
from dotenv import load_dotenv

from api.config import Config
from api.extensions import cors, login_manager
from api.blueprints import register_blueprints
from api.middleware.error_handler import register_error_handlers

def create_app(config_name="default"):
    # Load environment variables from API.env at root directory
    root_dir = Path(__file__).resolve().parent.parent
    env_path = root_dir / "API.env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        raise RuntimeError(
            "SECRET_KEY must be configured in the environment or API.env."
        )
    
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(Config)
    app.config["SECRET_KEY"] = secret_key
    
    # Initialize Flask extensions
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", ["http://localhost:5173"])}},
        supports_credentials=True
    )
    login_manager.init_app(app)
    
    # Register blueprints (with /api prefix handled internally or here)
    register_blueprints(app)
    
    # Register global JSON error handlers
    register_error_handlers(app)
    
    # In production, serve the React SPA static files from web/dist/
    if not app.debug:
        from flask import send_from_directory
        static_dir = str(Path(__file__).resolve().parent.parent / "web" / "dist")
        
        @app.route("/", defaults={"path": ""})
        @app.route("/<path:path>")
        def serve_react(path):
            full_path = Path(static_dir) / path
            if path and full_path.exists() and full_path.is_file():
                return send_from_directory(static_dir, path)
            return send_from_directory(static_dir, "index.html")
    
    return app
