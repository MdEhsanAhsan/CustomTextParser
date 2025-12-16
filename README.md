<!-- SEO: Concordance DAT to CSV, load file converter, export DAT to Excel, .DAT parsing tool, smart DAT file reader, merge Concordance load files, remove rows from DAT -->

# 📂 CustomTextParser

## 🔄 Concordance `.DAT` File Toolkit

**Easily convert and manipulate Concordance `.DAT` load files — perfect for legal e-discovery, metadata extraction, and bulk processing.**

---

### 🛠 What It Does

A powerful Python CLI tool designed to handle complex `.DAT` files with custom delimiters (`þ`, control characters), broken encodings, and Excel-incompatible data.

This tool can:

* ✅ Convert `.DAT` to `.CSV` to `.DAT`
* 🔁 Compare two `.DAT` files (with optional field mapping)
* 🧠 Replace or remap headers
* 🔗 Merge multiple `.DAT` files intelligently
* 🧹 Delete rows based on field values
* 🎯 Extract and export selected fields

---

---

## ⚡ Cython Acceleration (v1.1+)

This tool now uses **Cython-compiled quote-aware parsing** for maximum speed on large `.DAT` files.

### 🚀 Performance Gain
| File Size   | Rows      | Before (Pure Python) | Now (Cython) |
|-------------|-----------|----------------------|---------------|
| 131 MB      | ~90k      | ~17 sec              | **3.45 sec**  |
| 204 MB      | ~1.1M     | ~52 sec              | **13.56 sec** |
| 1.06 GB     | ~5.7M     | ~300 sec             | **64.39 sec** |

> ✅ Quote-safe, newline-tolerant, and 4–5× faster than the previous version.

### 🧱 How It Works
A custom parser module (`quote_split_chunked.pyx`) is written in Cython and compiled to a native `.pyd` extension, enabling fast, chunked line processing while preserving quote-state logic.

### 🛠 Compiling the Cython Module

Install a C compiler first:
- Windows: [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- Linux: `sudo apt install build-essential python3-dev`
- macOS: `xcode-select --install`

Then build:
```bash
python setup.py build_ext --inplace
```

### ⚙️ Key Features

* Handles Concordance `.DAT` files with embedded line breaks
* Supports various encodings: `UTF-8`, `UTF-16`, `Windows-1252`, and more
* Robust parsing even with Excel’s 32,767 character cell limit
* CLI-first design — ideal for automation and scripting

---

### 🚀 Use Cases

* Legal eDiscovery processing
* Metadata cleanup and normalization
* Custom conversions and field extraction
* Comparing vendor-delivered load files

## 📦 Installation
- 📥 [Download EXE](https://github.com/MdEhsanAhsan/CustomTextParser/releases/tag/v3.0.0)

### Clone the repo

```bash
git clone https://github.com/yourusername/dat-file-tool.git
cd dat-file-tool
```

### Install dependencies (optional)

* Python 3.7+
* Requires: `chardet`
* Optional: `cython` for native-speed parsing

---

### ✨ Features

- ✅ Convert `.dat` to `.csv` | `.csv` to `.dat` or keep as `.dat`
- 🔀 Compare two `.dat` files (with optional header mapping)
- 🧹 Delete specific rows from `.dat` using a value list
- 🔁 Merge `.dat` files by common headers
- 🔤 Auto-detect encoding (UTF-8, UTF-16, Windows-1252, Latin-1)
- 💬 Smart line reader handles embedded newlines and quoted fields
- 📁 Output directory support via `-o DIR`
- ⚠️ Excel field-length warning for long text fields (>32,767 chars)
- 🎯 Select only specific fields from a DAT file using `--select`

| Feature       | Description |
|---------------|-------------|
| `--csv`       | Export DAT file to CSV format (Comma Separated Value) |
| `--tsv`       | Export DAT file to TSV format (Tab Separated Value) |
| `--dat`       | Export to DAT format (default if none specified) |
| `--c`, `--compare` | Compare two DAT files line-by-line |
| `--r`, `--replace-header` | Replace headers using a mapping file (`old_header,new_header`) |
| `--merge`     | Merge multiple DAT files grouped by matching headers |
| `--delete`    | Delete rows based on field values listed in a file |
| `--select`    | Export only selected fields from the DAT file |
| `--join`       | Strictly join two DAT files using a key field, with duplicate header conflict resolution |
|`--key`        | Key field required to perform join |
| `--o`, `--output-dir`      | Specify output directory for generated files |

---

## 🧪 Usage Examples

### 🔁 Convert DAT to CSV / TSV

```bash
python Main.py input.dat --csv
# Output: input_converted.csv

python Main.py input.dat --tsv
# Output: input_converted.tsv
```
## 🎥 Demo Example
![Demo Animation](GIF/ToConvert.gif)

You can also specify custom output paths:

```bash
python Main.py input.dat --csv output.csv
```

---

---

#### 2. **Compare Two Files**

Compare two DAT files and generate a detailed difference report:

```bash
# Simple comparison
python Main.py file1.dat file2.dat --compare

# With header mapping (useful for comparing files with different headers)
python Main.py file1.dat file2.dat --compare --mapping mapping.txt
```

**Mapping File Format** (`mapping.txt`):
```
OldHeader1,NewHeader1
OldHeader2,NewHeader2
```

**Output**: Creates `file1_diff.csv` containing all differences with SHA256 hashes for verification.

---

#### 3. **Replace Headers**

Replace or rename column headers using a mapping file:

```bash
python Main.py data.dat --replace-header mapping.txt
```

**Mapping File Format**:
```
OldName,NewName
Age,PersonAge
Score,TestScore
```

**Output**: Creates `data_Replaced.dat` with renamed headers.

---

#### 4. **Select Specific Fields**

Extract only selected columns from a file:

```bash
python Main.py data.dat --select fields.txt
```

**Select File Format** (`fields.txt`):
```
Name
Email
Age
```

**Output**: Creates `data_selected.dat` containing only the specified fields.

---

#### 5. **Delete Rows**

Remove rows matching specific field values:

```bash
python Main.py data.dat --delete delete_list.txt
```

**Delete File Format** (`delete_list.txt`):
```
Status
Inactive
Deleted
Suspended
```

First line specifies the field, subsequent lines are values to delete.

**Output**: 
- Creates `data{kept}.dat` (rows to keep)
- Creates `data{removed}.dat` (rows deleted)

---

#### 6. **Join Two Files**

Perform a strict inner join on two DAT files based on key fields:

```bash
python Main.py file1.dat file2.dat --join --key "UserID"

# Multiple key fields
python Main.py file1.dat file2.dat --join --key "UserID Department"
```

**Features**:
- Validates key field existence in both files
- Detects and handles duplicate headers with three resolution modes:
  1. **Suffix mode**: Adds `_2` to file2 column names
  2. **File1 mode**: Keeps file1 values (default)
  3. **File2 mode**: Overwrites with file2 values
- Detects and reports duplicate keys with error handling

**Output**: Creates `file1_joined.dat` containing merged data.

---

#### 7. **Merge Multiple Files**

Merge multiple DAT files with automatic header validation:

```bash
python Main.py merge_list.txt --merge
```

**Merge List Format** (`merge_list.txt`):
```
/path/to/file1.dat
/path/to/file2.dat
/path/to/file3.dat
```

**Features**:
- Groups files by header hash
- Creates separate output files for each group
- Generates merge log with file counts and row statistics
- Validates file existence and readability
- Excludes problematic files with detailed warnings

**Output**: 
- Creates `merge_list_group_1.dat`, `merge_list_group_2.dat`, etc.
- Creates `merge_list_merge_log.csv` with merge statistics

---

## ⚙️ Optional Arguments

| Flag         | Description |
|--------------|-------------|
| `--o DIR`     | Set output directory |
| `--help`     | Show help message |

---

## 📦 Output Files

* All exports go to the directory specified by `-o`, or default to the input file's folder.
* Output filenames include tags like `{kept}`, `{removed}`, or `_Replaced`.

---

## 💡 Encoding Detection Logic

Handles common encodings reliably:

* ✅ UTF-8
* ✅ UTF-8 with BOM
* ✅ UTF-16 LE / BE (BOM detection)
* 🔍 Uses `chardet` fallback for uncertain cases (based on confidence)
---

## 🧪 Excel Limit Check

Warns if any field exceeds Excel's max cell limit (32,767 chars).

---

## 📁 Requirements

* Python 3.7+
* Dependencies (see `requirements.txt`):

---

## 🧰 Development Tips

### VS Code Debug Setup (optional)

Add `.vscode/launch.json`:

```json
{
  "name": "Debug Merge Example",
  "type": "python",
  "request": "launch",
  "program": "${workspaceFolder}/Main.py",
  "console": "integratedTerminal",
  "args": [
    "--merge", "File_list.csv", "--csv", "-o", "merged/"
  ]
}
```
---
## 🤝 Contributing

Feel free to fork, enhance, or report issues! Contributions are welcome 💬

---

## 👤 Author

**Md Ehsan Ahsan**
📧 [MyGitHub](https://github.com/MdEhsanAhsan)
🛠️ Built with love using Python 🐍

---

### ⚠️ Disclaimer

> This tool is provided **as-is** without any warranties.  
> Use it at your own risk.  
> I am not responsible if it eats your files, breaks your computer, or ruins your spreadsheet.  
> 
> 🚀 But Hey, if it helps you automate the boring stuff — you're welcome! 😄

---

## 📝 License

This project is free to use under the [MIT License](LICENSE).
