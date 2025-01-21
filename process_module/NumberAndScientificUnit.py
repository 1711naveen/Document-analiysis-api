import re
from docx import Document
from num2words import num2words
from word2number import w2n
import os


global_logs = []

def remove_unnecessary_apostrophes(word, line_num):
    original_word = word
    global global_logs
    word = re.sub(r"(\d{4})'s\b", r"\1s", word)
    word = re.sub(r"'(\d{2})s\b", r"\1s", word)
    word = re.sub(r"(\d{4}s)'\b", r"\1", word)
    word = re.sub(r"(\d+)'(s|st|nd|rd|th)\b", r"\1\2", word)
    word = re.sub(r"^(\d{2})s\b", r"19\1s", word)
    if word != original_word:
        global_logs.append(f"[apostrophes change] Line {line_num}: {original_word} -> {word}")
    
    return word


# twofold not two-fold hyphenate with numeral for numbers greater than nine, e.g. 10-fold. 
def replace_fold_phrases(text):
    """
    Replaces phrases with '-fold' to ensure correct formatting based on the number preceding it.
    Args:
        text (str): Input text to process.
    Returns:
        str: Updated text.
    """
    global global_logs
    def process_fold(match):
        original = match.group(0)
        num_str = match.group(1)
        separator = match.group(2)
        
        if separator != "-":
            return original

        try:
            if num_str.isdigit():
                number = int(num_str)
            else:
                number = w2n.word_to_num(num_str)

            if number > 9:
                modified = f"{number}-fold"
            else:
                modified = f"{num2words(number)}fold"

            if original != modified:
                line_number = text[:match.start()].count('\n') + 1
                global_logs.append(
                    f"[replace_fold_phrases] Line {line_number}: '{original}' -> '{modified}'"
                )
            return modified
        except ValueError:
            return original

    pattern = r"(\b\w+\b)(-?)fold"
    updated_text = re.sub(pattern, process_fold, text)
    return updated_text





# [remove_space_between_degree_and_direction] Line 10: '52 °N' -> '52°N'
def remove_space_between_degree_and_direction(text, line_number):
    global global_logs
    pattern = r"(\d+) \s*[º°]\s*(N|S|E|W)\b"
    def log_replacement(match):
        original_text = match.group(0)
        updated_text = match.group(1) + "º" + match.group(2)
        global_logs.append(
            f"[remove_space_between_degree_and_direction] Line {line_number}: '{original_text}' -> '{updated_text}'"
        )
        return updated_text
    updated_text = re.sub(pattern, log_replacement, text)
    return updated_text



# km not Km; kg not Kg; l not L. (2.9)
def enforce_lowercase_units(text, line_number):
    global global_logs
    unit_patterns = [
        (r"(\d+)\s*(K)(m|g|l)", 'K', 'k'),
        (r"(\d+)\s*(G)(m)", 'G', 'g'),
        (r"(\d+)\s*(M)(g)", 'M', 'm'),
        (r"(\d+)\s*(T)(g)", 'T', 't'),
        (r"(\d+)\s*(L)\b", 'L', 'l'),
        (r"(\d+)\s*(M)\b", 'M', 'm'),
        (r"(\d+)\s*(kg|mg|g|cm|m|km|l|s|h|min)", r"\1 \2", None)
    ]
    updated_text = text
    for pattern, original, updated in unit_patterns:
        matches = re.finditer(pattern, updated_text)
        for match in matches:
            original_text = match.group(0)
            if updated is not None:
                updated_text = updated_text.replace(original_text, original_text.replace(original, updated))
                global_logs.append(
                    f"[enforce_lowercase_units] Line {line_number}: '{original_text}' -> '{original_text.replace(original, updated)}'"
                )
            else:
                updated_text = updated_text.replace(original_text, f"{match.group(1)} {match.group(2)}")
                global_logs.append(
                    f"[enforce_lowercase_units] Line {line_number}: '{original_text}' -> '{match.group(1)} {match.group(2)}'"
                )
    return updated_text



# Done
# [precede_decimal_with_zero] Line 22: '.76' -> '0.76'
def precede_decimal_with_zero(text, line_number):
    global global_logs
    pattern = r"(?<!\d)(?<!\d\.)\.(\d+)"
    def log_replacement(match):
        original_text = match.group(0)
        updated_text = "0." + match.group(1)
        global_logs.append(
            f"[precede_decimal_with_zero] Line {line_number}: '{original_text}' -> '{updated_text}'"
        )
        return updated_text
    updated_text = re.sub(pattern, log_replacement, text)
    return updated_text



def adjust_ratios(text):
    """
    Ensures proper formatting of ratios with spaces around the colon (e.g., "1:2" -> "1 : 2").
    Args:
        text (str): Input text to process.
    Returns:
        str: Updated text.
    """
    global global_logs
    def process_ratio(match):
        original = match.group(0)
        modified = f"{match.group(1)} : {match.group(2)}"
        if original != modified:
            line_number = text[:match.start()].count('\n') + 1
            global_logs.append(
                f"[adjust_ratios] Line {line_number}: '{original}' -> '{modified}'"
            )
        return modified
    return re.sub(r"(\d)\s*:\s*(\d)", process_ratio, text)



def remove_commas_from_numbers(text, line_number):
    """
    Removes commas from numerical values in the text.
    Updates the global_log with the specific changes, including line number and changes made.
    """
    original_text = text
    changes = []
    global global_logs
    pattern = r'\b\d{1,3}(,\d{3})+\b'
    def replacer(match):
        original_number = match.group(0)
        updated_number = original_number.replace(",", " ")
        changes.append((original_number, updated_number))  # Log the change
        return updated_number

    # Replace numbers with commas in the text
    text = re.sub(pattern, replacer, text)

    # Log individual changes
    for original, updated in changes:
        global_logs.append(
            f"[process_symbols_in_doc] Line {line_number}: '{original}' -> '{updated}'"
        )

    return text



def remove_spaces_from_four_digit_numbers(text, line_number):
    """
    Removes spaces from four-digit numerals in the text.
    Updates the global_log with specific changes, including line number and changes made.
    """
    original_text = text
    changes = []
    global global_logs

    pattern = r'\b\d\s\d{3}\b'

    def replacer(match):
        original_number = match.group(0)  # Match the original number
        updated_number = original_number.replace(" ", "")  # Remove spaces
        changes.append((original_number, updated_number))  # Log the change
        return updated_number

    text = re.sub(pattern, replacer, text)

    for original, updated in changes:
        global_logs.append(
            f"[process_symbols_in_doc] Line {line_number}: '{original}' -> '{updated}'"
        )

    return text




def convert_decimal_to_baseline(paragraph_text, line_number):
    """
    Converts any non-standard decimal separator (•) to a standard decimal point (.)
    only when both sides are numeric.
    Logs the changes to the global_log, including line number and the change.
    """
    changes = []
    global global_logs
    # Regular expression to find '•' between numbers
    pattern = r'(?<=\d)\xB7(?=\d)'

    # Find all occurrences of '•' that are between digits and replace with '.'
    matches = re.findall(pattern, paragraph_text)
    if matches:
        original_text = paragraph_text
        updated_text = re.sub(pattern, '.', paragraph_text)  # Replace '•' with '.'
        changes.append((original_text, updated_text))

    for original, updated in changes:
        global_logs.append(
            f"[convert_decimal_to_baseline] Line {line_number}: '{original}' -> '{updated}'"
        )
    return updated_text if changes else paragraph_text



def correct_scientific_unit_symbols(text):
    """
    Ensures proper capitalization of units derived from proper names (e.g., J, Hz, W, N) only when preceded by a number.
    Args:
        text (str): Input text to process.
    Returns:
        str: Updated text.
    """
    global global_logs
    units = {
        "j": "J",
        "hz": "Hz",
        "w": "W",
        "n": "N",
        "pa": "Pa",
        "v": "V",
        "a": "A",
        "c": "C",
        "lm": "lm",
        "lx": "lx",
        "t": "T",
        "ohm": "Ω",
        "s": "S",
        "k": "K",
        "cd": "cd",
        "mol": "mol",
        "rad": "rad",
        "sr": "sr"
    }

    def process_unit(match):
        original = match.group(0)
        unit = match.group(2).lower()  # Capture the unit (second group)
        modified = f"{match.group(1)}{units.get(unit, match.group(2))}"  # Replace with capitalized unit if in dictionary
        if original != modified:
            line_number = text[:match.start()].count('\n') + 1  # Calculate the line number
            global_logs.append(
                f"[correct_scientific_unit_symbols] Line {line_number}: '{original}' -> '{modified}'"
            )
        return modified
    pattern = r"\b(\d+\s*)(%s)\b" % "|".join(re.escape(unit) for unit in units.keys())
    updated_text = re.sub(pattern, process_unit, text, flags=re.IGNORECASE)
    return updated_text


# Done
# [format_dates] Line 5: '386 BCE' -> '386 bce'
def format_dates(text, line_number):
    global global_logs

    def log_and_replace(pattern, replacement, text):
        def replacer(match):
            original = match.group(0)
            updated = replacement(match)
            if original != updated:
                global_logs.append(
                    f"[format_dates] Line {line_number}: '{original}' -> '{updated}'"
                )
            return updated
        return re.sub(pattern, replacer, text)
    text = log_and_replace(
        r"\b(\d+)\s?(BCE|CE)\b",
        lambda m: f"{m.group(1)} {m.group(2).lower()}",
        text
    )
    text = log_and_replace(
        r"\b(AD|BC)\.\b",
        lambda m: f"{m.group(1)} ",
        text
    )
    text = log_and_replace(
        r"(\d+)\s?(BCE|CE|AD|BC)\b",
        lambda m: f"{m.group(1)} {m.group(2)}",
        text
    )
    return text


def format_ellipses_in_series(text):
    # Matches series like "x1, x2, ..., xn" and ensures the ellipsis has a comma and space after it.
    text = re.sub(r"(\w+),\s*(\w+),\s*\.\.\.\s*(\w+)", r"\1, \2, …, \3", text)
    return text




def correct_units_in_ranges_with_logging(text):
    global global_logs
    unit_symbols = ['cm', 'm', 'kg', 's', 'A', 'K', 'mol', 'cd', '%']
    
    # Regex patterns
    range_pattern = rf"\b(\d+)\s*({'|'.join(re.escape(unit) for unit in unit_symbols)})\s*(to|-|–|—)\s*(\d+)\s*\2\b"
    thin_space_pattern = rf"\b(\d+)\s+({'|'.join(re.escape(unit) for unit in unit_symbols)})\b"

    lines = text.splitlines()
    updated_lines = []
    for line_number, line in enumerate(lines, start=1):
        original_line = line
        new_line = re.sub(
            range_pattern,
            lambda m: f"{m.group(1)} {m.group(3)} {m.group(4)} {m.group(2)}",
            line
        )
        new_line = re.sub(
            thin_space_pattern,
            lambda m: f"{m.group(1)} {m.group(2)}" if m.group(2) != "%" else f"{m.group(1)}{m.group(2)}",
            new_line
        )
        if new_line != line:
            change_details = f"{line.strip()} -> {new_line.strip()}"
            global_logs.append(f"Line {line_number}: {change_details}")
            line = new_line

        updated_lines.append(line)
    return "\n".join(updated_lines)



def use_numerals_with_percent(text):
    global global_logs

    lines = text.splitlines()
    modified_text = []

    for line_number, line in enumerate(lines, 1):
        original_line = line
        modified_line = line
        def replace_spelled_out_percent(match):
            word = match.group(1)
            try:
                num = w2n.word_to_num(word.lower())
                modified = f"{num}%"
                global_logs.append(
                    f"[numerals with percent] Line {line_number}: '{word} percent' -> '{modified}'"
                )
                return modified
            except ValueError:
                return match.group(0)

        modified_line = re.sub(
            r"\b([a-zA-Z\s\-]+)\s?(percent|per cent|percentage)\b",
            replace_spelled_out_percent,
            modified_line,
            flags=re.IGNORECASE,
        )

        def replace_numerical_percent(match):
            number = match.group(1)
            modified = f"{number}%"
            global_logs.append(
                f"[numerals with percent] Line {line_number}: '{match.group(0)}' -> '{modified}'"
            )
            return modified

        modified_line = re.sub(
            r"(\d+)\s?(percent|per cent|percentage)\b", replace_numerical_percent, modified_line, flags=re.IGNORECASE
        )

        modified_text.append(modified_line)

    return "\n".join(modified_text)



# def write_to_log(doc_id):
#     global global_logs
#     output_dir = os.path.join('output', str(doc_id))
#     os.makedirs(output_dir, exist_ok=True)
#     log_file_path = os.path.join(output_dir, 'global_logs.txt')

#     with open(log_file_path, 'w', encoding='utf-8') as log_file:
#         log_file.write("\n".join(global_logs))

#     global_logs = []


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



def process_doc_function2(payload: dict, doc: Document, doc_id):
    line_number = 1
    for para in doc.paragraphs:
        para.text = remove_unnecessary_apostrophes(para.text, line_number)
        para.text = replace_fold_phrases(para.text)
        para.text = use_numerals_with_percent(para.text)
        para.text = remove_space_between_degree_and_direction(para.text,line_number)
        para.text = enforce_lowercase_units(para.text,line_number)
        para.text = adjust_ratios(para.text)
        para.text = remove_commas_from_numbers(para.text,line_number)
        para.text = remove_spaces_from_four_digit_numbers(para.text,line_number)
        para.text = convert_decimal_to_baseline(para.text,line_number)
        para.text = correct_scientific_unit_symbols(para.text)
        para.text = format_dates(para.text, line_number)
        para.text = format_ellipses_in_series(para.text)
        para.text = correct_units_in_ranges_with_logging(para.text,line_number)
        line_number += 1
        
    write_to_log(doc_id)