from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from hashlib import md5
import jwt
import os
from db_config import get_db_connection

router = APIRouter()

JWT_SECRET = os.getenv("JWT_SECRET", "naveen")

class LoginRequest(BaseModel):
    email: str
    password: str

# @router.post("/login")
# async def login(request: LoginRequest):
#     email = request.email
#     password = request.password
#     hashed_password = md5(password.encode()).hexdigest()
#     print(hashed_password)

#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor(dictionary=True)
        
#         query = """
#         SELECT * FROM admins 
#         WHERE admin_email = %s AND admin_password = %s AND status = 1
#         """
#         cursor.execute(query, (email, hashed_password))
#         result = cursor.fetchone()
#         print(result)

#         cursor.close()
#         conn.close()

#         if result:
#             access_token = jwt.encode({"email": email}, JWT_SECRET, algorithm="HS256")
#             return {
#                 "success": True,
#                 "message": "Login successful",
#                 "accessToken": access_token,
#                 "name": result["admin_name"],
#                 "email": result["admin_email"]
#             }
#         else:
#             return {
#                 "success": False,
#                 "message": "Invalid credentials"
#             }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))





@router.post("/login")
async def login(request: LoginRequest):
    email = request.email
    password = request.password
    hashed_password = md5(password.encode()).hexdigest()
    print("Hashed password:", hashed_password)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT * FROM admins 
        WHERE admin_email = %s AND admin_password = %s AND status = 1
        """
        print("Query parameters:", email, hashed_password)
        cursor.execute(query, (email, hashed_password))
        result = cursor.fetchone()
        print("Query result:", result)

        cursor.close()
        conn.close()

        if result:
            access_token = jwt.encode({"email": email}, JWT_SECRET, algorithm="HS256")
            return {
                "success": True,
                "message": "Login successful",
                "accessToken": access_token,
                "name": result["admin_name"],
                "email": result["admin_email"]
            }
        else:
            return {
                "success": False,
                "message": "Invalid credentials"
            }

    except Exception as e:
        print("Error:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
