from typing import List

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
            r"\subtitle{}",
            r"\author{author\inst{1}}",
            r"\institute[Universities of Somewhere and Elsewhere]{",
            r"  \inst{1}%",
            r"  School of Computer Science and Mathematics",
            r"  Kingston University",
            r"}",
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
            lines.append(fr"\begin{{frame}}[allowframebreaks]{{{frame_title}}}")
            lines.append(r"\begin{itemize}")
            lines.extend(process_children(child.children, level=1))
            lines.append(r"\end{itemize}")
            lines.append(r"\end{frame}")

        lines.append(r"\end{document}")

    return lines



def render_latex_beamer_with_tags(node: Node, level: int = 0) -> List[str]:
    lines: List[str] = []
    # --- Preamble & title page frame ---
    if level == 0:
        document_title = escape_latex(node.children[0].title.strip()) if node.children else "Untitled"
        lines.extend([
            r"\documentclass{beamer}",
            r"\usepackage[T1]{fontenc}",
            r"\usetheme{Goettingen}",
            r"\definecolor{links}{HTML}{2A1B81}",
            r"\hypersetup{colorlinks,linkcolor=,urlcolor=links}",
            fr"\title{{{document_title}}}",
            r"\subtitle{}",
            r"\author{author\inst{1}}",
            r"\institute[Universities of Somewhere and Elsewhere]{",
            r"  \inst{1}%",
            r"  School of Computer Science and Mathematics",
            r"  Kingston University",
            r"}",
            r"\date{\today}",
            r"\AtBeginSection[]",
            r"{",
            r"  \begin{frame} <beamer> {Outline}",
            r"      \tableofcontents[currentsection, currentsubsection]",
            r"  \end{frame}",
            r"}",
            r"\begin{document}",
            r"\begin{frame}",
            r"  \titlepage",
            r"\end{frame}",
            ""
        ])

    # --- Helper: find all slide-tagged nodes anywhere in tree ---
    def find_slides(n: Node) -> List[Node]:
        slides: List[Node] = []
        parts = n.title.strip().split()
        tags = {p for p in parts if p.startswith('#')}
        if '#slide' in tags:
            slides.append(n)
        for c in n.children:
            slides.extend(find_slides(c))
        return slides

    # --- Emit section/subsection commands before frames ---
    def emit_sections(n: Node, depth: int):
        for c in n.children:
            parts = c.title.strip().split()
            tags = {p for p in parts if p.startswith('#')}
            clean = escape_latex(' '.join(p for p in parts if not p.startswith('#')))
            if '#h' in tags:
                if depth == 1:
                    lines.append(fr"\section{{{clean}}}")
                elif depth == 2:
                    lines.append(fr"\subsection{{{clean}}}")
            emit_sections(c, depth + 1)

    # --- Collect all \item lines for a given slide node ---
    def collect_items(n: Node, lvl: int = 0) -> List[str]:
        result: List[str] = []
        for c in n.children:
            parts = c.title.strip().split()
            tags = {p for p in parts if p.startswith('#')}
            clean = escape_latex(' '.join(p for p in parts if not p.startswith('#')))
            # Skip nested headers/slides
            if '#slide' in tags or '#h' in tags:
                result.extend(collect_items(c, lvl))
                continue
            indent = '  ' * lvl
            result.append(fr"{indent}\item {clean}")
            if c.note:
                note = escape_latex(c.note)
                result.extend([
                    fr"{indent}  \begin{{quote}}",
                    fr"{indent}  {note}",
                    fr"{indent}  \end{{quote}}",
                ])
            sub = collect_items(c, lvl + 1)
            if sub:
                result.append(fr"{indent}  \begin{{itemize}}")
                result.extend(sub)
                result.append(fr"{indent}  \end{{itemize}}")
        return result

    # --- Main: render each slide found anywhere ---
    slides = find_slides(node)
    for slide in slides:
        # emit sections for this slide
        emit_sections(slide, depth=1)
        # begin frame
        parts = slide.title.strip().split()
        clean_title = escape_latex(' '.join(p for p in parts if not p.startswith('#')))
        lines.append(fr"\begin{{frame}}{{{clean_title}}}")
        # items
        items = collect_items(slide)
        if items:
            lines.append(r"\begin{itemize}")
            lines.extend(items)
            lines.append(r"\end{itemize}")
        lines.append(r"\end{frame}")
        lines.append("")

    # --- End document ---
    if level == 0:
        lines.append(r"\end{document}")
    return lines

