from fastapi import FastAPI
from fastapi.responses import Response, FileResponse, RedirectResponse, HTMLResponse
from pydantic import BaseModel
from backend.database import (
    initialize_database,
    create_email,
    get_email_by_tracking_id,
    record_open,
    get_all_emails,
    record_click,
    record_confirmed_seen
)
from datetime import datetime, timezone
import uuid
from PIL import Image
import io


app = FastAPI(title="PixelTrail API")


# Initialize the database when the server starts
@app.on_event("startup")
def startup():
    initialize_database()


# Data we expect when creating a tracked email
class EmailCreate(BaseModel):
    recipient: str
    subject: str


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