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
def find_node(node: Node, prefix: str, case_sensitive: bool) -> Optional[Node]:
    text = node.title
    if case_sensitive:
        ok = text.startswith(prefix)
    else:
        ok = text.lower().startswith(prefix.lower())
    if ok:
        return node
    for c in node.children:
        res = find_node(c, prefix, case_sensitive)
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

#def escape_latex(s: str) -> str:
#    return s.replace('\\', r'\textbackslash{}').replace('&', r"\&").replace('%', r'\%').replace('$', r'\$')\
#            .replace('#', r'\#').replace('_', r'\_').replace('{', r'\{')\
#            .replace('}', r'\}').replace('~', r'\textasciitilde{}')\
#            .replace('^', r'\textasciicircum{}')
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



def render_latex_beamer_with_tags_former(node: Node, level: int = 0, expert_mode: bool = False, strip_tags: bool = False, fragment: bool = False) -> List[str]:
    lines: List[str] = []

    def clean_text(title: str) -> str:
        parts = title.strip().split()
        if strip_tags:
            parts = [p for p in parts if not p.startswith('#')]
        return escape_latex(' '.join(parts))

    # --- Preamble & title page frame ---
    if level == 0:
        if not fragment:
            doc_title = clean_text(node.children[0].title) if node.children else "Untitled"
            lines.extend([
                r"\documentclass{beamer}",
                r"\usepackage[T1]{fontenc}",
                r"\usepackage{graphicx}",
                r"\usetheme{Goettingen}",
                r"\definecolor{links}{HTML}{2A1B81}",
                r"\hypersetup{colorlinks,linkcolor=,urlcolor=links}",
                fr"\title{{{doc_title}}}",
                r"\date{\today}",
                r"\AtBeginSection[]",
                r"{",
                r"  \begin{frame}<beamer>{Outline}",
                r"      \tableofcontents[currentsection, currentsubsection]",
                r"  \end{frame}",
                r"}",
                r"\begin{document}",
                r"\begin{frame}",
                r"  \titlepage",
                r"\end{frame}",
                ""
            ])

    # --- Find only #slide nodes ---
    def find_slides(n: Node) -> List[Node]:
        slides: List[Node] = []
        if expert_mode:
            tags = {p for p in n.title.split() if p.startswith('#')}
            if '#slide' in tags:
                slides.append(n)
        for c in n.children:
            slides.extend(find_slides(c))
        return slides

    # --- Emit \section / \subsection before frames ---
    def emit_sections(n: Node, depth: int):
        if not expert_mode:
            return
        for c in n.children:
            tags = {p for p in c.title.split() if p.startswith('#')}
            clean = clean_text(c.title)
            if '#h' in tags and depth == 1:
                lines.append(fr"\section{{{clean}}}")
            elif '#h' in tags and depth == 2:
                lines.append(fr"\subsection{{{clean}}}")
            emit_sections(c, depth + 1)

    # --- Collect all \item… lines under a slide ---
    def collect_items(n: Node, lvl: int = 0) -> List[str]:
        result: List[str] = []
        for c in n.children:
            raw = c.title.strip()
            tags = {p for p in raw.split() if p.startswith('#')}

            # 1) IMAGE?
            m = IMAGE_RE.match(raw)
            if m:
                filename = m.group(1)            # e.g. "assets.png"
                result.extend([
                    r"\begin{figure}[t]",
                    fr"\includegraphics[width=.75\textwidth]{{{filename}}}",
                    r"\centering",
                    r"\end{figure}",
                ])
                # skip all the normal \item logic
                continue

            # 2) LINK?
            #    replace “[text](url)” → “\href{url}{text}”
            def link_sub(m: re.Match) -> str:
                text, url, description = m.group(1), m.group(2), m.group(3)
                return fr"\item \href{{{url}}}{{{escape_latex(text)}}} {escape_latex(description)}"

            l = LINK_RE.match(raw)
            if l:
                res = link_sub(l)
                result.append(res)
                continue



            # 2) HEADER/SLIDE tags (expert_mode) get skipped here
            if expert_mode and ('#slide' in tags or '#h' in tags):
                result.extend(collect_items(c, lvl))
                continue

            # 3) otherwise, a normal item
            text = clean_text(raw)
            indent = '  ' * lvl
            result.append(fr"{indent}\item {text}")

            if c.note:
                note = escape_latex(c.note)
                result.extend([
                    fr"{indent}  \begin{{quote}}",
                    fr"{indent}  {note}",
                    fr"{indent}  \end{{quote}}",
                ])

            # 4) recurse for sub-items
            sub = collect_items(c, lvl + 1)
            if sub:
                result.append(fr"{indent}  \begin{{itemize}}")
                result.extend(sub)
                result.append(fr"{indent}  \end{{itemize}}")

        return result

    # --- Determine which nodes become frames ---
    if expert_mode:
        # only #slide-tagged nodes
        slides = find_slides(node)
    else:
        # every top-level child is its own frame
        slides = list(node.children[0].children)

    # --- Render each frame ---
    for slide in slides:
        emit_sections(slide, depth=1)

        title = clean_text(slide.title)
        if not expert_mode:
            lines.append(fr"\begin{{frame}}{{{title}}}")
        else:
            lines.append(fr"\begin{{frame}}{{{title}}}")

        items = collect_items(slide)
        if items:
            lines.append(r"\begin{itemize}")
            lines.extend(items)
            lines.append(r"\end{itemize}")

        lines.append(r"\end{frame}")
        lines.append("")

    # --- Close document ---
    if level == 0:
        if not fragment:
            lines.append(r"\end{document}")

    return lines


