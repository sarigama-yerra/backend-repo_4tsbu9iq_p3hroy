import os
import smtplib
from email.mime.text import MIMEText
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from database import create_document
from schemas import Lead

app = FastAPI(title="Globalize API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Globalize.co.uk backend is running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


class LeadRequest(BaseModel):
    name: str
    email: EmailStr
    company: Optional[str] = None
    phone: Optional[str] = None
    services: Optional[List[str]] = None
    budget: Optional[str] = None
    message: Optional[str] = None


@app.post("/api/leads")
def create_lead(lead: LeadRequest):
    try:
        # Validate with schema and persist
        lead_model = Lead(**lead.model_dump())
        lead_id = create_document("lead", lead_model)

        # Try to send a confirmation email with lead magnet link (if SMTP configured)
        email_result = _maybe_send_lead_email(lead.email, lead.name)

        return {
            "status": "ok",
            "id": lead_id,
            "email_sent": email_result["sent"],
            "email_message": email_result["message"],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _maybe_send_lead_email(recipient: str, name: str):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender_email = os.getenv("SENDER_EMAIL", smtp_user)

    if not smtp_host or not smtp_port or not sender_email:
        return {"sent": False, "message": "SMTP not configured; skipped sending"}

    try:
        lead_magnet_url = os.getenv("FRONTEND_URL", "http://localhost:3000") + "/lead-magnet"
        subject = "Your Globalize Social Media Growth Toolkit"
        body = f"""
Hi {name},

Thanks for reaching out to Globalize. Here is your lead magnet:
{lead_magnet_url}

We'll be in touch shortly to learn more about your goals.

— Globalize Team
"""
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = recipient

        with smtplib.SMTP(host=smtp_host, port=int(smtp_port)) as server:
            server.starttls()
            if smtp_password:
                server.login(smtp_user, smtp_password)
            server.sendmail(sender_email, [recipient], msg.as_string())

        return {"sent": True, "message": "Confirmation email sent"}
    except Exception as e:
        return {"sent": False, "message": f"Email failed: {str(e)[:200]}"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        from database import db

        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
