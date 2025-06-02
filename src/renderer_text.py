from typing import List, Optional

from .models import Node
import xml.etree.ElementTree as ET
from .utils import indent


# -- RENDER TEXT ------------------------------------------------------------
def render_text(node: Node, level: int = 0, indent_size: int = 2, strip_tags: bool = False) -> List[str]:
    lines: List[str] = []
    for child in node.children:
        title = child.title
        if strip_tags:
            title = ' '.join(part for part in title.split() if not part.startswith('#'))
        prefix = ' ' * (level * indent_size) + '- ' + title

        lines.append(prefix)
        if child.note:
            lines.append(' ' * (level * indent_size) + f'"{child.note}"')
        lines.extend(render_text(child, level+1, indent_size, strip_tags=strip_tags))
    return lines

# -- RENDER OPML ------------------------------------------------------------
def node_to_outline_elem(node: Node, strip_tags: bool = False) -> ET.Element:
    elem = ET.Element('outline')
    title = node.title
    if strip_tags:
        title = ' '.join(part for part in title.split() if not part.startswith('#'))
    elem.set('text', title)
    if node.note:
        elem.set('_note', node.note)
    for c in node.children:
        elem.append(node_to_outline_elem(c, strip_tags=strip_tags))
    return elem

def build_opml(root: Node, owner_email: Optional[str] = None) -> ET.ElementTree:
    opml = ET.Element('opml', version='2.0')
    head = ET.SubElement(opml, 'head')
    if owner_email:
        em = ET.SubElement(head, 'ownerEmail')
        em.text = f"\n    {owner_email}\n  "
    body = ET.SubElement(opml, 'body')
    for c in root.children:
        body.append(node_to_outline_elem(c))
    tree = ET.ElementTree(opml)
    try:
        ET.indent(tree, space='  ')
    except AttributeError:
        indent(opml)
    return tree