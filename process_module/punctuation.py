import re
from docx import Document
import os
from db_config import get_db_connection


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


def apply_abbreviation_mapping(text, abbreviation_dict, line_number):
    global global_logs
    words = text.split()
    updated_text = []
    for word in words:
        updated_word = abbreviation_dict.get(word, word)
        if word != updated_word:
            global_logs.append(f"[apply_abbreviation_mapping] Line {line_number}: '{word}' -> '{updated_word}'")
        updated_text.append(updated_word)
    return ' '.join(updated_text)



def convert_century(text, line_number_offset):
    """
    Converts century notation like '21st' to 'the twenty-first century'
    and logs the changes with line numbers.

    :param text: The entire text to process, possibly spanning multiple lines.
    :param line_number_offset: The starting line number for this chunk of text.
    :return: The updated text with century notations converted.
    """
    global global_logs  # Global log to record changes
    lines = text.split('\n')  # Split text into individual lines
    updated_lines = []

    for index, line in enumerate(lines):
        words = line.split()  # Split line into words
        for i, word in enumerate(words):
            match = re.match(r"(\d+)(st|nd|rd|th)$", word)  # Match century notation
            if match:
                num = int(match.group(1))
                if num in century_map:
                    # Original and converted word
                    original_word = match.group(0)
                    converted_word = f"the {century_map[num]} century"
                    
                    # Log the change with the actual line number
                    global_logs.append(
                        f"[convert century] Line {line_number_offset + index}: {original_word} -> {converted_word}"
                    )
                    
                    # Replace the word in the line
                    words[i] = converted_word
        
        # Rebuild the updated line
        updated_lines.append(' '.join(words))

    # Return the updated text with all lines rebuilt
    return '\n'.join(updated_lines)


def set_latinisms_to_roman_in_runs(paragraph_text, line_number, latinisms=None):
    """
    Converts specific Latinisms from italic to roman text in a string of text.
    Logs changes to the global_log, including line number and original italicized Latinism.
    """
    if latinisms is None:
        latinisms = [
            "i.e.", "e.g.", "via", "vice versa", "etc.", "a posteriori", 
            "a priori", "et al.", "cf.", "c."
        ]
    
    changes = []
    global global_logs

    # Process the text, and for each Latinism, replace its italics if needed
    for lat in latinisms:
        if lat in paragraph_text:
            changes.append(lat)  # Log the Latinism that was changed

    # for changed in changes:
    #     global_logs.append(
    #         f"[process_symbols_in_doc] Line {line_number}: '{changed}' -> '{changed}'"
    #     )

    return paragraph_text 


def process_symbols_mark(text, line_number, symbols=["®", "™", "©", "℗", "℠"]):
    """
    Ensures symbols like ®, ™, etc., appear only the first time in the text.
    Updates the global_log with changes, including line number, original text, and updated text.
    """
    original_text = text
    symbol_set = set()
    global global_logs
    
    for symbol in symbols:
        occurrences = list(re.finditer(re.escape(symbol), text))
        if occurrences:
            first_occurrence = occurrences[0].start()
            # Replace all occurrences after the first one
            text = (
                text[:first_occurrence + 1]
                + re.sub(re.escape(symbol), "", text[first_occurrence + 1:])
            )
            symbol_set.add(symbol)

    # Log changes if the text was modified
    if original_text != text:
        global_logs.append(
            f"[process_symbols_in_doc] Line {line_number}: '{original_text}' -> '{text}'"
        )

    return text



def apply_remove_italics_see_rule(text):
    return text.replace('*see*', 'see')


def set_number_to_no(text, line_number):
    """
    Replaces 'Number X' or 'number X' with 'No. X' or 'no. X' and logs changes.
    :param text: The input text.
    :param line_number: Line number for logging.
    :return: Updated text with number abbreviations applied.
    """
    global global_logs

    def replace_number(match):
        word = match.group(1)
        num = match.group(2)
        updated_text = f"No. {num}" if word.istitle() else f"no. {num}"
        global_logs.append(f"[set_number_to_no] Line {line_number}: '{match.group(0)}' -> '{updated_text}'")
        return updated_text

    pattern = r'\b(Number|number)\s(\d+)\b'
    return re.sub(pattern, replace_number, text)



def format_titles_us_english_with_logging(text):
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
    }    
    lines = text.splitlines()
    updated_lines = []
    for line_number, line in enumerate(lines, start=1):
        original_line = line
        for title, replacement in titles.items():
            new_line = re.sub(rf"\b{title}\b", replacement, line, flags=re.IGNORECASE)
            if new_line != line:
                global_logs.append(f"[shorten title] Line {line_number}: {title} -> {replacement}")
                line = new_line
        updated_lines.append(line)
    return "\n".join(updated_lines)


def enforce_am_pm(text, line_num):
    """
    Ensures consistent formatting for 'am' and 'pm' in the entire paragraph and logs changes.
    :param text: The paragraph text to process.
    :param line_num: The line number in the document for logging.
    :return: The updated text with corrected 'am' and 'pm' formats.
    """
    global global_logs  # Use a global log to record changes
    original_text = text  # Store the original text for comparison
    words = text.split()  # Split the paragraph into words

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
    corrected_text = " ".join(corrected_words)
    return corrected_text



def enforce_serial_comma(text):
    lines = text.splitlines()
    updated_lines = []

    for line_number, line in enumerate(lines, start=1):
        original_line = line

        # Add a comma before "and" or "or" in lists
        new_line = re.sub(
            r'([^,]+), ([^,]+) (or) ([^,]+)',
            r'\1, \2, \3 \4',
            line
        )
        # Explicitly handle cases where "or" does not get the serial comma
        new_line = re.sub(
            r'([^,]+), ([^,]+) (and) ([^,]+)',
            r'\1, \2, \3 \4',
            new_line
        )
        if new_line != line:
            global_logs.append(f"[Serial comma correction] Line {line_number}: {line.strip()} -> {new_line.strip()}")
        updated_lines.append(new_line)
    return "\n".join(updated_lines)



def rename_section(text):
    # Replace all occurrences of the § symbol with 'Section'
    return re.sub(r'§', 'Section', text)


# There is one problem here for project, & document it is not changing and for project & document it is changing
def replace_ampersand(text):
    global global_logs
    def replacement(match):
        left, right = match.group(1), match.group(2)
        original = match.group(0)
        line_number = text[:match.start()].count('\n') + 1
        if left[0].isupper() and right[0].isupper():
            return original
        modified = left + ' and ' + right
        global_logs.append(
            f"[replace_ampersand] Line {line_number}: '{original}' -> '{modified}'"
        )
        return modified
    return re.sub(r'(?m)(\w+)\s*&\s*(\w+)', replacement, text)




def correct_possessive_names(text, line_number):
    global global_logs
    pattern_singular_possessive = r"\b([A-Za-z]+s)\b(?<!\bs')'"
    matches_singular = re.finditer(pattern_singular_possessive, text)
    updated_text = text
    for match in matches_singular:
        original_text = match.group(0)
        updated_text_singular = match.group(1)[:-1] + "'s"
        updated_text = updated_text.replace(original_text, updated_text_singular)
        global_logs.append(
            f"[correct_possessive_names] Line {line_number}: '{original_text}' -> '{updated_text_singular}'"
        )
    pattern_plural_possessive = r"\b([A-Za-z]+s)'\b"
    matches_plural = re.finditer(pattern_plural_possessive, updated_text)
    for match in matches_plural:
        original_text = match.group(0)
        updated_text_plural = match.group(1) + "'"
        updated_text = updated_text.replace(original_text, updated_text_plural)
        global_logs.append(
            f"[correct_possessive_names] Line {line_number}: '{original_text}' -> '{updated_text_plural}'"
        )
    return updated_text


def units_with_bracket(text):
    units = {
        "s": "second",
        "m": "meter",
        "kg": "kilogram",
        "A": "ampere",
        "K": "kelvin",
        "mol": "mole",
        "cd": "candela"
    }
    used_units = set()
    global global_logs
    processed_lines = []
    for line_num, line in enumerate(text.splitlines(), start=1):
        def replace_unit(match):
            number = match.group(1)
            unit = match.group(2)
            if unit in used_units:
                return match.group(0)
            else:
                used_units.add(unit)
                full_form = units[unit]
                if unit != "mol" and not full_form.endswith("s"):
                    full_form += "s"
                replacement = f"{number} {full_form} ({unit.lower()})"
                global_logs.append(
                    f"Line {line_num}: {match.group(0)} -> {replacement}"
                )
                return replacement
        pattern = r'\b(\d+)\s*(%s)\b' % '|'.join(re.escape(unit) for unit in units.keys())
        processed_line = re.sub(pattern, replace_unit, line)
        processed_lines.append(processed_line)
    return "\n".join(processed_lines)


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

def process_paragraph(text, line_number):
    """
    Processes paragraph text to ensure a comma is added before 'e.g.'
    if there is no verb between 'e.g.' and the end of the sentence.
    Args:
        text (str): The text of the paragraph.
        line_number (int): Line number for reference (useful for debugging/logging).
    Returns:
        str: Updated text with proper comma placement.
    """
    doc = nlp(text)
    updated_sentences = []

    for sentence in doc.sents:  # Split text into sentences
        sentence_text = sentence.text
        
        # Check if 'e.g.' is in the sentence
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
        
        updated_sentences.append(sentence_text)
    updated_text = " ".join(updated_sentences)
    return updated_text



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
    print(payload)
    for para in doc.paragraphs:
        para.text = convert_century(para.text, line_number)
        para.text = process_symbols_mark(para.text, line_number)
        para.text = enforce_serial_comma(para.text)
        para.text = set_number_to_no(para.text,line_number)
        para.text = apply_abbreviation_mapping(para.text, abbreviation_dict, line_number)
        para.text = enforce_am_pm(para.text, line_number)
        para.text = set_latinisms_to_roman_in_runs(para.text, line_number)
        if(payload["2"] == False):
            para.text = rename_section(para.text)
        para.text = replace_ampersand(para.text)
        para.text = correct_possessive_names(para.text, line_number)
        para.text = format_titles_us_english_with_logging(para.text)
        para.text = units_with_bracket(para.text)
        para.text = remove_and(para.text)
        para.text = remove_quotation(para.text)
        para.text = correct_acronyms(para.text, line_number)
        para.text = enforce_eg_rule_with_logging(para.text)
        para.text = enforce_ie_rule_with_logging(para.text)
        para.text = process_paragraph(para.text, line_number)
        para.text = apply_remove_italics_see_rule(para.text)
        para.text = standardize_etc(para.text)
        para.text = insert_thin_space_between_number_and_unit(para.text, line_number)
        line_number += 1

       
    write_to_log(doc_id)
    
    
    
