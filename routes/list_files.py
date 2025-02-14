# from fastapi import APIRouter, HTTPException
# from fastapi.responses import JSONResponse
# import os

# router = APIRouter()

# @router.get("/list_files/")
# async def list_files(id: str):
#     if not id:
#         raise HTTPException(status_code=400, detail="Missing 'id' parameter")

#     folder_path = os.path.join(os.getcwd(), "output", id)
    
#     try:
#         # Check if the folder exists
#         if os.path.exists(folder_path):
#             # List all files in the folder
#             files = os.listdir(folder_path)
#             return JSONResponse(content={"files": files}, status_code=200)
#         else:
#             raise HTTPException(status_code=404, detail="Folder not found")
#     except Exception as e:
#         print(f"Error reading the folder: {e}")
#         raise HTTPException(status_code=500, detail="Error reading the folder")


from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import os
from datetime import datetime

router = APIRouter()

@router.get("/list_files/")
async def list_files(doc_id: str):
    date = datetime.now().strftime("%Y-%m-%d")
    if not doc_id or not date:
        raise HTTPException(status_code=400, detail="Missing 'doc_id' or 'date' parameter")

    base_path = os.path.join(os.getcwd(), "output", "Admin", date, doc_id)

    doc_folder = os.path.join(base_path, "doc")
    text_folder = os.path.join(base_path, "text")

    try:
        # Check if folders exist and list files
        files = {
            "doc": os.listdir(doc_folder) if os.path.exists(doc_folder) else [],
            "text": os.listdir(text_folder) if os.path.exists(text_folder) else []
        }
        return JSONResponse(content={"files": files}, status_code=200)
    
    except Exception as e:
        print(f"Error reading the folder: {e}")
        raise HTTPException(status_code=500, detail="Error reading the folder")
