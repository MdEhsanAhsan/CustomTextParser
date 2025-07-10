<!-- SEO: Concordance DAT to CSV, load file converter, export DAT to Excel, .DAT parsing tool, smart DAT file reader, merge Concordance load files, remove rows from DAT -->

# 📂 CustomTextParser

**Easily convert Concordance `.DAT` load files to `.CSV` or cleaned `.DAT` formats.**  
Perfect for legal E-discovery or bulk metadata processing.

---

A powerful Python CLI tool for reading, comparing, cleaning, and exporting `.dat` files with custom delimiters (`þ` + control chars). Designed to handle Excel-incompatible files, embedded line breaks, and encoding challenges with ease.

---

## ✨ Features

- ✅ Convert `.dat` to `.csv`
- 🔀 Compare two `.dat` files (with optional header mapping)
- 🧹 Delete specific rows from `.dat` using a value list
- 🔁 Merge `.dat` files by common headers
- 🔤 Auto-detect encoding (UTF-8, UTF-16, Windows-1252, Latin-1)
- 💬 Smart line reader handles embedded newlines
- 📁 Output directory support via `-o`
- ⚠️ Excel field-length warning for long text fields

---

## ⚙️ Command Usage

```bash
python Main.py <input_file> [input_file2] [options]
````

### 🔄 Convert `.dat` to `.csv`

```bash
python Main.py myfile.dat --csv
python Main.py myfile.dat --tsv -o OutputDir/
python Main.py myfile.dat --dat
```

### 📊 Compare two `.dat` files (row-by-row value diff)

```bash
python Main.py file1.dat file2.dat --compare
python Main.py file1.dat file2.dat --compare --mapping Mapped.csv -o diffs/
```

> ✅ Mapping file format:
>
> ```
> HEADER_A_in_file1,HEADER_B_in_file2
> ```

### 🔁 Merge `.dat` files by matching headers

```bash
python Main.py --merge File_list.csv --csv -o merged_output/
```

> ✅ `File_list.csv` contains one `.dat` file path per row

### 🧹 Delete rows using a list of values

```bash
python Main.py myfile.dat --delete deleterows.csv --csv
```

> ✅ `deleterows.csv` format:
>
> ```
> FIELD_NAME
> VALUE_1
> VALUE_2
> ```

### 🔧 Replace headers using a mapping file

```bash
python Main.py myfile.dat --replace-header HeaderMap.csv --csv
```

> ✅ `HeaderMap.csv` format:
>
> ```
> OLD_NAME,NEW_NAME
> ```

---

## 📦 Output Files

* All exports go to the directory specified by `-o`, or default to the input file's folder.
* Output filenames include tags like `{kept}`, `{removed}`, or `_Replaced`.

---

## 💡 Encoding Detection Logic

Handles:

* UTF-8 BOM
* UTF-16 LE/BE
* Windows-1252 (via printable category)
* Latin-1 fallback

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
