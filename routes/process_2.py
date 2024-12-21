from fastapi import APIRouter, Query, HTTPException
from pathlib import Path
import os
import docx
from db_config import get_db_connection
import re

router = APIRouter()

def fetch_document_details(doc_id):
    """Fetch document details from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM row_document WHERE row_doc_id = %s", (doc_id,))
    rows = cursor.fetchone()
    conn.close()
    if not rows:
        raise HTTPException(status_code=404, detail="Document not found")
    return rows


def fetch_abbreviation_mappings():
    """Fetch abbreviation mappings from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT original_word, abbreviated_form FROM abbreviation_mapping")
    mappings = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in mappings}


def apply_abbreviation_mapping(text, abbreviation_dict):
    """Replace words in text based on abbreviation mappings."""
    words = text.split()
    updated_words = [abbreviation_dict.get(word, word) for word in words]
    return ' '.join(updated_words)



def apply_number_abbreviation_rule(text: str) -> str:
    """
    Replaces instances of 'Number X' or 'number X' with 'No. X' or 'no. X', preserving the case.
    """
    # Use regex to match 'Number' or 'number' followed by a space and a number
    def replace_number(match):
        word = match.group(1)  # 'Number' or 'number'
        num = match.group(2)  # The number following it
        if word.istitle():
            return f"No. {num}"  # Preserve capitalization for 'Number'
        else:
            return f"no. {num}"

    # Pattern matches 'Number' or 'number' followed by a space and a numerical value
    pattern = r'\b(Number|number)\s(\d+)\b'
    return re.sub(pattern, replace_number, text)



# def process_document(file_path, abbreviation_dict):
#     """Process the document to apply rules and mappings."""
#     doc = docx.Document(file_path)
#     for para in doc.paragraphs:
#         para.text = apply_abbreviation_mapping(para.text, abbreviation_dict)
#         para.text = apply_number_abbreviation_rule(para.text)
#     return doc

def log_transformations(log_path, transformations):
    """
    Write transformations to a log file.
    Each transformation includes the line number and change details.
    """
    with open(log_path, "w", encoding="utf-8") as log_file:
        log_file.write("---- Document Transformation Log ----\n\n")
        log_file.write("1. Abbreviated Words and Number Format changed:\n")
        for transformation in transformations:
            log_file.write(f"{transformation}\n")


# def process_document(file_path, abbreviation_dict, log_path):
#     """
#     Process the document to apply rules and mappings while logging changes.
#     """
#     doc = docx.Document(file_path)
#     transformations = []  # To store log details
    
#     for line_num, para in enumerate(doc.paragraphs, start=1):
#         original_text = para.text
#         updated_text = apply_abbreviation_mapping(original_text, abbreviation_dict)
#         if original_text != updated_text:
#             transformations.append(f"Line {line_num}: {original_text} -> {updated_text}")

#         # Apply number abbreviation rule
#         final_text = apply_number_abbreviation_rule(updated_text)
#         if updated_text != final_text:
#             transformations.append(f"Line {line_num}: {updated_text} -> {final_text}")

#         para.text = final_text

#     # Write log file
#     log_transformations(log_path, transformations)
#     return doc


def process_document(file_path, abbreviation_dict, log_path):
    """
    Process the document to apply rules and mappings while logging changes.
    """
    doc = docx.Document(file_path)
    transformations = []  # To store log details

    for line_num, para in enumerate(doc.paragraphs, start=1):
        original_text = para.text
        updated_words = []
        words = original_text.split()

        for word in words:
            # Check for abbreviation mapping changes
            if word in abbreviation_dict:
                updated_words.append(abbreviation_dict[word])
                transformations.append(f"Line {line_num}: {word} -> {abbreviation_dict[word]}")
            else:
                updated_words.append(word)

        # Apply the number abbreviation rule
        updated_line = ' '.join(updated_words)
        updated_line_with_numbers = apply_number_abbreviation_rule(updated_line)
        if updated_line != updated_line_with_numbers:
            number_matches = re.findall(r'\b(Number|number)\s(\d+)\b', updated_line)
            for match in number_matches:
                transformations.append(f"Line {line_num}: {match[0]} {match[1]} -> {'No.' if match[0].istitle() else 'no.'} {match[1]}")

        para.text = updated_line_with_numbers

    log_transformations(log_path, transformations)

    return doc




def save_processed_document(doc, doc_id, file_name):
    """Save the processed document to the output directory."""
    output_dir = Path(os.getcwd()) / 'output' / str(doc_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"processed_{file_name}"
    doc.save(output_path)
    return output_path



# @router.get("/process_file_with_abbreviations")
# async def process_file_with_abbreviations(doc_id: int = Query(...)):
#     try:
#         # Fetch document details
#         rows = fetch_document_details(doc_id)
#         file_path = os.path.join(os.getcwd(), 'files', rows[1])

#         if not os.path.exists(file_path):
#             raise HTTPException(status_code=404, detail="File not found on server")

#         # Fetch abbreviation mappings
#         abbreviation_dict = fetch_abbreviation_mappings()

#         # Process the document
#         doc = process_document(file_path, abbreviation_dict)

#         # Save the processed document
#         output_path = save_processed_document(doc, doc_id, rows[1])

#         return {"success": True, "message": f"File processed and saved at {output_path}"}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))



@router.get("/process_file_with_abbreviations")
async def process_file_with_abbreviations(doc_id: int = Query(...)):
    try:
        # Fetch document details
        rows = fetch_document_details(doc_id)
        file_path = os.path.join(os.getcwd(), 'files', rows[1])

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found on server")

        # Fetch abbreviation mappings
        abbreviation_dict = fetch_abbreviation_mappings()

        # Prepare output directory and log file path
        output_dir = Path(os.getcwd()) / 'output' / str(doc_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        log_path = output_dir / "processing_log.txt"

        # Process the document with logging
        doc = process_document(file_path, abbreviation_dict, log_path)

        # Save the processed document
        output_path = save_processed_document(doc, doc_id, rows[1])

        return {
            "success": True,
            "message": f"File processed and saved at {output_path}",
            "log": f"Log file created at {log_path}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))