# text_to_opml.py
"""Utility to convert between indented plain-text outlines and OPML,
with support for notes, optional subtree extraction, case sensitivity,
stdin/stdout, and flexible input/output formats."""

import sys
import os
import re
import argparse
import xml.etree.ElementTree as ET
from math import gcd
from typing import List, Optional

class Node:
    def __init__(self, title: str):
        self.title: str = title
        self.children: List[Node] = []
        self.note: Optional[str] = None

# -- TEXT PARSING ------------------------------------------------------------
def detect_indent(lines: List[str]) -> int:
    counts = [len(l) - len(l.lstrip(' ')) for l in lines if l.startswith(' ')]
    if not counts:
        return 1
    indent = counts[0]
    for c in counts[1:]:
        indent = gcd(indent, c)
    return indent or 1


def parse_text(lines: List[str]) -> Node:
    root = Node('root')
    stack = [(-1, root)]
    indent_size = detect_indent(lines)
    last_node: Optional[Node] = None

    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            continue
        # note lines
        if stripped.startswith('"') and stripped.endswith('"') and last_node:
            last_node.note = stripped.strip('"')
            continue
        # compute level
        leading = raw.expandtabs(indent_size)
        space_count = len(leading) - len(leading.lstrip(' '))
        extra = indent_size if leading.lstrip().startswith('-') else 0
        level = (space_count + extra) // indent_size
        title = re.sub(r'^-+\s*', '', leading.strip())
        node = Node(title)
        # attach
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack[-1][1].children.append(node)
        stack.append((level, node))
        last_node = node
    return root

# -- OPML PARSING -----------------------------------------------------------
def parse_opml(root_elem: ET.Element) -> Node:
    # find <body>
    body = root_elem.find('body')
    top = Node('root')
    if body is None:
        return top
    def recurse(elem: ET.Element) -> Node:
        node = Node(elem.get('text',''))
        note = elem.get('_note')
        if note:
            node.note = note
        for child in elem.findall('outline'):
            node.children.append(recurse(child))
        return node
    for outline in body.findall('outline'):
        top.children.append(recurse(outline))
    return top

# -- TREE UTILITIES ---------------------------------------------------------
def find_node(node: Node, prefix: str, case_sensitive: bool) -> Optional[Node]:
    text = node.title
    if case_sensitive:
        ok = text.startswith(prefix)
    else:
        ok = text.lower().startswith(prefix.lower())
    if ok:
        return node
    for c in node.children:
        res = find_node(c, prefix, case_sensitive)
        if res:
            return res
    return None

# -- RENDER TEXT ------------------------------------------------------------
def render_text(node: Node, level: int = 0, indent_size: int = 2) -> List[str]:
    lines: List[str] = []
    for child in node.children:
        prefix = ' ' * (level * indent_size) + '- ' + child.title
        lines.append(prefix)
        if child.note:
            lines.append(' ' * (level * indent_size) + f'"{child.note}"')
        lines.extend(render_text(child, level+1, indent_size))
    return lines

# -- RENDER OPML ------------------------------------------------------------
def node_to_outline_elem(node: Node) -> ET.Element:
    elem = ET.Element('outline')
    elem.set('text', node.title)
    if node.note:
        elem.set('_note', node.note)
    for c in node.children:
        elem.append(node_to_outline_elem(c))
    return elem


def build_opml(root: Node, owner_email: Optional[str] = None) -> ET.ElementTree:
    opml = ET.Element('opml', version='2.0')
    head = ET.SubElement(opml, 'head')
    if owner_email:
        em = ET.SubElement(head, 'ownerEmail')
        em.text = f"\n    {owner_email}\n  "
    body = ET.SubElement(opml, 'body')
    for c in root.children:
        body.append(node_to_outline_elem(c))
    tree = ET.ElementTree(opml)
    try:
        ET.indent(tree, space='  ')
    except AttributeError:
        indent(opml)
    return tree

# -- PRETTY INDENT ----------------------------------------------------------
def indent(elem: ET.Element, level: int = 0):
    pad = '\n' + level * '  '
    if elem:
        if not elem.text or not elem.text.strip():
            elem.text = pad + '  '
        for c in elem:
            indent(c, level+1)
        if not elem[-1].tail or not elem[-1].tail.strip():
            elem[-1].tail = pad
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = pad

# -- FILENAME SANITIZE -----------------------------------------------------
def sanitize_filename(s: str) -> str:
    name = re.sub(r"\s+", '_', s.strip())
    name = re.sub(r"[^\w\-]", '', name)
    return name or 'output'

# -- MAIN ------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description='Convert between text outline and OPML')
    p.add_argument('-i','--input', nargs='?', help='Input file (omit for stdin)')
    p.add_argument('--input-type', choices=['txt','opml'],
                   help='Force input type (default by extension or txt)')
    p.add_argument('-o','--output', help='Output filename (omit for auto)')
    p.add_argument('-d','--dir', default='./result', help='Output directory')
    p.add_argument('--output-format', choices=['opml','txt'], default='opml',
                   help='Output format')
    p.add_argument('-e','--email', help='Owner email for OPML head')
    p.add_argument('-s','--start', help='Prefix to extract subtree')
    p.add_argument('--case-insensitive', action='store_true', dest='ci', default=False,
                   help='Case-insensitive subtree match')
    p.add_argument('--stdout', action='store_true', help='Write to stdout')
    args = p.parse_args()

    # read lines or xml
    raw: List[str]
    root_node: Node
    # decide input type
    itype = args.input_type
    if not itype:
        if args.input and args.input.lower().endswith(('.opml','.xml')):
            itype = 'opml'
        else:
            itype = 'txt'
    if itype=='txt':
        # read text
        if args.input:
            with open(args.input, encoding='utf-8') as f:
                raw = [l.rstrip('\n') for l in f]
        else:
            print('Paste outline, finish with EOF:')
            raw = [l.rstrip('\n') for l in sys.stdin]
        root_node = parse_text(raw)
    else:
        # read opml
        src = args.input or None
        tree = ET.parse(args.input) if args.input else ET.parse(sys.stdin)
        xml_root = tree.getroot()
        root_node = parse_opml(xml_root)

    # subtree
    cs = not args.ci
    if args.start:
        n = find_node(root_node, args.start, cs)
        if not n:
            sys.exit(f"Prefix '{args.start}' not found")
        root_node = Node('root'); root_node.children=[n]

    # build output
    out_lines: Optional[List[str]] = None
    out_tree: Optional[ET.ElementTree] = None
    if args.output_format=='txt':
        out_lines = render_text(root_node)
    else:
        out_tree = build_opml(root_node, args.email)

    # emit
    if args.stdout:
        if out_lines is not None:
            sys.stdout.write('\n'.join(out_lines))
        else:
            out_tree.write(sys.stdout.buffer, encoding='utf-8', xml_declaration=True)
    else:
        os.makedirs(args.dir, exist_ok=True)
        # filename
        if args.output:
            fname = args.output
        else:
            first = root_node.children[0].title if root_node.children else 'output'
            ext = 'opml' if out_tree else 'txt'
            fname = sanitize_filename(first) + f'.{ext}'
        path = os.path.join(args.dir, fname)
        if out_lines is not None:
            with open(path,'w',encoding='utf-8') as f:
                f.write('\n'.join(out_lines))
        else:
            out_tree.write(path, encoding='utf-8', xml_declaration=True)
        print(f"Wrote {path}")

if __name__=='__main__':
    main()
