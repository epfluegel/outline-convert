import argparse
import os
import sys
import xml.etree.ElementTree as ET
from contextlib import nullcontext
from doctest import debug
from typing import Optional, List

import pyperclip

from .models import Node
from .parser import parse_text, parse_opml
from .renderer_latex import render_latex_beamer, render_latex
from .renderer_text import render_text, build_opml
from .utils import find_node
from .renderer_ppt import render_ppt
from .renderer_rtf import render_rtf

# -- MAIN PROGRAM -----------------------------------------------------
def main():
    # -- Argument parser configuration -------------------------------
    p = argparse.ArgumentParser(description='Convert between text outline, OPML, and LaTeX')

    # Input/Output arguments
    p.add_argument('input', nargs='?', help='Input file (omit for stdin or use --date)')
    p.add_argument('-c', '--clipboard', action='store_true', help='Read from clipboard')
    p.add_argument('-o', '--output', help='Output filename (omit for auto)')
    p.add_argument('-d', '--dir', default='.', help='Output directory')

    # Metadata arguments
    p.add_argument('-e', '--email', help='Author email information')
    p.add_argument('-a', '--author', help='Author information')
    p.add_argument('-f', '--format', choices=['txt', 'opml', 'latex', 'beamer', 'ppt', 'rtf'], default='txt',
                   help='Output format: plain text, OPML, LaTeX Article, LaTeX Beamer, PowerPoint, Rich Text')
    p.add_argument('-s', '--start', help='Start item for conversion')

    #p.add_argument('--stdout', action='store_true', help='Write to stdout')
    p.add_argument('-m', '--date', metavar='DIR',
                   help='Choose most recently modified file in directory DIR as input')
    p.add_argument('--expert-mode', action='store_true',
                   help='Enter expert mode to interpret nodes tagged with specific labels, see readme')

    # Output formatting arguments
    p.add_argument('--strip-tags', action='store_true', default=False, help='Strip tags from input')
    p.add_argument('--fragment', action='store_true', default=False, help='Only keep body of document for latex beamer and opml')
    p.add_argument('-w','--wait', action='store_true', default=False, help='Wait for key press after execution')
    p.add_argument('--debug', action='store_true', default=False, help='Gives debug information')
    p.add_argument('--add-new-line', action='store_true', default=False, help='Insert additional new line between items in output')
    p.add_argument('-t', '--indent-string', default="    ", help='Identation indent string used in output')
    p.add_argument('-n', '--include-notes', action='store_true', default=False, help='Include notes in ouput')
    p.add_argument('-b', '--bullet-symbol', default="", help="Symbol used for bullet points")
    p.add_argument( '--hide-completed',action='store_true', default=False, help="Hide completed items")
    p.add_argument( '--completed-only',action='store_true', default=False, help="Only includes completed items")

    args = p.parse_args()

    # -- Handle automatic date-based selection ----------------------
    if args.date:
        date_dir = args.date
        if not os.path.isdir(date_dir):
            sys.exit(f"Error: '{date_dir}' is not a directory.")
        candidates = [
            os.path.join(date_dir, name)
            for name in os.listdir(date_dir)
            if os.path.isfile(os.path.join(date_dir, name))
        ]
        if not candidates:
            sys.exit(f"No files found in '{date_dir}'.")
        chosen = max(candidates, key=lambda p: os.path.getmtime(p))
        print(f"Using latest file: {os.path.basename(chosen)}", file=sys.stderr)
        args.input = chosen

    # -- Read input data ------------------------------------------
    if args.input:
        with open(args.input, 'r', encoding='utf-8') as file:
            lines = file.read().splitlines()
    elif args.clipboard:
        lines = pyperclip.paste().splitlines()
    else:
        print('Paste outline below. Finish with Ctrl+D (linux) or Ctrl+Z + Enter(Windows):')
        lines = sys.stdin.read().splitlines()

    # -- Parse content --------------------------------------------
    root_node: Node
    try:
        tree = ET.fromstringlist(lines)
        root_node = parse_opml(tree, args=args)
    except:
        if args.debug:
            print("ompl not parsed correctly")
        root_node = parse_text(lines, args)

    # -- Optional subtree extraction ------------------------------
    if args.start:
        node = find_node(root_node, args.start)
        if not node:
            if args.debug:
                print("Prefix not found")
        root_node = node

    # -- Render based on chosen format ---------------------------
    out_lines: Optional[List[str]] = None
    out_tree: Optional[ET.ElementTree] = None
    if args.format == 'txt':
        tab=args.indent_string
        if tab == "\\t":
            tab = '\t'
        out_lines = render_text(root_node, args)
    elif args.format == 'latex':
        out_lines = render_latex(root_node, args)
    elif args.format == 'beamer':
        out_lines = render_latex_beamer(root_node, args)
    elif args.format == 'opml':  # opml
        out_tree = build_opml(root_node, args, owner_email=args.email)
    elif args.format == 'ppt':
        out_lines = render_ppt(root_node, args)
    elif args.format == 'rtf':
        out_lines = render_rtf(root_node, args)

    # -- Handle output -------------------------------------------
    if args.clipboard:
        if out_lines is not None:
            pyperclip.copy('\n'.join(out_lines))
        else:
            xml_string = ET.tostring(out_tree, encoding='unicode')
            pyperclip.copy(xml_string)
        print("Copied to clipboard")

    elif not args.output:  # Output to stdout
        if out_lines is not None:
            sys.stdout.write('\n'.join(out_lines) + '\n')
        else:
            out_tree.write(sys.stdout.buffer, encoding='utf-8', xml_declaration=True)
    else:  # Output to file
        os.makedirs(args.dir, exist_ok=True)
        path = os.path.join(args.dir, args.output)
        if out_lines is not None:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(out_lines))
        else:
            out_tree.write(path, encoding='utf-8', xml_declaration=True)
        print(f"Wrote {path}")

    # -- Handle final wait --------------------------------------
    if args.wait:
        input("Press any key to exit\n")

if __name__ == '__main__':
    main()