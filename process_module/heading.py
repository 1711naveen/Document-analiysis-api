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




def process_heading_titles_case(doc):
    """
    Process all heading paragraphs in the document.
    For each heading, every word with 5 or more characters is converted
    to title case (first letter uppercase, the rest lowercase), while words
    with fewer than 5 characters remain unchanged.
    """
    for para in doc.paragraphs:
        # Check if the paragraph is a heading (this assumes style names like "Heading 1", "Heading 2", etc.)
        if para.style.name.startswith("Heading"):
            words = para.text.split()
            new_words = []
            for word in words:
                if len(word) >= 5:
                    # Convert to title case: first letter uppercase, rest lowercase
                    new_words.append(word[0].upper() + word[1:].lower())
                else:
                    new_words.append(word)
            new_text = " ".join(new_words)
            para.text = new_text


def remove_dot_in_heading_runs(runs):
    """
    Processes a list of runs (from a heading paragraph) and removes the period (full stop)
    after the section number at the beginning of the text. This change is applied only if the 
    heading does NOT start with 'tables', 'figures', or 'chapters' (case insensitive).
    
    The regex looks for a section numbering pattern at the very beginning of the text,
    for example: "1. Introduction" or "1.2. Overview". It removes the period after the number.
    """
    if not runs:
        return

    # Combine all run texts to form the complete heading text
    full_text = ''.join(run.text for run in runs)

    # If the text (after stripping whitespace) starts with any of the exempt words, do nothing.
    if full_text.lstrip().lower().startswith(('tables', 'figures', 'chapters')):
        return

    # Regex pattern: Look for a numbering pattern at the beginning of the text followed by a dot and a space.
    # E.g., "1. " or "1.2. " etc.
    pattern = re.compile(r'^(\d+(?:\.\d+)*)(\.)\s')
    # Substitute the match by removing the dot: "1. " -> "1 "
    new_text = pattern.sub(r'\1 ', full_text)

    # Update the runs with the new text.
    offset = 0
    for run in runs:
        run_length = len(run.text)
        run.text = new_text[offset: offset + run_length]
        offset += run_length





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
        process_heading_titles_case(doc)
        for para in doc.paragraphs:
            remove_dot_in_heading_runs(para.runs)
        # remove_trailing_period_from_runs(para.runs)
        # remove_single_number_period(para.runs)
        
    write_to_log(doc_id, user)