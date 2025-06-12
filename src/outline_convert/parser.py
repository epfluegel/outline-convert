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
    skip_until_level: Optional[int] = None  # Used to skip subtrees

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

        if skip_until_level is not None and level > skip_until_level:
            continue  # Skip children of #wfe-ignore-outline node
        else:
            skip_until_level = None  # Reset if level is no longer deeper

        title = re.sub(r'^-+\s*', '', leading.strip())

        if expert_mode and "#wfe-ignore-outline" in title:
            skip_until_level = level
            last_node = None
            continue  # Skip this node and its entire subtree

        node = Node(title)

        while stack and stack[-1][0] >= level:
            stack.pop()
        parent = stack[-1][1]

        if expert_mode and "#wfe-ignore-item" in title:
            last_node = None
            continue  # Skip node, but children will still attach to parent

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

        if expert_mode and "#wfe-ignore-outline" in title:
            return  # Skip entire subtree

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
