# routes/__init__.py
from .auth_routes import auth_bp
from .admin_routes import admin_bp
from .file_routes import file_bp
from .api_routes import api_bp

def register_routes(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(file_bp)
    app.register_blueprint(api_bp)
