import os
from flask import current_app, has_app_context


def _twilio_config():
    if has_app_context():
        return (
            current_app.config["TWILIO_ACCOUNT_SID"],
            current_app.config["TWILIO_AUTH_TOKEN"],
            current_app.config["TWILIO_PHONE"],
        )
    return (
        os.getenv("TWILIO_ACCOUNT_SID", ""),
        os.getenv("TWILIO_AUTH_TOKEN", ""),
        os.getenv("TWILIO_PHONE", ""),
    )


def send_sms(to, msg):
    sid, token, phone = _twilio_config()
    if not sid:
        print(f"[SMS] To {to}: {msg}")
        return True
    try:
        from twilio.rest import Client

        Client(sid, token).messages.create(body=msg, from_=phone, to=to)
        return True
    except Exception as e:
        print(f"SMS error: {e}")
        return False
