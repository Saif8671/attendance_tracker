"""
API Gateway entrypoint.
Delegates routes to service blueprints while keeping a single process.
"""
from flask import Flask
from services.shared.config import load_config
from services.shared.db import init_db
from api_gateway.routes import register_gateway
from services.auth.routes import auth_bp
from services.crm.routes import crm_bp
from services.lead_ai.routes import lead_ai_bp

def create_app():
    app = Flask(
        __name__,
        template_folder="frontend/templates",
        static_folder="frontend/static",
        static_url_path="/static",
    )

    load_config(app)

    # Register service blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(crm_bp)
    app.register_blueprint(lead_ai_bp)

    # Register gateway routes (e.g., root, health)
    register_gateway(app)

    # Initialize DB schema with app context
    with app.app_context():
        init_db()

    return app

app = create_app()

if __name__ == "__main__":
    print("\nAttendX running at http://localhost:5000")
    app.run(debug=True, port=5000)
