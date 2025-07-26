<!-- SEO: Concordance DAT to CSV, load file converter, export DAT to Excel, .DAT parsing tool, smart DAT file reader, merge Concordance load files, remove rows from DAT -->

# 📂 CustomTextParser

## 🔄 Concordance `.DAT` File Toolkit

**Easily convert and manipulate Concordance `.DAT` load files — perfect for legal e-discovery, metadata extraction, and bulk processing.**

---

### 🛠 What It Does

A powerful Python CLI tool designed to handle complex `.DAT` files with custom delimiters (`þ`, control characters), broken encodings, and Excel-incompatible data.

This tool can:

* ✅ Convert `.DAT` to `.CSV`
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
- 📥[Download EXE](https://github.com/MdEhsanAhsan/CustomTextParser/releases/tag/v2.0.0)

### Clone the repo

```bash
git clone https://github.com/yourusername/dat-file-tool.git
cd dat-file-tool
```

### Install dependencies (optional)

This tool uses only built-in libraries — **no external packages required**!

---

### ✨ Features

- ✅ Convert `.dat` to `.csv` or keep as `.dat`
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
| `-c`, `--compare` | Compare two DAT files line-by-line |
| `-r`, `--replace-header` | Replace headers using a mapping file (`old_header,new_header`) |
| `--merge`     | Merge multiple DAT files grouped by matching headers |
| `--delete`    | Delete rows based on field values listed in a file |
| `--select`    | Export only selected fields from the DAT file |
| `-join`       | Strictly join two DAT files using a key field, with duplicate header conflict resolution |
|`--key`        | Key field required to perform join |
| `-o DIR`      | Specify output directory for generated files |

---

## 🧪 Usage Examples

### 🔁 Convert DAT to CSV / TSV

```bash
python Main.py input.dat --csv
# Output: input_converted.csv

python Main.py input.dat --tsv
# Output: input_converted.tsv
```

You can also specify custom output paths:

```bash
python Main.py input.dat --csv output.csv
```

---

### 🆚 Compare Two DAT Files

```bash
python Main.py file1.dat file2.dat -c
```

With optional header mapping:

```bash
python Main.py file1.dat file2.dat -c -m mapping.csv
```

Outputs differences to `value_diff.csv` (or `.dat`).

---

### 🔄 Replace Headers Using Mapping File

Create a mapping file (`mapping.csv`) like:

```csv
OldHeader1,NewHeader1
OldHeader2,NewHeader2
```

Run:

```bash
python Main.py input.dat -r mapping.csv --csv
# Output: input_Replaced.csv
```

---

### 📦 Merge Multiple DAT Files

Create a merge list file (`merge_list.csv`) containing one file path per line:

```
file1.dat
file2.dat
file3.dat
```

Then run:

```bash
python Main.py --merge merge_list.csv
# Outputs: merged_group_1.dat, merged_group_2.dat, etc.
```

Also creates a log file: `merged_group_log.csv`.

---

### 🗑️ Delete Rows Based on Field Value

Create a delete file (`delete.csv`) with the field name on the first line and values to delete below:

```
ID
1001
1003
1007
```

Run:

```bash
python Main.py input.dat --delete delete.csv --csv
# Outputs: input{kept}.csv and input{removed}.csv
```

---

### 🔍 Select Only Specific Fields

Create a selection file (`select.txt`) with one header per line:

```
Name
Age
City
```

Run:

```bash
python Main.py input.dat --select select.txt --csv
# Output: input_selected.csv
```
---

### 🔗 Strict Join of Two DAT Files

Join two DAT files based on one or more key fields, with strict validation:

```bash
python Main.py file1.dat file2.dat -join --key ID

---

## ⚙️ Optional Arguments

| Flag         | Description |
|--------------|-------------|
| `-o DIR`     | Set output directory |
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
* No external libraries (uses standard library only)

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
