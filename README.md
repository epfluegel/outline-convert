# Use cases and options currently working

```
outline-convertusage: outline-convert.py [-h] [-o OUTPUT] [-d DIR] [-e EMAIL] [-s START]
                          [--case-insensitive] [--stdout]
                          [input]

Convert plain-text outline to OPML (notes + subtree + case sensitivity +
directories + stdio).

positional arguments:
  input                 Input text file (omit to read stdin)

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Specify output filename (without directory)
  -d DIR, --dir DIR     Output directory
  -e EMAIL, --email EMAIL
                        Owner email for OPML head
  -s START, --start START
                        Prefix of node title to extract subtree from
  --case-insensitive    Match start prefix case-insensitively
  --stdout              Write OPML to stdout instead of file
```

```
The .bat or .sh files must stay where they are, is you want to move them then create a shortcut
```