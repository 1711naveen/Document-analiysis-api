import re
from docx.shared import RGBColor
from num2words import num2words
import enchant
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse
import os
import docx
from sqlalchemy import text
from db_config import get_db_connection
import mammoth
from datetime import datetime
from pathlib import Path
import logging  

router = APIRouter()

us_dict = enchant.Dict("en_US") #for US english
# uk_dict = enchant.Dict("en_GB") # for UK english

century_map = {
    1: "first",
    2: "second",
    3: "third",
    4: "fourth",
    5: "fifth",
    6: "sixth",
    7: "seventh",
    8: "eighth",
    9: "ninth",
    10: "tenth",
    11: "eleventh",
    12: "twelfth",
    13: "thirteenth",
    14: "fourteenth",
    15: "fifteenth",
    16: "sixteenth",
    17: "seventeenth",
    18: "eighteenth",
    19: "nineteenth",
    20: "twentieth",
    21: "twenty-first",
    22: "twenty-second",
    23: "twenty-third",
    24: "twenty-fourth",
    25: "twenty-fifth",
}

def convert_century(word):
    match = re.match(r"(\d+)(st|nd|rd|th)$", word)
    if match:
        num = int(match.group(1))
        if num in century_map:
            return f"the {century_map[num]} century"
    return word

def clean_word(word):
    return word.strip(",.?!:;\"'()[]{}")

def replace_curly_quotes_with_straight(text):
    return text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")

def correct_acronyms(word):
    if re.match(r"([a-z]\.){2,}[a-z]\.?", word):
        return word.replace(".", "")
    if re.match(r"([A-Z]\.){2,}[A-Z]\.?", word):
        return word.replace(".", "")
    return word

def enforce_am_pm(word):
    word_lower = word.lower()
    if word_lower in {"am", "a.m", "pm", "p.m"}:
        if "a" in word_lower:
            return "a.m."
        elif "p" in word_lower:
            return "p.m."
    return word

def remove_unnecessary_apostrophes(word):
    word = re.sub(r"(\d{4})'s\b", r"\1s", word)
    word = re.sub(r"'(\d{2})s\b", r"\1s", word)
    word = re.sub(r"(\d{4}s)'\b", r"\1", word)
    word = re.sub(r"(\d+)'(s|st|nd|rd|th)\b", r"\1\2", word)
    word = re.sub(r"^(\d{2})s\b", r"19\1s", word)
    return word

def spell_out_number_and_unit(sentence):
    match = re.match(r"^(\d+)\s+([a-zA-Z]+)", sentence)
    if match:
        number = int(match.group(1))
        unit = match.group(2)
        number_word = num2words(number, to="cardinal")
        unit_word = unit.lower() if unit.lower()[-1] == 's' else unit.lower() + "s"
        return f"{number_word.capitalize()} {unit_word}{sentence[len(match.group(0)):]}"
    return sentence


def insert_thin_space_between_number_and_unit(text):
    thin_space = '\u2009'
    text = re.sub(r"(\d)(?=\s?[a-zA-Z]+)(?!\s?°)", r"\1" + thin_space, text)
    return text



def format_dates(text):
    text = re.sub(r"\b(\d+)\s?(BCE|CE)\b", lambda m: f"{m.group(1)} {m.group(2).lower()}", text)
    text = re.sub(r"\b(AD|BC)\.\b", r"\1 ", text)
    text = re.sub(r"(\d+)\s?(BCE|CE|AD|BC)\b", r"\1 \2", text)
    return text


def remove_space_between_degree_and_direction(text):
    return re.sub(r"(\d+) °\s?(N|S|E|W)\b", r"\1°\2", text)


def enforce_lowercase_k_and_l(text):
    text = re.sub(r"(\d) K([m|g])", r"\1 k\2", text)
    text = re.sub(r"\bL\b", "l", text)
    return text


def precede_decimal_with_zero(text):
    # Matches standalone decimal numbers below 1, e.g., ".75" or " .5", but not parts of larger numbers.
    text = re.sub(r"(?<!\d)(?<!\d\.)\.(\d+)", r"0.\1", text)
    return text


def adjust_terminal_punctuation_in_quotes(text):
    # Matches quoted matter ending with a question or exclamation mark, ensuring punctuation is inside the quotes.
    text = re.sub(
        r"([‘“])([^’”]*[?!])([’”])\.",
        r"\1\2\3",
        text
    )
    return text


def correct_possessive_names(text):
    # Handles singular possessives for names ending in 's'
    text = re.sub(r"\b([A-Za-z]+s)\b(?<!\bs')'", r"\1's", text)  # Add 's' for singular possessives
    text = re.sub(r"\b([A-Za-z]+s)'\b", r"\1'", text)  # Retain just the apostrophe for plurals
    return text


def remove_concluding_slashes_from_urls(text):
    # Matches URLs ending with a forward slash, but not when followed by other characters (like periods).
    text = re.sub(r"(https?://[^\s/]+(?:/[^\s/]+)*)/", r"\1", text)
    return text


def clean_web_addresses(text):
    return re.sub(r"<(https?://[^\s<>]+)>", r"\1", text)


def format_ellipses_in_series(text):
    # Matches series like "x1, x2, ..., xn" and ensures the ellipsis has a comma and space after it.
    text = re.sub(r"(\w+),\s*(\w+),\s*\.\.\.\s*(\w+)", r"\1, \2, …, \3", text)
    return text


def highlight_and_correct(doc):
    for para in doc.paragraphs:
        para.text = format_dates(para.text)
        para.text = spell_out_number_and_unit(para.text)
        para.text = remove_space_between_degree_and_direction(para.text)
        para.text = enforce_lowercase_k_and_l(para.text)
        para.text = precede_decimal_with_zero(para.text)
        para.text = format_ellipses_in_series(para.text)  # New rule added here
        # para.text = adjust_terminal_punctuation_in_quotes(para.text)
        para.text = correct_possessive_names(para.text)
        para.text = remove_concluding_slashes_from_urls(para.text)
        para.text = clean_web_addresses(para.text)

        formatted_runs = []

        for run in para.runs:
            run_text = replace_curly_quotes_with_straight(run.text)
            run_text = insert_thin_space_between_number_and_unit(run_text)
            words = run_text.split()

            for i, word in enumerate(words):
                original_word = word
                punctuation = ""

                if word[-1] in ",.?!:;\"'()[]{}":
                    punctuation = word[-1]
                    word = word[:-1]

                if word.startswith('"') or word.startswith("'") or word.endswith('"') or word.endswith("'"):
                    formatted_runs.append((word, None))
                    if i < len(words) - 1:
                        formatted_runs.append((" ", None))
                    continue

                word = remove_unnecessary_apostrophes(word)

                cleaned_word = clean_word(word)
                corrected_word = cleaned_word

                if cleaned_word:
                    corrected_word = correct_acronyms(cleaned_word)
                    corrected_word = enforce_am_pm(corrected_word)
                    corrected_word = convert_century(corrected_word)

                    if corrected_word != cleaned_word:
                        formatted_runs.append((corrected_word + punctuation, RGBColor(0, 0, 0)))
                    elif not us_dict.check(corrected_word.lower()):
                        formatted_runs.append((corrected_word + punctuation, RGBColor(255, 0, 0)))
                    else:
                        formatted_runs.append((corrected_word + punctuation, None))
                else:
                    formatted_runs.append((original_word + punctuation, None))

                if i < len(words) - 1:
                    formatted_runs.append((" ", None))

        para.clear()
        for text, color in formatted_runs:
            new_run = para.add_run(text)
            if color:
                new_run.font.color.rgb = color


def clean_word1(word):
    return ''.join(filter(str.isalnum, word)).lower()


# Helper function to extract text from docx file
def extract_text_from_docx(file_path):
    try:
        with open(file_path, "rb") as docx_file:
            result = mammoth.extract_raw_text(docx_file)
            return result.value
    except Exception as e:
        # logging.error(f"Error extracting text from file: {e}")
        return ""

@router.get("/process_us")
async def process_file(doc_id: int = Query(...)):
    try:
        # Connect to the database
        conn = get_db_connection()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection error")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM row_document WHERE row_doc_id = %s", (doc_id,))
        # query = text('SELECT * FROM row_document WHERE row_doc_id = :doc_id')
        # result = db.execute(query, {"doc_id": doc_id})
        # rows = result.fetchall()
        
        rows = cursor.fetchone()
        # conn.close()

        if not rows:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # file_path = rows[1]
        file_path = os.path.join(os.getcwd(),'files',rows[1])


        # Verify the file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found on server")
        
        # Log file for wrong word
        log_filename = "spell_check_log.txt"
        # async with aiofiles.open(file_path, 'rb') as file:
        #     buffer = await file.read()

        # Extract raw text using Mammoth
        file_content = extract_text_from_docx(file_path)
        text = file_content

        # Start time of processing
        start_time = datetime.now()
               

        # Prepare log data
        log_data = []
        log_data.append(f"FileName: {rows[1]}\n")
        log_data.append(f"Processing started at: {start_time.isoformat()}\n")
        
        # Split text into lines and process each line
        lines = text.split('\n')
        for index, line in enumerate(lines):
            words = line.split()
            for word in words:
                cleaned = clean_word1(word)
                if cleaned and not us_dict.check(cleaned):
                    suggestions = us_dict.suggest(cleaned)
                    suggestion_text = (
                        f" Suggestions: {', '.join(suggestions)}"
                        if suggestions else " No suggestions available"
                    )
                    log_data.append(f"Line {index + 1}: {word} ->{suggestion_text}\n")

        # Write log data to file
        with open(log_filename, "w", encoding="utf-8") as log_file:
            log_file.writelines(log_data)
        
        end_time = datetime.now()
        
        # do it leter
        # time_taken = round(end_time - start_time, 2)  # Time in seconds
        # log_data = [f"\nAnalysis completed in {time_taken} seconds."]
        
        
        row_doc_name = rows[1]
        document_name = row_doc_name.replace('.docx', '')
        log_filename = f"{document_name}_log_us.txt"

        
        output_path_file = Path(os.getcwd()) / 'output' / str(doc_id) / log_filename
        # output_path_file=os.path.join(os.getcwd(),'output',str(doc_id),log_filename)
        
    
        dir_path = output_path_file.parent
        # dir_path = os.path.join(os.getcwd(), 'output', str(doc_id))
        
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            
        print(dir_path)

        # Write log data to the log file
        with open(output_path_file, 'w') as log_file:
            log_file.write("\n".join(log_data))

        # Get a database connection
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection error")
        

        # Check if the document already exists in the database
        cursor.execute("SELECT final_doc_id FROM final_document WHERE row_doc_id = %s", (doc_id,))
        existing_rows = cursor.fetchall()
        print(cursor)

        if existing_rows:
            # File already processed
            print('File already processed in final_document. Skipping insert.')
        else:
            # Insert new record if not present
            folder_url = f'/output/{doc_id}/'
            cursor.execute(
                '''INSERT INTO final_document (row_doc_id, user_id, final_doc_size, final_doc_url, status, creation_date)
                VALUES (%s, %s, %s, %s, %s, NOW())''',
                (doc_id, rows[1], rows[2], folder_url, rows[7])
            )
            print('New file processed and inserted into final_document.')
            

        # Commit changes to the database
        conn.commit()

        output_dir = os.path.join("output", str(doc_id))  # Create directory path based on doc_id
        os.makedirs(output_dir, exist_ok=True) 
        output_path = os.path.join(output_dir, f"processed_{os.path.basename(file_path)}")  # Generate output file path
        doc = docx.Document(file_path)
        highlight_and_correct(doc)
        doc.save(output_path)
        logging.info(f"Processed file stored at: {output_path}")
        
        return {"success": True, "message": f"File processed and stored at {output_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
