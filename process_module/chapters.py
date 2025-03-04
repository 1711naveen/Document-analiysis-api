import re
from docx import Document
import os
import roman
from word2number import w2n
from pathlib import Path
from datetime import datetime

global_logs = []



def update_run_chapter(run, chapter_counter):
    """
    If the run's text starts with a chapter heading like:
      "Chapter One:" or "Chapter I:" or "Chapter 2:"
    then replace it with the converted numeral (or chapter_counter if conversion fails)
    followed by any text after the colon.
    """
    pattern = re.compile(
        r"(?i)^Chapter\s+((?:[IVXLCDM]+)|(?:[a-z]+)|(?:\d+))[:.]\s*(.*)$"
    )
    match = pattern.match(run.text)
    if match:
        numeral = match.group(1)
        rest = match.group(2).strip()
        # Remove a trailing period from the title, if present.
        if rest.endswith('.'):
            rest = rest[:-1].strip()
        converted = None
        try:
            if re.fullmatch(r"[IVXLCDM]+", numeral, re.IGNORECASE):
                # Explicit mapping for common Roman numerals.
                roman_map = {
                    "I": 1,
                    "II": 2,
                    "III": 3,
                    "IV": 4,
                    "V": 5,
                    "VI": 6,
                    "VII": 7,
                    "VIII": 8,
                    "IX": 9,
                    "X": 10,
                }
                numeral_upper = numeral.upper()
                if numeral_upper in roman_map:
                    print(numeral_upper)
                    converted = roman_map[numeral_upper]
                    print(converted)
                else:
                    raise ValueError("Invalid roman numeral")
            elif re.fullmatch(r"[a-z]+", numeral, re.IGNORECASE):
                converted = w2n.word_to_num(numeral.lower())
            else:
                print('inside else error')
                converted = int(numeral)
        except Exception:
            # Fallback to chapter_counter if conversion fails.
            print(Exception)
            converted = chapter_counter
        
        # Replace the chapter heading with the converted numeral.
        run.text = f"{converted}: {rest}" if rest else f"{converted}:"
        print(run.text)
        return True
    return False



def format_chapter_title(runs):
    if not runs:
        return

    full_text = "".join(run.text for run in runs)

    match = re.match(r'^(\d+:\s.*)\.$', full_text)
    if match:
        new_text = match.group(1)

        # Update the runs: set the first run to the new text and clear the rest.
        runs[0].text = new_text
        for run in runs[1:]:
            run.text = ""



def process_title(title):
    words = title.split()
    processed_words = []
    for word in words:
        cleaned_word = word.strip()
        if not cleaned_word:
            continue
        if len(cleaned_word) >= 5:
            processed_word = cleaned_word[0].upper() + cleaned_word[1:].lower()
        else:
            processed_word = cleaned_word.lower()
        processed_words.append(processed_word)
    return ' '.join(processed_words)



def format_chapter_heading_runs(runs):
    full_text = ''.join(run.text for run in runs)
    
    match = re.match(r'^(Chapter \d+: )(.*)', full_text, re.DOTALL)
    if not match:
        return
    
    chapter_part, title_part = match.groups()
    processed_title = process_title(title_part.strip())
    new_text = chapter_part + processed_title
    
    if runs:
        for run in runs[1:]:
            run.text = ''
        runs[0].text = new_text
    else:
        # This case should theoretically never happen with valid documents
        return




# Global variable to track the current chapter number
chapter_num = 1

# Mapping of written numbers to integers
written_numbers = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
    'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
    'nineteen': 19, 'twenty': 20
}

def chapter_numbering(runs):
    global chapter_num

    # Combine all runs into a single string and strip whitespace
    full_text = ''.join(run.text for run in runs).strip()

    # Check for Roman numeral chapter format (e.g., Chapter I: Introduction)
    roman_match = re.match(r'^\s*Chapter\s+([IVXLCDM]+)\s*:\s*(.*)$', full_text, re.IGNORECASE)
    if roman_match:
        title = roman_match.group(2).strip()
        new_text = f"{chapter_num}: {title}"
        _update_runs(runs, new_text)
        chapter_num += 1
        return

    # Check for written number chapter format (e.g., Chapter One: Introduction)
    written_match = re.match(r'^\s*Chapter\s+([A-Za-z]+)\s*:\s*(.*)$', full_text, re.IGNORECASE)
    if written_match:
        number_word = written_match.group(1).lower()
        if number_word in written_numbers:
            title = written_match.group(2).strip()
            new_text = f"{chapter_num}: {title}"
            _update_runs(runs, new_text)
            chapter_num += 1
            return

    # Check for numeric chapter format (e.g., Chapter 1: Introduction) and renumber it
    numeric_match = re.match(r'^\s*Chapter\s+(\d+)\s*:\s*(.*)$', full_text, re.IGNORECASE)
    if numeric_match:
        title = numeric_match.group(2).strip()
        new_text = f"{chapter_num}: {title}"
        _update_runs(runs, new_text)
        chapter_num += 1
        return

def _update_runs(runs, new_text):
    """Clear all runs and set the new text to the first run."""
    for run in runs:
        run.text = ''
    if runs:
        runs[0].text = new_text




def write_to_log(doc_id, user):
    global global_logs
    current_date = datetime.now().strftime("%Y-%m-%d")
    output_path_file = Path(os.getcwd()) / 'output' / user / current_date / str(doc_id) / 'text' 
    # dir_path = output_path_file.parent

    # output_dir = os.path.join('output', str(doc_id))
    os.makedirs(output_path_file, exist_ok=True)
    log_file_path = os.path.join(output_path_file, 'global_logs.txt')

    with open(log_file_path, 'a', encoding='utf-8') as log_file:
        log_file.write("\n".join(global_logs))

    global_logs = []




def process_doc_function6(payload: dict, doc: Document, doc_id, user):
    chapter_counter = [0]
    global chapter_num
    chapter_num = 1
    for para in doc.paragraphs:
        format_chapter_heading_runs(para.runs)
        chapter_numbering(para.runs)
        if para.style.name == "Heading 1":
            # for run in para.runs:
            #     if update_run_chapter(run, chapter_counter):
            #         chapter_counter += 1
            #         break
            format_chapter_title(para.runs)
        
    write_to_log(doc_id, user)
    chapter_num = 1