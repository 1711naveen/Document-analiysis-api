import re
from docx import Document
import os
from datetime import datetime
from pathlib import Path

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

# This is not working properly
# def remove_double_dash(runs):
#     full_text = ''.join(run.text for run in runs)
#     processed_text = re.sub(r'(\w)--(\w)', r'\1\2', full_text)
#     processed_text = re.sub(r'(\w+)-\n-(\w+)', r'\1\2', processed_text)
#     for run in runs:
#         run.text = ''
#     if runs:
#         runs[0].text = processed_text


def remove_double_dash(runs):
    """
    Remove double dashes from runs without disturbing URLs.
    Instead of joining all runs into one (which may cause formatting changes
    such as unintended hyperlinking), process each run individually.
    If a URL is present in a run, it is temporarily protected.
    """
    # Pattern to detect URLs (http or https)
    url_pattern = re.compile(r'https?://[^\s]+')
    
    for run in runs:
        original_text = run.text
        
        # Protect URLs: temporarily replace them with placeholders.
        placeholders = {}
        def protect_url(match):
            placeholder = f"__URL{len(placeholders)}__"
            placeholders[placeholder] = match.group(0)
            return placeholder
        
        protected_text = url_pattern.sub(protect_url, original_text)
        
        # Remove double dashes between word characters.
        processed_text = re.sub(r'(\w)--(\w)', r'\1\2', protected_text)
        # Remove broken double dash across a newline (if any).
        processed_text = re.sub(r'(\w+)-\n-(\w+)', r'\1\2', processed_text)
        
        # Restore the protected URLs.
        for placeholder, url in placeholders.items():
            processed_text = processed_text.replace(placeholder, url)
        
        # Update the run text.
        run.text = processed_text


import re

def replace_hyphen_with_en_dash(text):
    """
    Replace all hyphens '-' with en dashes '–' in the text.
    
    Args:
        text: The input string.
        
    Returns:
        A new string with all hyphens replaced by en dashes.
    """
    return text.replace("-", "–")

def remove_gap_for_numbers(text):
    """
    Remove spaces around en dashes for numeric ranges.
    E.g., transforms "3 – 4" into "3–4".
    
    Args:
        text: The input string.
        
    Returns:
        A new string with number ranges formatted with no surrounding spaces.
    """
    number_range_pattern = re.compile(r'(\d+)\s*–\s*(\d+)')
    return number_range_pattern.sub(r'\1–\2', text)

def add_space_for_words(text):
    """
    Add a single space on each side of an en dash for word ranges.
    E.g., transforms "new–world" into "new – world".
    
    Args:
        text: The input string.
        
    Returns:
        A new string with word ranges having proper spacing.
    """
    word_range_pattern = re.compile(r'(\b\w+)\s*–\s*(\w+\b)')
    return word_range_pattern.sub(r'\1 – \2', text)

# Example of integrating these functions into the overall processing:
def format_runs(runs, line_number):
    """
    Process each run in 'runs' by applying the three transformations.
    
    Logs changes to the global 'global_logs' list.
    
    Args:
        runs: A list of objects having a 'text' attribute.
        line_number: The line number of the paragraph being processed.
    """
    global global_logs
    for run in runs:
        original_text = run.text
        # Apply the transformations in sequence:
        updated_text = replace_hyphen_with_en_dash(original_text)
        updated_text = remove_gap_for_numbers(updated_text)
        updated_text = add_space_for_words(updated_text)
        
        if updated_text != original_text:
            global_logs.append(
                f"Line {line_number}: '{original_text}' -> '{updated_text}'"
            )
        
        run.text = updated_text


# def format_year_range(runs):
#     pattern = re.compile(r'\b(\d{4})\s*–?\s*to\s*(\d{4})\b')
    
#     for run in runs:
#         if pattern.search(run.text):
#             run.text = pattern.sub(r'\1–\2', run.text)


def format_year_range(runs):
    pattern = re.compile(r'\b(\d+)\s*–?\s*to\s*(\d+)\b')
    for run in runs:
        if pattern.search(run.text):
            run.text = pattern.sub(r'\1–\2', run.text)


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
    


def process_doc_function3(payload: dict, doc: Document, doc_id, user):
    """
    This function processes the document by converting century notations
    and highlighting specific words.
    """
    line_number = 1
    for para in doc.paragraphs:
        format_year_range(para.runs)
        format_runs(para.runs, line_number)
        # remove_double_dash(para.runs)
        # format_hyphen_to_en_dash(para.runs, line_number)
        replace_dashes(para.runs, line_number)
        
    write_to_log(doc_id, user)

