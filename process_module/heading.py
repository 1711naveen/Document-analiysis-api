import re
from docx import Document
import os
import roman
from word2number import w2n
from pathlib import Path
from datetime import datetime

global_logs = []


def convert_to_title_case(text):
    words = text.split(' ')
    # Capitalize the first word
    if words:
        words[0] = words[0].title()
    # Capitalize other words only if their length is greater than 4
    for i in range(1, len(words)):
        if len(words[i]) > 4:
            words[i] = words[i].title()
    return ' '.join(words)


def remove_trailing_period_from_runs(runs):
    """
    Removes a period (full stop) if it appears at the end of the last run while preserving formatting.
    """
    if runs:
        last_run = runs[-1]
        if last_run.text.endswith('.'):
            last_run.text = last_run.text.rstrip('.')



def remove_dot_afternumber(runs):
    return runs



def update_heading_runs(runs):
    """
    Updates the text of the runs to title case while preserving formatting.
    """
    # Combine all runs into a single text
    combined_text = ''.join(run.text for run in runs)
    new_text = convert_to_title_case(combined_text)
    if runs:
        # Update the first run with the new text
        runs[0].text = new_text
        
        # Clear the remaining runs
        for run in runs[1:]:
            run.text = ''



def remove_single_number_period(runs):
    """
    Removes a period if it appears immediately after a single number (e.g., "1.") 
    but keeps periods in section numbers like "1.1" or "1.1.1".
    """
    if runs:
        first_run = runs[0]
        # Regex to match a single number followed by a period but not section numbers like 1.1 or 1.1.1
        match = re.match(r'^(\d+)\.(\s|$)', first_run.text)
        if match:
            first_run.text = first_run.text.replace(match.group(1) + ".", match.group(1), 1)



# def write_to_log(doc_id):
#     """
#     Writes the global logs to a log file. If the file already exists, it appends to it.
#     :param doc_id: The document ID used to determine the log file's directory.
#     """
#     global global_logs
#     output_dir = os.path.join('output', str(doc_id))
#     os.makedirs(output_dir, exist_ok=True)
#     log_file_path = os.path.join(output_dir, 'global_logs.txt')
#     with open(log_file_path, 'a', encoding='utf-8') as log_file:
#         log_file.write("\n".join(global_logs) + "\n")
#     global_logs = []


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



def process_doc_function7(payload: dict, doc: Document, doc_id, user):    
    for para in doc.paragraphs:
        update_heading_runs(para.runs)
        # remove_trailing_period_from_runs(para.runs)
        # remove_single_number_period(para.runs)
        
    write_to_log(doc_id, user)