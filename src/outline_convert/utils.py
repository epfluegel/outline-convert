import argparse
from math import gcd
from typing import List, Optional

from .models import Node
import xml.etree.ElementTree as ET
import re


def detect_indent(lines: List[str]) -> int:
    counts = [len(l) - len(l.lstrip(' ')) for l in lines if l.startswith(' ')]
    if not counts:
        return 1
    indent = counts[0]
    for c in counts[1:]:
        indent = gcd(indent, c)
    return indent or 1

def compute_level(line: str, indent_size: int) -> int:
    leading = line.expandtabs(indent_size)
    space_count = len(leading) - len(leading.lstrip(' '))
    extra = indent_size if leading.lstrip().startswith('-') else 0
    level = (space_count + extra) // indent_size
    return level

# -- TREE UTILITIES ---------------------------------------------------------

def find_node(forest: List[Node], prefix: str) -> List[Node]:
    for tree in forest:
        result = find_node_tree(tree, prefix)
        if result is not None:
            return [result]
    return []

def find_node_tree(node: Node, prefix: str) -> Optional[Node]:
    if node.title.startswith(prefix):
        return node
    for child in node.children:
        result = find_node_tree(child, prefix)
        if result is not None:
            return result

    return None
    
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

import re

def escape_latex(s: str) -> str:
    # Normalize $$...$$ to $...$
    s = re.sub(r'\$\$(.*?)\$\$', r'$\1$', s, flags=re.DOTALL)

    # Pattern to match inline math segments ($...$)
    math_pattern = re.compile(r'(\$.*?\$)')

    def escape_outside_math(text: str) -> str:
        return text.replace('\\', r'\textbackslash{}')\
                   .replace('&', r'\&')\
                   .replace('%', r'\%')\
                   .replace('$', r'\$')\
                   .replace('#', r'\#')\
                   .replace('_', r'\_')\
                   .replace('{', r'\{')\
                   .replace('}', r'\}')\
                   .replace('~', r'\textasciitilde{}')\
                   .replace('^', r'\textasciicircum{}')\

    # Split string into math and non-math parts
    parts = math_pattern.split(s)

    # Escape only non-math parts
    escaped_parts = [
        part if math_pattern.fullmatch(part)
        else escape_outside_math(part)
        for part in parts
    ]

    return ''.join(escaped_parts)

def clean_text(title: str, strip_tags: bool) -> str:
    parts = title.strip().split()
    if strip_tags:
        parts = [p for p in parts if not p.startswith('#')]
    return escape_latex(' '.join(parts))


def link_replacer(match):
    text, url = match.group(1), match.group(2)
    return fr"\href{{{url}}}{{{escape_latex(text)}}}"

def node_to_outline_elem(node: Node, args: argparse.Namespace) -> ET.Element:
    """Convert a single node to an outline element (no children processing)"""
    elem = ET.Element('outline')
    title = node.title
    if args.strip_tags:
        title = ' '.join(part for part in title.split() if not part.startswith('#'))
    elem.set('text', title)
    if args.include_notes and node.note:
        elem.set('_note', node.note)
    return elem

IGNORE_OUTLINE_TAGS = {"#wfe-ignore-outline", "#ignore-outline"}
IGNORE_ITEM_TAGS = {"#wfe-ignore-item", "#ignore-item", "#hh"}

def ignore_tree(node: Node, args: argparse.Namespace):
    is_complete = node.title.startswith('[COMPLETE]')
    has_children = bool(node.children)
    children_copy = list(node.children) if has_children else []
    ignore_item = (args.hide_completed and is_complete) or \
        (args.completed_only and not is_complete) or \
        (args.expert_mode and any(tag in node.title for tag in IGNORE_ITEM_TAGS))

    if ignore_item:
        if node.parent:
            parent = node.parent
            index = parent.children.index(node)
            if has_children:
                parent.children[index:index + 1] = children_copy
                for child in node.children:
                    child.parent = parent
            for child in children_copy:
                ignore_tree(child, args)
            return

    if args.expert_mode and any(tag in node.title for tag in IGNORE_OUTLINE_TAGS):
        if node.parent:
            node.parent.children.remove(node)
            return

    if has_children:
        for child in children_copy:
            ignore_tree(child, args)


def ignore_forest(forest: List[Node], args: argparse.Namespace) -> List[Node]:
    for tree in forest:
        ignore_tree(tree, args)
    return forest

def link_parent(parent: Node):
    for child in parent.children:
        child.parent = parent
        link_parent(child)

def print_forest(forest: List[Node]):
    for tree in forest:
        print_tree(tree)
        print("#################################################")

def print_tree(node: Node, level: int = 0):
    if node.parent:
        print('  ' * level,"title:",node.title,"|","note:", node.note, "|", "parent:", node.parent.title)
    else:
        print('  ' * level,"title:",node.title,"|","note:", node.note)
    for child in node.children:
        print_tree(child, level + 1)