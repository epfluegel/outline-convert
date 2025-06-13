from typing import List
import re

from .models import Node
from .utils import escape_latex


def render_latex(node: Node, level: int = 0, strip_tags: bool = False) -> List[str]:
    lines: List[str] = []
    if level == 0:
        lines.extend([
            r"\documentclass{article}",
            r"\usepackage{enumitem}",
            r"\usepackage[T1]{fontenc}",
            r"\begin{document}",
            r"\newlist{tree}{enumerate}{10}",
            r"\setlistdepth{10}",
            r"\setlist[tree]{label=\textbullet}",
            r"\begin{tree}"
        ])
    for child in node.children:

        title = child.title.strip()
        if strip_tags:
            title = ' '.join(part for part in title.split() if not part.startswith('#'))
        title = escape_latex(title)

        indent = '  ' * level
        lines.append(fr"{indent}\item {title}")
        if child.note:
            lines.append(fr"{indent}\begin{{quote}}")
            lines.append(fr"{indent}{child.note}")
            lines.append(fr"{indent}\end{{quote}}")
        if child.children:
            lines.append(fr"{indent}\begin{{tree}}")
            lines.extend(render_latex(child, level + 1, strip_tags=strip_tags))
            lines.append(fr"{indent}\end{{tree}}")
    if level == 0:
        lines.append(r"\end{tree}")
        lines.append(r"\end{document}")
    return lines


    def process_children(children: List[Node], level: int) -> List[str]:
        sublines: List[str] = []
        indent = '  ' * level
        for child in children:
            title = child.title.strip()
            if strip_tags:
                title = ' '.join(part for part in title.split() if not part.startswith('#'))
            title = escape_latex(title)

            sublines.append(fr"{indent}\item {title}")
            if child.note:
                sublines.append(fr"{indent}\begin{{quote}}")
                sublines.append(fr"{indent}{escape_latex(child.note)}")
                sublines.append(fr"{indent}\end{{quote}}")
            if child.children:
                sublines.append(fr"{indent}\begin{{itemize}}")
                sublines.extend(process_children(child.children, level + 1))
                sublines.append(fr"{indent}\end{{itemize}}")
        return sublines

    if level == 0:

        document_title = escape_latex(node.children[0].title.strip()) if node.children else "Untitled"
        lines.extend([
            r"\documentclass{beamer}",
            r"\usepackage[T1]{fontenc}",
            r"%\setbeamertemplate{frametitle continuation}{}",
            r"\usetheme{Goettingen}",
            r"\definecolor{links}{HTML}{2A1B81}",
            r"\hypersetup{colorlinks,linkcolor=,urlcolor=links}",
            fr"\title{{{document_title}}}",
            r"\date{\today}",
            r"\AtBeginSection[]",
            r"{",
            r"  \begin{frame} <beamer> {Outline}",
            r"    \tableofcontents[currentsection, currentsubsection]",
            r"  \end{frame}",
            r"}",
            r"\begin{document}",
            r"\begin{frame}",
            r"  \titlepage",
            r"\end{frame}"
        ])

        for child in node.children:
            frame_title = escape_latex(child.title.strip())
            lines.append(fr"\begin{{frame}}{{{frame_title}}}")
            lines.append(r"\begin{itemize}")
            lines.extend(process_children(child.children, level=1))
            lines.append(r"\end{itemize}")
            lines.append(r"\end{frame}")

        lines.append(r"\end{document}")

    return lines


IMAGE_RE = re.compile(r'!\[([^\]]+)\]\([^\)]+\)')

def render_latex_beamer_with_tags(node: Node, level: int = 0, expert_mode: bool = False, strip_tags: bool = False, fragment: bool = False) -> List[str]:
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
                    fr"\includegraphics[width=.75\textwidth]{{assets/{filename}}}",
                    r"\centering",
                    r"\end{figure}",
                ])
                # skip all the normal \item logic
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
