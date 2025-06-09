from typing import List, Optional

from .models import Node
import xml.etree.ElementTree as ET
import re
from .utils import detect_indent


def parse_text(lines: List[str], expert_mode: bool = False) -> Node:
    root = Node('root')
    stack = [(-1, root)]
    indent_size = detect_indent(lines)
    last_node: Optional[Node] = None

    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            continue
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
        parent = stack[-1][1]

        if expert_mode and "#wfe-ignore-item" in title:
            last_node = None
            continue

        parent.children.append(node)
        stack.append((level, node))
        last_node = node

    return root


def parse_opml(root_elem: ET.Element, expert_mode: bool = False) -> Node:
    body = root_elem.find('body')
    top = Node('root')
    if body is None:
        return top

    def recurse(elem: ET.Element, parent: Node):
        title = elem.get('text', '')
        node = Node(title)
        note = elem.get('_note')
        if note:
            node.note = note

        if expert_mode and "#wfe-ignore-item" in title:
            for child_elem in elem.findall('outline'):
                recurse(child_elem, parent)
        else:
            parent.children.append(node)
            for child_elem in elem.findall('outline'):
                recurse(child_elem, node)

    for outline in body.findall('outline'):
        recurse(outline, top)

    return top
