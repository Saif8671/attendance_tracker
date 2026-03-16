"""
AttendX — Attendance Tracker (Simplified)
Flask entrypoint wiring everything in a flat, professional structure.
"""
import os
from flask import Flask, g
from dotenv import load_dotenv

from config import load_config
from db.database import init_db, get_db
from routes.api import api_bp
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

load_config(app)
app.config["DB_INIT_DONE"] = False
app.config["DB_INIT_ATTEMPTED"] = False

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db:
        try:
            db.close()
        except Exception:
            pass

app.register_blueprint(api_bp)

@app.before_request
def ensure_db_initialized():
    if app.config.get("DB_INIT_DONE") or app.config.get("DB_INIT_ATTEMPTED"):
        return
    app.config["DB_INIT_ATTEMPTED"] = True
    try:
        init_db()
        app.config["DB_INIT_DONE"] = True
    except Exception:
        app.logger.exception("Database initialization failed")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\nAttendX running at http://localhost:{port}")
    app.run(debug=True, port=port)
