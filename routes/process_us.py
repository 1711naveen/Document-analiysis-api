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
import roman  # For converting Roman numerals to Arabic numerals
from roman import fromRoman


router = APIRouter()

us_dict = enchant.Dict("en_US") #for US english
# uk_dict = enchant.Dict("en_GB") # for UK english

global_logs = []

def fetch_abbreviation_mappings():
    """Fetch abbreviation mappings from the database."""
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
    """
    Replace words in text based on abbreviation mappings and log changes.
    :param text: The input text.
    :param abbreviation_dict: Dictionary of abbreviations.
    :param line_number: Line number for logging.
    :return: Updated text with abbreviations applied.
    """
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



# Done
def replace_percent_with_symbol(text):
    """
    Replaces 'percent' or 'per cent' with '%' if preceded by a number and logs the changes.
    Log messages are stored in a global array and written to a file later.
    
    :param text: The text to process.
    :param doc_id: The document ID used to create the output folder.
    :return: The modified text.
    """
    global global_logs  # Access the global log array

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

# Done
def replace_curly_quotes_with_straight(text):
    return text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")



# def correct_acronyms(word):
#     if re.match(r"([a-z]\.){2,}[a-z]\.?", word):
#         return word.replace(".", "")
#     if re.match(r"([A-Z]\.){2,}[A-Z]\.?", word):
#         return word.replace(".", "")
#     return word


# Done
def correct_acronyms(word, line_number):
    """
    Removes periods from acronyms and logs the changes with line numbers.
    :param word: The word to process.
    :param line_number: The line number in the document for logging.
    :return: The updated word with corrected acronyms.
    """
    global global_logs  # Use a global log to record changes
    original_word = word  # Store the original word for logging

    if re.match(r"([a-z]\.){2,}[a-z]\.?", word):
        word = word.replace(".", "")
    elif re.match(r"([A-Z]\.){2,}[A-Z]\.?", word):
        word = word.replace(".", "")

    # Log the change if the word was modified
    if word != original_word:
        global_logs.append(
            f"[correct_acronyms] Line {line_number}: '{original_word}' -> '{word}'"
        )

    return word


# Done
def enforce_am_pm(word, line_num):
    """
    Enforces the proper AM/PM format and logs the changes.
    
    :param word: The word to check and correct.
    :param line_num: The line number for logging purposes.
    :return: The corrected word.
    """
    word_lower = word.lower()
    global global_logs  # Access the global log array
    if word_lower in {"am", "a.m", "pm", "p.m"}:
        if "a" in word_lower:
            corrected_word = "a.m."
            global_logs.append(f"[am pm change] Line {line_num}: {word} -> {corrected_word}")
            return corrected_word
        elif "p" in word_lower:
            corrected_word = "p.m."
            global_logs.append(f"[am pm change] Line {line_num}: {word} -> {corrected_word}")
            return corrected_word
    return word


# Done
# [apostrophes change] : 60's -> 1960s 
def remove_unnecessary_apostrophes(word, line_num):
    """
    Removes unnecessary apostrophes from the word and logs the changes.
    :param word: The word to check and modify.
    :param line_num: The line number for logging purposes.
    :return: The modified word.
    """
    original_word = word  # Store the original word for comparison
    global global_logs  # Access the global log array
    word = re.sub(r"(\d{4})'s\b", r"\1s", word)
    word = re.sub(r"'(\d{2})s\b", r"\1s", word)
    word = re.sub(r"(\d{4}s)'\b", r"\1", word)
    word = re.sub(r"(\d+)'(s|st|nd|rd|th)\b", r"\1\2", word)
    word = re.sub(r"^(\d{2})s\b", r"19\1s", word)
    
    # If the word has changed, log the change
    if word != original_word:
        global_logs.append(f"[apostrophes change] Line {line_num}: {original_word} -> {word}")
    
    return word



# def spell_out_number_and_unit(sentence):
#     match = re.match(r"^(\d+)\s+([a-zA-Z]+)", sentence)
#     if match:
#         number = int(match.group(1))
#         unit = match.group(2)
#         number_word = num2words(number, to="cardinal")
#         unit_word = unit.lower() if unit.lower()[-1] == 's' else unit.lower() + "s"
#         return f"{number_word.capitalize()} {unit_word}{sentence[len(match.group(0)):]}"
#     return sentence


# pending not clear
# Spell out numbers below 10 unless used in conjunction with a unit of measurement in the text(2.15)
def spell_out_number_and_unit_with_rules(sentence, line_number):
    """
    Converts numbers to words following specific rules:
    - Spell out numbers below 10 unless used in conjunction with a unit of measurement.
    - Use numerals for numbers 10 and above.
    - Ensure consistency when a sentence contains both numerals and spelled-out numbers.
    
    :param sentence: The input sentence to process.
    :param line_number: The line number in the document for logging.
    :return: The updated sentence with numbers correctly formatted.
    """
    global global_logs  # Use a global log to record changes
    original_sentence = sentence  # Store the original sentence for comparison

    # Regex patterns
    unit_pattern = r"(\d+)\s+([a-zA-Z]+)"
    number_pattern = r"\b(\d+)\b"

    # Check if the sentence contains any units (e.g., kg, hours, months) 
    contains_unit = bool(re.search(unit_pattern, sentence))

    # If the sentence contains any units, do not spell out numbers in those cases
    if contains_unit:
        # Handle units: numbers remain as numerals
        sentence = re.sub(r"(\d+)\s+([a-zA-Z]+)", lambda m: f"{m.group(1)} {m.group(2)}", sentence)
    else:
        # Spell out numbers below 10 (unless part of a unit)
        sentence = re.sub(number_pattern, lambda m: num2words(int(m.group(0)), to="cardinal") if int(m.group(0)) < 10 else m.group(0), sentence)

    # Check for mixed sentences: when the sentence contains both spelled-out and numeric numbers, we use numerals for consistency
    if bool(re.search(r"\b[a-zA-Z]+\b", sentence)) and bool(re.search(r"\b\d+\b", sentence)):
        sentence = re.sub(r"\b([a-zA-Z]+)\b", lambda m: str(num2words(m.group(0), to="cardinal")) if m.group(0).isdigit() else m.group(0), sentence)

    # Log the change (if any)
    if sentence != original_sentence:
        global_logs.append(f"[spell_out_number_and_unit_with_rules] Line {line_number}: '{original_sentence}' -> '{sentence}'")

    return sentence




# 5% not five percent or 5 percent
def use_numerals_with_percent(text):
    """
    Converts spelled-out numbers with 'percent' or 'per cent' into numerals followed by '%'.
    Logs the changes (only the changed words) to a global array for writing later.

    :param text: The text to process.
    :param doc_id: The document ID used for logging purposes.
    :return: The modified text.
    """

    global global_logs  # Access the global log array

    lines = text.splitlines()
    modified_text = []

    for line_number, line in enumerate(lines, 1):
        original_line = line  # Keep the original line for comparison
        modified_line = line  # Start with the original line, apply changes below

        # Convert spelled-out numbers to numerals followed by '%'
        def replace_spelled_out_percent(match):
            word = match.group(1)
            num = w2n.word_to_num(word)
            modified = f"{num}%"
            # Log the change to the global array
            global_logs.append(
                f"[numerals with percent] Line {line_number}: {word} percent -> {modified}"
            )
            return modified

        modified_line = re.sub(
            r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)\s?(percent|per cent)",
            replace_spelled_out_percent,
            modified_line,
            flags=re.IGNORECASE,
        )

        # Replace numeral with 'percent' or 'per cent' to numerals with '%'
        def replace_numerical_percent(match):
            number = match.group(1)
            modified = f"{number}%"
            # Log the change to the global array
            global_logs.append(
                f"[numerals with percent] Line {line_number}: {match.group(0)} -> {modified}"
            )
            return modified

        modified_line = re.sub(
            r"(\d+)\s?(percent|per cent)", replace_numerical_percent, modified_line, flags=re.IGNORECASE
        )

        # Add the modified line to the final text
        modified_text.append(modified_line)

    # Return the modified text
    return "\n".join(modified_text)


def adjust_ratios(text):
    print("In function")
    # print(text)
    print(re.sub(r"(\d)\s*:\s*(\d)", r"\1 : \2", text))
    return re.sub(r"(\d)\s*:\s*(\d)", r"\1 : \2", text)

def correct_chapter_numbering(text, chapter_counter):
    # Pattern to match chapter headings
    chapter_pattern = re.compile(r"(?i)\bchapter\s+((?:[IVXLCDM]+)|(?:[a-z]+)|(?:\d+))[:.]?\s")

    def replace_chapter_heading(match):
        """
        Replace matched chapter heading with sequential numbering.
        """
        chapter_counter[0] += 1  # Increment the shared counter
        return f"Chapter {chapter_counter[0]}: "

    # Apply the substitution across the text
    return chapter_pattern.sub(replace_chapter_heading, text)




# uncommet it later for point 
# def correct_scientific_unit_symbols(text):
#     """
#     Removes incorrect plural forms, apostrophes, or periods from scientific unit symbols.
#     Ensures unit symbols like 'kg', 'm', 'L', etc., are used properly.

#     :param text: The text to process.
#     :return: The modified text.
#     """
#     # List of common scientific unit symbols
#     units = [
#         "kg", "g", "mg", "L", "ml", "m", "cm", "mm", "km", "s", "min", "h", "A", 
#         "mol", "cd", "K", "Pa", "N", "J", "W", "C", "V", "Ω", "Hz", "Bq", "Gy", "Sv", "lx", "lm"
#     ]
#     # Create regex pattern for units followed by invalid characters
#     pattern = r"\b(\d+)\s?(" + "|".join(units) + r")['s.]?\b"
#     # Replace invalid forms with correct form
#     return re.sub(pattern, r"\1 \2", text)



# Done
# [insert_thin_space_between_number_and_unit] Line 31: '5kg' -> '5 kg'
def insert_thin_space_between_number_and_unit(text, line_number):
    """
    Inserts a thin space between numbers and units in the text and logs the changes.
    
    :param text: The input text to process.
    :param line_number: The line number in the document for logging.
    :return: The updated text with thin spaces inserted.
    """
    global global_logs  # Use a global log to record changes
    original_text = text  # Store the original text for comparison
    thin_space = '\u2009'

    pattern = r"(\d+)(?=\s?[a-zA-Z]+)(?!\s?°)"

    updated_text = text  # Initialize updated text to the original

    matches = re.finditer(pattern, text)
    for match in matches:
        number = match.group(1)  # This is the number
        unit_start = match.end()
        unit = text[unit_start:].split()[0]  # The unit is the first word after the number
        
        original_word = number + unit
        updated_word = number + thin_space + unit  # Insert thin space between number and unit

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
    """
    Formats dates in the text and logs the changes with line numbers.
    
    :param text: The text to format.
    :param line_number: The line number in the document for logging.
    :return: The updated text with formatted dates.
    """
    global global_logs  # Use a global log to store changes

    def log_and_replace(pattern, replacement, text):
        # This helper function logs and performs replacements
        def replacer(match):
            original = match.group(0)
            updated = replacement(match)
            if original != updated:
                global_logs.append(
                    f"[format_dates] Line {line_number}: '{original}' -> '{updated}'"
                )
            return updated
        
        return re.sub(pattern, replacer, text)

    # Pattern and replacement rules
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



# def remove_space_between_degree_and_direction(text):
# return re.sub(r"(\d+) °\s?(N|S|E|W)\b", r"\1°\2", text)


# Done
# [remove_space_between_degree_and_direction] Line 10: '52 °N' -> '52°N'
def remove_space_between_degree_and_direction(text, line_number):
    """
    Removes the space between the degree symbol and direction (N/S/E/W) and logs the changes.
    
    :param text: The input text to process.
    :param line_number: The line number in the document for logging.
    :return: The updated text with the space removed.
    """
    global global_logs  # Use a global log to record changes
    
    # Regular expression to match a degree symbol followed by a space and direction (N/S/E/W)
    pattern = r"(\d+) °\s?(N|S|E|W)\b"
    
    # Use re.sub with a callback function to log the changes
    def log_replacement(match):
        original_text = match.group(0)  # Full match (e.g., "20 °N")
        updated_text = match.group(1) + "°" + match.group(2)  # Remove the space and combine number + degree + direction
        global_logs.append(
            f"[remove_space_between_degree_and_direction] Line {line_number}: '{original_text}' -> '{updated_text}'"
        )
        return updated_text
    
    # Apply the replacement using the callback function
    updated_text = re.sub(pattern, log_replacement, text)
    
    return updated_text


# Done
# km not Km; kg not Kg; l not L. (2.9)
def enforce_lowercase_units(text, line_number):
    """
    Enforces lowercase for specific units and logs the changes.
    
    - 'K' followed by 'm' or 'g' is converted to 'k' (e.g., '1 K m' becomes '1 k m').
    - 'L' is converted to lowercase 'l' wherever it appears as a standalone word.
    - Additional units like 'G', 'M', 'T', 'L' (liter), 'kg', 'mg', 'g', 'h', 'min', 's', 'cm' are handled.
    
    :param text: The input text to process.
    :param line_number: The line number in the document for logging.
    :return: The updated text with enforced lowercase for applicable units.
    """
    global global_logs  # Use a global log to record changes
    
    # Regular expressions for finding and replacing uppercase units
    updated_text = text
    
    # Units to replace: 'K' followed by 'm' or 'g', and standalone 'L'
    unit_patterns = [
        (r"(\d) K([mg])", 'K', 'k'),  # 'K' -> 'k' for 'kg', 'mg'
        (r"(\d) G([m])", 'G', 'g'),  # 'G' -> 'g'
        (r"(\d) M([g])", 'M', 'm'),  # 'M' -> 'm'
        (r"(\d) T([g])", 'T', 't'),  # 'T' -> 't'
        (r"\bL\b", 'L', 'l')  # 'L' -> 'l' (standalone)
    ]
    
    # Process each unit replacement
    for pattern, original, updated in unit_patterns:
        matches = re.finditer(pattern, updated_text)
        
        for match in matches:
            original_text = match.group(0)
            updated_text = updated_text.replace(original_text, original_text.replace(original, updated))
            
            # Log the change
            global_logs.append(
                f"[enforce_lowercase_units] Line {line_number}: '{original_text}' -> '{original_text.replace(original, updated)}'"
            )
    
    # Additional unit patterns for mass, volume, time, etc.
    additional_units = [
        (r"(\d) (kg|mg|g|cm)", 'K', 'k'),  # For mass units like kg, mg, g
        (r"(\d) (h|min|s)", 'H', 'h'),  # For time units like h, min, s
        (r"(\d) l", 'L', 'l'),  # For volume units like liter (l)
    ]
    
    for pattern, original, updated in additional_units:
        matches = re.finditer(pattern, updated_text)
        
        for match in matches:
            original_text = match.group(0)
            updated_text = updated_text.replace(original_text, original_text.replace(original, updated))
            
            # Log the change
            global_logs.append(
                f"[enforce_lowercase_units] Line {line_number}: '{original_text}' -> '{original_text.replace(original, updated)}'"
            )
    
    return updated_text




# def precede_decimal_with_zero(text):
#     # Matches standalone decimal numbers below 1, e.g., ".75" or " .5", but not parts of larger numbers.
#     text = re.sub(r"(?<!\d)(?<!\d\.)\.(\d+)", r"0.\1", text)
#     return text



# Done
# [precede_decimal_with_zero] Line 22: '.76' -> '0.76'
def precede_decimal_with_zero(text, line_number):
    global global_logs  # Use a global log to record changes
    
    # Regular expression to match decimal numbers below 1 (e.g., .75, .5)
    pattern = r"(?<!\d)(?<!\d\.)\.(\d+)"
    
    # Function to log the replacement and modify the text
    def log_replacement(match):
        original_text = match.group(0)  # The original match (e.g., ".75")
        updated_text = "0." + match.group(1)  # Precede with zero (e.g., "0.75")
        global_logs.append(
            f"[precede_decimal_with_zero] Line {line_number}: '{original_text}' -> '{updated_text}'"
        )
        return updated_text
    
    # Apply the replacement using the callback function
    updated_text = re.sub(pattern, log_replacement, text)
    return updated_text


# Done
def adjust_terminal_punctuation_in_quotes(text):
    # Matches quoted matter ending with a question or exclamation mark, ensuring punctuation is inside the quotes.
    text = re.sub(
        r"([‘“])([^’”]*[?!])([’”])\.",
        r"\1\2\3",
        text
    )
    return text


# def correct_possessive_names(text):
#     # Handles singular possessives for names ending in 's'
#     text = re.sub(r"\b([A-Za-z]+s)\b(?<!\bs')'", r"\1's", text)  # Add 's' for singular possessives
#     text = re.sub(r"\b([A-Za-z]+s)'\b", r"\1'", text)  # Retain just the apostrophe for plurals
#     return text


# Done
# [correct_possessive_names] Line 31: 'States'' -> 'States's'
def correct_possessive_names(text, line_number):
    """
    Corrects possessive forms for names ending in 's' and logs the changes.
    
    - Adds 's for singular possessive forms (e.g., "James" -> "James's").
    - Retains just the apostrophe for plural possessive forms (e.g., "James'" remains "James'").
    
    :param text: The input text to process.
    :param line_number: The line number in the document for logging.
    :return: The updated text with corrected possessive names.
    """
    global global_logs  # Use a global log to record changes
    
    # Regular expression for handling singular possessive names (e.g., James -> James's)
    pattern_singular_possessive = r"\b([A-Za-z]+s)\b(?<!\bs')'"
    matches_singular = re.finditer(pattern_singular_possessive, text)
    updated_text = text
    
    # Process singular possessives and log changes
    for match in matches_singular:
        original_text = match.group(0)  # e.g., "James'"
        updated_text_singular = match.group(1) + "'s"  # Convert to singular possessive form
        updated_text = updated_text.replace(original_text, updated_text_singular)
        
        # Log the change
        global_logs.append(
            f"[correct_possessive_names] Line {line_number}: '{original_text}' -> '{updated_text_singular}'"
        )
    
    # Regular expression for handling plural possessive names (e.g., James' -> James')
    pattern_plural_possessive = r"\b([A-Za-z]+s)'\b"
    matches_plural = re.finditer(pattern_plural_possessive, updated_text)
    
    # Process plural possessives and log changes
    for match in matches_plural:
        original_text = match.group(0)  # e.g., "James'"
        updated_text_plural = match.group(1) + "'"  # Retain just the apostrophe
        updated_text = updated_text.replace(original_text, updated_text_plural)
        
        # Log the change
        global_logs.append(
            f"[correct_possessive_names] Line {line_number}: '{original_text}' -> '{updated_text_plural}'"
        )
    
    return updated_text




# Done
# http://www.PHi.com/authorguidelines not http://www.PHi.com/authorguidelines/
def remove_concluding_slashes_from_urls(text, line_number):
    """
    Removes concluding slashes from URLs (except when followed by other characters, like periods) and logs the changes.
    
    :param text: The input text to process.
    :param line_number: The line number in the document for logging.
    :return: The updated text with concluding slashes removed from URLs.
    """
    global global_logs  # Use a global log to record changes
    
    # Regular expression for matching URLs ending with a slash
    pattern = r"(https?://[^\s/]+(?:/[^\s/]+)*)/"
    matches = re.finditer(pattern, text)
    updated_text = text
    
    # Process and log changes for each URL
    for match in matches:
        original_text = match.group(0)  # The original URL (e.g., "https://example.com/")
        updated_text_url = match.group(1)  # URL without the concluding slash (e.g., "https://example.com")
        updated_text = updated_text.replace(original_text, updated_text_url)
        
        # Log the change
        global_logs.append(
            f"[remove_concluding_slashes_from_urls] Line {line_number}: '{original_text}' -> '{updated_text_url}'"
        )
    
    return updated_text



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
        chapter_title = match.group(2).rstrip('.')  # Remove trailing period
        words = chapter_title.split()
        formatted_title = " ".join([
            word.capitalize() if i == 0 or len(word) >= 5 else word.lower()
            for i, word in enumerate(words)
        ])
        return f"{chapter_number}. {formatted_title}"
    return text




def format_titles_us_english_with_logging(text, doc_id):
    """
    Formats titles in US English and logs changes to a global array for writing later.

    :param text: The text to process.
    :param doc_id: The document ID for logging purposes.
    :return: The modified text.
    """

    global global_logs  # Access the global log array

    # Titles to be replaced
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
    
    # Process each line and check for title changes
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



def process_text_with_logging(text, doc_id):
    """
    Replaces unit abbreviations with their full forms and lowercase abbreviations in parentheses,
    and logs the changes with the exact format: 'Line X: s -> seconds (s)'.
    
    :param text: The input text to process.
    :param doc_id: Document identifier (for additional context if needed).
    :return: The processed text with replaced units and updated logs.
    """
    # Units and their full forms
    units = {
        "s": "second",
        "m": "meter",
        "kg": "kilogram",
        "A": "ampere",
        "K": "kelvin",
        "mol": "mole",
        "cd": "candela"
    }

    # Track used units
    used_units = set()
    global global_logs  # Use global logs to record changes

    # Process each line and track line numbers
    processed_lines = []
    for line_num, line in enumerate(text.splitlines(), start=1):
        # Function to replace units
        def replace_unit(match):
            unit = match.group(0)
            if unit in used_units:
                return unit  # Replace with just the unit abbreviation
            else:
                used_units.add(unit)
                full_form = units[unit]

                if unit != "mol" and not full_form.endswith("s"):
                    full_form += "s"
                replacement = f"{full_form} ({unit.lower()})"
                global_logs.append(
                    f"Line {line_num}: {unit} -> {replacement}"
                )

                return replacement

        # Create a regex pattern for the units
        pattern = r'\b(' + '|'.join(re.escape(unit) for unit in units.keys()) + r')\b'
        
        # Replace units in the line
        processed_line = re.sub(pattern, replace_unit, line)
        processed_lines.append(processed_line)

    # Return the processed text
    return "\n".join(processed_lines)




def write_to_log(doc_id):
    """
    Writes accumulated log messages from the global log array to a file.

    :param doc_id: The document ID used to create the output folder and file.
    """
    global global_logs  # Access the global log array

    output_dir = os.path.join('output', str(doc_id))
    os.makedirs(output_dir, exist_ok=True)
    log_file_path = os.path.join(output_dir, 'global_logs.txt')

    # Write the global log messages to the file
    with open(log_file_path, 'w', encoding='utf-8') as log_file:
        log_file.write("\n".join(global_logs))

    # Clear the global log array after writing
    global_logs = []


def highlight_and_correct(doc, doc_id):
    chapter_counter = [0]
    line_number = 1
    abbreviation_dict = fetch_abbreviation_mappings()
    for para in doc.paragraphs:
        # Process paragraph-level corrections
        if para.text.strip().startswith("Chapter"):
            para.text = correct_chapter_numbering(para.text, chapter_counter)
            formatted_title = format_chapter_title(para.text)
            para.text = formatted_title 

        para.text = adjust_ratios(para.text)
        para.text = format_dates(para.text, line_number)
        # para.text = spell_out_number_and_unit(para.text,line_number)
        # para.text = spell_out_number_and_unit_with_rules(para.text,line_number)
        para.text = remove_space_between_degree_and_direction(para.text, line_number)
        para.text = enforce_lowercase_units(para.text, line_number)
        para.text = precede_decimal_with_zero(para.text, line_number)
        para.text = format_ellipses_in_series(para.text)  # New rule added here
        para.text = correct_possessive_names(para.text, line_number)
        para.text = use_numerals_with_percent(para.text)
        para.text = replace_percent_with_symbol(para.text)
        para.text = remove_concluding_slashes_from_urls(para.text, line_number)
        para.text = clean_web_addresses(para.text)

        # Apply the new abbreviation and number abbreviation rules
        para.text = apply_abbreviation_mapping(para.text, abbreviation_dict, line_number)
        para.text = apply_number_abbreviation_rule(para.text, line_number)

        para.text = format_titles_us_english_with_logging(para.text, doc_id)
        para.text = process_text_with_logging(para.text, doc_id)

        lines = para.text.split('\n')
        updated_lines = []
        for line in lines:
            corrected_line = convert_century(line, line_number)
            updated_lines.append(corrected_line)
            line_number += 1

        para.text = '\n'.join(updated_lines)
        formatted_runs = []
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

                if (word.startswith('"') and word.endswith('"')) or (word.startswith("'") and word.endswith('"')):
                    formatted_runs.append((word, None))
                    if i < len(words) - 1:
                        formatted_runs.append((" ", None))
                    continue

                word = remove_unnecessary_apostrophes(word, line_number)

                cleaned_word = clean_word(word)
                corrected_word = cleaned_word

                if cleaned_word:
                    corrected_word = correct_acronyms(cleaned_word, line_number)
                    corrected_word = enforce_am_pm(corrected_word, line_number)

                    if corrected_word != cleaned_word:
                        formatted_runs.append((corrected_word + punctuation, RGBColor(0, 0, 0)))
                    elif not us_dict.check(corrected_word.lower()):
                        formatted_runs.append((corrected_word + punctuation, RGBColor(255, 0, 0)))
                    else:
                        formatted_runs.append((corrected_word + punctuation, None))
                else:
                    formatted_runs.append((original_word + punctuation, None))

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


        # Process the document and save it with corrections
        output_dir = os.path.join("output", str(doc_id))  # Folder based on doc_id
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, f"processed_{os.path.basename(file_path)}")

        doc = docx.Document(file_path)
        highlight_and_correct(doc,doc_id)
        doc.save(output_path)

        # Save document metadata to the database if not already processed
        cursor.execute("SELECT final_doc_id FROM final_document WHERE row_doc_id = %s", (doc_id,))
        existing_rows = cursor.fetchall()

        if existing_rows:
            logging.info('File already processed in final_document. Skipping insert.')
        else:
            # Insert new record into final_document table
            folder_url = f'/output/{doc_id}/'
            cursor.execute(
                '''INSERT INTO final_document (row_doc_id, user_id, final_doc_size, final_doc_url, status, creation_date)
                VALUES (%s, %s, %s, %s, %s, NOW())''',
                (doc_id, rows[1], rows[2], folder_url, rows[7])
            )
            logging.info('New file processed and inserted into final_document.')

        # Commit changes to the database
        conn.commit()
        # Write logs to file after processing the document
        write_to_log(doc_id)

        # Log the success message and return the response
        logging.info(f"Processed file stored at: {output_path}")
        return {"success": True, "message": f"File processed and stored at {output_path}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



