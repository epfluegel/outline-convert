import argparse
import os
import sys
import xml.etree.ElementTree as ET

from typing import Optional, List

from .models import Node
from .parser import parse_text, parse_opml
from .renderer_latex import render_latex_beamer_with_tags, render_latex_beamer, render_latex
from .renderer_text import render_text, build_opml
from .utils import find_node, sanitize_filename


# -- MAIN ------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description='Convert between text outline and OPML')
    p.add_argument('-i','--input', nargs='?', help='Input file (omit for stdin)')
    p.add_argument('--input-type', choices=['txt','opml'],
                   help='Force input type (default by extension or txt)')
    p.add_argument('-o','--output', help='Output filename (omit for auto)')
    p.add_argument('-d','--dir', default='.', help='Output directory')
    p.add_argument('--output-format', choices=['opml','txt','latex'], default='opml',
                   help='Output format')
    p.add_argument('-e','--email', help='Owner email for OPML head')
    p.add_argument('-s','--start', help='Prefix to extract subtree')
    p.add_argument('--case-insensitive', action='store_true', dest='ci', default=False,
                   help='Case-insensitive subtree match')
    p.add_argument('--stdout', action='store_true', help='Write to stdout')
    p.add_argument('--date', metavar='DIR',
                   help='Scan DIR and pick the most recently modified file as input')
    p.add_argument('--beamer_tags', action='store_true', help='Use Beamer format and interprete tags when outputting LaTeX')
    p.add_argument('--beamer', action='store_true', help='Use Beamer format when outputting LaTeX')

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

    # read lines or xml
    raw: List[str]
    root_node: Node

    itype = args.input_type
    if not itype:
        if args.input and args.input.lower().endswith(('.opml','.xml')):
            itype = 'opml'
        else:
            itype = 'txt'

    if itype == 'txt':
        if args.input:
            with open(args.input, encoding='utf-8') as f:
                raw = [l.rstrip('\n') for l in f]
        else:
            print('Paste outline, finish with EOF:')
            raw = [l.rstrip('\n') for l in sys.stdin]
        root_node = parse_text(raw)
    else:
        if args.input:
            tree = ET.parse(args.input)
        else:
            tree = ET.parse(sys.stdin)
        xml_root = tree.getroot()
        root_node = parse_opml(xml_root)

    cs = not args.ci
    if args.start:
        n = find_node(root_node, args.start, cs)
        if not n:
            sys.exit(f"Prefix '{args.start}' not found")
        root_node = Node('root')
        root_node.children = [n]

    out_lines: Optional[List[str]] = None
    out_tree: Optional[ET.ElementTree] = None
    if args.output_format == 'txt':
        out_lines = render_text(root_node)
    elif args.output_format == 'latex':
        if args.beamer_tags:
            out_lines = render_latex_beamer_with_tags(root_node)
        elif args.beamer:
            out_lines = render_latex_beamer(root_node)
        else:
            out_lines = render_latex(root_node)

    else:
        out_tree = build_opml(root_node, args.email)

    if args.stdout:
        if out_lines is not None:
            sys.stdout.write('\n'.join(out_lines))
        else:
            out_tree.write(sys.stdout.buffer, encoding='utf-8', xml_declaration=True)
    else:
        os.makedirs(args.dir, exist_ok=True)
        if args.output:
            fname = args.output
        else:
            first = root_node.children[0].title if root_node.children else 'output'
            ext = 'txt' if out_lines is not None else 'opml'
            if args.output_format == 'latex':
                ext = 'tex'
            fname = sanitize_filename(first) + f'.{ext}'
        path = os.path.join(args.dir, fname)
        if out_lines is not None:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(out_lines))
        else:
            out_tree.write(path, encoding='utf-8', xml_declaration=True)
        print(f"Wrote {path}")


if __name__ == '__main__':
    main()
