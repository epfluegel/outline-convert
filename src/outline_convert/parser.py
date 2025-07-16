import argparse
from typing import List, Optional

from .models import Node
import xml.etree.ElementTree as ET
import re
from .utils import detect_indent, compute_level, link_parent, print_tree

IGNORE_OUTLINE_TAGS = {"#wfe-ignore-outline", "#ignore-outline"}
IGNORE_ITEM_TAGS = {"#wfe-ignore-item", "#ignore-item", "#hh"}

def parse_text(lines, args):
    trees = []
    indent_size = detect_indent(lines)
    chunk = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue   # drop blank lines

        level = compute_level(line, indent_size)
        # only start a new chunk if it's a non-bullet level-0 line
        if level == 0 and not stripped.startswith('-'):
            if chunk:
                trees.append(parse_text_tree(chunk, args))
            chunk = [line]
        else:
            chunk.append(line)

    if chunk:
        trees.append(parse_text_tree(chunk, args))
    return trees


def parse_text_tree(lines: List[str], args: argparse.Namespace) -> Node:
    root = Node(lines[0].strip())
    stack = [(-1, root)]
    indent_size = detect_indent(lines)
    last_node: Optional[Node] = None
    skip_until_level: Optional[int] = None

    for line in lines[1:]:
        stripped = line.strip()

        # 1) skip blank lines
        if not stripped:
            continue

        # 2) if it's a quoted line, treat as a note
        if stripped.startswith('"') and stripped.endswith('"'):
            note_text = stripped.strip('"')
            if last_node:
                # attach to the most recently created node
                last_node.note = note_text
            else:
                # no node yet → this is the root's note
                root.note = note_text
            continue

        # 3) otherwise it's an outline item — compute its level
        leading = line.expandtabs(indent_size)
        level = compute_level(line, indent_size)

        title = re.sub(r'^-+\s*', '', leading.strip())

        # 5) create the node
        node = Node(title)

        # find its parent by popping until we reach the correct level
        while stack and stack[-1][0] >= level:
            stack.pop()
        parent = stack[-1][1]

        parent.children.append(node)
        stack.append((level, node))
        last_node = node
    link_parent(root)
    return root

def parse_opml(root_elem: ET.Element, args: argparse.Namespace) -> List[Node]:
    head = root_elem.find('head')
    title = 'Untitled'
    if head is not None:
        root_title = head.find('title')
        title = root_title.text
    root = Node(title)
    body = root_elem.find('body')
    if body is None:
        return Node('Empty OPML')
    
    first_outline = body.find('outline')
    if first_outline is None:
        return Node('Empty OPML')

    note = first_outline.get('_note')
    if note:
        root.note = note
    
    def recurse(elem: ET.Element, parent: Node):
        for child_elem in elem.findall('outline'):
            title = child_elem.get('text', '')
            node = Node(title)
            note = child_elem.get('_note')
            if note:
                node.note = note
            else:
                parent.children.append(node)
                node.parent = parent
                recurse(child_elem, node)

    recurse(body, root)

    return [root]