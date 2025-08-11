## 📦 Installation

You can install `outline-convert` globally in two ways:

### Using `pipx` (recommended)

```bash
  pipx install path/to/your/project
```
### Using `pip` 
```bash
  pip install path/to/your/project
```
Make sure ~/.local/bin is in your $PATH to call outline-convert globally.

### Using python3 -m

If you prefer not to install it, at the root directory, you can run it directly from source:

```bash
  python3 -m src.outline_convert [args...]
```
🧪 Usage

outline-convert [input] [options]

| Option                                                | Description                                                |
|-------------------------------------------------------|------------------------------------------------------------|
| `-h`, `--help`                                        | Show help message and exit                                 |
| *Input/Output*                                        |                                                            |
| `input`                                               | Input file (omit for stdin or use `--date`)                |
| `-c`, `--clipboard`                                   | Read input from clipboard                                  |
| `-o OUTPUT`, `--output OUTPUT`                        | Output filename (omit for auto)                            |
| `-d DIR`, `--dir DIR`                                 | Output directory (default: `.`)                            |
| *Metadata*                                            |                                                            |
| `-e EMAIL`, `--email EMAIL`                           | Author email (opml)                                        |
| `-a AUTHOR`, `--author AUTHOR`                        | Author name  (opml)                                        |
| `-f {txt,opml,latex,beamer,ppt,rtf,docx}`, `--format` | Output format (RTF and DOCX **not yet implemented**)       |
| `-s START`, `--start START`                           | Start item for conversion                                  |
| `-m DIR`, `--date DIR`                                | Use most recently modified file in directory as input      |
| `-z ZIP_DIR FILE_PATH`                                | Use specified file from the most recent ZIP backup         |
| `--expert-mode`                                       | Use advanced tag-based interpretation (see below)          |
| `-p`, `--parse-markdown`                              | Parse Markdown syntax for bold and italic                  |
| `--filter STRING`                                     | Filter for a specific string                               |
| *Output Formatting*                                   |                                                            |
| `--strip-tags`                                        | Remove tags from input                                     |
| `--fragment`                                          | Output only the body (LaTeX Beamer)                        |
| `-w`, `--wait`                                        | Wait for a key press after execution                       |
| `--debug`                                             | Print debug information                                    |
| `--add-new-line`                                      | Add extra new line between items (**not yet implemented**) |
| `-t INDENT_STRING`, `--indent-string INDENT_STRING`   | Indentation style (e.g., `"  "` or `"\t"` for plain text)  |
| `-n`, `--include-notes`                               | Include note blocks in output                              |
| `-b SYMBOL`, `--bullet-symbol SYMBOL`                 | Bullet symbol to use (for plain text)                      |
| `--hide-completed`                                    | Exclude completed items                                    |
| `--completed-only`                                    | Include only completed items                               |
