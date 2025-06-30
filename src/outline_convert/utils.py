from math import gcd
from typing import List, Optional

from .models import Node
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


# -- TREE UTILITIES ---------------------------------------------------------
def find_node(node: Node, prefix: str) -> Optional[Node]:
    text = node.title
    ok = text.startswith(prefix)
    if ok:
        return node
    for c in node.children:
        res = find_node(c, prefix)
        if res:
            return res
    return None



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

def clean_text(title: str, strip_tags: bool) -> str:
    parts = title.strip().split()
    if strip_tags:
        parts = [p for p in parts if not p.startswith('#')]
    return escape_latex(' '.join(parts))


def link_replacer(match):
    text, url = match.group(1), match.group(2)
    print("inside the link replacer")
    return fr"\href{{{url}}}{{{escape_latex(text)}}}"

