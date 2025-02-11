import re
from docx import Document
import os
import roman
from word2number import w2n


global_logs = []

def apply_sentence_case_footnotes(runs, line_number):
    """
    Converts the text in the given runs to sentence case.
    - The first letter of the first run is capitalized.
    - The rest of the text is converted to lowercase (except existing uppercase letters in abbreviations, etc.).
    """
    if not runs:
        return
    
    text = "".join(run.text for run in runs)
    if not text.strip():
        return
    
    sentence_cased_text = text[0].upper() + text[1:].lower() if len(text) > 1 else text.upper()
    
    start = 0
    for run in runs:
        run_length = len(run.text)
        run.text = sentence_cased_text[start:start + run_length]
        start += run_length



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
    


def process_doc_function8(payload: dict, doc: Document, doc_id):
    line_number = 1
    for para in doc.paragraphs:
        apply_sentence_case_footnotes(para.runs, line_number)
            
        
    write_to_log(doc_id)