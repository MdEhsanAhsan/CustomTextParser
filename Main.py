from heapq import merge
import sys
from unicodedata import category
import os
import csv
import argparse
from collections import defaultdict, OrderedDict
import hashlib


# === Global Constants ===
QUOTE_CHAR = '\xfe'  # Quote character used to enclose fields.
FIELD_SEP = '\x14'  # Field separator (DC4)
EXPORT_ENCODING = 'utf-16'

# === Character Reader Class ===
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

# === Helper Functions ===

def get_output_path(input_path, suffix="", ext=".dat", output_dir=None):
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    if ext == ".tsv":
        ext = ".csv"
        filename = f"{base_name}{suffix}{ext}"
    else:
        filename = f"{base_name}{suffix}{ext}"
    if output_dir and os.path.splitext(output_dir)[1]:
        user_ext = os.path.splitext(output_dir)[1].lower()
        expected_ext = ext.lower()
        if user_ext != expected_ext:
            print(f"⚠️  Output file extension '{user_ext}' does not match selected format '{expected_ext}'. Changing to '{expected_ext}'.")
            output_path = os.path.splitext(output_dir)[0] + expected_ext
        else:
            output_path = output_dir
        return output_path
    
    return os.path.join(output_dir or os.path.dirname(input_path), filename)


def detect_and_open(file_path, mode='r'):
    encoding = detect_encoding(file_path, os.path.basename(file_path))
    if encoding in ('Error', 'No File'):
        raise ValueError(f"Failed to detect encoding for {file_path}")
    return open(file_path, mode, encoding=encoding)


def read_headers_and_rows(file_path):
    with detect_and_open(file_path) as f:
        reader = CharReader(f)
        header_line = next(read_dat_file_smart(file_path, encoding=detect_encoding(file_path, "")))
        headers = [strip_one_quote(h) for h in header_line.split(QUOTE_CHAR + FIELD_SEP + QUOTE_CHAR)]
        rows = []
        for line in read_dat_file_smart(file_path, encoding=detect_encoding(file_path, "")):
            parsed = parse_line(line, headers)
            if parsed:
                rows.append(parsed)
        return headers, rows


def export_data(headers, rows, output_path, fmt="dat", encoding=EXPORT_ENCODING):
    
    if fmt == "csv":
        excel_warning(headers, rows) # Excel warning for CSV
        export_to_csv(headers, rows, output_path, encoding=encoding)
    elif fmt == "tsv":
        excel_warning(headers, rows) # Excel warning for TSV
        export_to_tsv(headers, rows, output_path, encoding=encoding)
    else:
        export_to_dat(headers, rows, output_path, encoding=encoding)


def get_mapping_dict(mapping_file):
    if not mapping_file:
        return {}
    return load_mapping_file(mapping_file)


# === Encoding Detection ===
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

# === Line Reader & Parser ===

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

# === Strip only one leading and one trailing QUOTE_CHAR if present ===
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

# === Excel Warnings ===
def excel_warning(headers, rows, warn_limit=32767):
    """
    Warns if any field value exceeds Excel's 32,767 character cell limit.
    """
    for row_idx, row in enumerate(rows, 2):
        for h in headers:
            val = str(row.get(h, ""))
            if len(val) > warn_limit:
                print(f"Warning: Value in row {row_idx}, column '{h}' exceeds Excel's 32,767 character cell limit ({len(val)} chars)❗")
                print(f"Excel won't display correctly! Consider truncating or splitting this value.❗")

# === Export Functions ===
def export_to_tsv(headers, rows, output_path, encoding=EXPORT_ENCODING):
    with open(output_path, 'w', newline='', encoding=encoding) as tsvfile:
        writer = csv.DictWriter(tsvfile, fieldnames=headers, delimiter='\t', quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows([{h: str(row.get(h, "")) for h in headers} for row in rows])
    print(f"Exported {len(rows)} rows to {output_path}")


def export_to_csv(headers, rows, output_path, encoding=EXPORT_ENCODING):
    with open(output_path, 'w', newline='', encoding=encoding) as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers, delimiter=',', quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows([{h: str(row.get(h, "")) for h in headers} for row in rows])
    print(f"Exported {len(rows)} rows to {output_path}")


def export_to_dat(headers, rows, output_path, encoding=EXPORT_ENCODING):
    sep = QUOTE_CHAR + FIELD_SEP + QUOTE_CHAR
    with open(output_path, 'w', encoding=encoding, newline='') as f:
        header_line = sep.join(headers)
        f.write(f"{QUOTE_CHAR}{header_line}{QUOTE_CHAR}\r\n")
        for row in rows:
            fields = [str(row.get(h, '')) for h in headers]
            line = sep.join(fields)
            f.write(f"{QUOTE_CHAR}{line}{QUOTE_CHAR}\r\n")
    print(f"Exported {len(rows)} rows to {output_path}")

# === Mapping Header Function ===

def load_mapping_file(mapping_file):
    header_map = {}
    with open(mapping_file, encoding=detect_encoding(mapping_file, os.path.basename(mapping_file))) as f:
        for line in f:
            if ',' in line:
                old, new = line.strip().split(',', 1)
                header_map[old] = new
    return header_map


# === Compare DAT Files ===
def compare_dat_files(file1_path, file2_path, MAP=None):

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

# === Replace Header ===
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


# === Merge DAT Files ===
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
        header_hash = hashlib.sha256("||".join(headers).encode()).hexdigest()

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
    output_dir = args.output_dir or os.path.dirname(merge_file)

    group_log = [] # List to keep track of merged groups and files

    # Export merged groups
    for idx, (header_hash, files_info) in enumerate(grouped_files.items(), 1):
        all_headers = files_info[0][1]
        all_rows = []
        for path, headers, rows in files_info:
            all_rows.extend(rows)
            group_log.append({"Group": f"merged_group_{idx}", "File": path,"RowCount": len(rows)})
        
        fmt = "dat"
        if args.tsv:
            fmt = "tsv"
        elif args.csv:
            fmt = "csv"
        # Create output path for merged group
        output_base = get_output_path(merge_file, f"_group_{idx}", "."+fmt, output_dir)
        print(f"✅ Merging group {idx} with {len(files_info)} files ({len(all_rows)} total rows)")
        export_data(all_headers, all_rows, output_base, fmt=fmt, encoding=m_EXPORT_ENCODING)

    # Write log CSV
    log_path = get_output_path(merge_file, "_merge_log", ".csv", output_dir)
    export_data(["Group", "File", "RowCount"], group_log, log_path, fmt="csv", encoding="utf-8-sig")
    print(f"📝 Merge log written to {log_path}")

    if excluded_files:
        print("\n⚠️ The following files were excluded from merging due to issues:")
        for ex in excluded_files:
            print(f"  - {ex}")

# === Delete Rows ===
def delete_rows(input_file, delete_file, args):
    input_name = os.path.splitext(os.path.basename(input_file))[0]
    input_dir = os.path.dirname(input_file)
    
    # Detect input encoding
    d_Export_ENCODING = detect_encoding(input_file, os.path.basename(input_file))  # Default export encoding for deleted rows
    
    # Load delete values
    delete_encoding = detect_encoding(delete_file, os.path.basename(delete_file))
    with open(delete_file, encoding=delete_encoding) as f:
        lines = [line.strip() for line in f if line.strip()]
        if not lines:
            print("❌ Deletion file List is empty.")
            return
        field = lines[0]
        delete_values_list = lines[1:]
        delete_values_set = set(delete_values_list)

    print(f"🧹 Will delete rows where '{field}' has one of the values: {', '.join(delete_values_list)}")

    # Read headers
    line_iter = read_dat_file_smart(input_file, d_Export_ENCODING)
    header_line = next(line_iter)
    headers = [strip_one_quote(h) for h in header_line.split(QUOTE_CHAR + FIELD_SEP + QUOTE_CHAR)]

    if field not in headers:
        print(f"❌ Field '{field}' not found in input file headers: {headers}")
        return

    if not file_has_valid_rows(input_file, headers, d_Export_ENCODING):
        print(f"❌ Input file has invalid rows. Aborting delete operation.")
        return

    # Gather all values present in the DAT file for the target field
    present_values = set()
    all_rows = []
    for i, line in enumerate(read_dat_file_smart(input_file, d_Export_ENCODING)):
        if i == 0:
            continue
        parsed = parse_line(line, headers)
        if parsed:
            present_values.add(parsed.get(field, ""))
            all_rows.append(parsed)

    # Check for missing delete values
    missing_values = delete_values_set - present_values
    if missing_values:
        print(f"⚠️ The following value(s) for '{field}' were not found in the DAT file: {', '.join(missing_values)}")

    # Filter rows
    kept_rows = []
    deleted_rows = []
    for i, line in enumerate(read_dat_file_smart(input_file, d_Export_ENCODING)):
        if i == 0:
            continue
        parsed = parse_line(line, headers)
        if parsed:
            if parsed.get(field) in delete_values_set:
                deleted_rows.append(parsed)
            else:
                kept_rows.append(parsed)
    fmt = "dat"
    if args.tsv:
        fmt = "tsv"
    elif args.csv:
        fmt = "csv"

    kept_path = get_output_path(input_file, "{kept}", "." + fmt, args.output_dir)
    removed_path = get_output_path(input_file, "{removed}", "." + fmt, args.output_dir)

    export_data(headers, kept_rows, kept_path, fmt=fmt, encoding=d_Export_ENCODING)
    export_data(headers, deleted_rows, removed_path, fmt=fmt, encoding=d_Export_ENCODING)
    print(f"✅ Done. Kept {len(kept_rows)} rows, removed {len(deleted_rows)} rows.")


# === Selected Header ===
def select_fields_and_collect(input_file_path, selected_headers, encoding):
    """
    Reads a DAT file and returns only the specified selected headers and corresponding row data.
    """
    new_headers = []
    rows = []

    for i, line in enumerate(read_dat_file_smart(input_file_path, encoding)):
        if i == 0:
            # Parse headers from first line
            headers = [strip_one_quote(h) for h in line.split(QUOTE_CHAR + FIELD_SEP + QUOTE_CHAR)]
            # Filter headers based on selection
            new_headers = [h for h in headers if h in selected_headers]
        else:
            parsed_row = parse_line(line, headers)
            if parsed_row:
                # Select only the desired fields
                filtered_row = {key: value for key, value in parsed_row.items() if key in selected_headers}
                rows.append(filtered_row)

    return new_headers, rows


    # === Utility Functions ===

def file_has_valid_rows(file_path, headers, encoding):
    for i, line in enumerate(read_dat_file_smart(file_path, encoding)):
        if i == 0:
            continue
        values = line.split(QUOTE_CHAR + FIELD_SEP + QUOTE_CHAR)
        values = [strip_one_quote(value) for value in values]
        if len(values) != len(headers):
            return False
    return True

    # === Argument Parsing ===

def get_arguments():
    parser = argparse.ArgumentParser(description="DAT File converter utility", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("input_file", nargs='?', help="Path to first input DAT file")
    parser.add_argument("input_file2", nargs="?", help="Path to second input DAT file (for compare)")
    parser.add_argument("--csv", nargs="?", const=True, metavar="OUTPUT", help="Convert input to CSV(Comma Separated Vlaue)")
    parser.add_argument("--tsv", nargs="?", const=True, metavar="OUTPUT", help="Export output as CSV(Tab Separated Vlaue)")
    parser.add_argument("--dat", nargs="?", const=True, metavar="OUTPUT", help="Export output as DAT")
    parser.add_argument("-c", "--compare", action="store_true", help="Compare two DAT files")
    parser.add_argument("-m", "--mapping", metavar="MAPPING_FILE", help="Header mapping file for comparison")
    parser.add_argument("-r", "--replace-header", metavar="HEADER_MAPPING_FILE", help="Replace headers using a mapping file")
    parser.add_argument("-merge", action="store_true", help="Merge multiple DAT files into groups")
    parser.add_argument("-delete", nargs="?", metavar="DELETE_FILE", help="Delete rows based on field values")
    parser.add_argument("-select", nargs="?", metavar="SELECT_FILE", help="Select rows based on field values")
    parser.add_argument("-o", "--output-dir", metavar="DIR", help="Directory for output files")

    try:
        return parser.parse_args()
    except SystemExit:
        print("\n" + "=" * 60)
        print("  ❌  Missing required arguments!\n")
        print("  Please provide an input file or use the --merge option.\n")
        print("  For help, run:\n  python Main_Refactored.py --help")
        print("=" * 60 + "\n")
        sys.exit(2)

# === Main Execution ===

if __name__ == '__main__':
    args = get_arguments()

    # Check if a primary operation is specified
    # Auto-assign input_file to merge if merge flag is set but value is None
    if args.merge is True and args.input_file:
        args.merge = args.input_file
        args.input_file = None
        Merge_dats(args.merge, args)
    elif args.compare:
        if not args.input_file2:
            print("Error: You must provide a second DAT file for comparison.")
        else:
            if args.mapping:
                map_dic = load_mapping_file(args.mapping)
            else:
                map_dic = None
            headers, diffs = compare_dat_files(args.input_file, args.input_file2, map_dic)
            if diffs: # Only export if there are differences
                fmt = "dat"
                if args.tsv:
                    fmt = "tsv"
                elif args.csv:
                    fmt = "csv"
                output_path = get_output_path(args.input_file, "_diff", "." + fmt, args.output_dir)
                export_data(headers, diffs, output_path, fmt=fmt)
            else:
                print("No differences found during comparison.")
    elif args.replace_header:
        # Ensure input_file is provided for replace-header
        if not args.input_file:
            print("Error: An input file is required for --replace-header.")
            sys.exit(2)
        
        input_file_path = args.input_file # Define input_file_path here
        
        # Detect input encoding
        Encode = detect_encoding(args.input_file, os.path.basename(args.input_file))
        header_map = get_mapping_dict(args.replace_header)
        new_headers, rows = replace_header_and_collect(args.input_file, header_map, Encode)
        
        fmt = "dat"
        if args.tsv:
            fmt = "tsv"
        elif args.csv:
            fmt = "csv"
        
        # Determine output path
        output_path = get_output_path(args.input_file, "_Replaced", "." + fmt, args.output_dir)
        
        export_data(new_headers, rows, output_path, fmt=fmt, encoding=Encode)

    elif args.delete:
        if not args.input_file:
            print("❌ Please provide the input file along with --delete option.")
        else:
            delete_rows(args.input_file, args.delete, args)

    elif args.select:
        if not args.input_file:
            print("❌ Please provide the input file along with --select option.")
        else:
            # Detect input encoding
            Encode = detect_encoding(args.input_file, os.path.basename(args.input_file))
            selected_headers = []
            with open(args.select, encoding=detect_encoding(args.select, os.path.basename(args.select))) as f:
                selected_headers = [line.strip() for line in f if line.strip()]
            if not selected_headers:
                print("❌ No headers selected in the selection file.")
                sys.exit(2)
            new_headers, rows = select_fields_and_collect(args.input_file, selected_headers, Encode)
            fmt = "dat"
            if args.tsv:
                fmt = "tsv"
            elif args.csv:
                fmt = "csv"
            output_path = get_output_path(args.input_file, "_selected", "." + fmt, args.output_dir)
            export_data(new_headers, rows, output_path, fmt=fmt, encoding=Encode)
    elif args.tsv or args.csv or args.dat:
        if not args.input_file:
            print("\n" + "=" * 60)
            print("  ❌  Missing required arguments!\n")
            print("  Please provide an input file for conversion.\n")
            print("  For help, run:\n  python Main_Refactored.py --help")
            print("=" * 60 + "\n")
            sys.exit(2)
        Encode = detect_encoding(args.input_file, os.path.basename(args.input_file))
        headers, rows = replace_header_and_collect(args.input_file, {}, Encode)
        fmt = "dat"
        if args.tsv:
            fmt = "tsv"
        elif args.csv:
            fmt = "csv"
        output_path = get_output_path(args.input_file, "_converted", "." + fmt, args.output_dir)
        export_data(headers, rows, output_path, fmt=fmt, encoding=Encode)
    else: # No specific operation or input file provided
        print("\n" + "=" * 60)
        print("  ❌  Missing required arguments!\n")
        print("  Please provide an input file or use the --merge option.\n")
        print("  For help, run:\n  python Main_Refactored.py --help")
        print("=" * 60 + "\n")