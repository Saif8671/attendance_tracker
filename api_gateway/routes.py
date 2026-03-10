from flask import Blueprint, jsonify

api_bp = Blueprint("api_gateway", __name__)

@api_bp.route("/health")
def health():
    return jsonify({"ok": True})

def register_gateway(app):
    app.register_blueprint(api_bp)
