# CustomTextParser

A Python script to robustly parse custom `.dat` files with quoted fields and special field separators, and export the data to a `.csv` file. The script automatically detects file encoding, handles malformed rows, and warns about Excel cell size limits.

## Features

- **Automatic Encoding Detection:** Detects UTF-8, UTF-16, Windows-1252, and Latin-1 encodings.
- **Custom Field Parsing:** Handles fields enclosed in a custom quote character (`þ`, `\xfe`) and separated by a custom separator (DC4, `\x14`).
- **Smart Line Reading:** Correctly reads logical lines, even if newlines appear inside quoted fields.
- **Header Extraction:** Uses the first line as headers.
- **Row Validation:** Skips rows where the number of fields does not match the header count.
- **Excel Compatibility Warning:** Warns if any field exceeds Excel’s cell limit (32,767 characters).
- **Automatic Output Path:** Exports to a `.csv` file with the same name as the input `.dat` file.
- **TSV Output:** Exports as tab-separated values with all fields quoted, using UTF-16 encoding for maximum compatibility.

## Usage

1. **Place your `.dat` file** in a known location.
2. **Edit the script** to set the `input_file_path` variable to your file’s path.
3. **Run the script:**
   ```sh
   python Main.py
   ```
4. **Output:**  
   - The script will create a `.csv` file in the same directory as your input file.
   - Any malformed rows (field count mismatch) will be skipped and reported in the console.
   - Warnings will be printed if any field exceeds Excel’s cell size limit.

## Example

Suppose your input file is:
```
þFIRSTBATESþþLASTBATESþ
þ123þþDOEþ
þ124þþSMITHþ
```

The script will produce `Test.csv` (tab-separated, all fields quoted) in the same folder.

## Notes

- The script expects fields to be enclosed in `þ` and separated by the DC4 character.
- Only rows matching the header field count are exported.
- Output is encoded as UTF-16 for best compatibility with Excel and special characters.

## Requirements

- Python 3.x

## Customization

- To change the input file, modify the `input_file_path` variable at the top of the script.
- To change the output format or encoding, edit the file writing section at the end of the script.

---

**Author:**  
Md Ehsan Ahsan
