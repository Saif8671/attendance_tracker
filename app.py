"""
AttendX — Attendance Tracker (modular)
Flask entrypoint wiring blueprints and shared services.
"""
from flask import Flask, g

from api_gateway.routes import register_gateway
from services.auth.routes import auth_bp
from services.crm.routes import crm_bp
from services.shared.config import load_config
from services.shared.db import init_db

app = Flask(
    __name__,
    template_folder="frontend/templates",
    static_folder="frontend/static",
    static_url_path="/static",
)

load_config(app)


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db:
        try:
            db.close()
        except Exception:
            pass


app.register_blueprint(auth_bp)
app.register_blueprint(crm_bp)
register_gateway(app)

with app.app_context():
    init_db()


if __name__ == "__main__":
    print("\nAttendX running at http://localhost:5000")
    app.run(debug=True, port=5000)
