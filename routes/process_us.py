import re
from docx.shared import RGBColor
from num2words import num2words
from word2number import w2n
import enchant
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse
import os
import docx
from sqlalchemy import text
from db_config import get_db_connection
import mammoth
from datetime import datetime
from pathlib import Path
import logging  
import roman
from roman import fromRoman
from urllib.parse import urlparse

router = APIRouter()

# us_dict = enchant.Dict("en_US")

us_dict = enchant.DictWithPWL("en_US","mywords.txt")

global_logs = []

def fetch_abbreviation_mappings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT original_word, abbreviated_form FROM abbreviation_mapping")
    mappings = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in mappings}


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



def apply_number_abbreviation_rule(text, line_number):
    """
    Replaces 'Number X' or 'number X' with 'No. X' or 'no. X' and logs changes.
    :param text: The input text.
    :param line_number: Line number for logging.
    :return: Updated text with number abbreviations applied.
    """
    global global_logs

    def replace_number(match):
        word = match.group(1)  # 'Number' or 'number'
        num = match.group(2)  # The number following it
        updated_text = f"No. {num}" if word.istitle() else f"no. {num}"
        global_logs.append(f"[apply_number_abbreviation_rule] Line {line_number}: '{match.group(0)}' -> '{updated_text}'")
        return updated_text

    pattern = r'\b(Number|number)\s(\d+)\b'
    return re.sub(pattern, replace_number, text)


def apply_numerals_rule(text):
    def text_to_num(match):
        try:
            return str(w2n.word_to_num(match.group(0)))
        except ValueError:
            return match.group(0)
    text = re.sub(r'\b(\w+ and a half|\w+ and \w+/\w+)\b', text_to_num, text)
    text = re.sub(r'\b(\w+-\w+/\w+)\b', text_to_num, text)
    text = re.sub(r'\b(\w+) years? old\b', text_to_num, text)
    text = re.sub(r'\b(\w+ (first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth))\b', text_to_num, text)
    return text

# Done
def replace_percent_with_symbol(text):
    global global_logs

    modified_text = []
    lines = text.splitlines()

    for line_number, line in enumerate(lines, 1):
        # Find matches for numbers followed by 'percent' or 'per cent'
        matches = re.findall(r"(\d+)\s?(percent|per cent)", line, flags=re.IGNORECASE)

        # If there are matches, replace them and store the change in the global log
        if matches:
            for match in matches:
                original_text = f"{match[0]} {match[1]}"
                modified_text_line = line.replace(original_text, f"{match[0]}%")
                global_logs.append(
                    f"[replace_percent_with_symbol] Line {line_number}: {original_text} -> {match[0]}%"
                )
                line = modified_text_line  # Update the line after the change

        modified_text.append(line)  # Add the modified line to the final text

    return "\n".join(modified_text)


# Done
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



def clean_word(word):
    return word.strip(",.?!:;\"'()[]{}")

# def clean_word(word):
#     return word

# Done
def replace_curly_quotes_with_straight(text):
    return text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")



# Done
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


# Done
# def enforce_am_pm(word, line_num):
#     word_lower = word.lower()
#     global global_logs
#     if word_lower in {"am", "a.m", "pm", "p.m"}:
#         if "a" in word_lower:
#             corrected_word = "a.m."
#             global_logs.append(f"[am pm change] Line {line_num}: {word} -> {corrected_word}")
#             return corrected_word
#         elif "p" in word_lower:
#             corrected_word = "p.m."
#             global_logs.append(f"[am pm change] Line {line_num}: {word} -> {corrected_word}")
#             return corrected_word
#     return word


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
        original_word = word  # Store the original word for logging
        word_lower = word.lower()  # Convert word to lowercase for comparison

        # Check and correct 'am' or 'pm' formats
        if word_lower in {"am", "a.m", "pm", "p.m"}:
            if "a" in word_lower:
                corrected_word = "a.m."
            elif "p" in word_lower:
                corrected_word = "p.m."
            
            # Log the change if the word was modified
            if corrected_word != original_word:
                global_logs.append(
                    f"[am pm change] Line {line_num}: '{original_word}' -> '{corrected_word}'"
                )
        else:
            corrected_word = word  # Keep the word unchanged if no match

        corrected_words.append(corrected_word)  # Add the corrected word to the list

    # Join the corrected words to form the updated paragraph
    corrected_text = " ".join(corrected_words)

    return corrected_text



# Done
# [apostrophes change] : 60's -> 1960s 
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


# pending not clear
# Spell out numbers below 10 unless used in conjunction with a unit of measurement in the text(2.15)
def spell_out_number_and_unit_with_rules(sentence, line_number):
    global global_logs
    original_sentence = sentence
    unit_pattern = r"(\d+)\s+([a-zA-Z]+)"
    number_pattern = r"\b(\d+)\b"
    contains_unit = bool(re.search(unit_pattern, sentence))
    if contains_unit:
        sentence = re.sub(r"(\d+)\s+([a-zA-Z]+)", lambda m: f"{m.group(1)} {m.group(2)}", sentence)
    else:
        sentence = re.sub(number_pattern, lambda m: num2words(int(m.group(0)), to="cardinal") if int(m.group(0)) < 10 else m.group(0), sentence)
    if bool(re.search(r"\b[a-zA-Z]+\b", sentence)) and bool(re.search(r"\b\d+\b", sentence)):
        sentence = re.sub(r"\b([a-zA-Z]+)\b", lambda m: str(num2words(m.group(0), to="cardinal")) if m.group(0).isdigit() else m.group(0), sentence)
    if sentence != original_sentence:
        global_logs.append(f"[spell_out_number_and_unit_with_rules] Line {line_number}: '{original_sentence}' -> '{sentence}'")
    return sentence



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



# def enforce_eg_rule_with_logging(text):
#     lines = text.splitlines()
#     updated_lines = []
#     for line_number, line in enumerate(lines, start=1):
#         original_line = line

#         # Step 1: Match "eg" or "e.g." with optional surrounding spaces and punctuation
#         new_line = re.sub(r'\beg\b', 'e.g.', line, flags=re.IGNORECASE)
#         new_line = re.sub(r'\beg,\b', 'e.g.', new_line, flags=re.IGNORECASE)  # Handle "eg,"

#         # Step 2: Fix extra periods like `e.g..` or `e.g...,` and ensure proper punctuation
#         new_line = re.sub(r'\.([.,])', r'\1', new_line)  # Removes an extra period before a comma or period
#         new_line = re.sub(r'\.\.+', '.', new_line)  # Ensures only one period after e.g.

#         # Step 3: Remove comma if e.g... is followed by it (e.g..., -> e.g.)
#         new_line = re.sub(r'e\.g\.,', 'e.g.', new_line)

#         # Log changes if the line is updated
#         if new_line != line:
#             global_logs.append(
#                 f"[e.g. correction] Line {line_number}: {line.strip()} -> {new_line.strip()}"
#             )
        
#         updated_lines.append(new_line)
#     return "\n".join(updated_lines)



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




# def standardize_etc(line):
#     line = re.sub(r'\b(et\.?\s?cetera|etc\.?,?|etc\.?\.?|etc\,?\.?)\b', 'etc.', line, flags=re.IGNORECASE)
#     line = re.sub(r'(\betc\.)\.(?=\s|$)', r'\1', line)
#     line = re.sub(r'(\betc\.)\.(?=\W)', r'\1', line)
#     return line

# def standardize_etc(text):
#     lines = text.splitlines()
#     updated_lines = []
#     pattern = r'\b(e\.?tc|e\.t\.c|e\.t\.c\.|et\.?\s?c|et\s?c|etc\.?|etc|et cetera|etcetera|Etc\.?|Etc|‘and etc\.’|et\.?\s?cetera|etc\.?,?|etc\.?\.?|etc\,?\.?)\b'
#     for line_number, line in enumerate(lines, start=1):
#         original_line = line
#         new_line = re.sub(pattern, 'etc.', line, flags=re.IGNORECASE)
#         if new_line != line:
#             global_logs.append(f"[etc. correction] Line {line_number}: {line.strip()} -> {new_line.strip()}")
#         updated_lines.append(new_line)
#     return "\n".join(updated_lines)


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

def adjust_ratios(text):
    return re.sub(r"(\d)\s*:\s*(\d)", r"\1 : \2", text)


def correct_chapter_numbering(text, chapter_counter):
    chapter_pattern = re.compile(r"(?i)\bchapter\s+((?:[IVXLCDM]+)|(?:[a-z]+)|(?:\d+))[:.]?\s")
    def replace_chapter_heading(match):
        chapter_content = match.group(1)
        if re.match(r"^[IVXLCDM]+$", chapter_content, re.IGNORECASE):
            chapter_number = roman.fromRoman(chapter_content.upper())
        elif re.match(r"^[a-z]+$", chapter_content, re.IGNORECASE):
            chapter_number = w2n.word_to_num(chapter_content.lower())
        else:
            chapter_number = int(chapter_content)
        return f"Chapter {chapter_number}: "
    return chapter_pattern.sub(replace_chapter_heading, text)


def enforce_number_spelling_rule(text: str):
    num_to_words = {
        "1": "one", "2": "two", "3": "three", "4": "four", "5": "five",
        "6": "six", "7": "seven", "8": "eight", "9": "nine"
    }
    units = r"(kg|g|mg|cm|mm|km|m|l|ml|%)"
    sentences = re.split(r"(?<=[.!?])\s+", text)
    updated_sentences = []
    for sentence in sentences:
        numbers = re.findall(r"\b\d+\b", sentence)
        if any(int(num) >= 10 for num in numbers) and any(int(num) < 10 for num in numbers):
            updated_sentences.append(sentence)
            continue
        def replace_number(match):
            number = match.group()
            if number in num_to_words:
                if re.search(rf"\b{number}\b\s+{units}", sentence):
                    return number
                if re.search(rf"\b{number}-[a-zA-Z-]+", sentence):
                    return num_to_words[number]  # Spell out
                return num_to_words[number]  # Spell out
            return number  # Keep numerals >= 10
        updated_sentence = re.sub(r"\b\d+\b", replace_number, sentence)
        updated_sentences.append(updated_sentence)
    return " ".join(updated_sentences)




# Done
# [insert_thin_space_between_number_and_unit] Line 31: '5kg' -> '5 kg'
def insert_thin_space_between_number_and_unit(text, line_number):
    global global_logs
    original_text = text
    thin_space = '\u2009'
    
    pattern = r"(\d+)(?=\s?[a-zA-Z]+)(?!\s?°)"

    updated_text = text  # Initialize updated text to the original

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




# def format_dates(text):
#     text = re.sub(r"\b(\d+)\s?(BCE|CE)\b", lambda m: f"{m.group(1)} {m.group(2).lower()}", text)
#     text = re.sub(r"\b(AD|BC)\.\b", r"\1 ", text)
#     text = re.sub(r"(\d+)\s?(BCE|CE|AD|BC)\b", r"\1 \2", text)
#     return text


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


# Done
# [remove_space_between_degree_and_direction] Line 10: '52 °N' -> '52°N'
def remove_space_between_degree_and_direction(text, line_number):
    global global_logs
    pattern = r"(\d+) \s*[º°]\s*(N|S|E|W)\b"
    def log_replacement(match):
        original_text = match.group(0)
        updated_text = match.group(1) + " " + "º" + match.group(2)
        global_logs.append(
            f"[remove_space_between_degree_and_direction] Line {line_number}: '{original_text}' -> '{updated_text}'"
        )
        return updated_text
    updated_text = re.sub(pattern, log_replacement, text)
    return updated_text



# Done
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


# Done
def adjust_terminal_punctuation_in_quotes(text):
    text = re.sub(
        r"([‘“])([^’”]*[?!])([’”])\.",
        r"\1\2\3",
        text
    )
    return text




def enforce_serial_comma(text):
    lines = text.splitlines()
    updated_lines = []

    for line_number, line in enumerate(lines, start=1):
        original_line = line

        # Add a comma before "and" or "or" in lists
        new_line = re.sub(
            r'([^,]+), ([^,]+) (and|or) ([^,]+)',  # Match the list structure without the serial comma
            r'\1, \2, \3 \4',                     # Add the serial comma before "and" or "or"
            line
        )

        # Log changes if the line is updated
        if new_line != line:
            global_logs.append(f"[Serial comma correction] Line {line_number}: {line.strip()} -> {new_line.strip()}")
        
        updated_lines.append(new_line)
    
    return "\n".join(updated_lines)



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




# Done
# http://www.PHi.com/authorguidelines not http://www.PHi.com/authorguidelines/
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


# Check out this link: <https://example.com> for more details.
# Check out this link: https://example.com for more details.
def clean_web_addresses(text):
    return re.sub(r"<(https?://[^\s<>]+)>", r"\1", text)


def format_ellipses_in_series(text):
    # Matches series like "x1, x2, ..., xn" and ensures the ellipsis has a comma and space after it.
    text = re.sub(r"(\w+),\s*(\w+),\s*\.\.\.\s*(\w+)", r"\1, \2, …, \3", text)
    return text



def format_chapter_title(text):
    match = re.match(r"Chapter\s+([\dIVXLCDM]+)[\.:]\s*(.*)", text, re.IGNORECASE)
    if match:
        chapter_number = match.group(1)
        chapter_title = match.group(2).rstrip('.')
        words = chapter_title.split()
        formatted_title = " ".join([
            word.capitalize() if i == 0 or len(word) >= 4 else word.lower()
            for i, word in enumerate(words)
        ])
        # print(formatted_title)
        return f"{chapter_number}. {formatted_title}"
    return text




def format_titles_us_english_with_logging(text, doc_id):
    global global_logs  # Access the global log array

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
            # Replace case-insensitive title with formatted title
            new_line = re.sub(rf"\b{title}\b", replacement, line, flags=re.IGNORECASE)
            if new_line != line:
                # Log the change to the global array
                global_logs.append(f"[shorten title] Line {line_number}: {title} -> {replacement}")
                line = new_line
        updated_lines.append(line)

    # Return the updated text
    return "\n".join(updated_lines)


def units_with_bracket(text, doc_id):
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



def correct_scientific_units_with_logging(text, doc_id):
    global global_logs
    unit_symbols = ['kg', 'm', 's', 'A', 'K', 'mol', 'cd', 'Hz', 'N', 'Pa', 'J', 'W', 'C', 'V', 'F', 'Ω', 'ohm', 'S', 'T', 'H', 'lm', 'lx', 'Bq', 'Gy', 'Sv', 'kat']
    pattern = rf"\b(\d+)\s*({'|'.join(re.escape(unit) for unit in unit_symbols)})\s*(s|'s|\.s)?\b"
    lines = text.splitlines()
    updated_lines = []
    for line_number, line in enumerate(lines, start=1):
        original_line = line
        new_line = re.sub(pattern, lambda m: f"{m.group(1)} {m.group(2)}", line)
        if new_line != line:
            global_logs.append(
                f"[unit correction] Doc {doc_id}, Line {line_number}: {line.strip()} -> {new_line.strip()}"
            )
            line = new_line
        updated_lines.append(line)
    return "\n".join(updated_lines)



def write_to_log(doc_id):
    global global_logs

    output_dir = os.path.join('output', str(doc_id))
    os.makedirs(output_dir, exist_ok=True)
    log_file_path = os.path.join(output_dir, 'global_logs.txt')

    with open(log_file_path, 'w', encoding='utf-8') as log_file:
        log_file.write("\n".join(global_logs))

    global_logs = []






def replace_fold_phrases(text):
    def process_fold(match):
        num_str = match.group(1)
        separator = match.group(2)
        if separator != "-":
            return match.group(0)
        try:
            if num_str.isdigit():
                number = int(num_str)
            else:
                number = w2n.word_to_num(num_str)

            if number > 9:
                return f"{number}-fold"
            else:
                return f"{num2words(number)}fold"
        except ValueError:
            return match.group(0)
    pattern = r"(\b\w+\b)(-?)fold"
    updated_text = re.sub(pattern, process_fold, text)
    return updated_text



def correct_preposition_usage(text):
    def process_from_to(match):
        return f"from {match.group(1)} to {match.group(2)}"

    def process_between_and(match):
        return f"between {match.group(1)} and {match.group(2)}"
    text = re.sub(r"from (\d{4})[–-](\d{4})", process_from_to, text)
    text = re.sub(r"between (\d{4})[–-](\d{4})", process_between_and, text)
    return text



def correct_scientific_unit_symbols(text):
    """
    Ensures proper capitalization of units derived from proper names (e.g., J, Hz, W, N) only when preceded by a number.

    Args:
        text (str): Input text to process.

    Returns:
        str: Updated text.
    """
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
        unit = match.group(2).lower()  # Capture the unit (second group)
        return f"{match.group(1)}{units.get(unit, match.group(2))}"  # Replace with capitalized unit if in dictionary

    # Regex to match a number followed by optional space and a unit
    pattern = r"\b(\d+\s*)(%s)\b" % "|".join(re.escape(unit) for unit in units.keys())
    updated_text = re.sub(pattern, process_unit, text, flags=re.IGNORECASE)

    return updated_text





def correct_units_in_ranges_with_logging(text, doc_id):
    global global_logs  # Access the global log array

    # List of valid unit symbols
    unit_symbols = ['cm', 'm', 'kg', 's', 'A', 'K', 'mol', 'cd', '%']

    # Regex patterns
    range_pattern = rf"\b(\d+)\s*({'|'.join(re.escape(unit) for unit in unit_symbols)})\s*(to|-|–|—)\s*(\d+)\s*\2\b"
    thin_space_pattern = rf"\b(\d+)\s+({'|'.join(re.escape(unit) for unit in unit_symbols)})\b"

    lines = text.splitlines()
    updated_lines = []

    for line_number, line in enumerate(lines, start=1):
        original_line = line

        # Correct repeated units in ranges
        new_line = re.sub(
            range_pattern,
            lambda m: f"{m.group(1)} {m.group(3)} {m.group(4)} {m.group(2)}",
            line
        )

        # Add thin space between value and unit (except %)
        new_line = re.sub(
            thin_space_pattern,
            lambda m: f"{m.group(1)} {m.group(2)}" if m.group(2) != "%" else f"{m.group(1)}{m.group(2)}",
            new_line
        )

        # Log changes if any
        if new_line != line:
            change_details = f"{line.strip()} -> {new_line.strip()}"
            global_logs.append(f"Line {line_number}: {change_details}")
            line = new_line

        updated_lines.append(line)

    # Return the updated text
    return "\n".join(updated_lines)





def correct_unit_spacing(text):
    units = ["Hz", "KHz", "MHz", "GHz", "kB", "MB", "GB", "TB"]
    pattern = r"(\d+)\s+(" + "|".join(units) + r")"
    
    # Replace spaces between numbers and units with no space
    corrected_text = re.sub(pattern, r"\1\2", text)
    return corrected_text



def apply_quotation_punctuation_rule(text: str):
    pattern = r"‘(.*?)’([!?])"
    updated_text = re.sub(pattern, r"‘\1\2’", text)
    return updated_text


def enforce_dnase_rule(text: str):
    pattern = r"\bDNAse\b"
    updated_text = re.sub(pattern, "DNase", text)
    return updated_text


def apply_remove_italics_see_rule(text):
    return text.replace('*see*', 'see')

# There is one problem here for project, & document it is not changing and for project & document it is changing
def replace_ampersand(text):
    def replacement(match):
        left, right = match.group(1), match.group(2)
        # If both words before and after '&' start with capital letters, leave '&' as is
        if left[0].isupper() and right[0].isupper():
            return match.group(0)  # Return the original match if both are capitalized
        return left + ' and ' + right
    
    return re.sub(r'(\w+)\s*&\s*(\w+)', replacement, text)


def rename_section(text):
    # Replace all occurrences of the § symbol with 'Section'
    return re.sub(r'§', 'Section', text)



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
    text = re.sub(r'\bhttp://(www\.\S+)', r'\1', text)
    text = re.sub(r'\b(www\.\S+)', r'http://\1', text)
    text = re.sub()
    return text


def process_url_remove_http(url):
    parsed = urlparse(url)
    if parsed.scheme == "http" and not (parsed.path or parsed.params or parsed.query or parsed.fragment):
        # If the scheme is http and there's nothing after the domain, remove the scheme
        return parsed.netloc
    return url





def highlight_and_correct(doc, doc_id):
    chapter_counter = [0]
    line_number = 1
    abbreviation_dict = fetch_abbreviation_mappings()
    for para in doc.paragraphs:
        if para.text.strip().startswith("Chapter"):
            para.text = correct_chapter_numbering(para.text, chapter_counter)
            formatted_title = format_chapter_title(para.text)
            para.text = formatted_title
            
        para.text = rename_section(para.text)
        para.text = replace_ampersand(para.text)
        para.text = correct_scientific_unit_symbols(para.text)
        para.text = adjust_ratios(para.text)
        para.text = format_dates(para.text, line_number)
        # para.text = spell_out_number_and_unit_with_rules(para.text,line_number)
        para.text = remove_space_between_degree_and_direction(para.text, line_number)
        para.text = enforce_lowercase_units(para.text, line_number)
        para.text = precede_decimal_with_zero(para.text, line_number)
        para.text = format_ellipses_in_series(para.text)
        para.text = correct_possessive_names(para.text, line_number)
        para.text = use_numerals_with_percent(para.text)
        para.text = remove_concluding_slashes_from_urls(para.text, line_number)
        para.text = clean_web_addresses(para.text)

        para.text = apply_abbreviation_mapping(para.text, abbreviation_dict, line_number)
        para.text = apply_number_abbreviation_rule(para.text, line_number)

        para.text = format_titles_us_english_with_logging(para.text, doc_id)
        para.text = units_with_bracket(para.text, doc_id)
        para.text = correct_units_in_ranges_with_logging(para.text,line_number)
        para.text = correct_scientific_units_with_logging(para.text,doc_id)
        para.text = replace_fold_phrases(para.text)
        para.text = correct_preposition_usage(para.text)
        para.text = correct_unit_spacing(para.text)
        para.text = apply_quotation_punctuation_rule(para.text)
        para.text = enforce_dnase_rule(para.text)
        
        para.text = correct_acronyms(para.text, line_number)
        para.text = enforce_am_pm(para.text, line_number)
        
        para.text = enforce_eg_rule_with_logging(para.text)
        para.text = enforce_ie_rule_with_logging(para.text)
        para.text = enforce_serial_comma(para.text)
        para.text = apply_remove_italics_see_rule(para.text)
        
        para.text = standardize_etc(para.text)
        para.text = process_url_add_http(para.text)
        para.text = process_url_remove_http(para.text)
        
        lines = para.text.split('\n')
        updated_lines = []
        for line in lines:
            corrected_line = convert_century(line, line_number)
            updated_lines.append(corrected_line)
            line_number += 1

        para.text = '\n'.join(updated_lines)
        formatted_runs = []
        
        # for run in para.runs:
        #     run_text = replace_curly_quotes_with_straight(run.text)
        #     run_text = insert_thin_space_between_number_and_unit(run_text, line_number)
            
        #     words = run_text.split()
        #     for i, word in enumerate(words):
        #         original_word = word
        #         punctuation = ""

        #         if word[-1] in ",.?!;\"'()[]{}":
        #             punctuation = word[-1]
        #             word = word[:-1]

        #         if (word.startswith('"') and word.endswith('"')) or (word.startswith("'") and word.endswith('"')):
        #             formatted_runs.append((word, None))
        #             if i < len(words) - 1:
        #                 formatted_runs.append((" ", None))
        #             continue

        #         word = remove_unnecessary_apostrophes(word, line_number)

        #         cleaned_word = clean_word(word)
        #         corrected_word = cleaned_word

        #         if cleaned_word:
        #             # corrected_word = correct_acronyms(cleaned_word, line_number)
        #             # corrected_word = enforce_am_pm(corrected_word, line_number)

        #             if corrected_word != cleaned_word:
        #                 formatted_runs.append((corrected_word + punctuation, RGBColor(0, 0, 0)))
        #             elif not us_dict.check(corrected_word.lower()):
        #                 formatted_runs.append((corrected_word + punctuation, RGBColor(255, 0, 0)))
        #             else:
        #                 formatted_runs.append((corrected_word + punctuation, None))
        #         else:
        #             formatted_runs.append((original_word + punctuation, None))

        #         if i < len(words) - 1:
        #             formatted_runs.append((" ", None))
        
        for run in para.runs:
            run_text = replace_curly_quotes_with_straight(run.text)
            run_text = insert_thin_space_between_number_and_unit(run_text, line_number)

            words = run_text.split()
            for i, word in enumerate(words):
                original_word = word
                punctuation = ""

                if word[-1] in ",.?!:;\"'()[]{}":
                    punctuation = word[-1]
                    word = word[:-1]

                if (word.startswith('"') and word.endswith('"')) or (word.startswith("'") and word.endswith("'")):
                    formatted_runs.append((original_word, None))
                    if i < len(words) - 1:
                        formatted_runs.append((" ", None))
                    continue

                if not word.strip():
                    formatted_runs.append((original_word, None))
                    if i < len(words) - 1:
                        formatted_runs.append((" ", None))
                    continue

                if not us_dict.check(word.lower()):
                    # Mark incorrect word in red
                    formatted_runs.append((original_word, RGBColor(255, 0, 0)))
                else:
                    # Keep correct word with no color
                    formatted_runs.append((original_word, None))

                # Add a space between words
                if i < len(words) - 1:
                    formatted_runs.append((" ", None))


        # Clear paragraph and rebuild runs
        para.clear()
        for text, color in formatted_runs:
            new_run = para.add_run(text)
            if color:
                new_run.font.color.rgb = color



def clean_word1(word):
    return ''.join(filter(str.isalnum, word)).lower()





# Helper function to extract text from docx file
def extract_text_from_docx(file_path):
    try:
        with open(file_path, "rb") as docx_file:
            result = mammoth.extract_raw_text(docx_file)
            return result.value
    except Exception as e:
        # logging.error(f"Error extracting text from file: {e}")
        return ""



@router.get("/process_us")
async def process_file(doc_id: int = Query(...)):
    try:
        # Connect to the database
        conn = get_db_connection()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection error")
        
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM row_document WHERE row_doc_id = %s", (doc_id,))
        rows = cursor.fetchone()

        if not rows:
            raise HTTPException(status_code=404, detail="Document not found")
        
        file_path = os.path.join(os.getcwd(), 'files', rows[1])

        # Verify the file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found on server")

        # Start time of processing
        start_time = datetime.now()

        # Extract raw text using Mammoth (you need your own extract_text_from_docx method)
        file_content = extract_text_from_docx(file_path)
        text = file_content

        # Prepare log data for spell checking
        global_logs.append(f"FileName: {rows[1]}\n\n")

        # Split text into lines and process each line for spelling errors
        lines = text.split('\n')
        for index, line in enumerate(lines):
            words = line.split()
            for word in words:
                cleaned = clean_word1(word)
                if cleaned and not us_dict.check(cleaned):
                    suggestions = us_dict.suggest(cleaned)
                    suggestion_text = (
                        f" Suggestions: {', '.join(suggestions)}"
                        if suggestions else " No suggestions available"
                    )
                    global_logs.append(f"Line {index}: {word} ->{suggestion_text}")

        # End time and time taken
        end_time = datetime.now()
        time_taken = round((end_time - start_time).total_seconds(), 2)
        time_log = f"\nStart Time: {start_time}\nEnd Time: {end_time}\nAnalysis completed in {time_taken} seconds.\n\n"

        # Prepend the time log to the existing log data
        global_logs.insert(0, time_log)

        # Define the log filename based on the document ID and name
        document_name = rows[1].replace('.docx', '')
        log_filename = f"log_main.txt"
        
        # Define output path for the log file inside a directory based on doc_id
        output_path_file = Path(os.getcwd()) / 'output' / str(doc_id) / log_filename
        dir_path = output_path_file.parent

        # Ensure the output directory exists
        dir_path.mkdir(parents=True, exist_ok=True)

        # try:
        #     # Read existing content of the log file if exists
        #     if output_path_file.exists():
        #         with open(output_path_file, "r", encoding="utf-8") as log_file:
        #             existing_content = log_file.read()
        #         with open(output_path_file, "w", encoding="utf-8") as log_file:
        #             log_file.write(''.join(global_logs) + existing_content)
        #     else:
        #         # If the file doesn't exist, create it with the new log data
        #         with open(output_path_file, "w", encoding="utf-8") as log_file:
        #             log_file.write(''.join(global_logs))

        # except FileNotFoundError:
        #     # If the log file does not exist at all, create a new one
        #     with open(output_path_file, "w", encoding="utf-8") as log_file:
        #         log_file.write(''.join(global_logs))


        output_dir = os.path.join("output", str(doc_id))
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, f"processed_{os.path.basename(file_path)}")

        doc = docx.Document(file_path)
        highlight_and_correct(doc,doc_id)
        doc.save(output_path)

        cursor.execute("SELECT final_doc_id FROM final_document WHERE row_doc_id = %s", (doc_id,))
        existing_rows = cursor.fetchall()

        if existing_rows:
            logging.info('File already processed in final_document. Skipping insert.')
        else:
            folder_url = f'/output/{doc_id}/'
            cursor.execute(
                '''INSERT INTO final_document (row_doc_id, user_id, final_doc_size, final_doc_url, status, creation_date)
                VALUES (%s, %s, %s, %s, %s, NOW())''',
                (doc_id, rows[1], rows[2], folder_url, rows[7])
            )
            logging.info('New file processed and inserted into final_document.')

        conn.commit()
        write_to_log(doc_id)
        logging.info(f"Processed file stored at: {output_path}")
        return {"success": True, "message": f"File processed and stored at {output_path}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


