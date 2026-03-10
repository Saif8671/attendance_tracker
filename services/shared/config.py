import os, secrets

def load_config(app):
    app.secret_key = secrets.token_hex(32)
    app.config["QR_VALID_SECONDS"] = int(os.getenv("QR_VALID_SECONDS", "120"))
    app.config["DATABASE_URL"] = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:USER%40supabase%408671@db.lnomjnooexjxlrkfgfvk.supabase.co:5432/postgres",
    )
    app.config["TWILIO_ACCOUNT_SID"] = os.getenv("TWILIO_ACCOUNT_SID", "")
    app.config["TWILIO_AUTH_TOKEN"] = os.getenv("TWILIO_AUTH_TOKEN", "")
    app.config["TWILIO_PHONE"] = os.getenv("TWILIO_PHONE", "")
    app.config["SMS_THRESHOLD"] = int(os.getenv("SMS_THRESHOLD", "75"))
