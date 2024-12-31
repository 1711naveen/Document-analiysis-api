from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import os

router = APIRouter()

@router.get("/list_files/")
async def list_files(id: str):
    if not id:
        raise HTTPException(status_code=400, detail="Missing 'id' parameter")

    folder_path = os.path.join(os.getcwd(), "output", id)
    try:
        # Check if the folder exists
        if os.path.exists(folder_path):
            # List all files in the folder
            files = os.listdir(folder_path)
            return JSONResponse(content={"files": files}, status_code=200)
        else:
            raise HTTPException(status_code=404, detail="Folder not found")
    except Exception as e:
        print(f"Error reading the folder: {e}")
        raise HTTPException(status_code=500, detail="Error reading the folder")
