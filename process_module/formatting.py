import re
from docx import Document
import os
from urllib.parse import urlparse


# Global logs to keep track of changes
global_logs = []


def clean_web_addresses(text):
    """
    Removes angle brackets around web addresses (e.g., "<http://example.com>" -> "http://example.com").
    Args:
        text (str): Input text to process.
    Returns:
        str: Updated text.
    """
    global global_logs
    def process_web_address(match):
        original = match.group(0)
        modified = match.group(1)

        if original != modified:
            line_number = text[:match.start()].count('\n') + 1
            global_logs.append(
                f"[clean_web_addresses] Line {line_number}: '{original}' -> '{modified}'"
            )
        return modified
    return re.sub(r"<(https?://[^\s<>]+)>", process_web_address, text)


    
    
def remove_concluding_slashes_from_urls(text, line_number):
    global global_logs
    pattern = r"(https?://[^\s/]+(?:/[^\s/]+)*)/"
    matches = re.finditer(pattern, text)
    updated_text = text
    
    for match in matches:
        original_text = match.group(0)
        updated_text_url = match.group(1)  # URL without the concluding slash (e.g., "https://example.com")
        updated_text = updated_text.replace(original_text, updated_text_url)
        
        # Log the change
        global_logs.append(
            f"[remove_concluding_slashes_from_urls] Line {line_number}: '{original_text}' -> '{updated_text_url}'"
        )    
    return updated_text



def process_url_add_http(text):
    """
    Adjusts URLs in the input text based on the given rules:
    1. If a URL starts with 'www.' but doesn't have 'http://', prepend 'http://'.
    2. If a URL already starts with 'http://', remove 'http://'.
    Args:
        text (str): The input text containing URLs.
    Returns:
        str: The modified text with URLs adjusted.
    """
    global global_logs
    def add_http_prefix(match):
        original = match.group(0)
        modified = f"http://{match.group(1)}"
        if original != modified:
            line_number = text[:match.start()].count('\n') + 1
            global_logs.append(
                f"[process_url_add_http] Line {line_number}: '{original}' -> '{modified}'"
            )
        return modified
    def remove_http_prefix(match):
        original = match.group(0)
        modified = match.group(1)
        if original != modified:
            line_number = text[:match.start()].count('\n') + 1
            global_logs.append(
                f"[process_url_add_http] Line {line_number}: '{original}' -> '{modified}'"
            )
        return modified
    text = re.sub(r"\bhttp://(www\.\S+)", remove_http_prefix, text)
    text = re.sub(r"\b(www\.\S+)", add_http_prefix, text)
    return text


def process_url_remove_http(url):
    """
    Removes 'http://' from a URL if there is no path, parameters, query, or fragment.
    Args:
        url (str): The input URL to process.
    Returns:
        str: The modified URL with 'http://' removed if applicable.
    """
    global global_logs
    parsed = urlparse(url)
    original = url
    if parsed.scheme == "http" and not (parsed.path or parsed.params or parsed.query or parsed.fragment):
        modified = parsed.netloc
        if original != modified:
            line_number = 1
            global_logs.append(
                f"[process_url_remove_http] Line {line_number}: '{original}' -> '{modified}'"
            )
        return modified
    return url



import re

def remove_url_underlining(text, line_number):
    """
    Ensures that web addresses/URLs in the text are not underlined.
    Logs any changes made to the `global_logs`.
    Args:
        text (str): The text content of a paragraph.
        line_number (int): The line number of the paragraph in the document.
    Returns:
        str: The text with URLs processed (underlining removed).
    """
    global global_logs
    url_pattern = r'(https?://[^\s]+)'
    words = text.split()
    modified_words = []
    for word in words:
        if re.match(url_pattern, word):
            modified_words.append(word)  # Keep the URL unchanged
            global_logs.append(
                f"[remove_url_underlining] Line {line_number}: Removed underlining from URL '{word}'"
            )
        else:
            modified_words.append(word)
    return " ".join(modified_words)



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
    


def process_doc_function4(payload: dict, doc: Document, doc_id):
    """
    This function processes the document by converting century notations
    and highlighting specific words.
    """
    line_number = 1
    for para in doc.paragraphs:
        para.text = remove_url_underlining(para.text, line_number)
        para.text = clean_web_addresses(para.text)
        para.text = remove_concluding_slashes_from_urls(para.text, line_number)
        para.text = process_url_add_http(para.text)
        para.text = process_url_remove_http(para.text)
       
    write_to_log(doc_id)
