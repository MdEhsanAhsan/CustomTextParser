from unicodedata import category
import os
import csv
import argparse
from collections import defaultdict, OrderedDict
import hashlib

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
EXPORT_ENCODING = 'utf-16' # Default export encoding

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


def excel_warning(headers, rows, warn_limit=32767):
    """
    Warns if any field value exceeds Excel's 32,767 character cell limit.
    """
    for row_idx, row in enumerate(rows, 2):
        for h in headers:
            val = str(row.get(h, ""))
            if len(val) > warn_limit:
                print(f"❗Warning: Value in row {row_idx}, column '{h}' exceeds Excel's 32,767 character cell limit ({len(val)} chars)❗")
                print(f"❗Excel won't display correctly! Consider truncating or splitting this value.❗")

def export_to_tsv(headers, rows, output_path, encoding=EXPORT_ENCODING):
    excel_warning(headers, rows)
    with open(output_path, 'w', newline='', encoding=encoding) as tsvfile:
        writer = csv.DictWriter(
            tsvfile,
            fieldnames=headers,
            delimiter='\t',
            quoting=csv.QUOTE_ALL
        )
        # Convert all values to strings before writing
        writer.writeheader()
        writer.writerows([{h: str(row.get(h, "")) for h in headers} for row in rows])
    print(f"Exported {len(rows)} rows to {output_path}")

def export_to_csv(headers, rows, output_path, encoding=EXPORT_ENCODING):
    excel_warning(headers, rows)
    with open(output_path, 'w', newline='', encoding=encoding) as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=headers,
            delimiter=',',
            quoting=csv.QUOTE_ALL
        )
        # Convert all values to strings before writing
        writer.writeheader()
        writer.writerows([{h: str(row.get(h, "")) for h in headers} for row in rows])
    print(f"Exported {len(rows)} rows to {output_path}")

def export_to_dat(headers, rows, output_path, encoding=EXPORT_ENCODING):
    sep = QUOTE_CHAR + FIELD_SEP + QUOTE_CHAR
    with open(output_path, 'w', encoding=encoding, newline='') as f:
        header_line = sep.join(headers)
        f.write(f"{QUOTE_CHAR}{header_line}{QUOTE_CHAR}\r\n")
        for row in rows:
            # Ensure all fields are strings
            fields = [str(row.get(h, '')) for h in headers]
            line = sep.join(fields)
            f.write(f"{QUOTE_CHAR}{line}{QUOTE_CHAR}\r\n")
    print(f"Exported {len(rows)} rows to {output_path}")

def get_headers(file_path, encoding):
    with open(file_path, 'r', encoding=encoding) as f:
        header_line = f.readline().strip('\r\n')
        headers = [strip_one_quote(h) for h in header_line.split(QUOTE_CHAR + FIELD_SEP + QUOTE_CHAR)]
        return headers

def file_has_valid_rows(file_path, headers, encoding):
    for i, line in enumerate(read_dat_file_smart(file_path, encoding)):
        if i == 0:
            continue
        values = line.split(QUOTE_CHAR + FIELD_SEP + QUOTE_CHAR)
        values = [strip_one_quote(value) for value in values]
        if len(values) != len(headers):
            return False
    return True

def compare_dat_files(file1_path, file2_path, MAP=None):
    global Encode

    # Detect encodings for both files
    encode1 = detect_encoding(file1_path, os.path.basename(file1_path))
    encode2 = detect_encoding(file2_path, os.path.basename(file2_path))

    if encode1 in ('Error', 'No File') or encode2 in ('Error', 'No File'):
        print("Failed to detect encoding for one or both files.")
        return None, None  # Return None for headers and diffs

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

    # Mapping logic
    if MAP:
        # MAP is expected to be {header_from_file1: header_from_file2}
        valid_mapped_headers = [
            (h1, h2) for h1, h2 in MAP.items()
            if h1 in headers1 and h2 in headers2
        ]

        if not valid_mapped_headers:
            print("No valid header mappings found — check your mapping file and headers.")
            return None, None

        # Split into two aligned lists
        mapped_headers1, mapped_headers2 = zip(*valid_mapped_headers)
    else:
        # If no mapping provided, require exact header match
        if headers1 != headers2:
            print("Headers do not match and no mapping file provided.")
            return None, None
        mapped_headers1 = headers1
        mapped_headers2 = headers2

    # Prepare filenames
    File1_Value = os.path.basename(file1_path)
    File2_Value = os.path.basename(file2_path)

    # Compare row values
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
                    "Row": idx + 2,  # +2 accounts for header and 1-based indexing
                    "Field": h1 if h1 == h2 else f"{h1} ↔ {h2}",
                    File1_Value: v1,
                    File2_Value: v2
                })

    if not diffs:
        print("No differences found.")
        return None, None

    fieldnames = ["Row", "Field", File1_Value, File2_Value]
    return fieldnames, diffs


def replace_header_and_export_dat(input_file_path, output_file_path, header_map, encoding):
    with open(output_file_path, 'w', encoding=encoding, newline='') as outfile:
        for i, line in enumerate(read_dat_file_smart(input_file_path, encoding)): # Use read_dat_file_smart
            if i == 0:
                # Replace headers
                headers = line.strip('\r\n').split(QUOTE_CHAR + FIELD_SEP + QUOTE_CHAR)
                headers = [strip_one_quote(h) for h in headers]
                new_headers = [header_map.get(h, h) for h in headers]
                # Reconstruct the header line in DAT format
                header_line = (QUOTE_CHAR + FIELD_SEP + QUOTE_CHAR).join(new_headers)
                header_line = f"{QUOTE_CHAR}{header_line}{QUOTE_CHAR}"
                outfile.write(header_line + '\n')
            else:
                outfile.write(line + '\r\n') # Add newline back as read_dat_file_smart strips it
    print(f"Exported DAT file with replaced headers to {output_file_path}")

def replace_header_and_collect(input_file_path, header_map, encoding):
    """
    Reads a DAT file, replaces headers using header_map, and returns new headers and rows.
    """
    new_headers = []
    rows = []
    for i, line in enumerate(read_dat_file_smart(input_file_path, encoding)): # Use read_dat_file_smart
        if i == 0:
            headers = [strip_one_quote(h) for h in line.split(QUOTE_CHAR + FIELD_SEP + QUOTE_CHAR)]
            new_headers = [header_map.get(h, h) for h in headers]
        else:
            # Use parse_line for consistent parsing
            parsed_row = parse_line(line, headers) # Pass original headers to parse_line
            if parsed_row:
                # Map the keys of the parsed_row to new_headers
                mapped_row = {new_headers[idx]: value for idx, (header, value) in enumerate(parsed_row.items())}
                rows.append(mapped_row)
    return new_headers, rows

def load_mapping_file(mapping_file):
    """
    Loads a header mapping file and returns a dictionary mapping old headers to new headers.
    """
    header_map = {}
    with open(mapping_file, encoding=detect_encoding(mapping_file, os.path.basename(mapping_file))) as f:
        for line in f:
            if ',' in line:
                old, new = line.strip().split(',', 1)
                header_map[old] = new
    return header_map

def Merge_dats(merge_file, args):
    if not os.path.isfile(merge_file):
        print(f"❌ Merge list file not found: {merge_file}")
        return

    # Read file paths from CSV
    with open(merge_file, encoding=detect_encoding(merge_file, os.path.basename(merge_file))) as f:
        reader = csv.reader(f)
        all_paths = [row[0] for row in reader if row]

    grouped_files = defaultdict(list)  # header_hash -> list of (filepath, headers, rows)
    excluded_files = []

    for path in all_paths:
        if not os.path.isfile(path):
            print(f"❌ File does not exist: {path}")
            excluded_files.append(path)
            continue

        encoding = detect_encoding(path, os.path.basename(path))
        if encoding in ['Error', 'No File']:
            excluded_files.append(path)
            continue
        try:
            line_iter = read_dat_file_smart(path, encoding)
            header_line = next(line_iter)
            headers = [strip_one_quote(h) for h in header_line.split(QUOTE_CHAR + FIELD_SEP + QUOTE_CHAR)]
        except Exception as e:
            print(f"❌ Failed to read headers from {path}: {e}")
            excluded_files.append(path)
            continue

        if not file_has_valid_rows(path, headers, encoding):
            print(f"⚠️ Invalid row structure detected, excluding file: {path}")
            excluded_files.append(path)
            continue
        # Create a hash of the headers
        header_hash = hashlib.md5("||".join(headers).encode()).hexdigest()

        # Collect rows
        rows = []
        for i, line in enumerate(read_dat_file_smart(path, encoding)):
            if i == 0:
                continue  # skip header
            parsed = parse_line(line, headers)
            if parsed:
                rows.append(parsed)

        grouped_files[header_hash].append((path, headers, rows))
        
    m_EXPORT_ENCODING = 'utf-8-sig'  # Set default export encoding for merged files
    
    # Export merged groups
    for idx, (header_hash, files_info) in enumerate(grouped_files.items(), 1):
        all_headers = files_info[0][1]
        all_rows = []
        for path, headers, rows in files_info:
            all_rows.extend(rows)
        output_base = f"merged_group_{idx}"
        print(f"✅ Merging group {idx} with {len(files_info)} files ({len(all_rows)} total rows)")

        if args.tsv:
            output_path = args.tsv if args.tsv is not True else f"{output_base}.csv"
            export_to_tsv(all_headers, all_rows, output_path, encoding=m_EXPORT_ENCODING)
        elif args.csv:
            output_path = args.csv if args.csv is not True else f"{output_base}.csv"
            export_to_csv(all_headers, all_rows, output_path, encoding=m_EXPORT_ENCODING)
        else:
            output_path = args.dat if getattr(args, 'dat', None) and args.dat is not True else f"{output_base}.dat"
            export_to_dat(all_headers, all_rows, output_path, encoding=m_EXPORT_ENCODING)

    if excluded_files:
        print("\n⚠️ The following files were excluded from merging due to issues:")
        for ex in excluded_files:
            print(f"  - {ex}")

# Get command-line arguments
# This function uses argparse to handle command-line arguments for the script.
def get_arguments():
    parser = argparse.ArgumentParser(
        description="File converter utility",
        usage=(
            "\n  %(prog)s input_file [input_file2] [options]\n\n"
            "Examples:\n"
            "  %(prog)s myfile.dat --csv\n"
            "  %(prog)s file1.dat file2.dat -c\n"
            "  %(prog)s --help\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    # Make input_file optional by adding nargs='?'
    parser.add_argument("input_file", nargs='?', help="Path to first input DAT file")
    parser.add_argument("input_file2", nargs="?", help="Path to second input DAT file (for compare)")
    parser.add_argument(
        "--csv",
        nargs="?",
        const=True,
        metavar="OUTPUT",
        help="Convert input to CSV (Comma Separated Values). Optionally specify output file path."
    )
    parser.add_argument(
        "--tsv",
        nargs="?",
        const=True,
        metavar="OUTPUT",
        help="Export output as CSV (Tab Separated Values). Optionally specify output file path."
    )
    parser.add_argument(
        "--dat",
        nargs="?",
        const=True,
        metavar="OUTPUT",
        help="Export output as DAT. Optionally specify output file path."
    )
    parser.add_argument(
        "-c", "--compare",
        action="store_true",
        help="Compare two DAT files"
    )
    parser.add_argument(
        "-m", "--mapping",
        metavar="MAPPING_FILE",
        help="Optional mapping file for header mapping when comparing"
    )
    parser.add_argument(
        "-r", "--replace-header",
        metavar="HEADER_MAPPING_FILE",
        help="Replace headers of input file using a mapping file and export as DAT/CSV/TSV"
    )
    parser.add_argument(
        "-merge",
        nargs="?",
        metavar="MERGE_FILE",
        help="Merge multiple DAT files into groups of same headers and export as DAT/CSV/TSV"
    )
    try:
        return parser.parse_args()
    except SystemExit:
        print("\n" + "="*60)
        print("  ❌  Missing required arguments!\n")
        print("  Please provide an input file or use the --merge option.\n")
        print("  For help, run:\n  python Main.py --help\n")
        print("="*60 + "\n")
        exit(2)

if __name__ == '__main__':
    args = get_arguments()

    # Check if a primary operation is specified
    if args.merge:
        Merge_dats(args.merge, args)
    elif args.compare:
        if not args.input_file2:
            print("Error: You must provide a second DAT file for comparison.")
        else:
            if args.mapping:
                map_dic = load_mapping_file(args.mapping)
            else:
                map_dic = None
            headers, diffs = compare_dat_files(
                args.input_file,
                args.input_file2,
                MAP=map_dic
            )
            if diffs: # Only export if there are differences
                if args.tsv:
                    output_path = args.tsv if args.tsv is not True else "value_diff.csv"
                    export_to_tsv(headers, diffs, output_path)
                elif args.csv:
                    output_path = args.csv if args.csv is not True else "value_diff.csv"
                    export_to_csv(headers, diffs, output_path, encoding='utf-8-sig')
                elif getattr(args, "dat", False):
                    output_path = args.dat if args.dat is not True else "value_diff.dat"
                    export_to_dat(headers, diffs, output_path)
                else:
                    print("No export format specified for comparison, defaulting to DAT.")
                    export_to_dat(headers, diffs, "value_diff.dat")
            else:
                print("No differences found during comparison.")
    elif args.replace_header:
        # Ensure input_file is provided for replace-header
        if not args.input_file:
            print("Error: An input file is required for --replace-header.")
            exit(2)
        input_file_path = args.input_file # Define input_file_path here

        # Determine output path
        if args.replace_output:
            output_dat_path = args.replace_output
        else:
            base, ext = os.path.splitext(input_file_path)
            output_dat_path = f"{base}_Replaced{ext}"

        # Load header mapping from file using the dedicated function
        header_map = load_mapping_file(args.replace_header)

        # Detect input encoding
        Encode = detect_encoding(input_file_path, os.path.basename(input_file_path))

        headers, rows = replace_header_and_collect(input_file_path, header_map, Encode)
        if args.tsv:
            output_path = args.tsv if args.tsv is not True else output_dat_path.replace('.dat', '.csv')
            export_to_tsv(headers, rows, output_path,encoding=Encode)
        elif args.csv:
            output_path = args.csv if args.csv is not True else output_dat_path.replace('.dat', '.csv')
            export_to_csv(headers, rows, output_path, encoding=Encode)
        elif getattr(args, "dat", False):
            output_path = args.dat if args.dat is not True else output_dat_path
            export_to_dat(headers, rows, output_path, encoding=Encode)
        else:
            print("No export format specified for header replacement, defaulting to DAT.")
            export_to_dat(headers, rows, output_dat_path, encoding=Encode)

    elif args.tsv or args.csv or args.dat: # General conversions (require input_file)
        if not args.input_file:
            print("\n" + "="*60)
            print("  ❌  Missing required arguments!\n")
            print("  Please provide an input file for conversion.\n")
            print("  For help, run:\n  python Main.py --help\n")
            print("="*60 + "\n")
            exit(2)
        input_file_path = args.input_file # Define input_file_path here

        if args.tsv:
            print(f"Converting {input_file_path} to CSV (Tab Separated Values)...")
            Encode = detect_encoding(input_file_path, os.path.basename(input_file_path))
            if args.tsv is True:
                base, _ = os.path.splitext(input_file_path)
                output_tsv_path = base + ".csv"
            else:
                output_tsv_path = args.tsv
            headers, rows = replace_header_and_collect(input_file_path, {}, Encode)
            export_to_tsv(headers, rows, output_tsv_path)

        elif args.csv:
            print(f"Converting {input_file_path} to CSV (Comma Separated Values)...")
            Encode = detect_encoding(input_file_path, os.path.basename(input_file_path))
            if args.csv is True:
                base, _ = os.path.splitext(input_file_path)
                output_csv_path = base + ".csv"
            else:
                output_csv_path = args.csv
            headers, rows = replace_header_and_collect(input_file_path, {}, Encode)
            export_to_csv(headers, rows, output_csv_path)

        elif args.dat:
            print(f"Converting {input_file_path} to DAT...")
            Encode = detect_encoding(input_file_path, os.path.basename(input_file_path))
            if args.dat is True:
                base, _ = os.path.splitext(input_file_path)
                output_dat_path = base + "_converted.dat"
            else:
                output_dat_path = args.dat
            headers, rows = replace_header_and_collect(input_file_path, {}, Encode)
            export_to_dat(headers, rows, output_dat_path)

    else: # No specific operation or input file provided
        print("\n" + "="*60)
        print("  ❌  Missing required arguments!\n")
        print("  Please provide an input file or use the --merge option.\n")
        print("  For help, run:\n  python Main.py --help\n")
        print("="*60 + "\n")