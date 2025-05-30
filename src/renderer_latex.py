from typing import List

from .models import Node
from .utils import escape_latex


def render_latex(node: Node, level: int = 0) -> List[str]:
    lines: List[str] = []
    if level == 0:
        lines.extend([
            r"\documentclass{article}",
            r"\usepackage{enumitem}",
            r"\begin{document}",
            r"\newlist{tree}{enumerate}{10}",
            r"\setlistdepth{10}",
            r"\setlist[tree]{label=\textbullet}",
            r"\begin{tree}"
        ])
    for child in node.children:
        indent = '  ' * level
        lines.append(fr"{indent}\item {child.title}")
        if child.note:
            lines.append(fr"{indent}\begin{{quote}}{child.note}\end{{quote}}")
        if child.children:
            lines.append(fr"{indent}\begin{{tree}}")
            lines.extend(render_latex(child, level + 1))
            lines.append(fr"{indent}\end{{tree}}")
    if level == 0:
        lines.append(r"\end{tree}")
        lines.append(r"\end{document}")
    return lines

def render_latex_beamer_with_tags(node: Node, level: int = 0) -> List[str]:
    lines: List[str] = []
    if level == 0:
        lines.extend([
            r"\documentclass{beamer}",
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
            lines.append(fr"\begin{{frame}}{{{clean_title}}}")
            if child.children:
                lines.append(r"\begin{itemize}")
                lines.extend(render_latex_beamer_with_tags(child, level + 1))
                lines.append(r"\end{itemize}")
            lines.append(r"\end{frame}")
        else:
            indent = '  ' * level
            lines.append(fr"{indent}\item {clean_title}")
            if child.note:
                lines.append(fr"{indent}\begin{{quote}}{child.note}\end{{quote}}")
            if child.children:
                lines.append(fr"{indent}\begin{{itemize}}")
                lines.extend(render_latex_beamer_with_tags(child, level + 1))
                lines.append(fr"{indent}\end{{itemize}}")

    if level == 0:
        lines.append(r"\end{document}")
    return lines

#removing every part starting with "#" so that may cause wrong interpretation
def render_latex_beamer(node: Node, level: int = 0) -> List[str]:
    lines: List[str] = []
    if level == 0:
        lines.extend([
            r"\documentclass{beamer}",
            r"\usetheme{Goettingen}",
            r"\definecolor{links}{HTML}{2A1B81}",
            r"\hypersetup{colorlinks,linkcolor=,urlcolor=links}",
            # todo fix title
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
            r"  \begin{frame} < beamer > {Outline}",
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
        title = ' '.join(part for part in title.split() if not part.startswith('#'))  # remove tags
        if '&' in title:
            print(f"DEBUG: Title before escaping: {title}")
            title = escape_latex(title)
            print(f"DEBUG: Title after escaping: {title}")

        if level == 0:
            lines.append(fr"\begin{{frame}}{title}")
            lines.append(r"\end{frame}")
            if child.children:
                lines.extend(render_latex_beamer(child, level + 1))

        elif level == 1:
            lines.append(fr"\begin{{frame}}[allowframebreaks]{title}")
            if child.children:
                lines.append(r"\begin{itemize}")
                lines.extend(render_latex_beamer(child, level + 1))
                lines.append(r"\end{itemize}")
            lines.append(r"\end{frame}")

        else:
            indent = '  ' * level
            lines.append(fr"{indent}\item {title}")
            if child.note:
                lines.append(fr"{indent}\begin{{quote}}{child.note}\end{{quote}}")
            if child.children:
                lines.append(fr"{indent}\begin{{itemize}}")
                lines.extend(render_latex_beamer(child, level + 1))
                lines.append(fr"{indent}\end{{itemize}}")

    if level == 0:
        lines.append(r"\end{document}")
    return lines
