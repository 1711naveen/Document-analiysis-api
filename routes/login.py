# from fastapi import APIRouter, HTTPException, Depends
# from pydantic import BaseModel
# from sqlalchemy import create_engine, text
# from hashlib import md5
# import jwt
# import os

# # Define the APIRouter
# router = APIRouter()

# # Environment variables (fallback to defaults for simplicity)
# JWT_SECRET = os.getenv("JWT_SECRET", "naveen")
# DB_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")  # Update with your DB URL

# def get_db_connection():
#     engine = create_engine(DB_URL)
#     connection = engine.connect()
#     return connection

# # Request model for parsing input
# class LoginRequest(BaseModel):
#     email: str
#     password: str

# @router.post("/login")
# async def login(request: LoginRequest):
#     email = request.email
#     password = request.password
#     hashed_password = md5(password.encode()).hexdigest()

#     try:
#         # Connect to the database
#         db = get_db_connection()
#         query = text(
#             'SELECT * FROM admins WHERE admin_email = :email AND admin_password = :password AND status = 1'
#         )
#         result = db.execute(query, {"email": email, "password": hashed_password})
#         rows = result.fetchall()

#         if rows:
#             admin = rows[0]
#             access_token = jwt.encode({"email": email}, JWT_SECRET, algorithm="HS256")
#             return {
#                 "success": True,
#                 "message": "Login successful",
#                 "accessToken": access_token,
#                 "name": admin["admin_name"],
#                 "email": admin["admin_email"]
#             }
#         else:
#             raise HTTPException(status_code=401, detail="Invalid credentials")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#     finally:
#         db.close()

# # Example of integrating this router into your main FastAPI app
# # from fastapi import FastAPI
# # app = FastAPI()
# # app.include_router(router, prefix="/api")
