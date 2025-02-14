# from fastapi import APIRouter, HTTPException
# from fastapi.responses import FileResponse
# import os

# router = APIRouter()

# @router.get("/download_file")
# async def download_file(id: str, file: str):
#     """
#     Endpoint to download a specific file from a folder.
#     Parameters:
#         id: Folder ID
#         file: File name
#     """
#     if not id or not file:
#         raise HTTPException(status_code=400, detail="Missing 'id' or 'file' parameters")

#     # Construct the folder and file paths
#     folder_path = os.path.join(os.getcwd(), "output", id)
#     file_path = os.path.join(folder_path, file)

#     try:
#         # Check if the folder and file exist
#         if os.path.exists(folder_path) and os.path.exists(file_path):
#             # Use FileResponse to stream the file with appropriate headers
#             return FileResponse(
#                 file_path,
#                 media_type="application/octet-stream",
#                 filename=file,
#             )
#         else:
#             raise HTTPException(status_code=404, detail="File not found")
#     except Exception as e:
#         print(f"Error reading the file: {e}")
#         raise HTTPException(status_code=500, detail="Error reading the file")




from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
from datetime import datetime

router = APIRouter()

@router.get("/download_file")
async def download_file(id: str, folder: str, file: str):
    """
    Endpoint to download a specific file from a folder.
    Parameters:
        id: Folder ID
        folder: Subfolder ('doc' or 'text')
        file: File name
    """
    if not id or not folder or not file:
        raise HTTPException(status_code=400, detail="Missing 'id', 'folder', or 'file' parameters")

    # Validate folder type
    if folder not in ["doc", "text"]:
        raise HTTPException(status_code=400, detail="Invalid folder type. Use 'doc' or 'text'.")

    # Construct the file path
    date = datetime.now().strftime("%Y-%m-%d")
    base_path = os.path.join(os.getcwd(), "output", "Admin", date, id, folder)
    file_path = os.path.join(base_path, file)

    try:
        # Check if the file exists
        if os.path.exists(file_path):
            return FileResponse(
                file_path,
                media_type="application/octet-stream",
                filename=file,
            )
        else:
            raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        print(f"Error reading the file: {e}")
        raise HTTPException(status_code=500, detail="Error reading the file")
