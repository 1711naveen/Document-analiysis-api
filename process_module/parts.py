import re
from docx import Document
import os
import roman
from word2number import w2n
from pathlib import Path
from datetime import datetime

global_logs = []



def some_function(runs):
    """
    Process a list of runs:
    - Convert words with at least 5 characters so that only the first letter is uppercase and the rest lowercase.
    """
    def process_word(match):
        word = match.group(0)
        if len(word) >= 5:
            return word[0].upper() + word[1:].lower()
        return word

    for run in runs:
        # Update the run's text using a regex substitution
        run.text = re.sub(r'\b\w+\b', process_word, run.text)
        


def convert_part_numbers(runs, is_heading=False):
    """
    Convert occurrences of phrases like "part <number>" in the given runs
    to have proper title-case (e.g., "Part One", "Part Two", etc.).
    The conversion is only applied if the text is not marked as a heading.

    Parameters:
        runs (list): A list of run objects from a docx paragraph.
        is_heading (bool): If True, no conversion will occur.
    """
    if is_heading:
        return

    # Define a mapping from lower-case number words to their title-case versions.
    number_mapping = {
        'one': 'One',
        'two': 'Two',
        'three': 'Three',
        'four': 'Four',
        'five': 'Five',
        'six': 'Six',
        'seven': 'Seven',
        'eight': 'Eight',
        'nine': 'Nine',
        'ten': 'Ten',
        'eleven': 'Eleven',
        'tweleve':'Tweleve'
    }

    # Compile a single regex that matches "part" followed by a number word.
    pattern = re.compile(r'\bpart\s+(\w+)\b', re.IGNORECASE)

    def replacer(match):
        # Get the captured number word and normalize it to lower-case.
        num_word = match.group(1).lower()
        if num_word in number_mapping:
            # Return "Part" with proper title-case for the number word.
            return "Part " + number_mapping[num_word]
        # If the number word isn't in our mapping, leave it unchanged.
        return match.group(0)

    # Update each run's text using the regex substitution.
    for run in runs:
        run.text = pattern.sub(replacer, run.text)
        
        
def some_function(runs):
    def process_word(match):
        word = match.group(0)
        if len(word) >= 5:
            return word[0].upper() + word[1:].lower()
        return word

    for run in runs:
        # Process words with regex substitution
        run.text = re.sub(r'\b\w+\b', process_word, run.text)
        # Remove a trailing dot at the end of the text, if it exists
        run.text = re.sub(r'\.$', '', run.text)


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




def process_doc_function5(payload: dict, doc: Document, doc_id, user):
    for para in doc.paragraphs:
        is_heading = para.style.name.startswith("Heading")
        convert_part_numbers(para.runs, is_heading=is_heading)
        
        if para.style.name.startswith("Heading"):
            some_function(para.runs)
            if para.runs and para.runs[-1].text.endswith('.'):
                para.runs[-1].text = para.runs[-1].text.rstrip('.')
        
    write_to_log(doc_id, user)