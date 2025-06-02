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
    p = argparse.ArgumentParser(description='Convert between text outline, OPML, and LaTeX')

    p.add_argument('input', nargs='?', help='Input file (omit for stdin or use --date)')
    p.add_argument('-f', '--format', choices=['txt', 'opml', 'latex-a', 'latex-b'], default='opml',
                   help='Output format: txt, opml, latex-a (article), latex-b (beamer)')
    p.add_argument('-o', '--output', help='Output filename (omit for auto)')
    p.add_argument('-d', '--dir', default='.', help='Output directory')
    p.add_argument('-e', '--email', help='Owner email for OPML head')
    p.add_argument('-s', '--start', help='Prefix to extract subtree')
    p.add_argument('--case-insensitive', action='store_true', dest='ci', default=False,
                   help='Case-insensitive subtree match')
    p.add_argument('--stdout', action='store_true', help='Write to stdout')
    p.add_argument('--date', metavar='DIR',
                   help='Scan DIR and pick the most recently modified file as input')
    p.add_argument('--expert-mode', action='store_true',
                   help='(latex-b only) Interpret tags when outputting LaTeX Beamer')
    p.add_argument('-s', '--strip-tags', action='store_true', help='Strip tags like #slide from output titles')

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
            root_node = parse_opml(xml_root)
    else:
        # Parse plain text
        if args.input:
            with open(args.input, 'r', encoding='utf-8') as f:
                raw = [line.rstrip('\n') for line in f]
        else:
            print('Paste outline below. Finish with Ctrl+D (EOF):')
            raw = [line.rstrip('\n') for line in sys.stdin]
        root_node = parse_text(raw)

    # -- optional subtree extraction ----------------------------------------
    cs = not args.ci
    if args.start:
        node = find_node(root_node, args.start, cs)
        if not node:
            sys.exit(f"Prefix '{args.start}' not found")
        root_node = Node('root')
        root_node.children = [node]

    # -- render based on format ---------------------------------------------
    out_lines: Optional[List[str]] = None
    out_tree: Optional[ET.ElementTree] = None

    if args.format == 'txt':
        out_lines = render_text(root_node)
    elif args.format == 'latex-a':
        out_lines = render_latex(root_node)
    elif args.format == 'latex-b':
        if args.expert_mode:
            out_lines = render_latex_beamer_with_tags(root_node)
        else:
            out_lines = render_latex_beamer(root_node)
    else:  # opml
        out_tree = build_opml(root_node, args.email)

    # -- output result ------------------------------------------------------
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
            ext = {
                'txt': 'txt',
                'latex-a': 'tex',
                'latex-b': 'tex',
                'opml': 'opml'
            }.get(args.format, 'out')
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