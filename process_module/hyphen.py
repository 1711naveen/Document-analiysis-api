import re
from docx import Document
import os


global_logs = []


# def replace_dashes(text, line_number):
#     """
#     Replaces em dashes (—) and normal hyphens (-) with en dashes (–) in the given text.
#     Logs changes to a global list with details of the modification in the desired format.
#     Args:
#         text: The text content of a paragraph.
#         line_number: The line number of the paragraph for context.
#     Returns:
#         str: The modified text with dashes replaced.
#     """
#     global global_logs
#     original_text = text
#     modified_text = text.replace('—', '–').replace('-', '–')
#     # If changes are made, log the change
#     if original_text != modified_text:
#         global_logs.append(
#             f"[replace_dashes_with_logging] Line {line_number}: '{original_text}' -> '{modified_text}'"
#         )
#     return modified_text



def replace_dashes(text, line_number):
    """
    Replaces em dashes (—) and normal hyphens (-) with en dashes (–) in the given text.
    Logs changes to a global list with details of the modification in the desired format.
    Args:
        text: The text content of a paragraph.
        line_number: The line number of the paragraph for context.
    Returns:
        str: The modified text with dashes replaced.
    """
    global global_logs
    original_text = text
    modified_text = text.replace('—', '–').replace('-', '–')

    # If changes are made, log the specific characters that changed
    if original_text != modified_text:
        for orig, new in zip(original_text, modified_text):
            if orig != new:
                global_logs.append(
                    f"[replace_dashes_with_logging] Line {line_number}: '{orig}' -> '{new}'"
                )

    return modified_text




def format_hyphen_to_en_dash(text, line_number):
    """
    Replace hyphens with en dashes in the given text.
    Adjust spacing based on surrounding context:
    - Add spaces if there are words on both sides.
    - Remove spaces if there are numbers on both sides.
    Logs changes to the global 'global_logs' list.
    Args:
        text: The text content of a paragraph.
        line_number: The line number of the paragraph being processed.
    Returns:
        str: The modified text with hyphens formatted as en dashes.
    """
    global global_logs
    word_range_pattern = re.compile(r'(\b\w+)\s*-\s*(\w+\b)')
    number_range_pattern = re.compile(r'(\d+)\s*-\s*(\d+)')
    original_text = text
    # Replace hyphen with en dash and remove spaces for number ranges
    updated_text = number_range_pattern.sub(r'\1–\2', original_text)
    # Replace hyphen with en dash and ensure spaces for word ranges
    updated_text = word_range_pattern.sub(r'\1 – \2', updated_text)
    if updated_text != original_text:
        # Log the change
        global_logs.append(
            f"Line {line_number}: '{original_text}' -> '{updated_text}'"
        )
    return updated_text

                

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
        para.text = replace_dashes(para.text, line_number)
        para.text = format_hyphen_to_en_dash(para.text, line_number)
        
    write_to_log(doc_id)

