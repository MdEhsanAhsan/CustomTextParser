# Concordance DAT File Parser

A lightweight and robust parser for **Concordance DAT files**, designed to make working with these legacy flat-file databases easier — especially for data cleanup, transformation, and analysis tasks.

## 📌 Why This Tool Exists

Concordance DAT files are commonly used in **legal technology and eDiscovery** workflows as a transport format between systems. However, they're difficult to work with directly due to:
- Special field separators (`DC4`, ASCII 20)
- Quote characters (`þ`, Latin small letter thorn)
- Embedded newlines and DC4s within quoted fields
- Lack of modern tools that support them natively

This tool aims to solve that by:
- Parsing DAT files accurately
- Validating structure using headers
- Exporting to CSV or DAT
- Optionally isolating malformed lines for review

---

## ✨ Features

- ✅ Supports custom delimiters: `DC4` (`\x14`) and quote char `þ` (`\xfe`)
- ✅ Handles embedded line breaks and DC4s inside quoted fields
- ✅ Validates each line against header field count
- ✅ Optionally saves malformed lines to a separate file for QC
- ✅ Simple CLI interface for batch processing
- ✅ UTF-8 only (for now) – perfect for modernization workflows

---

## 🧰 Requirements

- Python 3.7+
- Standard library only (no external dependencies)

---

## 📦 Installation

You can run this script directly without installation:

```bash
git clone https://github.com/yourusername/concordance-dat-parser.git
cd CustomTextParser
python main.py
```

No pip install required!

---

## 🚀 Usage

### Basic Example

```bash
python dat_parser.py input.dat --output output.csv
```

### With Malformed Line Reporting

```bash
python dat_parser.py input.dat --output output.csv --malformed malformed_lines.dat
```

---

## 🛠️ Command-line Options

| Option | Description |
|--------|-------------|
| `input_file` | Path to input DAT file |
| `--output` | Optional CSV output path |
| `--malformed` | Optional output path for malformed lines |
| `--fix` | Automatically fix malformed quotes during parsing |
| `--quiet` | Suppress detailed output |

---

## 🧪 Sample Input

```text
þImageIDþ\x14þImagePathþ\x14þDescriptionþ
XFD001\x14C:\Images\img1.tif\x14Document A
þMULTI
LINE
FIELDþ\x14C:\Images\img2.tif\x14Document B
```

---

## 📁 Output Examples

### CSV Output

```csv
ImageID,ImagePath,Description
XFD001,C:\Images\img1.tif,Document A
"MULTI
LINE
FIELD",C:\Images\img2.tif,Document B
```

### Malformed Lines Output (if any)

```text
þBADLINE\x14MissingQuote
```

---

## 💡 Future Ideas

- [ ] GUI version using Tkinter or PyQt
- [ ] Export DAT files back to original format
- [ ] Support for other encodings (Latin-1, UTF-16LE)

---

## 🤝 Contributing

Contributions are welcome! Whether you want to improve the parser logic, add features like CSV export, or build a GUI version, feel free to open a PR or issue.
Happy coding! 🚀
