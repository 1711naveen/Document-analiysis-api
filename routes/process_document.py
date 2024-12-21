import os
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException,APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from docx import Document
import mammoth
from db_config import get_db_connection

router = APIRouter()

logging.basicConfig(filename='app.log', level=logging.INFO)

# Helper function to write the docx file
def write_array_to_docx(array, name, doc_id, heading, chapter):
    try:
        doc = Document()

        # Add Heading and Chapter
        doc.add_paragraph(heading, style='Heading 1')
        doc.add_paragraph(chapter, style='Heading 2')

        # Add content to the document
        for item in array:
            doc.add_paragraph(item)

        # Create directories if they don't exist
        output_path = os.path.join(os.getcwd(), 'output', doc_id, name)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        doc.save(output_path)

        log_message = f"File Created: {name}\nPath: {output_path}\nDate and Time: {datetime.now()}\n{'-'*40}\n"
        logging.info(log_message)

    except Exception as e:
        logging.error(f"Error creating .docx file: {e}")

# Helper function to extract text from docx file
def extract_text_from_docx(file_path):
    try:
        with open(file_path, "rb") as docx_file:
            result = mammoth.extract_raw_text(docx_file)
            return result.value
    except Exception as e:
        logging.error(f"Error extracting text from file: {e}")
        return ""

# Route to handle API requests

@router.get("/process_document")
async def process_document(doc_id: str):
    try:
        conn = get_db_connection()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection error")
        
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM row_document WHERE row_doc_id = %s", (doc_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Document not found")

        file_path = os.path.join(os.getcwd(),'files', row[1])
        # Extract text from the Word document
        file_content = extract_text_from_docx(file_path)
        # print(file_content)
        chapter = file_content[0] if file_content else 1

        # Extract Figures and Tables
        figure_array = [line for line in file_content.split("\n") if line.startswith("Figure")]
        table_array = [line for line in file_content.split("\n") if line.startswith("Table")]
        print("table and figures")

        # Clean up Figures and Tables by removing colons and dots
        updated_figure_array = [figure.replace(":", "", 1) for figure in figure_array]
        updated_table_array = [table.replace(":", "", 1) for table in table_array]

        write_array_to_docx(updated_table_array, "Table.docx", doc_id, "List of Tables", f"Chapter {chapter}")
        write_array_to_docx(updated_figure_array, "Figure.docx", doc_id, "List of Figures", f"Chapter {chapter}")

        # Log the creation of the final document
        folder_url = f"/output/{doc_id}/"
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO final_document (row_doc_id, user_id, final_doc_size, final_doc_url, status, creation_date) '
                       'VALUES (%s, %s, %s, %s, %s, NOW())', (doc_id, row[2], row[3], folder_url, row[4]))  # Adjust indices
        conn.commit()
        conn.close()

        return JSONResponse(content={"success": True, "doc_id": doc_id})

    except Exception as e:
        logging.error(f"Error processing document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
