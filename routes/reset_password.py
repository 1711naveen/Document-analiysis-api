from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import hashlib
from db_config import get_db_connection

class ResetPasswordRequest(BaseModel):
    email: str

router = APIRouter()

@router.post("/reset_password/")
async def reset_password(request: ResetPasswordRequest):
    email = request.email
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    random_password = '12345'
    hashed_password = hashlib.md5(random_password.encode()).hexdigest()

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admins WHERE admin_email = %s", (email,))
        user = cursor.fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        print(f"User found: {user}")

        cursor.execute(
            "UPDATE admins SET admin_password = %s WHERE admin_email = %s",
            (hashed_password, email),
        )
        conn.commit()
        print(f"Password updated successfully for email: {email}")
        cursor.close()
        conn.close()
        return JSONResponse(
            content={"message": "Password reset successful. Check your email for the new password."},
            status_code=200,
        )
    except Exception as error:
        print(f"Error: {error}")
        raise HTTPException(status_code=500, detail="Internal server error.")







