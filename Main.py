import codecs
import io
from heapq import merge
import sys
from unicodedata import category, normalize
import os
import csv
import argparse
from collections import defaultdict, OrderedDict
import hashlib
import mmap
import time
import chardet
from Module.quote_split_chunked import QuoteLineSplitter  # Import the Cython module for optimized performance


# === Global Constants ===
QUOTE_CHAR = '\xfe'  # Quote character used to enclose fields.
FIELD_SEP = '\x14'   # Field separator (DC4)
LINE_ENDINGS = ('\n', '\r\n', '\r')
MAX_MEMORY_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
EXPORT_ENCODING = 'utf-8-sig'

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
def get_output_path(input_path, suffix="", ext=".dat", output_dir=None, filename=None):
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    if ext == ".tsv":
        ext = ".csv"
    default_name = f"{base_name}{suffix}{ext}"

    # Case 1: --filename is used
    if filename:
        user_ext = os.path.splitext(filename)[1].lower()
        expected_ext = ext.lower()
        if user_ext and user_ext != expected_ext:
            print(f"⚠️ Output file extension '{user_ext}' does not match selected format '{expected_ext}'. Changing to '{expected_ext}'.")
            filename = os.path.splitext(filename)[0] + expected_ext
        elif not user_ext:
            filename += expected_ext
        return os.path.join(os.path.dirname(input_path), filename)

    # Case 2: --output-dir is used
    if output_dir:
        # Normalize path
        output_dir = os.path.normpath(output_dir)
        user_ext = os.path.splitext(output_dir)[1].lower()
        expected_ext = ext.lower()

        # Case 2a: Full file path
        if user_ext:
            if user_ext != expected_ext:
                print(f"⚠️ Output file extension '{user_ext}' does not match selected format '{expected_ext}'. Changing to '{expected_ext}'.")
                output_path = os.path.splitext(output_dir)[0] + expected_ext
            else:
                output_path = output_dir
            return output_path

        # Case 2b: Directory path
        return os.path.join(output_dir, default_name)

    # Case 3: No output_dir or filename → default to input file's directory
    return os.path.join(os.path.dirname(input_path), default_name)


def detect_and_open(file_path, mode='r'):
    encoding = detect_encoding(file_path, os.path.basename(file_path))
    if encoding in ('Error', 'No File'):
        raise ValueError(f"Failed to detect encoding for {file_path}")
    return open(file_path, mode, encoding=encoding)


def read_headers_and_rows(file_path, encoding=None):
    if encoding is None:
        encoding = detect_encoding(file_path, os.path.basename(file_path))
    headers = []
    rows = []
    for i, line in enumerate(read_dat_file_smart(file_path, encoding=encoding)):
        if i == 0:
            headers = [strip_one_quote(h) for h in line.split(QUOTE_CHAR + FIELD_SEP + QUOTE_CHAR)]
            validate_headers(headers, os.path.basename(file_path))
        else:
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


# === Export Functions ===
def export_to_tsv(headers, rows, output_path, encoding):
    with open(output_path, 'w', newline='', encoding=encoding) as tsvfile:
        writer = csv.DictWriter(tsvfile, fieldnames=headers, delimiter='\t', quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows([{h: str(row.get(h, "")) for h in headers} for row in rows])
    print(f"Exported {len(rows)} rows to {output_path}")


def export_to_csv(headers, rows, output_path, encoding):
    find_encoding_errors(rows, headers, encoding=encoding)  # or 'ansi'
    with open(output_path, 'w', newline='', encoding=encoding) as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers, delimiter=',', quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows([{h: str(row.get(h, "")) for h in headers} for row in rows])
    print(f"Exported {len(rows)} rows to {output_path}")


def export_to_dat(headers, rows, output_path, encoding):
    sep = QUOTE_CHAR + FIELD_SEP + QUOTE_CHAR
    with open(output_path, 'w', encoding=encoding, newline='') as f:
        header_line = sep.join(headers)
        f.write(f"{QUOTE_CHAR}{header_line}{QUOTE_CHAR}\r\n")
        for row in rows:
            fields = [str(row.get(h, '')) for h in headers]
            line = sep.join(fields)
            f.write(f"{QUOTE_CHAR}{line}{QUOTE_CHAR}\r\n")
    print(f"Exported {len(rows)} rows to {output_path}")


# === Excel Warnings ===
def excel_warning(headers, rows, warn_limit=32767, max_warnings=20):
    """
    Collects warnings for Excel cell length and prints a compact table.
    """
    warnings = []
    for row_idx, row in enumerate(rows, 2):
        for h in headers:
            val = str(row.get(h, ""))
            if len(val) > warn_limit:
                warnings.append((h, row_idx, len(val)))
                if len(warnings) >= max_warnings:
                    break
        if len(warnings) >= max_warnings:
            break

    if warnings:
        print("════════════════════════════════════════════════════════════════════════════════════════════════════════")
        print(f"{'FieldName':<15}{'RowNo.':<10}{'CurrentLength':<15}")
        for h, row_idx, length in warnings:
            print(f"{h:<15}{row_idx:<10}{length:<15}")
        if len(warnings) == max_warnings:
            print(f"...Further warnings suppressed. Only first {max_warnings} shown.")
        print("Warning: Excel may not display these cells correctly. Consider truncating or splitting.")
        print("════════════════════════════════════════════════════════════════════════════════════════════════════════")


def find_encoding_errors(rows, headers, encoding='cp1252'):
    for line_num, row in enumerate(rows, 1):
        for h in headers:
            val = str(row.get(h, ''))
            try:
                val.encode(encoding)
            except UnicodeEncodeError as e:
                print(f"Encoding error on line {line_num}, column '{h}': {repr(val)}")
                print(f" -> Bad character: {repr(val[e.start:e.end])}")
                return  # stop on first error or remove this to check all

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
            size_chunk = 1 * 1024 * 1024  # 1 MB chunk size for large files
            raw = file.read(size_chunk)  # Read first 1MB for better analysis

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
            elif raw.startswith(b'\xc3\xbe'):
                print(f"{fname} is detected as UTF-8")
                return 'utf-8'
            try:
                
                enc = chardet.detect(raw)
                print(f"{fname} is detected as {enc['encoding']} (confidence: {enc['confidence']:.2%})")
                if enc['encoding'] is None or enc['confidence'] < 0.5:
                    print(f"Warning: Low confidence in encoding detection for {fname}. Defaulting to 'utf-8'.\nIf you encounter issues, consider manually change the encoding of file to UTF-8 BOM.")
                    return 'utf-8'
                return enc['encoding']
            except Exception as e:
                print(f"Error detecting encoding for {fname}: {e}")
                return 'Error'

    except FileNotFoundError:

        print(f"File not found: {file_path}")

        return 'No File'

# === Line Reader & Parser ===

def read_dat_file_smart(file_path, encoding):
    file_size = os.path.getsize(file_path)
    chunk_size = 2 * 1024 * 1024 # 2 MB chunk size for large files

    if file_size <= MAX_MEMORY_FILE_SIZE:
        with open(file_path, 'r', encoding=encoding, errors='replace', newline='') as f:
            content = f.read()
            # yield from _process_content(content)
        splitter = QuoteLineSplitter()
        for line in splitter.feed_chunk(content) + splitter.flush():
            yield line
    else:
        decoder = codecs.getincrementaldecoder(encoding)(errors='replace')
        splitter = QuoteLineSplitter()

        with open(file_path, 'rb') as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                pos = 0
                while pos < file_size:
                    end = min(pos + chunk_size, file_size)
                    chunk = mm[pos:end]
                    pos = end

                    decoded = decoder.decode(chunk)
                    for line in splitter.feed_chunk(decoded):
                        yield line

                for line in splitter.flush():
                    yield line
    print(f"-----\nFileSize:{human_readable_size(file_size)}\n-----")

# === Human Readable Size Function ===
def human_readable_size(size_in_bytes):
    """
    Convert a file size in bytes to a human-readable string (KB, MB, GB).
    """
    if size_in_bytes < 1024:
        return f"{size_in_bytes} bytes"
    elif size_in_bytes < 1024**2:
        return f"{size_in_bytes / 1024:.2f} KB"
    elif size_in_bytes < 1024**3:
        return f"{size_in_bytes / (1024**2):.2f} MB"
    else:
        return f"{size_in_bytes / (1024**3):.2f} GB"

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


# === Splitting Utilities ===

def split_rows_evenly(rows, n_splits):
    """Split a list of rows into n_splits parts as evenly as possible.
    Returns a list of lists.
    """
    if n_splits <= 0:
        raise ValueError("n_splits must be >= 1")
    print(f"Splitting {len(rows)} rows into {n_splits} parts evenly.")
    print("-----")
    total = len(rows)
    remainder = total % n_splits
    effective_total = total - remainder

    base = effective_total // n_splits
    parts = []

    idx = 0
    for i in range(n_splits):
        size = base
        # add remainder only to the LAST split
        if i == n_splits - 1:
            size += remainder

        parts.append(rows[idx:idx + size])
        idx += size

    return parts



def chunk_rows(rows, chunk_size):
    """Yield successive chunks of size chunk_size from rows."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be >= 1")
    print(f"Splitting {len(rows)} rows into {chunk_size} rows in each file.")
    print("-----")
    for i in range(0, len(rows), chunk_size):
        yield rows[i:i+chunk_size]


def split_rows_grouped(rows, group_field, n_splits=None, max_rows=None):
    """Split rows while keeping groups (by group_field) intact.

    If n_splits is provided, will distribute groups to balance total row counts across n_splits buckets.
    If max_rows is provided, will create buckets until each bucket has approx <= max_rows (groups are never split).
    If a single group's size > max_rows, the group will be placed alone in a bucket and a warning printed.
    """
    if not group_field:
        raise ValueError("group_field is required for grouped splitting")
    print(f"Splitting {len(rows)} rows into {max_rows} in each file.")
    print("-----")
    # Build groups
    groups = {}
    for r in rows:
        key = r.get(group_field)
        groups.setdefault(key, []).append(r)

    group_items = [(k, len(v), v) for k, v in groups.items()]

    # If n_splits mode: use greedy balance (place largest groups first into smallest bucket)
    if n_splits is not None:
        if n_splits <= 0:
            raise ValueError("n_splits must be >= 1")
        # initialize buckets: list of (size, list)
        buckets = [(0, []) for _ in range(n_splits)]
        # sort groups by descending size
        group_items.sort(key=lambda x: x[1], reverse=True)
        for _, size, grp in group_items:
            # pick bucket with min size
            min_idx = min(range(len(buckets)), key=lambda i: buckets[i][0])
            buckets[min_idx][1].extend(grp)
            buckets[min_idx] = (buckets[min_idx][0] + size, buckets[min_idx][1])
        return [b[1] for b in buckets]

    # If max_rows mode: fill sequential buckets until max reached, start new bucket
    if max_rows is not None:
        if max_rows <= 0:
            raise ValueError("max_rows must be >= 1")

        buckets = []
        current_bucket = []
        current_size = 0
        # iterate groups in any stable order
        for _, size, grp in sorted(group_items, key=lambda x: x[1], reverse=True):
            if size > max_rows and current_size == 0:
                # group alone will exceed max_rows; place alone with a warning
                print(f"⚠️ Group of size {size} exceeds max_rows {max_rows}; group placed alone in its own file.")
                buckets.append(list(grp))
                continue
            if current_size + size > max_rows and current_bucket:
                buckets.append(current_bucket)
                current_bucket = []
                current_size = 0
            current_bucket.extend(grp)
            current_size += size
        if current_bucket:
            buckets.append(current_bucket)
        return buckets

    # If neither n_splits nor max_rows provided, just return single group of all rows
    return [rows]


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

    # Check if file names are the same
    if os.path.basename(file1_path) == os.path.basename(file2_path):
        File1_Value = file1_path  # Use full path for file 1
        File2_Value = file2_path  # Use full path for file 2
    else:
        File1_Value = os.path.basename(file1_path)  # Use base name for file 1
        File2_Value = os.path.basename(file2_path)  # Use base name for file 2

    # Compare row values
    diffs = []
    row_count = min(len(rows1), len(rows2))
    for idx in range(row_count):
        r1 = rows1[idx]
        r2 = rows2[idx]
        for h1, h2 in zip(mapped_headers1, mapped_headers2):
            v1 = r1.get(h1, "")
            v2 = r2.get(h2, "")

            # Normalize to a canonical Unicode form and strip BOM-like characters so
            # visually-equal text hashes the same regardless of source encoding.
            nv1 = normalize('NFC', v1).lstrip('\ufeff')
            nv2 = normalize('NFC', v2).lstrip('\ufeff')

            if nv1 != nv2:
                v1hash = hashlib.sha256(nv1.encode('utf-8')).hexdigest()
                v2hash = hashlib.sha256(nv2.encode('utf-8')).hexdigest()
                diffs.append({
                    "Row": idx + 2,  # +2 accounts for header and 1-based indexing
                    "Field": h1 if h1 == h2 else f"{h1} ↔ {h2}",
                    File1_Value: v1,
                    File2_Value: v2,
                    "File_1_Hash": v1hash,
                    "File_2_Hash": v2hash
                })

    if not diffs:
        print("No differences found.")
        return None, None

    fieldnames = ["Row", "Field", File1_Value, File2_Value,"File_1_Hash","File_2_Hash"]
    return fieldnames, diffs

# === Replace Header ===
def replace_header_and_collect(input_file_path, header_map, encoding, is_replace=False):
    """
    Reads a DAT file, replaces headers using header_map, and returns new headers and rows.
    Displays fields that were not renamed and unused mappings only if is_compare is True.
    """
    new_headers = []
    rows = []
    unused_mappings = set(header_map.keys()) if header_map else set()  # Track unused mappings only if header_map exists

    for i, line in enumerate(read_dat_file_smart(input_file_path, encoding)):
        if i == 0:
            headers = [strip_one_quote(h) for h in line.split(QUOTE_CHAR + FIELD_SEP + QUOTE_CHAR)]
            validate_headers(headers, os.path.basename(input_file_path))
            new_headers = [header_map.get(h, h) for h in headers] if header_map else headers

            if header_map and is_replace:  # Only display warnings if is_compare is True
                unused_mappings -= set(headers)  # Remove used mappings
                not_renamed = [h for h in headers if h not in header_map]
                if not_renamed:
                    print(f"⚠️ The following fields were not renamed: {', '.join(not_renamed)}")
                    print("\n===================================================================")
                if unused_mappings:
                    print(f"⚠️ The following mappings were unused: {', '.join(unused_mappings)}")
                    print("\n===================================================================")
        else:
            parsed_row = parse_line(line, headers)
            if parsed_row:
                mapped_row = {new_headers[idx]: value for idx, (header, value) in enumerate(parsed_row.items())}
                rows.append(mapped_row)

    return new_headers, rows
# === SPECIAL FUNCTIONS FOR CSV TO DAT ===

# def read_csv(filepath, encoding):
#     """
#     Reads a CSV file and returns headers and rows as a list of dictionaries.
#     """
#     with open(filepath, newline='', encoding=encoding) as csvfile:
#         sample = csvfile.read(1024)
#         csvfile.seek(0)
#         dialect = csv.Sniffer().sniff(sample)
#         reader = csv.reader(csvfile, dialect)
#         headers = next(reader)  # Read the header row
#         rows = [dict(zip(headers, row)) for row in reader]  # Convert rows to dictionaries
#     return headers, rows

def read_csv(filepath,  encoding=None):
    rows = []
    delimiter=","

    with open(filepath, "r", encoding=encoding, newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)

        try:
            headers = next(reader)
        except StopIteration:
            raise ValueError("CSV file is empty")

        header_count = len(headers)

        for line_num, row in enumerate(reader, start=2):
            if len(row) != header_count:
                raise ValueError(
                    f"QC FAILED at line {line_num}: "
                    f"Expected {header_count} columns, found {len(row)}"
                )

            rows.append(dict(zip(headers, row)))

    return headers, rows

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
            validate_headers(headers, os.path.basename(path))
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
        
    #m_EXPORT_ENCODING = 'utf-8-sig'  # Set default export encoding for merged files
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
        export_data(all_headers, all_rows, output_base, fmt=fmt, encoding=EXPORT_ENCODING)

    # Write log CSV
    log_path = get_output_path(merge_file, "_merge_log", ".csv", output_dir)
    export_data(["Group", "File", "RowCount"], group_log, log_path, fmt="csv", encoding=EXPORT_ENCODING)
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

# === Join DAT Files ===
def join_dat_files(file1_path, file2_path, encoding1, encoding2, key_field_string):
    key_fields = [k.strip() for k in key_field_string.strip().split()]
    headers1, rows1 = read_headers_and_rows(file1_path, encoding1)
    headers2, rows2 = read_headers_and_rows(file2_path, encoding2)

    # Validate key presence
    for key in key_fields:
        if key not in headers1 or key not in headers2:
            print(f"❌ Key '{key}' not found in both files.")
            sys.exit(2)

    # Build lookup dictionaries
    def build_lookup(rows, source):
        key_map = {}
        duplicates = set()
        for row in rows:
            key = tuple(row.get(k, "").strip() for k in key_fields)
            if key in key_map:
                duplicates.add(key)
            key_map[key] = row
        if duplicates:
            print(f"❌ Duplicate key(s) found in {source}:")
            for d in duplicates:
                print(f"   - {d}")
            sys.exit(2)
        return key_map

    lookup1 = build_lookup(rows1, "File1")
    lookup2 = build_lookup(rows2, "File2")

    keys1 = set(lookup1.keys())
    keys2 = set(lookup2.keys())

    if keys1 != keys2:
        print("❌ Strict join failed: Key sets do not match exactly.")
        sys.exit(2)

    # Detect overlapping headers
    overlapping_headers = set(headers1) & set(headers2) - set(key_fields)
    if overlapping_headers:
        print("⚠️ Detected duplicate field(s) in both files (excluding keys):")
        for h in overlapping_headers:
            print(f"   - {h}")

        print("\nHow would you like to resolve these?")
        print("  [1] Add suffix to file2 fields (e.g., 'Score_2')")
        print("  [2] Keep file1 values only")
        print("  [3] Overwrite with file2 values")
        while True:
            choice = input("Enter choice [1/2/3]: ").strip()
            if choice in {"1", "2", "3"}:
                break
            print("Invalid choice. Please enter 1, 2, or 3.")
        if choice == "1":
            duplicate_mode = "suffix"
        elif choice == "2":
            duplicate_mode = "file1"
        else:
            duplicate_mode = "file2"
    else:
        duplicate_mode = "file1"  # default (won't matter since no overlaps)

    # Apply user strategy
    header_map2 = {}
    if duplicate_mode == "suffix":
        for h in headers2:
            if h in key_fields:
                header_map2[h] = h
            elif h in overlapping_headers:
                header_map2[h] = f"{h}_2"
            else:
                header_map2[h] = h
    elif duplicate_mode == "file1":
        for h in headers2:
            if h not in headers1:
                header_map2[h] = h
    elif duplicate_mode == "file2":
        for h in headers2:
            header_map2[h] = h

    # Final headers
    if duplicate_mode == "suffix":
        unified_headers = headers1 + [header_map2[h] for h in headers2 if h not in headers1 or h in overlapping_headers]
    elif duplicate_mode == "file1":
        unified_headers = headers1 + [h for h in headers2 if h not in headers1]
    elif duplicate_mode == "file2":
        unified_headers = headers1.copy()
        for h in headers2:
            if h not in key_fields and h not in unified_headers:
                unified_headers.append(h)

    # Merge rows
    joined_rows = []
    for key in sorted(keys1):
        row1 = lookup1[key]
        row2 = lookup2[key]
        merged_row = row1.copy()

        for h in headers2:
            if h in key_fields:
                continue
            if duplicate_mode == "file1" and h in overlapping_headers:
                continue
            merged_name = header_map2.get(h, h)
            merged_row[merged_name] = row2.get(h, "")

        joined_rows.append(merged_row)

    print(f"✅ Join successful on {len(joined_rows)} rows using strategy: {duplicate_mode}")
    return unified_headers, joined_rows


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

def validate_headers(headers, source="Input"):
    """
    Checks for duplicate headers and exits if any are found.
    """
    seen = set()
    duplicates = set()
    for h in headers:
        if h in seen:
            duplicates.add(h)
        seen.add(h)
    if duplicates:
        print(f"❌ Duplicate header(s) found in {source}: {', '.join(duplicates)}")
        sys.exit(2)

# === Handler functions ===

def handle_convert(args):
    if not args.input_file:
        print("❌ Please provide an input file for conversion.")
        sys.exit(2)
    Encode = detect_encoding(args.input_file, os.path.basename(args.input_file))
    ext = os.path.splitext(args.input_file)[1][1:]
    if ext == 'csv':
        headers, rows = read_csv(args.input_file, Encode)
    else:
        headers, rows = replace_header_and_collect(args.input_file, {}, Encode)

    fmt = "csv" if args.csv else "tsv" if args.tsv else "dat"

    # Splitting behavior
    if args.split or args.max_rows:
        # Decide split parts
        if args.group_by:
            parts = split_rows_grouped(rows, args.group_by, n_splits=args.split, max_rows=args.max_rows)
        else:
            if args.split:
                parts = split_rows_evenly(rows, args.split)
            else:
                parts = list(chunk_rows(rows, args.max_rows))

        # Export each part
        for i, part in enumerate(parts, start=1):
            suffix = f"_part{i}"
            output_path = get_output_path(args.input_file, suffix, "." + fmt, args.output_dir, args.filename)
            export_data(headers, part, output_path, fmt=fmt, encoding=Encode)
        print(f"✅ Split into {len(parts)} files completed.")
    else:
        # Single-file export (original behavior)
        suffix = "_converted"
        output_path = get_output_path(args.input_file, suffix, "." + fmt, args.output_dir, args.filename)
        export_data(headers, rows, output_path, fmt=fmt, encoding=Encode)

def handle_compare(args):
    if not args.input_file or not args.input_file2:
        print("❌ Please provide both input files for comparison.")
        sys.exit(2)
    mapping = load_mapping_file(args.mapping) if args.mapping else None
    headers, diffs = compare_dat_files(args.input_file, args.input_file2, mapping)
    if diffs:
        fmt = "csv" if args.csv else "tsv" if args.tsv else "dat"
        output_path = get_output_path(args.input_file, "_diff", "." + fmt, args.output_dir,args.filename)
        export_data(headers, diffs, output_path, fmt=fmt)
    else:
        print("No differences found during comparison.")

def handle_replace_header(args):
    if not args.input_file:
        print("❌ Please provide an input file for header replacement.")
        sys.exit(2)
    Encode = detect_encoding(args.input_file, os.path.basename(args.input_file))
    header_map = get_mapping_dict(args.replace_header)
    new_headers, rows = replace_header_and_collect(args.input_file, header_map, Encode,is_replace=args.replace_header)
    fmt = "csv" if args.csv else "tsv" if args.tsv else "dat"
    output_path = get_output_path(args.input_file, "_Replaced", "." + fmt, args.output_dir,args.filename)
    export_data(new_headers, rows, output_path, fmt=fmt, encoding=Encode)

def handle_delete(args):
    if not args.input_file or not args.delete:
        print("❌ Please provide both input file and delete file.")
        sys.exit(2)
    delete_rows(args.input_file, args.delete, args)

def handle_select(args):
    if not args.input_file or not args.select:
        print("❌ Please provide both input file and select file.")
        sys.exit(2)
    Encode = detect_encoding(args.input_file, os.path.basename(args.input_file))
    with open(args.select, encoding=detect_encoding(args.select, os.path.basename(args.select))) as f:
        selected_headers = [line.strip() for line in f if line.strip()]
    if not selected_headers:
        print("❌ No headers selected.")
        sys.exit(2)
    new_headers, rows = select_fields_and_collect(args.input_file, selected_headers, Encode)
    fmt = "csv" if args.csv else "tsv" if args.tsv else "dat"
    output_path = get_output_path(args.input_file, "_selected", "." + fmt, args.output_dir,args.filename)
    export_data(new_headers, rows, output_path, fmt=fmt, encoding=Encode)

def handle_join(args):
    if not args.input_file or not args.input_file2:
        print("❌ Please provide both input files for joining.")
        sys.exit(2)
    if not args.key:
        print("❌ Please specify --key with one or more fields using --key \"FieldA FieldB\"")
        sys.exit(2)

    Encode1 = detect_encoding(args.input_file, os.path.basename(args.input_file))
    Encode2 = detect_encoding(args.input_file2, os.path.basename(args.input_file2))

    headers, joined_rows = join_dat_files(args.input_file, args.input_file2, Encode1, Encode2, args.key)
    fmt = "csv" if args.csv else "tsv" if args.tsv else "dat"
    output_path = get_output_path(args.input_file, "_joined", "." + fmt, args.output_dir,args.filename)
    export_data(headers, joined_rows, output_path, fmt=fmt, encoding=Encode1)

def handle_reorder_header(args):
    if not args.input_file:
        print("❌ Please provide an input file for header reordering.")
        sys.exit(2)
    Encode = detect_encoding(args.input_file, os.path.basename(args.input_file))

    if not args.reorder_header:
        print("❌ Please provide a header order file using --reorder-header.")
        sys.exit(2)

    order_file = args.reorder_header
    order_enc = detect_encoding(order_file, os.path.basename(order_file))

    # Read desired header order from the provided file
    try:
        with open(order_file, encoding=order_enc) as f:
            desired_order = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"❌ Header order file not found: {order_file}")
        sys.exit(2)

    if not desired_order:
        print("❌ Header order file is empty.")
        sys.exit(2)

    if len(set(desired_order)) != len(desired_order):
        print("❌ Duplicate header names found in the header order file. Please remove duplicates.")
        sys.exit(2)

    # Read input file headers and validate
    line_iter = read_dat_file_smart(args.input_file, Encode)
    try:
        header_line = next(line_iter)
    except StopIteration:
        print(f"❌ Input file appears to be empty: {args.input_file}")
        sys.exit(2)

    headers = [strip_one_quote(h) for h in header_line.split(QUOTE_CHAR + FIELD_SEP + QUOTE_CHAR)]
    validate_headers(headers, os.path.basename(args.input_file))

    # Check file row integrity
    if not file_has_valid_rows(args.input_file, headers, Encode):
        print("❌ Input file has invalid rows. Aborting reorder operation.")
        return

    # Compute new header order: include requested headers (if present) first, append any remaining headers
    missing_in_input = [h for h in desired_order if h not in headers]
    if missing_in_input:
        print(f"⚠️ The following headers from the order file were not found in the input file and will be ignored: {', '.join(missing_in_input)}")

    new_headers = [h for h in desired_order if h in headers]
    remaining = [h for h in headers if h not in new_headers]
    new_headers.extend(remaining)

    # Collect rows in the new order
    rows = []
    for i, line in enumerate(read_dat_file_smart(args.input_file, Encode)):
        if i == 0:
            continue
        parsed = parse_line(line, headers)
        if parsed:
            ordered_row = {h: parsed.get(h, "") for h in new_headers}
            rows.append(ordered_row)

    fmt = "csv" if args.csv else "tsv" if args.tsv else "dat"
    output_path = get_output_path(args.input_file, "_reordered", "." + fmt, args.output_dir, args.filename)
    export_data(new_headers, rows, output_path, fmt=fmt, encoding=Encode)
    print(f"✅ Header reorder completed. Output written to {output_path}")

# === Print Logo ===
def print_logo():
    logo = r'''
   ______              
  / __/ /  ______ ____ 
 / _// _ \(_-< _ `/ _ \
/___/_//_/___|_,_/_//_/
    -----Author: Ehsan
    Version: 3.2.0
    Date: 2025-07-27
    DAT File Converter Utility
    GitHub: https://github.com/MdEhsanAhsan/CustomTextParser/tree/Cython_Version
    -------------------------
    '''
    print(logo)
# === Argument Parsing ===

def get_arguments():
    parser = argparse.ArgumentParser(
        description="DAT File converter utility",
        formatter_class=argparse.RawTextHelpFormatter
    )

    # 🔹 Positional Arguments
    parser.add_argument("input_file", nargs='?', help="Path to first input DAT file")
    parser.add_argument("input_file2", nargs="?", help="Path to second input DAT file (for compare)")

    # 🔸 Output Format Options
    output_group = parser.add_argument_group("Output Format Options")
    output_group.add_argument("--csv", action="store_true", help="Convert input to CSV (Comma Separated Value)")
    output_group.add_argument("--tsv", action="store_true", help="Export output as TSV (Tab Separated Value)")
    output_group.add_argument("--dat", action="store_true", help="Export output as DAT")

    # 🔍 Comparison & Join Options
    compare_group = parser.add_argument_group("Comparison and Join Options")
    compare_group.add_argument("--compare", "--c", action="store_true", help="Compare two DAT files")
    compare_group.add_argument("--mapping", "--m", metavar="MAPPING_FILE", help="Header mapping file for comparison")
    compare_group.add_argument("--key", metavar="KEY_FIELDS", help="Key field(s) for joining. e.g., --key \"User ID\"")
    compare_group.add_argument("--join", action="store_true", help="Join two DAT files into a single file based on Key Field")

    # 🧩 Data Transformation Options
    transform_group = parser.add_argument_group("Data Transformation Options")
    transform_group.add_argument("--merge", action="store_true", help="Merge multiple DAT files into groups")
    transform_group.add_argument("--delete", metavar="DELETE_FILE", help="Delete rows based on field values")
    transform_group.add_argument("--select", metavar="SELECT_FILE", help="Select fields based on header values")
    transform_group.add_argument("--replace-header", "--r", metavar="HEADER_MAPPING_FILE", help="Replace headers using a mapping file")
    transform_group.add_argument("--reorder-header", "--reorder", metavar="HEADER_ORDER_FILE", help="Reorder headers based on a specified order file")

    # 🔸 Splitting Options
    split_group = parser.add_mutually_exclusive_group()
    split_group.add_argument("--split", type=int, metavar="N", help="Split converted output into N files (even split)")
    split_group.add_argument("--max-rows", type=int, metavar="N", help="Maximum rows per output file (e.g., 10000).")
    transform_group.add_argument("--group-by", metavar="FIELD", help="Keep groups (by FIELD) intact when splitting")  

    # 📁 Output Control
    exclusive_output = output_group.add_mutually_exclusive_group() # Ensure only one of these can be used at a time
    exclusive_output.add_argument("--filename", "--f", metavar="FileNames", help="Output file name pattern")
    exclusive_output.add_argument("--output-dir", "--o", metavar="DIR", help="Directory for output files")
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
    print_logo()
    start_time = time.time()
    args = get_arguments()

    if args.merge and args.input_file:
        args.merge = args.input_file
        args.input_file = None
        Merge_dats(args.merge, args)
    elif args.compare:
        handle_compare(args)
    elif args.replace_header:
        handle_replace_header(args)
    elif args.delete:
        handle_delete(args)
    elif args.select:
        handle_select(args)
    elif args.join:
        handle_join(args)
    elif args.reorder_header:
        handle_reorder_header(args)
    elif args.csv or args.tsv or args.dat:
        handle_convert(args)
    else:
        print("❌ No valid operation provided. Run with --help to see options.")
        sys.exit(2)
    print(f"Elapsed time: {time.time() - start_time:.2f} seconds")
