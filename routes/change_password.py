# from fastapi import APIRouter, HTTPException, Depends
# from pydantic import BaseModel, EmailStr
# from db_config import get_db_connection
# import bcrypt

# router = APIRouter()

# # Define request model
# class ChangePasswordRequest(BaseModel):
#     email: EmailStr
#     new_password: str
#     confirm_password: str

# @router.post("/change_password/")
# async def change_password(request: ChangePasswordRequest):
#     # Validate passwords
#     if request.new_password != request.confirm_password:
#         raise HTTPException(status_code=400, detail="Passwords do not match")

#     # Hash the new password
#     hashed_password = bcrypt.hashpw(request.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

#     try:
#         # Get database connection
#         connection = get_db_connection()
#         cursor = connection.cursor()

#         # Update password in the database
#         cursor.execute(
#             "UPDATE admins SET admin_password = %s WHERE admin_email = %s",
#             (hashed_password, request.email)
#         )
#         connection.commit()

#         if cursor.rowcount == 0:
#             # No rows updated, email not found
#             raise HTTPException(status_code=404, detail="Email not found")

#         return {"success": True, "message": "Password changed successfully"}

#     except Exception as e:
#         print(f"Error updating password: {e}")
#         raise HTTPException(status_code=500, detail="An error occurred while updating the password")

#     finally:
#         # Close the connection
#         cursor.close()
#         connection.close()
