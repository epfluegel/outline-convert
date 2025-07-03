from typing import List, Optional

from .models import Node
import xml.etree.ElementTree as ET
from .utils import indent, node_to_outline_elem
import argparse


def render_text(node: Node, args: argparse.Namespace, level: int = 0, ) -> List[str]:
    lines: List[str] = []

    title = node.title
    if args.strip_tags:
        title = ' '.join(part for part in title.split() if not part.startswith('#'))
    indent = args.indent_string * level
    if level == 0:
        lines.append(title)
    else:
        bullet_prefix = args.bullet_symbol + ' '
        lines.append(indent + bullet_prefix + title)

    if node.note and args.include_notes:
        lines.append(indent + f'"{node.note}"')

    for child in node.children:
        lines.extend(render_text(child, args, level + 1))

    return lines


def render_opml(node: Node, args: argparse.Namespace, level: int = 0) -> ET.ElementTree:
    """Recursively render nodes to OPML, similar to render_text pattern"""
    if level == 0:
        # Create the root OPML structure only at the top level
        opml = ET.Element('opml', version='2.0')
        head = ET.SubElement(opml, 'head')
        if args.email:
            em = ET.SubElement(head, 'ownerEmail')
            em.text = f"\n      {args.email}\n    "
        body = ET.SubElement(opml, 'body')

        # Add the root node
        root_elem = node_to_outline_elem(node, args)
        body.append(root_elem)

        # Recursively add children to the root element
        for child in node.children:
            child_tree = render_opml(child, args, level + 1)
            root_elem.append(child_tree)

        # Format and return the complete tree
        tree = ET.ElementTree(opml)
        try:
            ET.indent(tree, space='  ')
        except AttributeError:
            indent(opml)
        return tree
    else:
        # For recursive calls, just return the element for this node
        elem = node_to_outline_elem(node, args)

        # Add children recursively
        for child in node.children:
            child_elem = render_opml(child, args, level + 1)
            elem.append(child_elem)

        return elem
