import os
import requests


BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def send_email(
    recipient,
    subject,
    html_body,
    sandbox=False
):
    api_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("BREVO_SENDER_EMAIL")
    sender_name = os.getenv("BREVO_SENDER_NAME")

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