from typing import List, Optional

from .models import Node
import xml.etree.ElementTree as ET
from .utils import indent
import argparse


def render_text(node: Node, args: argparse.Namespace, indent_char: str , bullet_symbol: str, strip_tags: bool = False, level: int = 0, ) -> List[str]:
    lines: List[str] = []
    if level == 0:
        lines.append(node.title)
    for child in node.children:
        title = child.title
        if strip_tags:
            title = ' '.join(part for part in title.split() if not part.startswith('#'))
        prefix = indent_char * level + bullet_symbol + ' ' * len(bullet_symbol) + title

        lines.append(prefix)
        if child.note:
            lines.append(' ' * level + f'"{child.note}"')
        lines.extend(
            render_text(child, args, indent_char=indent_char, bullet_symbol=bullet_symbol, strip_tags=strip_tags,
                        level=level + 1))
    return lines


# -- RENDER OPML ------------------------------------------------------------
def node_to_outline_elem(node: Node, args: argparse.Namespace, strip_tags: bool = False) -> ET.Element:
    elem = ET.Element('outline')
    title = node.title
    if strip_tags:
        title = ' '.join(part for part in title.split() if not part.startswith('#'))
    elem.set('text', title)
    if node.note:
        elem.set('_note', node.note)
    for c in node.children:
        elem.append(node_to_outline_elem(c, args, strip_tags=strip_tags))
    return elem

def build_opml(root: Node,args: argparse.Namespace, owner_email: Optional[str] = None, strip_tags: bool = False) -> ET.ElementTree:
    opml = ET.Element('opml', version='2.0')
    head = ET.SubElement(opml, 'head')
    if owner_email:
        em = ET.SubElement(head, 'ownerEmail')
        em.text = f"\n      {owner_email}\n    "
    body = ET.SubElement(opml, 'body')
    for c in root.children:
        # pass strip_tags down into node_to_outline_elem
        body.append(node_to_outline_elem(c, args, strip_tags=strip_tags))
    tree = ET.ElementTree(opml)
    try:
        ET.indent(tree, space='  ')
    except AttributeError:
        indent(opml)
    return tree