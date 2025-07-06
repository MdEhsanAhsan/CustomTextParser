Here's an updated **README.md** with emojis and enhanced documentation for your GitHub repo:

---

# 🧠 CustomTextParser  
*A robust DAT file parser and converter with advanced features*

[![License](https://github.com/MdEhsanAhsan/CustomTextParser/blob/main/LICENSE)](LICENSE)

A Python script to parse custom `.dat` files with quoted fields and special field separators, and export data to CSV/TSV formats. Handles edge cases like embedded newlines, encoding detection, and Excel compatibility warnings.

---

## 🌟 Features  
- 📦 **Automatic Encoding Detection**: Supports UTF-8, UTF-16 (LE/BE), Windows-1252, and Latin-1.  
- 🔍 **Custom Field Parsing**: Handles fields enclosed in `þ` (FE hex) and separated by DC4 (`\x14`).  
- 🔁 **Smart Line Reader**: Correctly parses logical lines even with newlines inside quoted fields.  
- 📊 **Header Management**: Extracts headers from the first line or allows header replacement via mapping.  
- 🧮 **Row Validation**: Skips malformed rows with field count mismatches.  
- 📈 **Excel Compatibility**: Warns if fields exceed Excel's 32,767 character limit.  
- 📄 **Flexible Output**: Exports to UTF-16 TSV with all fields quoted for maximum compatibility.  
- 🔄 **File Comparison**: Compares two DAT files row-by-row with optional header mapping.  
- ✏️ **Header Replacement**: Renames headers using a CSV mapping file.  

---

## 🔍 Usage  
### 🛠️ CLI Commands  
```bash
# Convert DAT to TSV/CSV
python Main.py input.dat --csv [output.tsv]

# Compare two DAT files
python Main.py file1.dat file2.dat --compare

# Compare with header mapping
python Main.py file1.dat file2.dat --compare -m header_map.csv

# Replace headers in DAT file
python Main.py input.dat --replace-header header_map.csv --replace-output output.dat
```

### 🧪 Example  
**Input (`input.dat`)**:
```
þFIRSTBATESþþLASTBATESþ
þ123þþDOEþ
þ124þþSMITHþ
```

**Output (`input.csv`)**:
```tsv
"FIRSTBATES"	"LASTBATES"
"123"	"DOE"
"124"	"SMITH"
```

---

## 📝 Notes  
- **Encoding**: Output files use UTF-16 for Excel compatibility.  
- **Field Format**: Assumes fields are enclosed in `þ` and separated by DC4 (`\x14`).  
- **Validation**: Only rows matching the header field count are exported.  

---

## 📋 Requirements  
- 🐍 Python 3.x  
- 🔌 No external dependencies (uses built-in modules: `csv`, `argparse`, `unicodedata`)  

---

## 🎨 Customization  
- Modify `QUOTE_CHAR` (`\xfe`) and `FIELD_SEP` (`\x14`) in `Main.py` for custom formats.  
- Adjust output format (e.g., delimiter, encoding) in the `export_to_tsv()` function.  

---

## 👤 Author  
**Md Ehsan Ahsan**  
[GitHub Profile](https://github.com/MdEhsanAhsan)  
MIT License  

---

### 📌 Tip  
For large datasets, use `utf-16-sig` encoding to ensure proper BOM handling in Excel!

---

Let me know if you'd like to add badges for Python version, license, or build status! 🚀