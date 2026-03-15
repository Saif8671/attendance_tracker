from flask import Blueprint, jsonify

lead_ai_bp = Blueprint("lead_ai", __name__)

@lead_ai_bp.route("/ai/status")
def ai_status():
    return jsonify({
        "status": "online",
        "engine": "AttendX-LLM-v1",
        "insights_available": False,
        "message": "AI services are initialization. Risk reports will appear once more attendance data is collected."
    })
