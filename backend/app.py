"""
AttendX — Attendance Tracker (Simplified)
Flask entrypoint wiring everything in a flat, professional structure.
"""
import os
from flask import Flask
from dotenv import load_dotenv

from config import load_config

load_dotenv()

app = Flask(__name__)

load_config(app)

from routes.api import api_bp

app.register_blueprint(api_bp)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\nAttendX running at http://localhost:{port}")
    app.run(debug=True, port=port)
