import re
from docx import Document
import os
import roman
from word2number import w2n


global_logs = []


def correct_chapter_numbering(runs, chapter_counter):
    chapter_pattern = re.compile(r"(?i)\bchapter\s+((?:[IVXLCDM]+)|(?:[a-z]+)|(?:\d+))[:.]?\s")
    
    for run in runs:
        match = chapter_pattern.search(run.text)
        if match:
            chapter_content = match.group(1)
            if re.match(r"^[IVXLCDM]+$", chapter_content, re.IGNORECASE):
                chapter_number = roman.fromRoman(chapter_content.upper())
            elif re.match(r"^[a-z]+$", chapter_content, re.IGNORECASE):
                chapter_number = w2n.word_to_num(chapter_content.lower())
            else:
                chapter_number = int(chapter_content)
            
            run.text = chapter_pattern.sub(f"Chapter {chapter_number}: ", run.text, count=1)



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
    


def process_doc_function6(payload: dict, doc: Document, doc_id):
    
    chapter_counter = [0]
    for para in doc.paragraphs:
        if para.text.strip().startswith("Chapter"):
            # para.text = correct_chapter_numbering(para.text, chapter_counter)
            # formatted_title = format_chapter_title(para.text)
            # para.text = formatted_title
            
            correct_chapter_numbering(para.runs, chapter_counter)
            format_chapter_title(para.runs)
        
    write_to_log(doc_id)