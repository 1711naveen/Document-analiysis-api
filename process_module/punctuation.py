import re
from docx import Document
import os
from db_config import get_db_connection
from datetime import datetime


# Global logs to keep track of changes
global_logs = []

# A map of numbers to century strings
century_map = {
    1: "first",
    2: "second",
    3: "third",
    4: "fourth",
    5: "fifth",
    6: "sixth",
    7: "seventh",
    8: "eighth",
    9: "ninth",
    10: "tenth",
    11: "eleventh",
    12: "twelfth",
    13: "thirteenth",
    14: "fourteenth",
    15: "fifteenth",
    16: "sixteenth",
    17: "seventeenth",
    18: "eighteenth",
    19: "nineteenth",
    20: "twentieth",
    21: "twenty-first",
    22: "twenty-second",
    23: "twenty-third",
    24: "twenty-fourth",
    25: "twenty-fifth",
}


def fetch_abbreviation_mappings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT original_word, abbreviated_form FROM abbreviation_mapping")
    mappings = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in mappings}

# change long form to shor form abbrevaited form
def apply_abbreviation_mapping(runs, abbreviation_dict, line_number):
    global global_logs
    for run in runs:
        words = run.text.split()  # Split the run's text into words
        updated_words = []
        
        for word in words:
            updated_word = abbreviation_dict.get(word, word)
            if word != updated_word:
                global_logs.append(f"[apply_abbreviation_mapping] Line {line_number}: '{word}' -> '{updated_word}'")
            updated_words.append(updated_word)
        
        # Join the updated words and reassign it to the run's text
        run.text = ' '.join(updated_words)



# Converts century notation like '21st' to 'the twenty-first century'
def convert_century_in_runs(runs, line_number_offset):
    """
    Converts century notation like '21st' to 'the twenty-first century'
    and logs the changes with line numbers.

    :param runs: List of Run objects in the paragraph.
    :param line_number_offset: The starting line number for this paragraph.
    :return: None (modifies runs in place).
    """
    global global_logs  # Global log to record changes

    for run in runs:
        words = run.text.split()  # Split the run's text into words
        updated_words = []

        for word in words:
            match = re.match(r"(\d+)(st|nd|rd|th)$", word)  # Match century notation
            if match:
                num = int(match.group(1))
                if num in century_map:
                    # Original and converted word
                    original_word = match.group(0)
                    converted_word = f"the {century_map[num]} century"
                    
                    # Log the change with the actual line number
                    global_logs.append(
                        f"[convert century] Line {line_number_offset}: {original_word} -> {converted_word}"
                    )
                    
                    # Replace the word in the run
                    word = converted_word
            
            updated_words.append(word)
        
        # Rebuild the run's text with updated words
        run.text = ' '.join(updated_words)


# change italics of latin word to roman
def set_latinisms_to_roman_in_runs(runs, line_number, latinisms=None):
    """
    Converts specific Latinisms from italic to roman text in a paragraph.
    Logs changes to the global_log, including line number and original italicized Latinism.

    :param runs: List of Run objects in the paragraph.
    :param line_number: The line number for logging purposes.
    :param latinisms: List of Latinisms to convert (defaults to common Latinisms).
    :return: None (modifies runs in place).
    """
    if latinisms is None:
        latinisms = [
            "i.e.", "e.g.", "via", "vice versa", "etc.", "a posteriori", 
            "a priori", "et al.", "cf.", "c."
        ]
    global global_logs

    for run in runs:
        for lat in latinisms:
            if lat in run.text:
                # Log the change
                global_logs.append(
                    f"[set_latinisms_to_roman] Line {line_number}: '{lat}' -> '{lat}'"
                )
                
                # Remove italic formatting for the Latinism
                run.text = run.text.replace(lat, lat)
                run.font.italic = False  # Set the font to non-italic


# make symbols for copyright only once
def process_symbols_mark_in_runs(runs, line_number, symbols=["®", "™", "©", "℗", "℠"]):
    """
    Ensures symbols like ®, ™, etc., appear only the first time in the text.
    Updates the global_log with changes, including line number, original text, and updated text.

    :param runs: List of Run objects in the paragraph.
    :param line_number: The line number for logging purposes.
    :param symbols: List of symbols to process (defaults to ["®", "™", "©", "℗", "℠"]).
    :return: None (modifies runs in place).
    """
    global global_logs
    symbol_set = set()

    # Track the first occurrence of each symbol in the paragraph
    first_occurrence_indices = {symbol: None for symbol in symbols}

    # First pass: Find the first occurrence of each symbol
    for run in runs:
        for symbol in symbols:
            if symbol in run.text and first_occurrence_indices[symbol] is None:
                first_occurrence_indices[symbol] = (run, run.text.index(symbol))

    # Second pass: Remove all occurrences after the first one
    for run in runs:
        for symbol in symbols:
            if symbol in run.text:
                first_run, first_index = first_occurrence_indices[symbol]
                if (run, run.text.index(symbol)) != (first_run, first_index):
                    # Remove the symbol from this run
                    run.text = run.text.replace(symbol, "")
                    symbol_set.add(symbol)

    # Log changes if any symbols were removed
    if symbol_set:
        global_logs.append(
            f"[process_symbols_in_doc] Line {line_number}: Removed duplicate symbols {symbol_set}"
        )


# change italics of see to roman
def apply_remove_italics_see_rule_in_runs(runs):
    """
    Replaces '*see*' with 'see' in the text, removing italics for the word 'see'.
    Modifies the runs in place.

    :param runs: List of Run objects in the paragraph.
    :return: None (modifies runs in place).
    """
    for run in runs:
        if '*see*' in run.text:
            # Replace '*see*' with 'see' and remove italics for this run
            run.text = run.text.replace('*see*', 'see')
            run.font.italic = False  # Ensure 'see' is not italicized


# change number to no. if followed by number
def set_number_to_no_in_runs(runs, line_number):
    """
    Replaces 'Number X' or 'number X' with 'No. X' or 'no. X' and logs changes.
    Modifies the runs in place.

    :param runs: List of Run objects in the paragraph.
    :param line_number: Line number for logging.
    :return: None (modifies runs in place).
    """
    global global_logs

    def replace_number(match):
        word = match.group(1)
        num = match.group(2)
        updated_text = f"No. {num}" if word.istitle() else f"no. {num}"
        global_logs.append(f"[set_number_to_no] Line {line_number}: '{match.group(0)}' -> '{updated_text}'")
        return updated_text

    pattern = r'\b(Number|number)\s(\d+)\b'

    for run in runs:
        if re.search(pattern, run.text):
            # Replace 'Number X' or 'number X' with 'No. X' or 'no. X'
            run.text = re.sub(pattern, replace_number, run.text)



# change long titile before name to short form
def format_titles_us_english_with_logging_in_runs(runs, line_number):
    """
    Replaces long titles (e.g., 'Doctor', 'Mister') with their short forms (e.g., 'Dr.', 'Mr.').
    Logs changes to the global_log.
    :param runs: List of Run objects in the paragraph.
    :return: None (modifies runs in place).
    """
    global global_logs
    titles = {
        "doctor": "Dr.",
        "mister": "Mr.",
        "misses": "Mrs.",
        "miss": "Miss.",
        "ms": "Ms.",
        "professor": "Professor",
        "sir": "Sir",
        "madam": "Madam",
        "saint": "St",
        "Doctor": "Dr.",
        "Mister": "Mr.",
        "Misses": "Mrs.",
        "Miss": "Miss.",
        "Ms": "Ms.",
        "Professor": "Professor",
        "Sir": "Sir",
        "Madam": "Madam",
        "Saint": "St",
    }

    for run in runs:
        for title, replacement in titles.items():
            if title in run.text:
                # Replace the title with its short form
                run.text = re.sub(rf"\b{title}\b", replacement, run.text, flags=re.IGNORECASE)
                # Log the change
                global_logs.append(f"[shorten title] Line {line_number}: {title} -> {replacement}")



# a.m. not AM or am.
# p.m not PM or pm.
def enforce_am_pm_in_runs(runs, line_num):
    """
    Ensures consistent formatting for 'am' and 'pm' in the paragraph and logs changes.
    Modifies the runs in place.

    :param runs: List of Run objects in the paragraph.
    :param line_num: The line number in the document for logging.
    :return: None (modifies runs in place).
    """
    global global_logs  # Use a global log to record changes

    for run in runs:
        words = run.text.split()  # Split the run's text into words
        corrected_words = []

        for word in words:
            original_word = word
            word_lower = word.lower()
            if word_lower in {"am", "a.m", "pm", "p.m"}:
                if "a" in word_lower:
                    corrected_word = "a.m."
                elif "p" in word_lower:
                    corrected_word = "p.m."
                
                if corrected_word != original_word:
                    global_logs.append(
                        f"[am pm change] Line {line_num}: '{original_word}' -> '{corrected_word}'"
                    )
            else:
                corrected_word = word 
            corrected_words.append(corrected_word)
        
        # Rebuild the run's text with corrected words
        run.text = " ".join(corrected_words)


# apples, pears, and bananas
# apples, pears, or bananas
def enforce_serial_comma_in_runs(runs):
    """
    Ensures the use of the serial comma (Oxford comma) in lists.
    Modifies the runs in place.

    :param runs: List of Run objects in the paragraph.
    :return: None (modifies runs in place).
    """
    for run in runs:
        # Add a comma before "and" or "or" in lists
        run.text = re.sub(
            r'([^,]+), ([^,]+) (or) ([^,]+)',
            r'\1, \2, \3 \4',
            run.text
        )
        # Explicitly handle cases where "and" does not get the serial comma
        run.text = re.sub(
            r'([^,]+), ([^,]+) (and) ([^,]+)',
            r'\1, \2, \3 \4',
            run.text
        )




# Replace all occurrences of the § symbol with 'Section'
def rename_section_in_runs(runs):
    """
    Replaces all occurrences of the § symbol with 'Section'.
    Modifies the runs in place.

    :param runs: List of Run objects in the paragraph.
    :return: None (modifies runs in place).
    """
    for run in runs:
        run.text = re.sub(r'§', 'Section', run.text)


# There is one problem here for project, & document it is not changing and for project & document it is changing
# chnage and to & if in between two word starting with capitals
def replace_ampersand_in_runs(runs, line_number):
    """
    Replaces '&' with 'and' unless both sides are uppercase (e.g., 'R&D').
    Modifies the runs in place and logs changes.

    :param runs: List of Run objects in the paragraph.
    :return: None (modifies runs in place).
    """
    global global_logs

    def replacement(match):
        left, right = match.group(1), match.group(2)
        original = match.group(0)
        if left[0].isupper() and right[0].isupper():
            return original  # Preserve '&' if both sides are uppercase (e.g., 'R&D')
        modified = left + ' and ' + right
        global_logs.append(
            f"[replace_ampersand] Line {line_number}: '{original}' -> '{modified}'"
        )
        return modified

    for run in runs:
        run.text = re.sub(r'(\w+)\s*&\s*(\w+)', replacement, run.text)



# changes word like James' to James's
def correct_possessive_names_in_runs(runs, line_number):
    """
    Corrects possessive names (e.g., "James'" to "James's").
    Modifies the runs in place and logs changes.

    :param runs: List of Run objects in the paragraph.
    :param line_number: The line number for logging.
    :return: None (modifies runs in place).
    """
    global global_logs

    for run in runs:
        # Correct singular possessive (e.g., "James'" to "James's")
        run.text = re.sub(r"\b([A-Za-z]+s)\b(?<!\bs')'", r"\1's", run.text)
        
        # Correct plural possessive (e.g., "students'" remains "students'")
        run.text = re.sub(r"\b([A-Za-z]+s)'\b", r"\1'", run.text)




# change the unis to short form only first time in full form in brackets
def units_with_bracket_in_runs(runs, replaced_units):
    """
    Replaces units with their full names and appends the abbreviated form in brackets.
    Modifies the runs in place.

    :param runs: List of Run objects in the paragraph.
    :param replaced_units: Set of units that have already been replaced.
    :return: None (modifies runs in place).
    """
    units = {
        "s": "seconds",
        "m": "meter",
        "kg": "kilogram",
        "A": "ampere",
        "K": "kelvin",
        "mol": "mole",
        "cd": "candela"
    }

    def replace(match):
        number = match.group(1)
        unit = match.group(2)
        
        if unit not in replaced_units:
            replaced_units.add(unit)
            full_unit = units.get(unit, unit)
            return f"{number} {full_unit} ({unit})"
        else:
            return f"{number} {unit}"

    pattern = r"(\d+)\s?([a-zA-Z]+)"

    for run in runs:
        run.text = re.sub(pattern, replace, run.text)


def remove_and(text: str):
    """
    Replaces 'and' between two capitalized words with an ampersand (&).
    Args:
        text (str): Input text to process.
    Returns:
        str: Updated text.
    """
    global global_logs
    pattern = r'([A-Z][a-z]+)\s+and\s+([A-Z][a-z]+)'
    def process_and_replacement(match):
        original = match.group(0)
        modified = f"{match.group(1)} & {match.group(2)}"
        if original != modified:
            line_number = text[:match.start()].count('\n') + 1
            global_logs.append(
                f"[remove_and] Line {line_number}: '{original}' -> '{modified}'"
            )
        return modified
    text = re.sub(pattern, process_and_replacement, text)
    return text


def remove_quotation(text: str):
    """
    Removes single quotation marks (') following capitalized words.
    Args:
        text (str): Input text to process.
    Returns:
        str: Updated text.
    """
    global global_logs
    pattern = r"([A-Z]+)'"
    def process_quotation_removal(match):
        original = match.group(0)
        modified = f"{match.group(1)}"

        if original != modified:
            line_number = text[:match.start()].count('\n') + 1
            global_logs.append(
                f"[remove_quotation] Line {line_number}: '{original}' -> '{modified}'"
            )
        return modified
    para_text = re.sub(pattern, process_quotation_removal, text)
    return para_text


def correct_acronyms(text, line_number):
    global global_logs
    original_text = text
    words = text.split()
    corrected_words = []
    for word in words:
        original_word = word
        if re.match(r"([a-z]\.){2,}[a-z]\.?", word):
            word = word.replace(".", "")
        elif re.match(r"([A-Z]\.){2,}[A-Z]\.?", word):
            word = word.replace(".", "")
        if word != original_word:
            global_logs.append(
                f"[correct_acronyms] Line {line_number}: '{original_word}' -> '{word}'"
            )
        corrected_words.append(word)
    corrected_text = " ".join(corrected_words)
    return corrected_text


# changes eg to e.g.
def enforce_eg_rule_with_logging(text):
    lines = text.splitlines()
    updated_lines = []
    for line_number, line in enumerate(lines, start=1):
        original_line = line

        # Step 1: Match "eg" or "e.g." with optional surrounding spaces and punctuation
        new_line = re.sub(r'\beg\b', 'e.g.', line, flags=re.IGNORECASE)
        new_line = re.sub(r'\beg,\b', 'e.g.', new_line, flags=re.IGNORECASE)  # Handle "eg,"

        # Step 2: Fix extra periods like `e.g..` or `e.g...,` and ensure proper punctuation
        new_line = re.sub(r'\.([.,])', r'\1', new_line)  # Removes an extra period before a comma or period
        new_line = re.sub(r'\.\.+', '.', new_line)  # Ensures only one period after e.g.

        # Step 3: Remove comma if e.g... is followed by it (e.g..., -> e.g.)
        new_line = re.sub(r'e\.g\.,', 'e.g.', new_line)

        # Step 4: Change e.g, to e.g.
        new_line = re.sub(r'e\.g,', 'e.g.', new_line)

        # Log changes if the line is updated
        if new_line != line:
            global_logs.append(
                f"[e.g. correction] Line {line_number}: {line.strip()} -> {new_line.strip()}"
            )
        updated_lines.append(new_line)
    return "\n".join(updated_lines)



def enforce_ie_rule_with_logging(text):
    lines = text.splitlines()
    updated_lines = []
    for line_number, line in enumerate(lines, start=1):
        original_line = line

        # Step 1: Match "ie" or "i.e." with optional surrounding spaces and punctuation
        new_line = re.sub(r'\bie\b', 'i.e.', line, flags=re.IGNORECASE)  # Handle standalone "ie"
        new_line = re.sub(r'\bie,\b', 'i.e.', new_line, flags=re.IGNORECASE)  # Handle "ie,"

        # Step 2: Fix extra periods like `i.e..` or `i.e...,` and ensure proper punctuation
        new_line = re.sub(r'\.([.,])', r'\1', new_line)  # Removes an extra period before a comma or period
        new_line = re.sub(r'\.\.+', '.', new_line)  # Ensures only one period after i.e.

        # Step 3: Remove comma if i.e... is followed by it (i.e..., -> i.e.)
        new_line = re.sub(r'i\.e\.,', 'i.e.', new_line)
        
        # Step 4: Change i.e, to i.e.
        new_line = re.sub(r'i\.e,', 'i.e.', new_line)

        # Log changes if the line is updated
        if new_line != line:
            global_logs.append(
                f"[i.e. correction] Line {line_number}: {line.strip()} -> {new_line.strip()}"
            )
        updated_lines.append(new_line)
    return "\n".join(updated_lines)


def standardize_etc(text):
    lines = text.splitlines()
    updated_lines = []
    pattern = r'\b(e\.?tc|e\.t\.c|e\.t\.c\.|et\.?\s?c|et\s?c|etc\.?|etc|et cetera|etcetera|Etc\.?|Etc|‘and etc\.’|et\.?\s?cetera|etc\.?,?|etc\.?\.?|etc\,?\.?)\b'
    
    for line_number, line in enumerate(lines, start=1):
        original_line = line
        
        # Replace all matches of "etc." variations with "etc."
        new_line = re.sub(pattern, 'etc.', line, flags=re.IGNORECASE)
        
        # Explicitly replace "etc.." with "etc."
        new_line = re.sub(r'etc\.\.+', 'etc.', new_line)
        
        # Explicitly replace "etc.." with "etc."
        new_line = re.sub(r'etc\.\.+', 'etc.', new_line)
        
        # Explicitly replace "etc.," with "etc."
        new_line = re.sub(r'etc\.,', 'etc.', new_line)

        # Log changes if the line is updated
        if new_line != line:
            global_logs.append(f"[etc. correction] Line {line_number}: {line.strip()} -> {new_line.strip()}")
        
        updated_lines.append(new_line)
    return "\n".join(updated_lines)



def insert_thin_space_between_number_and_unit(text, line_number):
    global global_logs
    original_text = text
    thin_space = '\u2009'
    
    pattern = r"(\d+)(?=\s?[a-zA-Z]+)(?!\s?°)"
    updated_text = text
    matches = re.finditer(pattern, text)
    for match in matches:
        number = match.group(1)  # This is the number
        unit_start = match.end()
        unit = text[unit_start:].split()[0] 
        original_word = number + unit
        updated_word = number + thin_space + unit
        updated_text = updated_text.replace(original_word, updated_word, 1)
        global_logs.append(
            f"[insert_thin_space_between_number_and_unit] Line {line_number}: '{original_word}' -> '{updated_word}'"
        )
    return updated_text

import spacy
import re

# Load the spaCy model
nlp = spacy.load("en_core_web_sm")


# def process_paragraph(text, line_number):
#     """
#     Processes paragraph text to ensure a comma is added before 'e.g.'
#     if there is no verb between 'e.g.' and the end of the sentence.
#     Args:
#         text (str): The text of the paragraph.
#         line_number (int): Line number for reference (useful for debugging/logging).
#     Returns:
#         str: Updated text with proper comma placement.
#     """
#     doc = nlp(text)
#     updated_sentences = []

#     for sentence in doc.sents:  # Split text into sentences
#         sentence_text = sentence.text
        
#         # Check if 'e.g.' is in the sentence
#         if "e.g." in sentence_text:
#             # Find the position of 'e.g.'
#             eg_start_idx = sentence_text.find("e.g.")
#             after_eg_text = sentence_text[eg_start_idx:]
            
#             # Process the text after 'e.g.' to look for verbs
#             after_eg_doc = nlp(after_eg_text)
#             has_verb = any(token.pos_ == "VERB" for token in after_eg_doc)
            
#             if not has_verb:
#                 # Add a comma before 'e.g.' if no verb is found
#                 sentence_text = re.sub(r"(?<!,)\s+e\.g\.", ", e.g.", sentence_text)
        
#         updated_sentences.append(sentence_text)
#     updated_text = " ".join(updated_sentences)
#     return updated_text


def process_paragraph(text, line_number):
    """
    Processes paragraph text to:
    1. Add a comma before 'e.g.' if there is no verb between 'e.g.' and the end of the sentence.
    2. Add a semicolon before 'i.e.' wherever it appears.
    Args:
        text (str): The text of the paragraph.
        line_number (int): Line number for reference (useful for debugging/logging).
    Returns:
        str: Updated text with proper comma and semicolon placement.
    """
    doc = nlp(text)
    updated_sentences = []

    for sentence in doc.sents:  # Split text into sentences
        sentence_text = sentence.text

        # Step 1: Handle 'e.g.'
        if "e.g." in sentence_text:
            # Find the position of 'e.g.'
            eg_start_idx = sentence_text.find("e.g.")
            after_eg_text = sentence_text[eg_start_idx:]
            
            # Process the text after 'e.g.' to look for verbs
            after_eg_doc = nlp(after_eg_text)
            has_verb = any(token.pos_ == "VERB" for token in after_eg_doc)
            
            if not has_verb:
                # Add a comma before 'e.g.' if no verb is found
                sentence_text = re.sub(r"(?<!,)\s+e\.g\.", ", e.g.", sentence_text)
        
        # Step 2: Handle 'i.e.'
        if "i.e." in sentence_text:
            # Add a semicolon before 'i.e.' if not already present
            sentence_text = re.sub(r"(?<!;)\s+i\.e\.", ": i.e.", sentence_text)
            
        updated_sentences.append(sentence_text)

    updated_text = " ".join(updated_sentences)
    return updated_text


def apply_quotation_punctuation_rule(text: str):
    """
    Adjusts the placement of punctuation marks within single quotes.
    Args:
        text (str): Input text to process.
    Returns:
        str: Updated text.
    """
    global global_logs
    pattern = r"‘(.*?)’([!?])"
    def process_quotation_punctuation(match):
        original = match.group(0)
        modified = f"‘{match.group(1)}{match.group(2)}’"
        if original != modified:
            line_number = text[:match.start()].count('\n') + 1
            global_logs.append(
                f"[apply_quotation_punctuation_rule] Line {line_number}: '{original}' -> '{modified}'"
            )
        return modified
    updated_text = re.sub(pattern, process_quotation_punctuation, text)
    return updated_text



# Dictionary to convert word numbers to integer values
word_to_num = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11,
    'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15, 'sixteen': 16,
    'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20, 'twenty-one': 21,
    'twenty-two': 22, 'twenty-three': 23, 'twenty-four': 24, 'twenty-five': 25,
    'twenty-six': 26, 'twenty-seven': 27, 'twenty-eight': 28, 'twenty-nine': 29,
    'thirty': 30, 'thirty-one': 31, 'thirty-two': 32, 'thirty-three': 33,
    'thirty-four': 34, 'thirty-five': 35, 'thirty-six': 36, 'thirty-seven': 37,
    'thirty-eight': 38, 'thirty-nine': 39, 'forty': 40, 'forty-one': 41,
    'forty-two': 42, 'forty-three': 43, 'forty-four': 44, 'forty-five': 45,
    'forty-six': 46, 'forty-seven': 47, 'forty-eight': 48, 'forty-nine': 49,
    'fifty': 50, 'fifty-one': 51, 'fifty-two': 52, 'fifty-three': 53,
    'fifty-four': 54, 'fifty-five': 55, 'fifty-six': 56, 'fifty-seven': 57,
    'fifty-eight': 58, 'fifty-nine': 59, 'sixty': 60, 'sixty-one': 61,
    'sixty-two': 62, 'sixty-three': 63, 'sixty-four': 64, 'sixty-five': 65,
    'sixty-six': 66, 'sixty-seven': 67, 'sixty-eight': 68, 'sixty-nine': 69,
    'seventy': 70, 'seventy-one': 71, 'seventy-two': 72, 'seventy-three': 73,
    'seventy-four': 74, 'seventy-five': 75, 'seventy-six': 76, 'seventy-seven': 77,
    'seventy-eight': 78, 'seventy-nine': 79, 'eighty': 80, 'eighty-one': 81,
    'eighty-two': 82, 'eighty-three': 83, 'eighty-four': 84, 'eighty-five': 85,
    'eighty-six': 86, 'eighty-seven': 87, 'eighty-eight': 88, 'eighty-nine': 89,
    'ninety': 90, 'ninety-one': 91, 'ninety-two': 92, 'ninety-three': 93,
    'ninety-four': 94, 'ninety-five': 95, 'ninety-six': 96, 'ninety-seven': 97,
    'ninety-eight': 98, 'ninety-nine': 99, 'hundred': 100
}

# Reverse dictionary to convert integer values back to words
num_to_word = {v: k for k, v in word_to_num.items()}

# Function to convert word number to integer
def word_to_int(word):
    return word_to_num.get(word.lower(), None)

# Function to convert integer to word
def int_to_word(num):
    return num_to_word.get(num, None)

# Regular expression to match "word and word" pattern
pattern = re.compile(r'(\b\w+\b) and (\b\w+\b)')

# Function to process the string with regex and apply transformations
def process_string(text):
    def replace_match(match):
        word1 = match.group(1)
        word2 = match.group(2)
        # Convert words to their numeric values
        num1 = word_to_int(word1)
        num2 = word_to_int(word2)
        
        # If both numbers are less than 9, return them as word form
        if (num1 is not None and num1 < 9) and (num2 is not None and num2 < 9):
            return f"{word1} and {word2}"  # No change if both are < 9
        
        # If either number is greater than or equal to 9, convert to numeric form
        if (num1 is not None and num1 >= 9) or (num2 is not None and num2 >= 9):
            # Convert both to numeric form
            num1 = num1 if num1 is not None else word1
            num2 = num2 if num2 is not None else word2
            return f"{num1} and {num2}"  # Replace with numeric values
        
        return match.group(0)  # Return the match as is if both are < 9
    
    # Apply regex substitution with the replace function
    return pattern.sub(replace_match, text)




def write_to_log(doc_id):
    global global_logs
    output_dir = os.path.join('output', str(doc_id))
    os.makedirs(output_dir, exist_ok=True)
    log_file_path = os.path.join(output_dir, 'global_logs.txt')
    with open(log_file_path, 'w', encoding='utf-8') as log_file:
        log_file.write("\n".join(global_logs))
    global_logs = []
    





def process_doc_function1(payload: dict, doc: Document, doc_id):
    """
    This function processes the document by converting century notations
    and highlighting specific words.
    """
    line_number = 1
    abbreviation_dict = fetch_abbreviation_mappings()
    
    for para in doc.paragraphs:
        # para.text = convert_century(para.text, line_number)
        # para.text = process_symbols_mark(para.text, line_number)
        # para.text = enforce_serial_comma(para.text)
        # para.text = set_number_to_no(para.text,line_number)
        # para.text = apply_abbreviation_mapping(para.text, abbreviation_dict, line_number)
        # para.text = enforce_am_pm(para.text, line_number)
        # para.text = set_latinisms_to_roman(para.text, line_number)
        # if(payload["2"] == False):
        #     para.text = rename_section(para.text)
        # para.text = replace_ampersand(para.text)
        # para.text = correct_possessive_names(para.text, line_number)
        # para.text = format_titles_us_english_with_logging(para.text)
        # para.text = units_with_bracket(para.text)
        # para.text = remove_and(para.text)
        # para.text = remove_quotation(para.text)
        # para.text = correct_acronyms(para.text, line_number)
        # para.text = enforce_eg_rule_with_logging(para.text)
        # para.text = enforce_ie_rule_with_logging(para.text)
        # para.text = process_paragraph(para.text, line_number)
        # para.text = apply_remove_italics_see_rule(para.text)
        # para.text = standardize_etc(para.text)
        # para.text = insert_thin_space_between_number_and_unit(para.text, line_number)
        # para.text = process_string(para.text)
        # para.text = apply_quotation_punctuation_rule(para.text)
        # line_number += 1
        convert_century_in_runs(para.runs, line_number)
        set_latinisms_to_roman_in_runs(para.runs, line_number)
        process_symbols_mark_in_runs(para.runs, line_number)
        apply_remove_italics_see_rule_in_runs(para.runs)
        set_number_to_no_in_runs(para.runs, line_number)
        format_titles_us_english_with_logging_in_runs(para.runs, line_number)
        enforce_am_pm_in_runs(para.runs, line_number)
        enforce_serial_comma_in_runs(para.runs)
        rename_section_in_runs(para.runs)
        replace_ampersand_in_runs(para.runs, line_number)
        correct_possessive_names_in_runs(para.runs, line_number)
        # units_with_bracket_in_runs(para.runs, replaced_units)
        line_number += 1

    write_to_log(doc_id)
    
    
    