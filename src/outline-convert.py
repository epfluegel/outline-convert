# text_to_opml.py
"""Utility to convert an indented plain-text outline into OPML, with support for notes and dynamic output filename."""

import sys
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
        if stripped.startswith('"') and stripped.endswith('"'):
            if last_node:
                last_node.note = stripped.strip('"')
            continue

        leading = raw.expandtabs(indent_size)
        space_count = len(leading) - len(leading.lstrip(' '))
        if leading.lstrip().startswith('-'):
            effective_indent = space_count + indent_size
        else:
            effective_indent = space_count
        level = effective_indent // indent_size

        title = re.sub(r'^-+\s*', '', leading.strip())
        node = Node(title)

        while stack and stack[-1][0] >= level:
            stack.pop()
        stack[-1][1].children.append(node)
        stack.append((level, node))
        last_node = node

    return root


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
        email_elem.text = "\n    " + owner_email + "\n  "
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
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for child in elem:
            indent(child, level + 1)
        if not elem[-1].tail or not elem[-1].tail.strip():
            elem[-1].tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i


def sanitize_filename(s: str) -> str:
    # Replace spaces with underscores and remove illegal chars
    name = re.sub(r"\s+", "_", s.strip())
    name = re.sub(r"[^\w\-]", "", name)
    return name or 'output'


def main():
    parser = argparse.ArgumentParser(
        description='Convert indented plain-text outline to OPML (with notes).'
    )
    parser.add_argument('input', help='Input text file')
    parser.add_argument('-o', '--output', help='Output OPML file (defaults to first bullet).')
    parser.add_argument('-e', '--email', help='Owner email for OPML head')
    args = parser.parse_args()

    with open(args.input, encoding='utf-8') as f:
        lines = [l.rstrip('\n') for l in f]
    root = parse_outline(lines)

    # Determine output filename
    if args.output:
        out_file = args.output
    else:
        first = root.children[0].title if root.children else 'output'
        out_file = sanitize_filename(first) + '.opml'

    tree = build_opml(root, args.email)
    tree.write(out_file, encoding='utf-8', xml_declaration=True)
    print(f"OPML saved to {out_file}")


if __name__ == '__main__':
    main()
