from flask import Flask

def register_blueprints(app: Flask):
    """
    Register all blueprints for the application.
    For Phase 0, we only register the health check blueprint.
    """
    from api.blueprints.health import health_bp
    from api.blueprints.auth import auth_bp
    from api.blueprints.dashboard import dashboard_bp
    from api.blueprints.cases import cases_bp
    from api.blueprints.documents import documents_bp
    from api.blueprints.entry import entry_bp
    from api.blueprints.sobo import sobo_bp
    from api.blueprints.organizations import organizations_bp
    from api.blueprints.delivery import delivery_bp
    from api.blueprints.templates_bp import templates_bp
    from api.blueprints.settings import settings_bp
    
    # Register blueprints with /api prefix
    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(cases_bp, url_prefix="/api/cases")
    app.register_blueprint(documents_bp, url_prefix="/api")
    app.register_blueprint(entry_bp, url_prefix="/api")
    app.register_blueprint(sobo_bp, url_prefix="/api")
    app.register_blueprint(organizations_bp, url_prefix="/api")
    app.register_blueprint(delivery_bp, url_prefix="/api")
    app.register_blueprint(templates_bp, url_prefix="/api")
    app.register_blueprint(settings_bp, url_prefix="/api")
