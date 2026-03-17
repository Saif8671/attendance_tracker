import os, secrets

def load_config(app):
    app.secret_key = os.getenv("FLASK_SECRET") or secrets.token_hex(32)
    app.config["QR_VALID_SECONDS"] = int(os.getenv("QR_VALID_SECONDS", "120"))
    app.config["TWILIO_ACCOUNT_SID"] = os.getenv("TWILIO_ACCOUNT_SID", "")
    app.config["TWILIO_AUTH_TOKEN"] = os.getenv("TWILIO_AUTH_TOKEN", "")
    app.config["TWILIO_PHONE"] = os.getenv("TWILIO_PHONE", "")
    app.config["SMS_THRESHOLD"] = int(os.getenv("SMS_THRESHOLD", "75"))
