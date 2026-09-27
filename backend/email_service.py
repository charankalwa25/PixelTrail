import os
from urllib import response
import requests


BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def send_email(
    recipient,
    subject,
    html_body,
    sandbox=False,
    sender_email=None,
    sender_name=None
):
    api_key = os.getenv("BREVO_API_KEY")

    sender_email = (
        sender_email
        or os.getenv("BREVO_SENDER_EMAIL")
    )

    sender_name = (
        sender_name
        or os.getenv("BREVO_SENDER_NAME")
    )

    if not api_key:
        raise RuntimeError(
            "BREVO_API_KEY is not configured."
        )

    if not sender_email:
        raise RuntimeError(
            "BREVO_SENDER_EMAIL is not configured."
        )

    payload = {
        "sender": {
            "name": sender_name or "PixelTrail",
            "email": sender_email
        },
        "to": [
            {
                "email": recipient
            }
        ],
        "subject": subject,
        "htmlContent": html_body
    }

    if sandbox:
        payload["headers"] = {
            "X-Sib-Sandbox": "drop"
        }

    response = requests.post(
        BREVO_API_URL,
        headers={
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json"
        },
        json=payload,
        timeout=30
    )

    if response.status_code != 201:
        raise RuntimeError(
            f"Brevo email send failed: "
            f"{response.status_code} - {response.text}"
        )

    return response.json()

def create_brevo_sender(name, email):
    api_key = os.getenv("BREVO_API_KEY")

    if not api_key:
        raise RuntimeError("BREVO_API_KEY is not configured.")

    payload = {
        "name": name,
        "email": email
    }

    response = requests.post(
        "https://api.brevo.com/v3/senders",
        headers={
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json"
        },
        json=payload,
        timeout=30
    )

    if response.status_code != 201:
        raise RuntimeError(
            f"Brevo sender creation failed: "
            f"{response.status_code} - {response.text}"
        )

    return response.json()

def get_brevo_senders():
        api_key = os.getenv("BREVO_API_KEY")

        if not api_key:
            raise RuntimeError("BREVO_API_KEY is not configured.")

        response = requests.get(
        "https://api.brevo.com/v3/senders",
        headers={
            "accept": "application/json",
            "api-key": api_key
        },
        timeout=30
    )

        if response.status_code != 200:
            raise RuntimeError(
            f"Brevo sender lookup failed: "
            f"{response.status_code} - {response.text}"
        )

        return response.json().get("senders", [])

# ==========================================
# VALIDATE BREVO SENDER OTP
# ==========================================

def validate_brevo_sender_otp(sender_id, otp):
    api_key = os.getenv("BREVO_API_KEY")

    if not api_key:
        raise RuntimeError(
            "BREVO_API_KEY is not configured."
        )

    try:
        otp = int(otp)
    except (TypeError, ValueError):
        raise RuntimeError(
            "Verification code must be a 6-digit number."
        )

    if otp < 100000 or otp > 999999:
        raise RuntimeError(
            "Verification code must be a 6-digit number."
        )

    response = requests.put(
        f"https://api.brevo.com/v3/senders/"
        f"{sender_id}/validate",
        headers={
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json"
        },
        json={
            "otp": otp
        },
        timeout=30
    )

    if response.status_code != 204:
        raise RuntimeError(
            f"Brevo sender verification failed: "
            f"{response.status_code} - {response.text}"
        )

    return True