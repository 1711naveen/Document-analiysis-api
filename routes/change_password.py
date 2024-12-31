from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from hashlib import md5
from db_config import get_db_connection

router = APIRouter()

class ChangePasswordRequest(BaseModel):
    email: EmailStr
    new_password: str
    confirm_password: str

@router.post("/change-password")
async def change_password(request: ChangePasswordRequest):
    email = request.email
    new_password = request.new_password
    confirm_password = request.confirm_password
    if new_password != confirm_password:
        return {
            "success": False,
            "message": "Passwords do not match"
        }
    hashed_password = md5(new_password.encode()).hexdigest()

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = "UPDATE admins SET admin_password = %s WHERE admin_email = %s"
        cursor.execute(query, (hashed_password, email))
        conn.commit()
        if cursor.rowcount == 0:
            return {
                "success": False,
                "message": "Password update failed, email not found"
            }
        return {
            "success": True,
            "message": "Password changed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
