from typing import List, Optional

from .models import Node
import xml.etree.ElementTree as ET
from .utils import indent
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
        bullet_prefix = args.bullet_symbol + ' ' * len(args.bullet_symbol)
        lines.append(indent + bullet_prefix + title)

    if node.note and args.include_notes:
        lines.append(indent + f'"{node.note}"')

    for child in node.children:
        lines.extend(render_text(child, args, level + 1))

    return lines


# -- RENDER OPML ------------------------------------------------------------
def node_to_outline_elem(node: Node, args: argparse.Namespace) -> ET.Element:
    elem = ET.Element('outline')
    title = node.title
    if args.strip_tags:
        title = ' '.join(part for part in title.split() if not part.startswith('#'))
    elem.set('text', title)
    if args.include_notes and node.note:
        elem.set('_note', node.note)
    for c in node.children:
        elem.append(node_to_outline_elem(c, args))
    return elem

def build_opml(root: Node,args: argparse.Namespace, owner_email: Optional[str] = None) -> ET.ElementTree:
    opml = ET.Element('opml', version='2.0')
    head = ET.SubElement(opml, 'head')
    if owner_email:
        em = ET.SubElement(head, 'ownerEmail')
        em.text = f"\n      {owner_email}\n    "
    body = ET.SubElement(opml, 'body')

    body.append(node_to_outline_elem(root, args))
    tree = ET.ElementTree(opml)
    try:
        ET.indent(tree, space='  ')
    except AttributeError:
        indent(opml)
    return tree