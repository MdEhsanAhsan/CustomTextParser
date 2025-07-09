# 🧠 CustomTextParser
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.x-blue)](https://www.python.org/)
[![Issues](https://img.shields.io/github/issues/MdEhsanAhsan/CustomTextParser)](https://github.com/MdEhsanAhsan/CustomTextParser/issues)
[![Build](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/MdEhsanAhsan/CustomTextParser)

A robust DAT file parser and converter with advanced features for handling complex text formats, encoding detection, and multi-file operations.

---

## 🌟 Features

- **📦 Automatic Encoding Detection**  
  Supports UTF-8, UTF-16 (LE/BE), Windows-1252, and Latin-1 with BOM detection.

- **🔍 Custom Field Parsing**  
  Handles fields enclosed in `þ` (FE hex) and separated by DC4 (`\x14`).

- **🔁 Smart Line Reader**  
  Correctly parses logical lines even with embedded newlines inside quoted fields.

- **📊 Header Management**  
  Extracts headers from the first line or allows replacement via CSV mapping.

- **🧮 Row Validation**  
  Skips malformed rows with field count mismatches (now validates **all rows**).

- **📈 Excel Compatibility**  
  Warns if fields exceed Excel's 32,767 character limit.

- **📄 Flexible Output**  
  Exports to TSV/CSV/DAT with configurable encoding (`utf-16` default, merged DAT files use `utf-8-sig`).

- **🔄 File Comparison**  
  Compares two DAT files row-by-row with optional header mapping.

- **✏️ Header Replacement**  
  Renames headers using a CSV mapping file.

---

## 🔧 CLI Commands

```bash
# Convert DAT to TSV/CSV/DAT
python Main.py input.dat --csv [output.csv]
python Main.py input.dat --tsv [output.tsv]
python Main.py input.dat --dat [output.dat]

# Compare two DAT files
python Main.py file1.dat file2.dat --compare

# Compare with header mapping
python Main.py file1.dat file2.dat --compare -m header_map.csv

# Replace headers in DAT file
python Main.py input.dat --replace-header header_map.csv --replace-output output.dat

```

---

## 📝 Notes

- **Encoding Defaults**:  
  - Exports default to `utf-16`.
  - TSV/CSV exports from merged files retain the **input file's encoding**.

- **Field Format**:  
  Assumes fields are enclosed in `þ` and separated by DC4 (`\x14`).

- **Validation**:  
  Only rows matching the header field count are exported.

- **Customization**:  
  Modify `QUOTE_CHAR`, `FIELD_SEP`, or `EXPORT_ENCODING` in `Main.py` for custom formats.

---

## 📦 Requirements

- **🐍 Python 3.x**
- **🔌 No external dependencies** (uses built-in modules: `csv`, `argparse`, `unicodedata`)

---

## 👤 Author

- **Md Ehsan Ahsan**  
  [GitHub Profile](https://github.com/MdEhsanAhsan)

- **License**: MIT

---

## 📌 Tip

For large datasets, use `utf-16-sig` encoding to ensure proper BOM handling in Excel!
```