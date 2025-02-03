import re
from docx import Document
import os
from urllib.parse import urlparse


# Global logs to keep track of changes
global_logs = []


import re

global_logs = []



def clean_web_addresses(runs):
    """
    Removes angle brackets around web addresses (e.g., "<http://example.com>" -> "http://example.com").
    Args:
        runs (list): A list of runs (segments of text in the document).
    """
    def process_web_address(match, text):
        original = match.group(0)
        modified = match.group(1)

        if original != modified:
            line_number = text[:match.start()].count('\n') + 1
            global_logs.append(
                f"[clean_web_addresses] Line {line_number}: '{original}' -> '{modified}'"
            )
        return modified

    for run in runs:
        # Apply cleaning to each run's text in place
        run.text = re.sub(r"<(https?://[^\s<>]+)>", lambda match: process_web_address(match, run.text), run.text)



def remove_concluding_slashes_from_urls(runs, line_number):
    """
    Removes the concluding slash from URLs in the runs (e.g., "https://example.com/" -> "https://example.com").
    Args:
        runs (list): A list of runs (segments of text in the document).
        line_number (int): Line number where the change occurs.
    """
    pattern = r"(https?://[^\s/]+(?:/[^\s/]+)*)/"
    
    for run in runs:
        matches = re.finditer(pattern, run.text)
        updated_text = run.text
        
        for match in matches:
            original_text = match.group(0)
            updated_text_url = match.group(1)  # URL without the concluding slash (e.g., "https://example.com")
            updated_text = updated_text.replace(original_text, updated_text_url)
            
            # Log the change
            global_logs.append(
                f"[remove_concluding_slashes_from_urls] Line {line_number}: '{original_text}' -> '{updated_text_url}'"
            )
        # Update the run's text in place
        run.text = updated_text



def process_url_add_http(runs):
    """
    Adjusts URLs in the input text based on the given rules:
    1. If a URL starts with 'www.' but doesn't have 'http://', prepend 'http://'.
    2. If a URL already starts with 'http://', remove 'http://'.
    Args:
        runs (list): A list of runs (segments of text in the document).
    """
    def add_http_prefix(match, text):
        original = match.group(0)
        modified = f"http://{match.group(1)}"
        if original != modified:
            line_number = text[:match.start()].count('\n') + 1
            global_logs.append(
                f"[process_url_add_http] Line {line_number}: '{original}' -> '{modified}'"
            )
        return modified

    def remove_http_prefix(match, text):
        original = match.group(0)
        modified = match.group(1)
        if original != modified:
            line_number = text[:match.start()].count('\n') + 1
            global_logs.append(
                f"[process_url_add_http] Line {line_number}: '{original}' -> '{modified}'"
            )
        return modified

    for run in runs:
        # Apply the changes in place to each run's text
        run.text = re.sub(r"\bhttp://(www\.\S+)", lambda match: remove_http_prefix(match, run.text), run.text)
        run.text = re.sub(r"\b(www\.\S+)", lambda match: add_http_prefix(match, run.text), run.text)



def process_url_remove_http(runs):
    """
    Removes 'http://' from a URL if there is no path, parameters, query, or fragment.
    Args:
        runs (list): A list of runs (segments of text in the document).
    """
    def process_url(match, text):
        original = match.group(0)
        parsed = urlparse(original)
        
        # Remove 'http://' if there is no path, parameters, query, or fragment
        if parsed.scheme == "http" and not (parsed.path or parsed.params or parsed.query or parsed.fragment):
            modified = parsed.netloc
            if original != modified:
                line_number = text[:match.start()].count('\n') + 1
                global_logs.append(
                    f"[process_url_remove_http] Line {line_number}: '{original}' -> '{modified}'"
                )
            return modified
        return original

    for run in runs:
        # Apply the changes in place to each run's text
        run.text = re.sub(r"\bhttp://[^\s]+", lambda match: process_url(match, run.text), run.text)



def remove_url_underlining(runs, line_number):
    """
    Ensures that web addresses/URLs in the text are not underlined.
    Logs any changes made to the `global_logs`.
    Args:
        runs (list): A list of runs (segments of text in the document).
        line_number (int): The line number of the paragraph in the document.
    """
    url_pattern = r'(https?://[^\s]+)'

    for run in runs:
        # Split the run's text into words and process each word
        words = run.text.split()
        modified_words = []
        
        for word in words:
            if re.match(url_pattern, word):
                modified_words.append(word)  # Keep the URL unchanged
                global_logs.append(
                    f"[remove_url_underlining] Line {line_number}: Removed underlining from URL '{word}'"
                )
            else:
                modified_words.append(word)
        
        # Update the run's text in place
        run.text = " ".join(modified_words)




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
        # para.text = remove_url_underlining(para.text, line_number)
        # para.text = clean_web_addresses(para.text)
        # para.text = remove_concluding_slashes_from_urls(para.text, line_number)
        # para.text = process_url_add_http(para.text)
        # para.text = process_url_remove_http(para.text)
        clean_web_addresses(para.runs)
        remove_concluding_slashes_from_urls(para.runs, line_number)
        process_url_add_http(para.runs)
        process_url_remove_http(para.runs)
        remove_url_underlining(para.runs, line_number)

       
    write_to_log(doc_id)
