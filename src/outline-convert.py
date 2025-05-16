# text_to_opml.py
"""Utility to convert an indented plain-text outline into OPML,
with support for notes, optional subtree extraction, case sensitivity, and output directory."""

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


def detect_indent(lines: List[str]) -> int:
    counts = [len(l) - len(l.lstrip(' ')) for l in lines if l.startswith(' ')]
    if not counts:
        return 1
    indent = counts[0]
    for c in counts[1:]:
        indent = gcd(indent, c)
    return indent or 1


def parse_outline(lines: List[str]) -> Node:
    root = Node('root')
    stack: List[tuple[int, Node]] = [(-1, root)]
    indent_size = detect_indent(lines)
    last_node: Optional[Node] = None

    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            continue
        # Note line
        if stripped.startswith('"') and stripped.endswith('"') and last_node:
            last_node.note = stripped.strip('"')
            continue

        leading = raw.expandtabs(indent_size)
        space_count = len(leading) - len(leading.lstrip(' '))
        extra = indent_size if leading.lstrip().startswith('-') else 0
        level = (space_count + extra) // indent_size

        title = re.sub(r'^-+\s*', '', leading.strip())
        node = Node(title)

        while stack and stack[-1][0] >= level:
            stack.pop()
        stack[-1][1].children.append(node)
        stack.append((level, node))
        last_node = node

    return root


def find_node(node: Node, prefix: str, case_sensitive: bool) -> Optional[Node]:
    if case_sensitive:
        match = node.title.startswith(prefix)
    else:
        match = node.title.lower().startswith(prefix.lower())
    if match:
        return node
    for child in node.children:
        found = find_node(child, prefix, case_sensitive)
        if found:
            return found
    return None


def node_to_outline_elem(node: Node) -> ET.Element:
    elem = ET.Element('outline')
    elem.set('text', node.title)
    if node.note:
        elem.set('_note', node.note)
    for child in node.children:
        elem.append(node_to_outline_elem(child))
    return elem


def build_opml(root: Node, owner_email: Optional[str] = None) -> ET.ElementTree:
    opml = ET.Element('opml', version="2.0")
    head = ET.SubElement(opml, 'head')
    if owner_email:
        email_elem = ET.SubElement(head, 'ownerEmail')
        email_elem.text = f"\n    {owner_email}\n  "
    body = ET.SubElement(opml, 'body')
    for child in root.children:
        body.append(node_to_outline_elem(child))

    tree = ET.ElementTree(opml)
    try:
        ET.indent(tree, space="  ")
    except AttributeError:
        indent(opml)
    return tree


def indent(elem: ET.Element, level: int = 0):
    pad = "\n" + level * "  "
    if elem:
        if not elem.text or not elem.text.strip():
            elem.text = pad + "  "
        for child in elem:
            indent(child, level + 1)
        if not elem[-1].tail or not elem[-1].tail.strip():
            elem[-1].tail = pad
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = pad


def sanitize_filename(s: str) -> str:
    name = re.sub(r"\s+", "_", s.strip())
    name = re.sub(r"[^\w\-]", "", name)
    return name or 'output'


def main():
    parser = argparse.ArgumentParser(
        description='Convert plain-text outline to OPML (notes + subtree + case sensitivity + output directory).'
    )
    parser.add_argument('input', help='Input text file')
    parser.add_argument('-o', '--output', help='Output OPML filename')
    parser.add_argument('-d', '--dir', default='./result', help='Output directory')
    parser.add_argument('-e', '--email', help='Owner email for OPML head')
    parser.add_argument('-s', '--start', help='Prefix of node title to extract subtree from')
    parser.add_argument('--case-insensitive', action='store_true',
                        dest='case_insensitive', default=False,
                        help='Match start prefix case-insensitively')
    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(args.dir, exist_ok=True)

    with open(args.input, encoding='utf-8') as f:
        lines = [l.rstrip('\n') for l in f]

    full_root = parse_outline(lines)
    case_sensitive = not args.case_insensitive

    if args.start:
        start_node = find_node(full_root, args.start, case_sensitive)
        if not start_node:
            print(f"Error: start node prefix '{args.start}' not found.", file=sys.stderr)
            sys.exit(1)
        root = Node('root')
        root.children = [start_node]
    else:
        root = full_root

    if args.output:
        filename = args.output
    else:
        title = root.children[0].title if root.children else 'output'
        filename = sanitize_filename(title) + '.opml'

    out_path = os.path.join(args.dir, filename)
    tree = build_opml(root, args.email)
    tree.write(out_path, encoding='utf-8', xml_declaration=True)
    print(f"OPML saved to {out_path}")

if __name__ == '__main__':
    main()
