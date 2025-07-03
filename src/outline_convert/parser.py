import argparse
from typing import List, Optional

from .models import Node
import xml.etree.ElementTree as ET
import re
from .utils import detect_indent


def parse_text(lines: List[str], args: argparse.Namespace) -> Node:
    # Create root with the first line as its title
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
        space_count = len(leading) - len(leading.lstrip(' '))
        extra = indent_size if leading.lstrip().startswith('-') else 0
        level = (space_count + extra) // indent_size

        # 4) handle #wfe-ignore-outline
        if skip_until_level is not None and level > skip_until_level:
            continue
        else:
            skip_until_level = None

        title = re.sub(r'^-+\s*', '', leading.strip())

        if args.expert_mode and "#wfe-ignore-outline" in title:
            skip_until_level = level
            last_node = None
            continue

        # 5) create the node
        node = Node(title)

        # find its parent by popping until we reach the correct level
        while stack and stack[-1][0] >= level:
            stack.pop()
        parent = stack[-1][1]

        if args.expert_mode and "#wfe-ignore-item" in title:
            last_node = None
            continue  # skip this node but keep stacking its children

        parent.children.append(node)
        stack.append((level, node))
        last_node = node

    return root

def parse_opml(root_elem: ET.Element, args: argparse.Namespace) -> Node:
    body = root_elem.find('body')
    if body is None:
        return Node('Empty OPML')
    
    first_outline = body.find('outline')
    if first_outline is None:
        return Node('Empty OPML')
    
    root_title = first_outline.get('text', 'Untitled')
    root = Node(root_title)
    note = first_outline.get('_note')
    if note:
        root.note = note
    
    def recurse(elem: ET.Element, parent: Node):
        for child_elem in elem.findall('outline'):
            title = child_elem.get('text', '')

            if args.expert_mode and "#wfe-ignore-outline" in title:
                continue  # Skip entire subtree

            node = Node(title)
            note = child_elem.get('_note')
            if note:
                node.note = note

            if args.expert_mode and "#wfe-ignore-item" in title:
                recurse(child_elem, parent)
            else:
                parent.children.append(node)
                recurse(child_elem, node)

    recurse(first_outline, root)
    
    return root