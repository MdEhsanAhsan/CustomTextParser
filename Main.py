from unicodedata import category
import os
import csv

class CharReader:
    def __init__(self, file):
        self.file = file
        self.lookahead = []

    def read(self):
        """Reads the next character from the file."""
        if self.lookahead:
            return self.lookahead.pop(0)
        return self.file.read(1)

    def peek(self):
        """Peeks at the next character without consuming it."""
        while len(self.lookahead) < 1:
            next_char = self.file.read(1)
            if not next_char:  # EOF
                return None
            self.lookahead.append(next_char)
        return self.lookahead[0]

    def peek_two(self):
        """Peeks at the next two characters without consuming them."""
        while len(self.lookahead) < 2:
            next_char = self.file.read(1)
            if not next_char:  # EOF
                break
            self.lookahead.append(next_char)
        if len(self.lookahead) >= 2:
            return (self.lookahead[0], self.lookahead[1])
        elif len(self.lookahead) == 1:
            return (self.lookahead[0], None)
        else:
            return (None, None)

#Global constants for the DAT file format
# These constants are used to identify the structure of the DAT file.

QUOTE_CHAR = '\xfe' # Quote character used to enclose fields.
FIELD_SEP = '\x14' # Data Control 4 (DC4) character, used as field separator.
Encode = None  # Global variable to hold the detected encoding

def detect_encoding(file_path, fname):

    """

    Detects the file encoding by reading a larger sample (4KB) and applying several heuristics.

    Returns the detected encoding as a string or 'Error' if detection fails.

    """

    try:

        with open(file_path, 'rb') as file:

            raw = file.read(4096)  # Read first 4KB for better analysis

            # Check for BOM signatures first.

            if raw.startswith(b'\xEF\xBB\xBF'):

                print(f"{fname} is detected as UTF-8 BOM")

                return 'utf-8-sig'

            elif raw.startswith(b'\xFF\xFE'):

                print(f"{fname} is detected as UTF-16 LE BOM")

                return 'utf-16'

            elif raw.startswith(b'\xFE\xFF'):

                print(f"{fname} is detected as UTF-16 BE BOM")

                return 'utf-16'

            # Try to decode as UTF-8 (heuristic: if no error, assume UTF-8).

            try:

                raw.decode('utf-8')

                print(f"{fname} is detected as UTF-8 (heuristic: decodes without error)")

                return 'utf-8'

            except UnicodeDecodeError:

                pass

            # Fallback to latin-1

            try:

                data = file.read()

                for b in data:

                    if 0x80 <= b <= 0x9F:

                        #decode with Windows-1252 and Latin-1

                        char_win = bytes([b]).decode('windows-1252',errors='replace')

                        char_latin = bytes([b]).decode('latin-1',errors='replace')

                        #Check category

                        cat_win = category(char_win)

                        cat_latin = category(char_latin)

                        #Printable in Windows-1252 but Control Number in Latin-1

                        if not cat_win.startswith('C') and cat_latin.startswith('C'):

                            print(f"{fname} is detected as Windows-1252")

                            return 'Windows-1252'

                # No definitive Windows-1252 charater found

                print(f"{fname} is detected as LATIN-1")

                return 'LATIN-1'

            except UnicodeDecodeError:

                print(f"{fname}: Unable to determine encoding using heuristics.")

                return 'Error'

    except FileNotFoundError:

        print(f"File not found: {file_path}")

        return 'No File'

def read_dat_file_smart(file_path, encoding):
    """
    Reads a DAT file smartly, ignoring newlines that occur inside quoted fields.
    Yields complete logical lines.
    """
    with open(file_path, 'r', encoding=encoding) as f:
        reader = CharReader(f)
        buffer = ''
        in_quote = False  # Track whether we are inside a quoted field

        while True:
            char = reader.read()
            peeked = reader.peek_two()
            next_chars = "".join(c if c is not None else "" for c in peeked)
            if not char:
                if buffer:
                    yield buffer.strip('\r\n')
                break

            if char == QUOTE_CHAR and not in_quote:
                in_quote = True
                buffer += char
            elif char == QUOTE_CHAR and in_quote and (next_chars == FIELD_SEP + QUOTE_CHAR or next_chars == '\n' + QUOTE_CHAR):
                in_quote = False
                buffer += char
            elif (char == '\n' or char == '\r') and not in_quote and next_chars != FIELD_SEP + QUOTE_CHAR:
                yield buffer.strip('\r\n')
                buffer = ''
            else:
                buffer += char

# Strip only one leading and one trailing QUOTE_CHAR if present
def strip_one_quote(s):
    if s.startswith(QUOTE_CHAR):
        s = s[1:]
    if s.endswith(QUOTE_CHAR):
        s = s[:-1]
    return s

def parse_line(line, headers):
    """
    Parses a line from the DAT file, splitting it into fields.
    Returns a dict mapping headers to values, or None if field count mismatch.
    """
    values = line.split(QUOTE_CHAR + FIELD_SEP + QUOTE_CHAR)
    values = [strip_one_quote(value) for value in values]
    if len(values) != len(headers):
        print(f"Field count mismatch: expected {len(headers)}, got {len(values)} in row: {line}")
        return None  # Field count mismatch, skip this row
    row = {header: value for header, value in zip(headers, values)}
    return row

def export_to_tsv(input_file_path,Encode):
    """Parse DAT and export as TSV (UTF-16), warn for long fields."""

    if Encode is None:
        Encode = detect_encoding(input_file_path, os.path.basename(input_file_path))
        if Encode == 'Error' or Encode == 'No File':
            print(f"Error detecting encoding of file: {input_file_path}")
            exit(1)

    base, _ = os.path.splitext(input_file_path)
    output_csv_path = base + ".csv"

    parsed_rows = []
    headers = []
    for i, line in enumerate(read_dat_file_smart(input_file_path)):
        if i == 0:
            headers = line.split(QUOTE_CHAR + FIELD_SEP + QUOTE_CHAR)
            headers = [strip_one_quote(header) for header in headers]
            continue
        parsed = parse_line(line, headers)
        if parsed is None:
            print(f"Skipping malformed row at line {i+1}: {line}")
            continue
        parsed_rows.append(parsed)

    MAX_EXCEL_CELL_LENGTH = 32_767
    for row_num, row in enumerate(parsed_rows, start=2):
        for field, value in row.items():
            if len(value) > MAX_EXCEL_CELL_LENGTH:
                print(
                    f"Warning: Field '{field}' in row {row_num} exceeds Excel's cell limit of "
                    f"{MAX_EXCEL_CELL_LENGTH} chars (actual length: {len(value)}). "
                    "It may not display correctly in Excel."
                )

    with open(output_csv_path, 'w', newline='', encoding='utf-16') as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=headers,
            delimiter='\t',
            quoting=csv.QUOTE_ALL
        )
        writer.writeheader()
        writer.writerows(parsed_rows)
    print(f"Exported {len(parsed_rows)} rows to {output_csv_path}")

def compare_dat_files(file1_path, file2_path, mapping_file=None, output_diff_path="value_diff.tsv"):
    global Encode

    # Detect encodings for both files
    encode1 = detect_encoding(file1_path, os.path.basename(file1_path))
    encode2 = detect_encoding(file2_path, os.path.basename(file2_path))

    if encode1 in ('Error', 'No File') or encode2 in ('Error', 'No File'):
        print("Failed to detect encoding for one or both files.")
        return

    # Read lines from both files
    def get_headers_and_rows(file_path, encoding):
        headers = []
        rows = []
        for i, line in enumerate(read_dat_file_smart(file_path, encoding)):
            if i == 0:
                headers = [strip_one_quote(h) for h in line.split(QUOTE_CHAR + FIELD_SEP + QUOTE_CHAR)]
            else:
                parsed = parse_line(line, headers)
                if parsed:
                    rows.append(parsed)
        return headers, rows

    headers1, rows1 = get_headers_and_rows(file1_path, encode1)
    headers2, rows2 = get_headers_and_rows(file2_path, encode2)

    # Load mapping if provided
    if mapping_file:
        header_map = {}
        with open(mapping_file, encoding='utf-8') as f:
            for line in f:
                if ',' in line:
                    a, b = line.strip().split(',', 1)
                    header_map[a] = b
        headers_common = [h for h in headers1 if h in header_map]
        mapped_headers1 = headers_common
        mapped_headers2 = [header_map[h] for h in headers_common]
    else:
        if headers1 != headers2:
            print("Headers do not match and no mapping file provided.")
            return
        mapped_headers1 = headers1
        mapped_headers2 = headers2

    # Export result
    File1_Value = os.path.basename(file1_path)
    File2_Value = os.path.basename(file2_path)

    # Compare values
    diffs = []
    row_count = min(len(rows1), len(rows2))
    for idx in range(row_count):
        r1 = rows1[idx]
        r2 = rows2[idx]
        for h1, h2 in zip(mapped_headers1, mapped_headers2):
            v1 = r1.get(h1, "")
            v2 = r2.get(h2, "")
            if v1 != v2:
                diffs.append({
                    "Row": idx + 2,
                    "Field": h1 if h1 == h2 else f"{h1} ↔ {h2}",
                    File1_Value: v1,
                    File2_Value: v2
                })

    if not diffs:
        print("No differences found.")
        return

    fieldnames = ["Row", "Field", File1_Value, File2_Value]
    with open(output_diff_path, 'w', encoding='utf-8-SIG', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames, delimiter=',', quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(diffs)

    print(f"Exported {len(diffs)} differences to {output_diff_path}")


if __name__ == '__main__':
    input_file_path = r"C:\Users\ehsan\OneDrive\Desktop\DAT\Test.dat"
    input_file_path2 = r"C:\Users\ehsan\OneDrive\Desktop\DAT\Test3.dat"
    mapping_file = r"C:\Users\ehsan\OneDrive\Desktop\DAT\Mapped.csv"
    # Encode = detect_encoding(input_file_path, os.path.basename(input_file_path))
    # export_to_tsv(input_file_path,Encode)
    compare_dat_files(input_file_path, input_file_path2, mapping_file=mapping_file, output_diff_path=r"C:\Users\ehsan\OneDrive\Desktop\DAT\value_diff.csv")