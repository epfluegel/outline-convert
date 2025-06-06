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

def render_latex_beamer(node: Node, level: int = 0, strip_tags: bool = False) -> List[str]:
    lines: List[str] = []

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
    if level == 0:
        lines.extend([
            r"\documentclass{beamer}",
            r"\usepackage[T1]{fontenc}",
            r"\usetheme{Goettingen}",
            r"\definecolor{links}{HTML}{2A1B81}",
            r"\hypersetup{colorlinks,linkcolor=,urlcolor=links}",
            #todo fix title
            r"\title{Guidance on Dissertation Project Topic }",
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
            r"  \begin",
            r"      {frame} < beamer > {Outline}",
            r"          \tableofcontents[currentsection, currentsubsection]",
            r"  \end{frame}",
            r"}",
            r"\begin{document}",
            r"\begin{frame}",
            r"  \titlepage",
            r"\end{frame}"
        ])

    for child in node.children:
        title = child.title.strip()
        tags = [part for part in title.split() if part.startswith('#')]
        clean_title = ' '.join(part for part in title.split() if not part.startswith('#'))
        if "#wfe-ignore-outline" in title:
            continue
        if "#slide" in tags:
            clean_title = escape_latex(clean_title)
            lines.append(fr"\begin{{frame}}{{{clean_title}}}")
            if child.children:
                lines.append(r"\begin{itemize}")
                lines.extend(render_latex_beamer_with_tags(child, level + 1))
                lines.append(r"\end{itemize}")
            lines.append(r"\end{frame}")
        else:
            indent = '  ' * level
            clean_title = escape_latex(clean_title)
            lines.append(fr"{indent}\item {clean_title}")
            if child.note:
                note = escape_latex(child.note)
                lines.append(fr"{indent}\begin{{quote}}")
                lines.append(fr"{indent}{note}")
                lines.append(fr"{indent}\end{{quote}}")
            if child.children:
                lines.append(fr"{indent}\begin{{itemize}}")
                lines.extend(render_latex_beamer_with_tags(child, level + 1))
                lines.append(fr"{indent}\end{{itemize}}")

    if level == 0:
        lines.append(r"\end{document}")
    return lines

def render_latex_beamer_with_tags_V2(node: Node, level: int = 0) -> List[str]:
    lines: List[str] = []

    # At level 0, emit the preamble once
    if level == 0:
        lines.extend([
            r"\documentclass{beamer}",
            r"\usepackage[T1]{fontenc}",
            r"\usetheme{Goettingen}",
            r"\definecolor{links}{HTML}{2A1B81}",
            r"\hypersetup{colorlinks,linkcolor=,urlcolor=links}",
            # TODO: adjust title/author/institute as needed
            r"\title{Guidance on Dissertation Project Topic}",
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
            r"  \begin{frame}{Outline}",
            r"    \tableofcontents[currentsection, currentsubsection]",
            r"  \end{frame}",
            r"}",
            r"\begin{document}",
            r"\begin{frame}",
            r"  \titlepage",
            r"\end{frame}"
        ])

    # Now iterate over each child of this node
    for child in node.children:
        raw_title = child.title.strip()
        # Pull out any “#…” tags
        tags = [part for part in raw_title.split() if part.startswith('#')]
        # Remove tags from the text
        clean_title = ' '.join(part for part in raw_title.split() if not part.startswith('#'))
        # Escape any LaTeX metacharacters
        clean_title = escape_latex(clean_title)

        # —————— LEVEL 0: always a new frame ——————
        if level == 0:
            # Open frame with the (possibly empty) clean_title
            lines.append(fr"\begin{{frame}}{{{clean_title}}}")
            # If there are children, put them into an itemize block
            if child.children:
                lines.append(r"\begin{itemize}")
                lines.extend(render_latex_beamer_with_tags(child, level + 1))
                lines.append(r"\end{itemize}")
            lines.append(r"\end{frame}")
            # Skip the rest; we've handled this node completely
            continue

        # —————— LEVEL 1: always an item in itemize ——————
        if level == 1:
            indent = '  ' * (level - 1)
            lines.append(fr"{indent}\item {clean_title}")
            if child.note:
                note = escape_latex(child.note)
                lines.append(fr"{indent}  \begin{{quote}}")
                lines.append(fr"{indent}  {note}")
                lines.append(fr"{indent}  \end{{quote}}")
            # If it has grandchildren, nest another itemize
            if child.children:
                lines.append(fr"{indent}  \begin{{itemize}}")
                lines.extend(render_latex_beamer_with_tags(child, level + 1))
                lines.append(fr"{indent}  \end{{itemize}}")
            # No explicit \end{frame} here, because items live inside the frame begun at level 0
            continue

        # —————— LEVEL ≥ 2: deeper bullets become nested \item ——————
        indent = '  ' * (level - 1)
        lines.append(fr"{indent}\item {clean_title}")
        if child.note:
            note = escape_latex(child.note)
            lines.append(fr"{indent}  \begin{{quote}}")
            lines.append(fr"{indent}  {note}")
            lines.append(fr"{indent}  \end{{quote}}")
        if child.children:
            lines.append(fr"{indent}  \begin{{itemize}}")
            lines.extend(render_latex_beamer_with_tags(child, level + 1))
            lines.append(fr"{indent}  \end{{itemize}}")

    # At the very end (once we've unwound all levels back to 0), close the document
    if level == 0:
        lines.append(r"\end{document}")

    return lines

