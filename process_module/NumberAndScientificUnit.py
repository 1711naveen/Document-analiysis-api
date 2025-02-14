import re
from docx import Document
from num2words import num2words
from word2number import w2n
import os
from datetime import datetime
from pathlib import Path

global_logs = []


def remove_unnecessary_apostrophes(runs, line_number):
    """
    Removes unnecessary apostrophes while preserving formatting.
    Args:
        runs (list): List of Word paragraph runs to preserve formatting.
        line_number (int): Line number for logging.
    """
    global global_logs
    full_text = "".join(run.text for run in runs)
    
    # Define replacement rules
    replacement_patterns = [
        (r"(\d{4})'s\b", r"\1s"),      # 1990's → 1990s
        (r"'(\d{2})s\b", r"\1s"),      # '90s → 90s
        (r"(\d{4}s)'\b", r"\1"),       # 1990s' → 1990s
        (r"(\d+)'(s|st|nd|rd|th)\b", r"\1\2"),  # 1'st → 1st, 2'nd → 2nd
        (r"^(\d{2})s\b", r"19\1s")     # 90s → 1990s
    ]

    # Apply each regex replacement
    updated_text = full_text
    for pattern, replacement in replacement_patterns:
        updated_text = re.sub(pattern, replacement, updated_text)
    if updated_text != full_text:
        global_logs.append(f"[apostrophes change] Line {line_number}: '{full_text}' -> '{updated_text}'")
    current_index = 0
    for run in runs:
        run.text = updated_text[current_index : current_index + len(run.text)]
        current_index += len(run.text)



# twofold not two-fold hyphenate with numeral for numbers greater than nine, e.g. 10-fold. 
def replace_fold_phrases(runs, line_number):
    """
    Replaces phrases with '-fold' to ensure correct formatting based on the number preceding it.
    Args:
        runs (list): List of Word paragraph runs to preserve formatting.
        line_number (int): Line number for logging.
    """
    global global_logs

    # Extract full text from runs
    full_text = "".join(run.text for run in runs)

    def process_fold(match):
        original = match.group(0)
        num_str = match.group(1)
        separator = match.group(2)

        # Ensure we only modify correctly formatted fold phrases
        if separator != "-":
            return original

        try:
            # Convert number string to integer
            if num_str.isdigit():
                number = int(num_str)
            else:
                number = w2n.word_to_num(num_str)

            # Apply formatting rules
            if number > 9:
                modified = f"{number}-fold"
            else:
                modified = f"{num2words(number)}fold"

            if original != modified:
                global_logs.append(
                    f"[replace_fold_phrases] Line {line_number}: '{original}' -> '{modified}'"
                )
            return modified
        except ValueError:
            return original

    # Regex pattern to find fold phrases
    pattern = r"(\b\w+\b)(-?)fold"
    updated_text = re.sub(pattern, process_fold, full_text)

    # Update runs while keeping formatting intact
    current_index = 0
    for run in runs:
        run.text = updated_text[current_index : current_index + len(run.text)]
        current_index += len(run.text)




# [remove_space_between_degree_and_direction] Line 10: '52 °N' -> '52°N'
def remove_space_between_degree_and_direction(runs, line_number):
    """
    Removes spaces between the degree symbol (º or °) and directional letters (N, S, E, W).
    Args:
        runs (list): List of Word paragraph runs to preserve formatting.
        line_number (int): Line number for logging.
    """
    global global_logs
    full_text = "".join(run.text for run in runs)

    def log_replacement(match):
        original_text = match.group(0)
        updated_text = match.group(1) + "°" + match.group(2)  # Ensuring ° is used consistently
        global_logs.append(
            f"[remove_space_between_degree_and_direction] Line {line_number}: '{original_text}' -> '{updated_text}'"
        )
        return updated_text

    # Regex pattern to match cases like "30 ° N" or "45º  S"
    pattern = r"(\d+)\s*[º°]\s*(N|S|E|W)\b"
    updated_text = re.sub(pattern, log_replacement, full_text)
    current_index = 0
    for run in runs:
        run.text = updated_text[current_index : current_index + len(run.text)]
        current_index += len(run.text)




# km not Km; kg not Kg; l not L. (2.9)
def enforce_lowercase_units(runs, line_number):
    """
    Ensures units like Km, L, Gm, etc., are correctly formatted in lowercase.
    Args:
        runs (list): List of Word paragraph runs to preserve formatting.
        line_number (int): Line number for logging.
    """
    global global_logs

    # Extract full text from runs
    full_text = "".join(run.text for run in runs)

    # Define patterns for incorrect unit capitalization
    unit_patterns = [
        (r"(\d+)\s*(K)(m|g|l)", 'K', 'k'),
        (r"(\d+)\s*(G)(m)", 'G', 'g'),
        (r"(\d+)\s*(M)(g)", 'M', 'm'),
        (r"(\d+)\s*(T)(g)", 'T', 't'),
        (r"(\d+)\s*(L)\b", 'L', 'l'),
        (r"(\d+)\s*(M)\b", 'M', 'm'),
        # (r"(\d+)\s*(kg|mg|g|cm|m|km|l|s|h|min)", r"\1 \2", None)
    ]

    # Apply patterns
    def process_match(match, original, updated):
        original_text = match.group(0)
        if updated is not None:
            corrected_text = original_text.replace(original, updated)
        else:
            corrected_text = f"{match.group(1)} {match.group(2)}"
        
        if original_text != corrected_text:
            global_logs.append(
                f"[enforce_lowercase_units] Line {line_number}: '{original_text}' -> '{corrected_text}'"
            )
        return corrected_text

    updated_text = full_text
    for pattern, original, updated in unit_patterns:
        updated_text = re.sub(pattern, lambda match: process_match(match, original, updated), updated_text)

    # Update runs while keeping formatting intact
    current_index = 0
    for run in runs:
        run.text = updated_text[current_index : current_index + len(run.text)]
        current_index += len(run.text)




# Done
# [precede_decimal_with_zero] Line 22: '.76' -> '0.76'
def precede_decimal_with_zero(runs, line_number):
    """
    Ensures that decimals without leading zeros are preceded by '0' (e.g., '.5' → '0.5').
    Args:
        runs (list): List of Word paragraph runs to preserve formatting.
        line_number (int): Line number for logging.
    """
    global global_logs

    # Extract full text from runs
    full_text = "".join(run.text for run in runs)

    # Regex pattern for decimals missing leading zeros
    pattern = r"(?<!\d)(?<!\d\.)\.(\d+)"

    def process_match(match):
        original_text = match.group(0)
        corrected_text = "0." + match.group(1)

        global_logs.append(
            f"[precede_decimal_with_zero] Line {line_number}: '{original_text}' -> '{corrected_text}'"
        )
        return corrected_text

    # Apply transformation
    updated_text = re.sub(pattern, process_match, full_text)

    # Update runs while keeping formatting intact
    current_index = 0
    for run in runs:
        run.text = updated_text[current_index : current_index + len(run.text)]
        current_index += len(run.text)



def adjust_ratios(runs, line_number):
    """
    Ensures proper formatting of ratios with spaces around the colon (e.g., "1:2" → "1 : 2").
    Args:
        runs (list): List of Word paragraph runs to preserve formatting.
        line_number (int): Line number for logging.
    """
    global global_logs
    full_text = "".join(run.text for run in runs)

    # Regex pattern for improperly formatted ratios
    pattern = r"(\d)\s*:\s*(\d)"

    def process_match(match):
        original_text = match.group(0)
        corrected_text = f"{match.group(1)} : {match.group(2)}"
        global_logs.append(
            f"[adjust_ratios] Line {line_number}: '{original_text}' -> '{corrected_text}'"
        )
        return corrected_text
    updated_text = re.sub(pattern, process_match, full_text)

    # Update runs while keeping formatting intact
    current_index = 0
    for run in runs:
        run.text = updated_text[current_index : current_index + len(run.text)]
        current_index += len(run.text)




def remove_commas_from_numbers(runs, line_number):
    """
    Removes commas from numerical values in the runs of a paragraph.
    Updates the global_log with the specific changes, including line number and changes made.
    """
    global global_logs
    pattern = r'\b\d{1,3}(,\d{3})+\b'

    def replacer(match):
        original_number = match.group(0)
        updated_number = original_number.replace(",", " ")
        changes.append((original_number, updated_number))
        return updated_number

    # Iterate through each run in the paragraph
    for run in runs:
        original_text = run.text
        changes = []

        # Replace numbers with commas in the run's text
        updated_text = re.sub(pattern, replacer, original_text)

        # Update the run's text if changes were made
        if updated_text != original_text:
            run.text = updated_text

        # Log individual changes
        for original, updated in changes:
            global_logs.append(
                f"[process_symbols_in_doc] Line {line_number}: '{original}' -> '{updated}'"
            )


def remove_spaces_from_four_digit_numbers(runs, line_number):
    """
    Removes spaces from four-digit numerals in the runs of a paragraph.
    Updates the global_log with specific changes, including line number and changes made.
    """
    global global_logs
    pattern = r'\b\d\s\d{3}\b'

    def replacer(match):
        original_number = match.group(0)  # Match the original number
        updated_number = original_number.replace(" ", "")  # Remove spaces
        changes.append((original_number, updated_number))  # Log the change
        return updated_number

    # Iterate through each run in the paragraph
    for run in runs:
        original_text = run.text
        changes = []

        # Replace four-digit numbers with spaces in the run's text
        updated_text = re.sub(pattern, replacer, original_text)

        # Update the run's text if changes were made
        if updated_text != original_text:
            run.text = updated_text

        # Log individual changes
        for original, updated in changes:
            global_logs.append(
                f"[process_symbols_in_doc] Line {line_number}: '{original}' -> '{updated}'"
            )



def convert_decimal_to_baseline(runs, line_number):
    """
    Converts any non-standard decimal separator (•) to a standard decimal point (.)
    only when both sides are numeric, in the runs of a paragraph.
    Logs the changes to the global_log, including line number and the change.
    """
    global global_logs
    # Regular expression to find '•' between numbers
    pattern = r'(?<=\d)\xB7(?=\d)'
    
    # Iterate through each run in the paragraph
    for run in runs:
        original_text = run.text
        changes = []

        # Find all occurrences of '•' that are between digits and replace with '.'
        updated_text = re.sub(pattern, '.', original_text)

        # Update the run's text if changes were made
        if updated_text != original_text:
            run.text = updated_text
            changes.append((original_text, updated_text))

        # Log individual changes
        for original, updated in changes:
            global_logs.append(
                f"[convert_decimal_to_baseline] Line {line_number}: '{original}' -> '{updated}'"
            )


def correct_scientific_unit_symbols(runs):
    """
    Ensures proper capitalization of units derived from proper names (e.g., J, Hz, W, N) only when preceded by a number.
    Processes each run in a paragraph and updates the text accordingly.
    Logs the changes to the global_log.
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
        "t": "T",
        "ohm": "Ω",
        "s": "S",
        "k": "K",
    }

    def process_unit(match):
        original = match.group(0)
        unit = match.group(2).lower()
        modified = f"{match.group(1)} {units.get(unit, match.group(2))}"
        if original != modified:
            global_logs.append(
                f"[correct_scientific_unit_symbols] '{original}' -> '{modified}'"
            )
        return modified

    # Create a regex pattern to match numbers followed by units
    # pattern = r"\b(\d+\s*)(%s)\b" % "|".join(re.escape(unit) for unit in units.keys())
    pattern = r"\b(\d+)\s+(%s)\b" % "|".join(re.escape(unit) for unit in units.keys())


    # Iterate through each run in the paragraph
    for run in runs:
        original_text = run.text

        # Replace incorrect unit symbols in the run's text
        updated_text = re.sub(pattern, process_unit, original_text, flags=re.IGNORECASE)

        # Update the run's text if changes were made
        if updated_text != original_text:
            run.text = updated_text



# Spell out numbers below 10 unless used in conjunction with a unit of measurement in the text(2.15)
# now working because it is converting number to words
def spell_out_number_and_unit_with_rules(runs, line_number):
    global global_logs
    unit_pattern = r"(\d+)\s+([a-zA-Z]+)"
    number_pattern = r"\b(\d+)\b"
    
    for run in runs:
        original_text = run.text
        words = original_text.split()
        modified_words = words[:]
        
        for i, word in enumerate(words):
             
            if re.match(unit_pattern, " ".join(words[i:i+2])):
                continue  # Skip since it's already formatted correctly
             
            if re.match(number_pattern, word):
                try:
                    number = int(word)
                    if number < 10:
                        modified_words[i] = num2words(number, to="cardinal")
                except ValueError:
                    # If it's not a valid number, just continue without modifying
                    continue
        
        modified_text = " ".join(modified_words)
        if original_text != modified_text:
            global_logs.append(f"[spell_out_number_and_unit_with_rules] Line {line_number}: '{original_text}' -> '{modified_text}'")
            run.text = modified_text



# Done
# [format_dates] Line 5: '386 BCE' -> '386 bce'
def format_dates(runs, line_number):
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
    
    for run in runs:
        original_text = run.text
        modified_text = original_text
        
        modified_text = log_and_replace(
            r"\b(\d+)\s?(BCE|CE)\b",
            lambda m: f"{m.group(1)} {m.group(2).lower()}",
            modified_text
        )
        modified_text = log_and_replace(
            r"\b(AD|BC)\.\b",
            lambda m: f"{m.group(1)} ",
            modified_text
        )
        modified_text = log_and_replace(
            r"(\d+)\s?(BCE|CE|AD|BC)\b",
            lambda m: f"{m.group(1)} {m.group(2)}",
            modified_text
        )
        
        if original_text != modified_text:
            run.text = modified_text



def format_ellipses_in_series(runs):
    """
    Formats ellipses in a series and ensures proper grammar.
    1. Ensures ellipses use exactly three dots ('...') with no spaces between them.
    2. Replaces more than three dots (e.g., '.....') with exactly three dots ('...').
    3. Removes spaces in improperly spaced ellipses (e.g., '. . .' becomes '...').
    4. Capitalizes the first word after the ellipses if it starts a new sentence.
    5. Ensures no period follows the ellipses at the end of an incomplete sentence.
    """
    for run in runs:
        original_text = run.text
        modified_text = original_text

        # Replace more than three dots with exactly three dots
        modified_text = re.sub(r"\.{4,}", "...", modified_text)

        # Replace improperly spaced ellipses with '...'
        modified_text = re.sub(r"\.\s*\.\s*\.", "...", modified_text)

        # Ensure capitalization of the first word after ellipses if it starts a sentence
        def capitalize_after_ellipsis(match):
            ellipsis = match.group(1)
            following_text = match.group(2).strip()
            # Capitalize the first letter of the following word
            return f"{ellipsis} {following_text.capitalize()}"

        # Matches ellipses followed by text that starts a new sentence
        modified_text = re.sub(r"(\.\.\.)(\s+[a-z])", capitalize_after_ellipsis, modified_text)
        
        # Ensure no period follows ellipses at the end of an incomplete sentence
        modified_text = re.sub(r"(\.\.\.)\.", r"\1", modified_text)
        
        if original_text != modified_text:
            run.text = modified_text


# Do not repeat the unit in ranges. For example: from 10 to 20 cm not from(2.27)
def correct_units_in_ranges_with_logging(runs):
    global global_logs
    unit_symbols = ['cm', 'm', 'kg', 's', 'A', 'K', 'mol', 'cd', '%']
    
    # Regex patterns
    range_pattern = rf"\b(\d+)\s*({'|'.join(re.escape(unit) for unit in unit_symbols)})\s*(to|-|–|—)\s*(\d+)\s*\2\b"
    thin_space_pattern = rf"\b(\d+)\s+({'|'.join(re.escape(unit) for unit in unit_symbols)})\b"
    
    for run in runs:
        original_text = run.text
        modified_text = re.sub(
            range_pattern,
            lambda m: f"{m.group(1)} {m.group(3)} {m.group(4)} {m.group(2)}",
            original_text
        )
        modified_text = re.sub(
            thin_space_pattern,
            lambda m: f"{m.group(1)} {m.group(2)}" if m.group(2) != "%" else f"{m.group(1)}{m.group(2)}",
            modified_text
        )
        
        if original_text != modified_text:
            global_logs.append(f"[correct_units_in_ranges_with_logging]: '{original_text}' -> '{modified_text}'")
            run.text = modified_text


# 24 kg not 24 kgs, kg.s or kg's (2.8)
def correct_scientific_units_with_logging(runs):
    global global_logs
    unit_symbols = ['kg', 'm', 's', 'A', 'K', 'mol', 'cd', 'Hz', 'N', 'Pa', 'J', 'W', 'C', 'V', 'F', 'Ω', 'ohm', 'S', 'T', 'H', 'lm', 'lx', 'Bq', 'Gy', 'Sv', 'kat']
    pattern = rf"\b(\d+)\s*({'|'.join(re.escape(unit) for unit in unit_symbols)})\s*(s|'s|\.s)?\b"
    
    for run in runs:
        original_text = run.text
        changes = []
        new_text = re.sub(pattern, lambda m: f"{m.group(1)} {m.group(2)}", original_text)
        
        if new_text != original_text:
            for match in re.finditer(pattern, original_text):
                original = match.group(0)
                corrected = f"{match.group(1)} {match.group(2)}"
                if original != corrected:
                    changes.append(f"'{original}' -> '{corrected}'")
            
            if changes:
                global_logs.append(
                    f"[unit correction] '{original_text}' -> '{new_text}'"
                )
            run.text = new_text


def use_numerals_with_percent(runs):
    global global_logs

    for run in runs:
        original_text = run.text
        modified_text = original_text
        
        def replace_spelled_out_percent(match):
            word = match.group(1)
            try:
                num = w2n.word_to_num(word.lower())
                modified = f"{num}%"
                global_logs.append(
                    f"[numerals with percent] '{word} percent' -> '{modified}'"
                )
                return modified
            except ValueError:
                return match.group(0)
        
        modified_text = re.sub(
            r"\b([a-zA-Z\s\-]+)\s?(percent|per cent|percentage)\b",
            replace_spelled_out_percent,
            modified_text,
            flags=re.IGNORECASE,
        )
        
        def replace_numerical_percent(match):
            number = match.group(1)
            modified = f"{number}%"
            global_logs.append(
                f"[numerals with percent] '{match.group(0)}' -> '{modified}'"
            )
            return modified
        
        modified_text = re.sub(
            r"(\d+)\s?(percent|per cent|percentage)\b",
            replace_numerical_percent,
            modified_text,
            flags=re.IGNORECASE,
        )
        
        if modified_text != original_text:
            run.text = modified_text




def correct_preposition_usage(runs):
    """
    Corrects preposition usage for date ranges (e.g., "from 2000-2010" -> "from 2000 to 2010").
    Args:
        runs (list): List of text runs to process.
    Returns:
        None: Modifies runs in place.
    """
    global global_logs
    
    for run in runs:
        original_text = run.text
        modified_text = original_text
        
        def process_from_to(match):
            original = match.group(0)
            modified = f"from {match.group(1)} to {match.group(2)}"
            if original != modified:
                global_logs.append(f"[correct_preposition_usage] '{original}' -> '{modified}'")
            return modified
        
        def process_between_and(match):
            original = match.group(0)
            modified = f"between {match.group(1)} and {match.group(2)}"
            if original != modified:
                global_logs.append(f"[correct_preposition_usage] '{original}' -> '{modified}'")
            return modified
        
        modified_text = re.sub(r"from (\d{4})[–-](\d{4})", process_from_to, modified_text)
        modified_text = re.sub(r"between (\d{4})[–-](\d{4})", process_between_and, modified_text)
        
        if modified_text != original_text:
            run.text = modified_text


def correct_unit_spacing(runs):
    """
    Corrects spacing between numbers and units (e.g., "100 MB" -> "100MB").
    Args:
        runs (list): List of Run objects from a paragraph.
    Returns:
        None: Modifies runs in place.
    """
    global global_logs
    units = ["Hz", "KHz", "MHz", "GHz", "kB", "MB", "GB", "TB"]
    pattern = r"(\d+)\s+(" + "|".join(units) + r")"
    
    for run in runs:
        original_text = run.text
        def process_spacing(match):
            original = match.group(0)
            modified = f"{match.group(1)}{match.group(2)}"
            if original != modified:
                global_logs.append(
                    f"[correct_unit_spacing] '{original}' -> '{modified}'"
                )
            return modified
        
        run.text = re.sub(pattern, process_spacing, original_text)



def convert_currency_to_symbols(runs, line_number):
    """
    Converts textual currency names (dollar, pound, euro) to symbols ($, £, €) 
    when preceded by a numerical value in the text of a paragraph.
    Logs changes to a global list with details of the modification in the desired format.    
    Args:
        runs: The runs of a paragraph.
        line_number: The line number of the paragraph for context.

    Returns:
        None: Modifies the runs in place.
    """
    global global_logs
    currency_patterns = {
        r'(\b\d+\s*)dollars\b': r'$\1',
        r'(\b\d+\s*)pounds\b': r'£\1',
        r'(\b\d+\s*)euros\b': r'€\1'
    }

    original_text = "".join(run.text for run in runs)
    modified_text = original_text

    # Apply each currency replacement pattern
    for pattern, replacement in currency_patterns.items():
        modified_text = re.sub(pattern, replacement, modified_text, flags=re.IGNORECASE)

    # If changes are made, log the change
    if original_text != modified_text:
        global_logs.append(
            f"[convert_currency_to_symbols] Line {line_number}: '{original_text}' -> '{modified_text}'"
        )
        
        # Modify runs in place
        remaining_text = modified_text
        for run in runs:
            run.text = remaining_text[:len(run.text)]
            remaining_text = remaining_text[len(run.text):]


from datetime import datetime
from word2number import w2n

def process_string_years(input_string):
    # Define regex patterns for the various date formats
    date_patterns = [
        r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b',          # MM/DD/YYYY
        r'\b(\d{1,2})/(\d{1,2})/(\d{2})\b',          # MM/DD/YY
        r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b',          # YYYY-MM-DD
        r'\b(\d{1,2})[.-](\d{1,2})[.-](\d{4})\b',    # MM.DD.YYYY or MM-DD-YYYY
        r'\b(\d{1,2})[-.](\w{3,})[-.](\d{2})\b',     # DD-MMM-YY
        r'\b(\w{3,})[. ](\d{1,2}),[ ]?(\d{2,4})\b',  # Jan. 27, 25 or Jan. 27, 2025
        r'\b(\d{1,2})[ ](\w{3,})[ ](\d{4})\b',       # DD Month YYYY
        r'\b(\w{3,9})[ ](\d{1,2}),?[ ](\d{2,4})\b',  # Month DD, YYYY or Month DD, YY
        r'\b(\d{1,2})[ ](\w{3,})-?(\d{2})\b',        # DD Month-YY
    ]
    
    # Define a function to parse and reformat dates
    def reformat_date(match):
        try:
            # Try to parse the date from the matched string
            original_date = match.group(0)
            for fmt in [
                "%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%m.%d.%Y", "%d-%b-%y",
                "%b. %d, %y", "%b. %d, %Y", "%d %b %Y", "%B %d, %y", "%B %d, %Y",
                "%d %B %Y", "%d %b-%y"
            ]:
                try:
                    date = datetime.strptime(original_date, fmt)
                    break
                except ValueError:
                    continue
            else:
                return original_date  # If no formats match, return the original
            
            # Reformat the date
            if date.year >= 2025:
                return date.strftime("%B %d, %Y")  # January 16, 2025
            else:
                return date.strftime("%m/%d/%Y")  # 12/25/1991
        except Exception:
            return match.group(0)  # Return original if parsing fails
    
    # Process the input string and reformat dates
    for pattern in date_patterns:
        input_string = re.sub(pattern, reformat_date, input_string)
    return input_string

def process_string_ratio(input_string):
    def replace_ratio(match):
        left_word = match.group(1).strip()
        right_word = match.group(2).strip()
        try:
            # Convert words to numbers using word2number
            left_num = w2n.word_to_num(left_word)
            right_num = w2n.word_to_num(right_word)
            if left_num > right_num:
                print(left_num)
                print(right_num)
            return f"{left_num} : {right_num}"
        except ValueError:
            # If conversion fails, keep the original words
            return f"{left_word} : {right_word}"

    # Regex to find patterns like 'word : word'
    pattern = r"(\b[a-zA-Z]+\b)\s*:\s*(\b[a-zA-Z]+\b)"
    return re.sub(pattern, replace_ratio, input_string)


def process_text(runs):
    # Iterate over each run in the paragraph
    for run in runs:
        # Process the text in the run
        run.text = process_string_years(run.text)
        run.text = process_string_ratio(run.text)
    return runs



# def write_to_log(doc_id):
#     """
#     Writes the global logs to a log file. If the file already exists, it appends to it.
#     :param doc_id: The document ID used to determine the log file's directory.
#     """
#     global global_logs
#     output_dir = os.path.join('output', str(doc_id))
#     os.makedirs(output_dir, exist_ok=True)
#     log_file_path = os.path.join(output_dir, 'global_logs.txt')
#     with open(log_file_path, 'a', encoding='utf-8') as log_file:
#         log_file.write("\n".join(global_logs) + "\n")
#     global_logs = []


def write_to_log(doc_id, user):
    global global_logs
    # output_dir = os.path.join('output', str(doc_id))
    current_date = datetime.now().strftime("%Y-%m-%d")
    output_path_file = Path(os.getcwd()) / 'output' / user / current_date / str(doc_id) / 'text'
    os.makedirs(output_path_file, exist_ok=True)
    
    log_file_path = os.path.join(output_path_file, 'global_logs.txt')
    with open(log_file_path, 'a', encoding='utf-8') as log_file:
        log_file.write("\n".join(global_logs))
    global_logs = []


def process_doc_function2(payload: dict, doc: Document, doc_id,user):
    line_number = 1
    for para in doc.paragraphs:
        # working
        remove_unnecessary_apostrophes(para.runs, line_number)
        replace_fold_phrases(para.runs, line_number)
        remove_space_between_degree_and_direction(para.runs, line_number)
        enforce_lowercase_units(para.runs, line_number)
        precede_decimal_with_zero(para.runs, line_number)
        adjust_ratios(para.runs, line_number)
        remove_commas_from_numbers(para.runs, line_number)
        remove_spaces_from_four_digit_numbers(para.runs, line_number)
        # convert_decimal_to_baseline(para.runs, line_number)not working
        correct_scientific_unit_symbols(para.runs)
        # spell_out_number_and_unit_with_rules(para.runs, line_number)
        format_dates(para.runs, line_number)
        # format_ellipses_in_series(para.runs)
        correct_units_in_ranges_with_logging(para.runs)
        correct_scientific_units_with_logging(para.runs)
        # use_numerals_with_percent(para.runs) not working
        correct_preposition_usage(para.runs)
        correct_unit_spacing(para.runs)
        convert_currency_to_symbols(para.runs, line_number)
        # process_text(para.runs)
        
        # paragraph_text = " ".join([run.text for run in para.runs])
        # para.clear()
        # para.add_run(paragraph_text)

        line_number += 1
        
    write_to_log(doc_id,user)