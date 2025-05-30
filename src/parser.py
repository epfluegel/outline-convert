from typing import List, Optional

from .models import Node
import xml.etree.ElementTree as ET
import re
from .utils import detect_indent


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