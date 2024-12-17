from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from db_config import get_db_connection  # Importing database connection

router = APIRouter()

class ResetPasswordRequest(BaseModel):
    email: str

@router.post("/reset_password/")
async def reset_password(request: ResetPasswordRequest):
    """
    Endpoint to reset the password for an admin user and send an email.
    Parameters:
        email: Admin's email address
    """
    email = request.email
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    random_password = '12345'
    hashed_password = hashlib.md5(random_password.encode()).hexdigest()  # MD5 hash

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Update the password in the database
        update = await cursor.execute(
            "UPDATE admins SET admin_password = ? WHERE admin_email = ?",
            (hashed_password, email),
        )
        if update.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found.")

        # Send email with the new password
        send_email(email, random_password)

        return JSONResponse(
            content={"message": "Password reset successful. Check your email for the new password."},
            status_code=200,
        )

    except Exception as error:
        print(error)
        raise HTTPException(status_code=500, detail="Internal server error.")

def send_email(email: str, new_password: str):
    """
    Function to send an email with the new password.
    """
    sender_email = "your_email@example.com"
    receiver_email = email
    password = "your_email_password"
    
    # Set up the MIME
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = "Password Reset Notification"
    
    # Add body to email
    body = f"Your password has been reset. Your new password is: {new_password}"
    msg.attach(MIMEText(body, "plain"))
    
    try:
        # Connect to the SMTP server and send email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send email.")
