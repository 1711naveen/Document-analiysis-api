
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
import os
import shutil
from zipfile import ZipFile
from xml.etree.ElementTree import fromstring
import mammoth
from db_config import get_db_connection

router = APIRouter()


SECRET_KEY = "naveen"
security = HTTPBearer()

@router.post("/upload/")
async def upload_file(
    file: UploadFile = File(...),
    token: HTTPAuthorizationCredentials = Depends(security)
):
    # Verify the JWT token
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=["HS256"])
        email = payload.get("email")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Validate file
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    # Save file to disk
    upload_dir = "files"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    print(file)

    # Extract metadata from the Word document
    try:
        with ZipFile(file_path, "r") as zip_file:
            app_xml_content = zip_file.read("docProps/app.xml").decode("utf-8")
            root = fromstring(app_xml_content)
            namespace = {"ns": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"}
            pages = root.find("ns:Pages", namespace).text if root.find("ns:Pages", namespace) is not None else None
            characters = root.find("ns:Characters", namespace).text if root.find("ns:Characters", namespace) is not None else None
            lines = root.find("ns:Lines", namespace).text if root.find("ns:Lines", namespace) is not None else None
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid .docx structure or missing metadata")




    # Extract text using Mammoth
    try:
        with open(file_path, "rb") as doc_file:
            result = mammoth.extract_raw_text(doc_file)
            extracted_text = result.value
            word_count = len(extracted_text.split())
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error extracting text from .docx file")


    print("pages")
    print(pages)
    print(characters)
    print(lines)
    print(word_count)

    # Save file metadata to the database
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Get admin ID from email
            cursor.execute("SELECT admin_id FROM admins WHERE admin_email = %s", (email,))
            admin_row = cursor.fetchone()
            if not admin_row:
                raise HTTPException(status_code=404, detail="Admin not found")

            admin_id = admin_row[0]
            print(admin_id)

            # Insert document details into the database
            cursor.execute(
                """
                INSERT INTO row_document 
                (row_doc_name, row_doc_type, row_doc_size, user_id, row_doc_url, status, creation_date)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """,
                (file.filename, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", file.size, admin_id, f"/files/{file.filename}", "active")
            )
            connection.commit()

            # Get the last inserted ID
            cursor.execute("SELECT LAST_INSERT_ID() AS last_inserted_id")
            last_inserted_id = cursor.fetchone()[0]
            print(last_inserted_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        connection.close()

    # Return success response
    return JSONResponse(
        {
            "success": True,
            "message": "File uploaded and saved to database",
            "characters": characters,
            "words": word_count,
            "lines": lines,
            "pages": pages,
            "doc_id": last_inserted_id,
        }
    )
