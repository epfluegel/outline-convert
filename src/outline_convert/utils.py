import argparse
from math import gcd
from typing import List, Optional

from .models import Node, TextSegment
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
#find all the nodes with this substring
def find_sub_string(node: Node, substring: str) -> List[Node]:
    res = []
    if substring in node.title:
        res.append(node)
    for child in node.children:
        res.extend(find_sub_string(child, substring))
    return res

#returns the path to the node including its subtree
def get_path(node: Node) -> List[Node]:
    res = []
    if node:
        current = node
        while node.parent is not None:
            #here is the line that keeps the subTree
            #use current = node.title if we only want to keep the title
            parent = Node(node.parent.title)
            parent.children.append(current)
            current = parent
            node = node.parent
        res.append(current)
    return res

#returns all the paths of all occurencies of the filtered node
def filter(forest: List[Node], substring: str) -> List[Node]:
    res = []
    for tree in forest:
        filtered_trees = find_sub_string(tree, substring)
        for node in filtered_trees:
            res.extend(get_path(node))
    return res


def parse_opml_children(elem: ET.Element, parent: Node):
    for child_elem in elem.findall('outline'):
        title = child_elem.get('text', '')
        node = Node(title)
        note = child_elem.get('_note')
        if note:
            node.note = note

        parent.children.append(node)
        node.parent = parent
        parse_opml_children(child_elem, node)
    
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

def escape_markdown(s: str) -> str:
    s = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', s, flags=re.DOTALL)
    s = re.sub(r'\*(.*?)\*', r'\\textit{\1}', s, flags=re.DOTALL)
    return s

def clean_text(title: str, args: argparse.Namespace) -> str:
    # Step 1: Split into words and filter tags
    parts = title.strip().split()
    if args.strip_tags:
        parts = [p for p in parts if not p.startswith('#')]

    # Step 2: Build segments
    segments: List[TextSegment] = [TextSegment(part, 'plain') for part in parts]

    # Step 3: Markdown parsing
    if args.parse_markdown:
        for segment in segments:
            s = escape_markdown(segment.text)
            if s != segment.text:
                segment.text = s
                segment.type = 'markdown_parsed'

    # Step 4: LaTeX escaping
    if args.format in ['latex', 'beamer']:
        for segment in segments:
            if segment.type == 'plain':
                segment.text = escape_latex(segment.text)

    # Step 5: Join back with spaces
    return ' '.join(segment.text for segment in segments)


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
            parent.children[index:index + 1] = children_copy
            if has_children:
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
    result = []
    for node in forest:
        is_complete = node.title.startswith('[COMPLETE]')
        ignore_item = (args.hide_completed and is_complete) or \
                      (args.completed_only and not is_complete) or \
                      (args.expert_mode and any(tag in node.title for tag in IGNORE_ITEM_TAGS))

        if ignore_item:
            result.extend(node.children if node.children else [])
            continue

        if args.expert_mode and any(tag in node.title for tag in IGNORE_OUTLINE_TAGS):
            continue

        result.append(node)

    for tree in result:
        ignore_tree(tree, args)

    return result


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
        print('  ' * level,"title:",node.title,"|","note:", node.note, "|", "parent:", node.parent.title, "|", "children:", print_children(node))
    else:
        print('  ' * level,"title:",node.title,"|","note:", node.note, "|", "children:", print_children(node))
    for child in node.children:
        print_tree(child, level + 1)

def print_children(node:Node) -> str:
    res = ""
    for child in node.children:
        res += f"{child.title}/"
    return res