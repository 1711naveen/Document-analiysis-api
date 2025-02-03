import re
from docx import Document
import os


global_logs = []


def replace_dashes(runs, line_number):
    """
    Replaces em dashes (—) and normal hyphens (-) with en dashes (–) in the given runs.
    Logs changes to a global list with details of the modification in the desired format.
    Args:
        runs: The list of runs in a paragraph.
        line_number: The line number of the paragraph for context.
    """
    global global_logs
    for run in runs:
        original_text = run.text
        modified_text = original_text.replace('—', '–').replace('-', '–')

        # If changes are made, log the specific characters that changed
        if original_text != modified_text:
            for orig, new in zip(original_text, modified_text):
                if orig != new:
                    global_logs.append(
                        f"[replace_dashes_with_logging] Line {line_number}: '{orig}' -> '{new}'"
                    )

        # Update the run text
        run.text = modified_text


def format_hyphen_to_en_dash(runs, line_number):
    """
    Replace hyphens with en dashes in the given runs.
    Adjust spacing based on surrounding context:
    - Add spaces if there are words on both sides.
    - Remove spaces if there are numbers on both sides.
    Logs changes to the global 'global_logs' list.
    Args:
        runs: The list of runs in a paragraph.
        line_number: The line number of the paragraph being processed.
    """
    global global_logs
    word_range_pattern = re.compile(r'(\b\w+)\s*-\s*(\w+\b)')
    number_range_pattern = re.compile(r'(\d+)\s*-\s*(\d+)')

    for run in runs:
        original_text = run.text
        # Replace hyphen with en dash and remove spaces for number ranges
        updated_text = number_range_pattern.sub(r'\1–\2', original_text)
        # Replace hyphen with en dash and ensure spaces for word ranges
        updated_text = word_range_pattern.sub(r'\1 – \2', updated_text)

        if updated_text != original_text:
            # Log the change
            global_logs.append(
                f"Line {line_number}: '{original_text}' -> '{updated_text}'"
            )

        # Update the run text
        run.text = updated_text

                

def write_to_log(doc_id):
    """
    Writes the global logs to a log file. If the file already exists, it appends to it.
    :param doc_id: The document ID used to determine the log file's directory.
    """
    global global_logs
    output_dir = os.path.join('output', str(doc_id))
    os.makedirs(output_dir, exist_ok=True)
    log_file_path = os.path.join(output_dir, 'global_logs.txt')
    with open(log_file_path, 'a', encoding='utf-8') as log_file:
        log_file.write("\n".join(global_logs) + "\n")
    global_logs = []
    


def process_doc_function3(payload: dict, doc: Document, doc_id):
    """
    This function processes the document by converting century notations
    and highlighting specific words.
    """
    line_number = 1
    for para in doc.paragraphs:
        replace_dashes(para.runs, line_number)
        format_hyphen_to_en_dash(para.runs, line_number)
        
    write_to_log(doc_id)

