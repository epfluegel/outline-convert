import argparse
import os
import sys
import xml.etree.ElementTree as ET
from contextlib import nullcontext
from typing import Optional, List

from .models import Node
from .parser import parse_text, parse_opml
from .renderer_latex import render_latex_beamer_with_tags, render_latex
from .renderer_text import render_text, build_opml
from .utils import find_node


# -- MAIN ------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description='Convert between text outline, OPML, and LaTeX')

    p.add_argument('input', nargs='?', help='Input file (omit for stdin or use --date)')
    p.add_argument('-o', '--output', help='Output filename (omit for auto)')
    p.add_argument('-d', '--dir', default='.', help='Output directory')
    p.add_argument('-e', '--email', help='Author email information')
    p.add_argument('-a', '--author', help='Author information')
    p.add_argument('-f', '--format', choices=['txt', 'opml', 'latex', 'beamer', 'ppt', 'rtf'], default='opml',
                   help='Output format: plain text, OPML, LaTeX Article, LaTeX Beamer, PowerPoint, Rich Text')
    p.add_argument('-s', '--start', help='Start item for conversion')

    #p.add_argument('--stdout', action='store_true', help='Write to stdout')
    p.add_argument('-m', '--date', metavar='DIR',
                   help='Choose most recently modified file in directory DIR as input')
    p.add_argument('--expert-mode', action='store_true',
                   help='Enter expert mode to interpret nodes tagged with specific labels, see readme')

    p.add_argument('--strip-tags', action='store_true', help='Strip tags from input')
    p.add_argument('--fragment', action='store_true',help='Only keep body of document for latex beamer and opml')
    p.add_argument('-w','--wait', action='store_true',help='Wait for key press after execution')
    p.add_argument('--debug', action='store_true',help='Gives debug information')
    p.add_argument('--add-new-line', action='store_true',help='Insert additional new line between items in output')
    p.add_argument('-t', '--tab-char', help='Identation tab character used in output')
    p.add_argument('-n', '--notes-include', action='store_true',help='Include notes in ouput')

    p.add_argument('-b', '--bullet')

    args = p.parse_args()

    # -- handle --date auto-selection ---------------------------------------
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

    # -- determine input type -----------------------------------------------
    root_node: Node
    if args.input and args.input.lower().endswith(('.opml', '.xml')):
        # Parse OPML
        with open(args.input, 'r', encoding='utf-8') as f:
            tree = ET.parse(f)
            xml_root = tree.getroot()
            root_node = parse_opml(xml_root, expert_mode = args.expert_mode)
    else:
        # Parse plain text
        if args.input:
            with open(args.input, 'r', encoding='utf-8') as f:
                raw = [line.rstrip('\n') for line in f]
        else:
            print('Paste outline below. Finish with Ctrl+D (linux) or Ctrl+Z + Enter(Windows):')
            raw = [line.rstrip('\n') for line in sys.stdin]
        root_node = parse_text(raw, expert_mode = args.expert_mode)


    # -- optional subtree extraction ----------------------------------------

    if args.start:
        node = find_node(root_node, args.start)
        if not node:
            sys.exit(f"Prefix '{args.start}' not found")
        root_node = node


    # -- render based on format ---------------------------------------------
    out_lines: Optional[List[str]] = None
    out_tree: Optional[ET.ElementTree] = None

    if args.format == 'txt':
        out_lines = render_text(root_node, indent_char=args.tab_char if args.tab_char else "", bullet_symbol=args.bullet if args.bullet else "-", strip_tags=args.strip_tags)
    elif args.format == 'latex':
        out_lines = render_latex(root_node, strip_tags=args.strip_tags)
    elif args.format == 'beamer':
        out_lines = render_latex_beamer_with_tags(root_node, expert_mode=args.expert_mode, strip_tags=args.strip_tags, fragment=args.fragment, note=args.notes_include)
    else:  # opml
        out_tree = build_opml(root_node, owner_email=args.email, strip_tags=args.strip_tags)


    # -- output result ------------------------------------------------------
    should_write_to_stdout = not args.output

    if should_write_to_stdout:
        if out_lines is not None:
            sys.stdout.write('\n'.join(out_lines) + '\n')
        else:
            out_tree.write(sys.stdout.buffer, encoding='utf-8', xml_declaration=True)
    else:
        os.makedirs(args.dir, exist_ok=True)
        path = os.path.join(args.dir, args.output)
        if out_lines is not None:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(out_lines))
        else:
            out_tree.write(path, encoding='utf-8', xml_declaration=True)
        print(f"Wrote {path}")
    if args.wait:
        print("\nPress Ctrl+C to exit...")
        try:
            while True:
                input()
        except KeyboardInterrupt:
            print("\nExiting...")


if __name__ == '__main__':
    main()