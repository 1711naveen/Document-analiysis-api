import re
from docx import Document
import os
import roman
from word2number import w2n
from pathlib import Path
from datetime import datetime

global_logs = []


# def correct_chapter_numbering(runs, chapter_counter):
#     chapter_pattern = re.compile(r"(?i)\bchapter\s+((?:[IVXLCDM]+)|(?:[a-z]+)|(?:\d+))[:.]?\s")
    
#     for run in runs:
#         match = chapter_pattern.search(run.text)
#         if match:
#             chapter_content = match.group(1)
#             if re.match(r"^[IVXLCDM]+$", chapter_content, re.IGNORECASE):
#                 chapter_number = roman.fromRoman(chapter_content.upper())
#             elif re.match(r"^[a-z]+$", chapter_content, re.IGNORECASE):
#                 chapter_number = w2n.word_to_num(chapter_content.lower())
#             else:
#                 chapter_number = int(chapter_content)
            
#             run.text = chapter_pattern.sub(f"Chapter {chapter_number}: ", run.text, count=1)



def correct_chapter_numbering(runs, chapter_counter):
    
    # Regex to match a chapter heading at the beginning of the text.
    # It matches the word "Chapter" (ignoring case), followed by one or more spaces and a chapter number,
    # which can be in the form of Roman numerals, words, or digits. Optional punctuation follows.
    chapter_pattern = re.compile(r"^chapter\s+((?:[IVXLCDM]+)|(?:[a-z]+)|(?:\d+))[:.]?\s", re.IGNORECASE)

    for run in runs:
        # Only process runs with a style that indicates a heading.
        if not (hasattr(run, 'style') and run.style and hasattr(run.style, 'name') and 
                run.style.name.lower().startswith('heading')):
            continue
        
        # Process only if the text starts with a chapter heading.
        if chapter_pattern.search(run.text):
            run.text = chapter_pattern.sub(f"Chapter {chapter_counter}: ", run.text, count=1)
            chapter_counter += 1

    return runs


def format_chapter_title(runs):
    chapter_pattern = re.compile(r"Chapter\s+([\dIVXLCDM]+)[\.:]\s*(.*)", re.IGNORECASE)
    
    for run in runs:
        match = chapter_pattern.match(run.text)
        if match:
            chapter_number = match.group(1)
            chapter_title = match.group(2).rstrip('.')
            words = chapter_title.split()
            formatted_title = " ".join([
                word.capitalize() if i == 0 or len(word) >= 4 else word.lower()
                for i, word in enumerate(words)
            ])
            run.text = f"{chapter_number}. {formatted_title}"



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


def process_doc_function6(payload: dict, doc: Document, doc_id, user):
    
    chapter_counter = [0]
    for para in doc.paragraphs:
        if para.text.strip().startswith("Chapter"):
            # para.text = correct_chapter_numbering(para.text, chapter_counter)
            # formatted_title = format_chapter_title(para.text)
            # para.text = formatted_title
            
            correct_chapter_numbering(para.runs, chapter_counter)
            format_chapter_title(para.runs)
        
    write_to_log(doc_id, user)