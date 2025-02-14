# from fastapi import APIRouter, HTTPException
# from fastapi.responses import StreamingResponse
# from db_config import get_db_connection
# import os
# import zipfile
# from io import BytesIO

# router = APIRouter()

# @router.get("/download_zip")
# async def download_files(final_doc_id: str):
#     """
#     Endpoint to download a folder as a ZIP file for a given final_doc_id.
#     """
#     # Fetch file data from the database
#     file_data = get_file_data_from_database(final_doc_id)
#     if not file_data:
#         raise HTTPException(status_code=404, detail="File not found")


#     # print(os.getcwd())
#     # folder_path = os.path.join(os.getcwd(), file_data["final_doc_url"])
#     # print(folder_path)
    
#     current_dir = os.getcwd()
#     print(f"Current Directory: {current_dir}")

#     # Ensure there's no leading slash in final_doc_url
#     final_doc_url = file_data["final_doc_url"].lstrip("/")

#     # Join the paths correctly
#     folder_path = os.path.join(current_dir, final_doc_url)

#     # Print the final folder path
#     print(f"Folder Path: {folder_path}")
    
#     if not os.path.exists(folder_path):
#         raise HTTPException(status_code=404, detail="Folder not found")

#     # Create a ZIP file in memory
#     zip_buffer = BytesIO()
#     with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
#         for root, _, files in os.walk(folder_path):
#             for file in files:
#                 file_path = os.path.join(root, file)
#                 arcname = os.path.relpath(file_path, start=folder_path)
#                 zip_file.write(file_path, arcname=arcname)

#     zip_buffer.seek(0)

#     # Return the ZIP file as a downloadable response
#     return StreamingResponse(
#         zip_buffer,
#         media_type="application/zip",
#         headers={
#             "Content-Disposition": f'attachment; filename="files_{final_doc_id}.zip"',
#         },
#     )

# def get_file_data_from_database(final_doc_id):
#     """
#     Fetch file data (folder path) for a given final_doc_id from the database.
#     """
#     try:
#         connection = get_db_connection()
#         cursor = connection.cursor(dictionary=True)
#         cursor.execute(
#             "SELECT final_doc_url FROM final_document WHERE row_doc_id = %s", (final_doc_id,)
#         )
#         result = cursor.fetchone()
#         print(result)
#         return result if result else None
#     except Exception as e:
#         print(f"Database error: {e}")
#         return None
#     finally:
#         cursor.close()
#         connection.close()



from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from db_config import get_db_connection
import os
import zipfile
from io import BytesIO
from datetime import datetime

router = APIRouter()

@router.get("/download_zip")
async def download_files(final_doc_id: str):
    """
    Endpoint to download a folder as a ZIP file for a given final_doc_id.
    """

    # Fetch file data from the database
    file_data = get_file_data_from_database(final_doc_id)
    if not file_data:
        raise HTTPException(status_code=404, detail="File not found")

    current_dir = os.getcwd()
    date = datetime.now().strftime("%Y-%m-%d")

    # Construct the correct folder path
    base_path = os.path.join(current_dir, "output", "Admin", date, final_doc_id)

    # Ensure the retrieved folder path from DB is valid
    final_doc_url = file_data["final_doc_url"].lstrip("/")
    folder_path = os.path.join(base_path, final_doc_url)

    print(f"Resolved Folder Path: {folder_path}")  # Debugging

    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="Folder not found")

    # Create a ZIP file in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=folder_path)
                zip_file.write(file_path, arcname=arcname)

    zip_buffer.seek(0)

    # Return the ZIP file as a downloadable response
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="files_{final_doc_id}.zip"'
        },
    )


def get_file_data_from_database(final_doc_id):
    """
    Fetch file data (folder path) for a given final_doc_id from the database.
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT final_doc_url FROM final_document WHERE row_doc_id = %s",
            (final_doc_id,),
        )
        result = cursor.fetchone()
        print(f"Database Result: {result}")  # Debugging
        return result if result else None
    except Exception as e:
        print(f"Database error: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
