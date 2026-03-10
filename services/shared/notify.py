from flask import current_app

def send_sms(to, msg):
    if not current_app.config["TWILIO_ACCOUNT_SID"]:
        print(f"[SMS] To {to}: {msg}")
        return True
    try:
        from twilio.rest import Client
        Client(
            current_app.config["TWILIO_ACCOUNT_SID"],
            current_app.config["TWILIO_AUTH_TOKEN"],
        ).messages.create(body=msg, from_=current_app.config["TWILIO_PHONE"], to=to)
        return True
    except Exception as e:
        print(f"SMS error: {e}")
        return False
