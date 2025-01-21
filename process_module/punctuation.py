import re
from docx import Document
import os
from db_config import get_db_connection


# Global logs to keep track of changes
global_logs = []

# A map of numbers to century strings
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


def fetch_abbreviation_mappings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT original_word, abbreviated_form FROM abbreviation_mapping")
    mappings = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in mappings}


def apply_abbreviation_mapping(text, abbreviation_dict, line_number):
    global global_logs
    words = text.split()
    updated_text = []
    for word in words:
        updated_word = abbreviation_dict.get(word, word)
        if word != updated_word:
            global_logs.append(f"[apply_abbreviation_mapping] Line {line_number}: '{word}' -> '{updated_word}'")
        updated_text.append(updated_word)
    return ' '.join(updated_text)



def convert_century(text, line_number_offset):
    """
    Converts century notation like '21st' to 'the twenty-first century'
    and logs the changes with line numbers.

    :param text: The entire text to process, possibly spanning multiple lines.
    :param line_number_offset: The starting line number for this chunk of text.
    :return: The updated text with century notations converted.
    """
    global global_logs  # Global log to record changes
    lines = text.split('\n')  # Split text into individual lines
    updated_lines = []

    for index, line in enumerate(lines):
        words = line.split()  # Split line into words
        for i, word in enumerate(words):
            match = re.match(r"(\d+)(st|nd|rd|th)$", word)  # Match century notation
            if match:
                num = int(match.group(1))
                if num in century_map:
                    # Original and converted word
                    original_word = match.group(0)
                    converted_word = f"the {century_map[num]} century"
                    
                    # Log the change with the actual line number
                    global_logs.append(
                        f"[convert century] Line {line_number_offset + index}: {original_word} -> {converted_word}"
                    )
                    
                    # Replace the word in the line
                    words[i] = converted_word
        
        # Rebuild the updated line
        updated_lines.append(' '.join(words))

    # Return the updated text with all lines rebuilt
    return '\n'.join(updated_lines)



def process_symbols_mark(text, line_number, symbols=["®", "™", "©", "℗", "℠"]):
    """
    Ensures symbols like ®, ™, etc., appear only the first time in the text.
    Updates the global_log with changes, including line number, original text, and updated text.
    """
    original_text = text
    symbol_set = set()
    global global_logs
    
    for symbol in symbols:
        occurrences = list(re.finditer(re.escape(symbol), text))
        if occurrences:
            first_occurrence = occurrences[0].start()
            # Replace all occurrences after the first one
            text = (
                text[:first_occurrence + 1]
                + re.sub(re.escape(symbol), "", text[first_occurrence + 1:])
            )
            symbol_set.add(symbol)

    # Log changes if the text was modified
    if original_text != text:
        global_logs.append(
            f"[process_symbols_in_doc] Line {line_number}: '{original_text}' -> '{text}'"
        )

    return text





def enforce_serial_comma(text):
    lines = text.splitlines()
    updated_lines = []

    for line_number, line in enumerate(lines, start=1):
        original_line = line

        # Add a comma before "and" or "or" in lists
        new_line = re.sub(
            r'([^,]+), ([^,]+) (or) ([^,]+)',
            r'\1, \2, \3 \4',
            line
        )
        # Explicitly handle cases where "or" does not get the serial comma
        new_line = re.sub(
            r'([^,]+), ([^,]+) (and) ([^,]+)',
            r'\1, \2, \3 \4',
            new_line
        )
        if new_line != line:
            global_logs.append(f"[Serial comma correction] Line {line_number}: {line.strip()} -> {new_line.strip()}")
        
        updated_lines.append(new_line)
    return "\n".join(updated_lines)


def set_number_to_no(text, line_number):
    """
    Replaces 'Number X' or 'number X' with 'No. X' or 'no. X' and logs changes.
    :param text: The input text.
    :param line_number: Line number for logging.
    :return: Updated text with number abbreviations applied.
    """
    global global_logs

    def replace_number(match):
        word = match.group(1)
        num = match.group(2)
        updated_text = f"No. {num}" if word.istitle() else f"no. {num}"
        global_logs.append(f"[apply_number_abbreviation_rule] Line {line_number}: '{match.group(0)}' -> '{updated_text}'")
        return updated_text

    pattern = r'\b(Number|number)\s(\d+)\b'
    return re.sub(pattern, replace_number, text)




def enforce_am_pm(text, line_num):
    """
    Ensures consistent formatting for 'am' and 'pm' in the entire paragraph and logs changes.
    :param text: The paragraph text to process.
    :param line_num: The line number in the document for logging.
    :return: The updated text with corrected 'am' and 'pm' formats.
    """
    global global_logs  # Use a global log to record changes
    original_text = text  # Store the original text for comparison
    words = text.split()  # Split the paragraph into words

    corrected_words = []
    for word in words:
        original_word = word
        word_lower = word.lower()
        if word_lower in {"am", "a.m", "pm", "p.m"}:
            if "a" in word_lower:
                corrected_word = "a.m."
            elif "p" in word_lower:
                corrected_word = "p.m."
            
            if corrected_word != original_word:
                global_logs.append(
                    f"[am pm change] Line {line_num}: '{original_word}' -> '{corrected_word}'"
                )
        else:
            corrected_word = word 
        corrected_words.append(corrected_word)
    corrected_text = " ".join(corrected_words)
    return corrected_text



def enforce_serial_comma(text):
    lines = text.splitlines()
    updated_lines = []

    for line_number, line in enumerate(lines, start=1):
        original_line = line

        # Add a comma before "and" or "or" in lists
        new_line = re.sub(
            r'([^,]+), ([^,]+) (or) ([^,]+)',
            r'\1, \2, \3 \4',
            line
        )
        # Explicitly handle cases where "or" does not get the serial comma
        new_line = re.sub(
            r'([^,]+), ([^,]+) (and) ([^,]+)',
            r'\1, \2, \3 \4',
            new_line
        )
        if new_line != line:
            global_logs.append(f"[Serial comma correction] Line {line_number}: {line.strip()} -> {new_line.strip()}")
        updated_lines.append(new_line)
    return "\n".join(updated_lines)



def write_to_log(doc_id):
    global global_logs
    output_dir = os.path.join('output', str(doc_id))
    os.makedirs(output_dir, exist_ok=True)
    log_file_path = os.path.join(output_dir, 'global_logs.txt')
    with open(log_file_path, 'w', encoding='utf-8') as log_file:
        log_file.write("\n".join(global_logs))
    global_logs = []



def process_doc_function1(payload: dict, doc: Document, doc_id):
    """
    This function processes the document by converting century notations
    and highlighting specific words.
    """
    line_number = 1
    abbreviation_dict = fetch_abbreviation_mappings()
    for para in doc.paragraphs:
        para.text = convert_century(para.text, line_number)
        para.text = process_symbols_mark(para.text, line_number)
        para.text = enforce_serial_comma(para.text)
        para.text = set_number_to_no(para.text,line_number)
        para.text = apply_abbreviation_mapping(para.text, abbreviation_dict, line_number)
        para.text = enforce_am_pm(para.text, line_number)
        line_number += 1

       
    write_to_log(doc_id)
    
    
    
