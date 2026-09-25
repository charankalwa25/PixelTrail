import email

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response, FileResponse, RedirectResponse, HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

import os

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL")
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME")

from backend.database import (
    initialize_database,
    create_email,
    get_email_by_tracking_id,
    record_open,
    get_all_emails,
    record_click,
    record_confirmed_seen,
    create_user,
    get_user_by_email,
    get_user_by_id,
    create_campaign,
    get_campaign_by_id,
    get_campaigns_by_user,
    get_emails_by_campaign,
    create_campaign_email,
    get_campaign_email_by_recipient,
    update_campaign_status,
    update_campaign_email_status,
    update_campaign_email_message_id
)

from backend.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)

from backend.email_service import send_email

from datetime import datetime, timezone
import uuid
import re
from PIL import Image
import io

app = FastAPI(title="PixelTrail API")
security = HTTPBearer()

# Initialize the database when the server starts
@app.on_event("startup")
def startup():
    initialize_database()


# Data we expect when creating a tracked email
class EmailCreate(BaseModel):
    recipient: str
    subject: str

class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str

class CampaignCreate(BaseModel):
    name: str
    subject: str
    body: str

class RecipientsRequest(BaseModel):
    recipients: str

def personalize_body(body, recipient):
    email = recipient.strip().lower()

    first_name = email.split("@")[0]

    # Make common separators look like a name
    first_name = re.sub(r"[._-]+", " ", first_name)

    # Use the first part as the first name
    first_name = first_name.split()[0].capitalize()

    personalized_body = body.replace(
        "{{first_name}}",
        first_name
    )

    personalized_body = personalized_body.replace(
        "{{email}}",
        email
    )

    return personalized_body

def build_tracked_email_html(body, tracking_id):
    tracking_pixel_url = (
        f"https://pixeltrail.onrender.com/"
        f"track/{tracking_id}.png"
    )

    confirm_seen_url = (
        f"https://pixeltrail.onrender.com/"
        f"track/confirm/{tracking_id}"
    )

    tracking_footer = f"""
        <div style="margin-top:30px;">
            <p style="font-size:12px;color:#888;">
                If you have read this email, you can confirm it here:
            </p>

            <a
                href="{confirm_seen_url}"
                style="
                    display:inline-block;
                    padding:8px 14px;
                    background:#111827;
                    color:#ffffff;
                    text-decoration:none;
                    border-radius:6px;
                    font-size:12px;
                "
            >
                Confirm Seen
            </a>
        </div>

        <img
            src="{tracking_pixel_url}"
            width="1"
            height="1"
            alt=""
            style="display:block;width:1px;height:1px;"
        />
    """

    if "</body>" in body.lower():
        return body.replace(
            "</body>",
            tracking_footer + "</body>"
        )

    return body + tracking_footer

@app.post("/auth/register")
def register_user(request: RegisterRequest):
    email = request.email.strip().lower()
    password = request.password

    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long."
        )

    existing_user = get_user_by_email(email)

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists."
        )

    password_hash = hash_password(password)

    created_at = datetime.now(timezone.utc).isoformat()

    user_id = create_user(
        email=email,
        password_hash=password_hash,
        created_at=created_at
    )

    token = create_access_token(user_id)

    return {
        "message": "Account created successfully",
        "user_id": user_id,
        "email": email,
        "access_token": token,
        "token_type": "bearer"
    }


@app.post("/auth/login")
def login_user(request: LoginRequest):
    email = request.email.strip().lower()

    user = get_user_by_email(email)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    if not verify_password(
        request.password,
        user["password_hash"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    token = create_access_token(user["id"])

    return {
        "message": "Login successful",
        "user_id": user["id"],
        "email": user["email"],
        "access_token": token,
        "token_type": "bearer"
    }

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    user_id = decode_access_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token."
        )

    user = get_user_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found."
        )

    return user

@app.get("/auth/me")
def get_me(current_user=Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "created_at": current_user["created_at"]
    }



@app.post("/campaigns")
def create_new_campaign(
    campaign: CampaignCreate,
    current_user=Depends(get_current_user)
):
    created_at = datetime.now(timezone.utc).isoformat()

    campaign_id = create_campaign(
        user_id=current_user["id"],
        name=campaign.name.strip(),
        subject=campaign.subject.strip(),
        body=campaign.body,
        created_at=created_at,
        status="draft"
    )

    return {
        "message": "Campaign created successfully",
        "campaign_id": campaign_id,
        "name": campaign.name,
        "subject": campaign.subject,
        "status": "draft"
    }

@app.get("/campaigns")
def get_my_campaigns(
    current_user=Depends(get_current_user)
):
    campaigns = get_campaigns_by_user(current_user["id"])

    return {
        "campaigns": [dict(campaign) for campaign in campaigns]
    }

@app.get("/campaigns/{campaign_id}/emails")
def get_campaign_emails(
    campaign_id: int,
    current_user=Depends(get_current_user)
):
    campaign = get_campaign_by_id(campaign_id)

    if campaign is None:
        raise HTTPException(
            status_code=404,
            detail="Campaign not found."
        )

    if campaign["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this campaign."
        )

    emails = get_emails_by_campaign(campaign_id)

    return {
        "campaign_id": campaign_id,
        "emails": [dict(email) for email in emails]
    }
@app.post("/campaigns/{campaign_id}/send")
def send_campaign(
    campaign_id: int,
    current_user=Depends(get_current_user)
):
    campaign = get_campaign_by_id(campaign_id)

    if campaign is None:
        raise HTTPException(
            status_code=404,
            detail="Campaign not found."
        )

    if campaign["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this campaign."
        )

    if campaign["status"] == "sent":
        raise HTTPException(
            status_code=400,
            detail="Campaign has already been sent."
        )

    emails = get_emails_by_campaign(campaign_id)

    if not emails:
        raise HTTPException(
            status_code=400,
            detail="Campaign has no recipients."
        )

    update_campaign_status(
        campaign_id,
        "sending"
    )

    sent_count = 0
    failed_count = 0
    results = []

    for email in emails:

        if email["status"] == "sent":
            sent_count += 1

            results.append({
                "email_id": email["id"],
                "recipient": email["recipient"],
                "status": "sent"
            })

            continue

        try:
            tracked_html = build_tracked_email_html(
                email["body"] or "",
                email["tracking_id"]
            )

            result = send_email(
                recipient=email["recipient"],
                subject=email["subject"],
                html_body=tracked_html
            )

            update_campaign_email_status(
                email["id"],
                "sent"
            )

            update_campaign_email_message_id(
                email["id"],
                result.get("messageId")
            )

            sent_count += 1

            results.append({
                "email_id": email["id"],
                "recipient": email["recipient"],
                "status": "sent",
                "message_id": result.get("messageId")
            })

        except Exception as error:

            update_campaign_email_status(
                email["id"],
                "failed"
            )

            failed_count += 1

            results.append({
                "email_id": email["id"],
                "recipient": email["recipient"],
                "status": "failed",
                "error": str(error)
            })

    if failed_count == 0:
        campaign_status = "sent"
    elif sent_count > 0:
        campaign_status = "partially_sent"
    else:
        campaign_status = "failed"

    update_campaign_status(
        campaign_id,
        campaign_status
    )

    return {
        "message": "Campaign sending completed.",
        "campaign_id": campaign_id,
        "recipient_count": len(emails),
        "sent_count": sent_count,
        "failed_count": failed_count,
        "status": campaign_status,
        "results": results
    }

@app.post("/campaigns/{campaign_id}/recipients")
def add_recipients(
    campaign_id: int,
    request: RecipientsRequest,
    current_user=Depends(get_current_user)
):
    campaign = get_campaign_by_id(campaign_id)

    if campaign is None:
        raise HTTPException(
            status_code=404,
            detail="Campaign not found."
        )

    if campaign["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this campaign."
        )

    # Split by newline, comma, or semicolon
    raw_recipients = re.split(r"[\n,;]+", request.recipients)

    valid_emails = []
    invalid_emails = []
    duplicates_removed = 0
    existing_recipients = 0
    created_recipients = []

    email_pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    for raw_email in raw_recipients:
        email = raw_email.strip().lower()

        if not email:
            continue

        # Validate email format
        if not re.match(email_pattern, email):
            invalid_emails.append(email)
            continue

        # Remove duplicates from the same request
        if email in valid_emails:
            duplicates_removed += 1
            continue

        valid_emails.append(email)

    # Create one database record for each new recipient
    for email in valid_emails:

        existing_email = get_campaign_email_by_recipient(
            campaign_id,
            email
        )

        if existing_email:
            existing_recipients += 1
            continue

        tracking_id = str(uuid.uuid4())
        sent_at = datetime.now(timezone.utc).isoformat()

        create_campaign_email(
            campaign_id=campaign_id,
            tracking_id=tracking_id,
            recipient=email,
            subject=campaign["subject"],
            body=personalize_body(
                campaign["body"],
                email
            ),
            sent_at=sent_at,
            status="queued"
        )

        created_recipients.append(email)

    return {
        "campaign_id": campaign_id,
        "created_count": len(created_recipients),
        "existing_recipients": existing_recipients,
        "duplicates_removed": duplicates_removed,
        "invalid_count": len(invalid_emails),
        "created_recipients": created_recipients,
        "invalid_emails": invalid_emails
    }

# Home page
@app.get("/")
def root():
    return {
        "message": "PixelTrail backend is running!"
    }


# Health check
@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# Database check
@app.get("/database-status")
def database_status():
    return {
        "status": "database connected"
    }


# Create a tracked email
@app.post("/emails")
def create_tracked_email(email: EmailCreate):

    # Generate a unique tracking ID
    tracking_id = str(uuid.uuid4())

    # Get current UTC time
    sent_at = datetime.now(timezone.utc).isoformat()

    # Save email in database
    create_email(
        tracking_id=tracking_id,
        recipient=email.recipient,
        subject=email.subject,
        sent_at=sent_at
    )

    # Return tracking information
    return {
        "message": "Tracked email created successfully",
        "tracking_id": tracking_id,
        "recipient": email.recipient,
        "subject": email.subject,
        "sent_at": sent_at,
        "tracking_pixel_url": f"https://pixeltrail.onrender.com/track/{tracking_id}.png",
        "confirm_seen_url": f"https://pixeltrail.onrender.com/track/seen/{tracking_id}"
    }


# Tracking pixel endpoint
@app.get("/track/{tracking_id}.png")
def track_email_open(tracking_id: str):

    # Find the email using its tracking ID
    email = get_email_by_tracking_id(tracking_id)

    # If tracking ID doesn't exist
    if email is None:
        return Response(
            content=b"",
            status_code=404
        )

    # Record the time the tracking pixel was requested
    opened_at = datetime.now(timezone.utc).isoformat()

    record_open(
        tracking_id=tracking_id,
        opened_at=opened_at
    )

    # Create a transparent 1x1 pixel
    image = Image.new(
        "RGBA",
        (1, 1),
        (0, 0, 0, 0)
    )

    # Convert image to PNG bytes
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")

    # Return the invisible pixel
    return Response(
        content=image_bytes.getvalue(),
        media_type="image/png",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )
@app.get("/emails/{tracking_id}")
def get_tracked_email(tracking_id: str):

    email = get_email_by_tracking_id(tracking_id)

    if email is None:
        return {
            "error": "Tracking ID not found"
        }

    return dict(email)
@app.get("/emails")
def get_tracked_emails():

    emails = get_all_emails()

    return {
        "emails": [dict(email) for email in emails]
    }
@app.get("/dashboard")
def dashboard():
    return FileResponse("dashboard/index.html")
@app.get("/track/click/{tracking_id}")
def track_link_click(tracking_id: str, url: str):

    # Check whether this tracking ID exists
    email = get_email_by_tracking_id(tracking_id)

    if email is None:
        return Response(
            content=b"Tracking ID not found",
            status_code=404
        )

    # Record the click
    clicked_at = datetime.now(timezone.utc).isoformat()

    record_click(
        tracking_id=tracking_id,
        clicked_at=clicked_at
    )

    # Redirect the recipient to the original website
    return RedirectResponse(
        url=url,
        status_code=302
    )
@app.get("/track/seen/{tracking_id}")
@app.get("/track/confirm/{tracking_id}")
def confirm_seen(tracking_id: str):

    # Check whether this tracking ID exists
    email = get_email_by_tracking_id(tracking_id)

    if email is None:
        return HTMLResponse(
            content="""
            <html>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h2>PixelTrail</h2>
                    <p>Tracking ID not found.</p>
                </body>
            </html>
            """,
            status_code=404
        )

    # Record the confirmation time
    confirmed_at = datetime.now(timezone.utc).isoformat()

    record_confirmed_seen(
        tracking_id=tracking_id,
        confirmed_at=confirmed_at
    )

    # Show confirmation page
    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html>
            <head>
                <title>PixelTrail - Confirmed</title>
            </head>

            <body style="
                margin: 0;
                background: #0d1117;
                color: #ffffff;
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                text-align: center;
            ">

                <div>
                    <div style="font-size: 50px;">✓</div>

                    <h1>Seen confirmed</h1>

                    <p style="color: #9fb0bf;">
                        Your confirmation has been recorded.
                    </p>
                </div>

            </body>
        </html>
        """,
        status_code=200
    )