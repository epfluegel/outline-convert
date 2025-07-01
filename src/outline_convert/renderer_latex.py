import argparse
from inspect import cleandoc
from typing import List
import re

from .models import Node
from .utils import escape_latex, clean_text, link_replacer


def render_latex(node: Node, args: argparse.Namespace, level: int = 0) -> List[str]:
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
        if args.strip_tags:
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
            lines.extend(render_latex(child, args = args))
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
            if args.strip_tags:
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
LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

def render_latex_beamer(node: Node, args: argparse.Namespace, level: int = -1, header_level: int = 0) -> List[str]:
    lines: List[str] = []
    if level == -1:
        if not args.fragment:
            doc_title = clean_text(node.title, strip_tags=args.strip_tags) if node.children else "Untitled"
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
        level = level + 1

    for child in node.children:
        title = child.title.strip()
        tags = [part for part in title.split() if part.startswith('#')]
        if args.expert_mode:
            if "#h" in tags:
                clean_title = clean_text(title, args.strip_tags)
                if header_level == 0:
                    lines.append(fr"\section{{{clean_title}}}")
                    lines.extend(render_latex_beamer(child, args=args, level=level+1, header_level=header_level + 1))

                elif header_level == 1:
                    lines.append(fr"\subsection{{{clean_title}}}")
                    lines.extend(render_latex_beamer(child, args=args, level=level+1,header_level=header_level + 1))
                else:
                    lines.append(fr"\subsubsection{{{clean_title}}}")
                    lines.extend(render_latex_beamer(child, args=args, level=level+1, header_level=header_level + 1))

# There should not be any #h inside a slide node

            elif "#slide" in tags or level == 0 :
                clean_title = clean_text(title, args.strip_tags)
                lines.append(fr"\begin{{frame}}{{{clean_title}}}")
                if child.children:
                    lines.append(r"\begin{itemize}")
                    lines.extend(render_latex_beamer(child, args=args, level=level+1, header_level=header_level))
                    lines.append(r"\end{itemize}")
                lines.append(r"\end{frame}")

            else:

                i = IMAGE_RE.match(title)
                if i:
                    filename = i.group(1)
                    lines.extend([
                        r"\begin{figure}[t]",
                        fr"\includegraphics[width=.75\textwidth]{{{filename}}}",
                        r"\centering",
                        r"\end{figure}",
                    ])
                    continue

                res = LINK_RE.sub(link_replacer, title)
                if res != title:
                    lines.append(fr'\item {res}')
                    continue

                indent = '  ' * level
                clean_title = clean_text(title, args.strip_tags)
                lines.append(fr"{indent}\item {clean_title}")
                if args.include_notes:
                    if child.note:
                        note = clean_text(child.note, args.strip_tags)
                        lines.append(fr"{indent}\begin{{quote}}")
                        lines.append(fr"{indent}{note}")
                        lines.append(fr"{indent}\end{{quote}}")
                if child.children:
                    lines.append(fr"{indent}\begin{{itemize}}")
                    lines.extend(render_latex_beamer(child, args=args, level=level+1, header_level=header_level))
                    lines.append(fr"{indent}\end{{itemize}}")
        else:
            if level == 0:
                clean_title = clean_text(title, args.strip_tags)
                lines.append(fr"\begin{{frame}}{{{clean_title}}}")
                if child.children:
                    lines.append(r"\begin{itemize}")
                    lines.extend(
                        render_latex_beamer(child, args=args, level=level+1, header_level=header_level))
                    lines.append(r"\end{itemize}")
                lines.append(r"\end{frame}")
            else:
                i = IMAGE_RE.match(title)
                if i:
                    filename = i.group(1)
                    lines.extend([
                        r"\begin{figure}[t]",
                        fr"\includegraphics[width=.75\textwidth]{{{filename}}}",
                        r"\centering",
                        r"\end{figure}",
                    ])
                    continue

                l = LINK_RE.match(title)
                if l:
                    text, url, description = l.group(1), l.group(2), l.group(3)
                    res = fr"\item \href{{{url}}}{{{escape_latex(text)}}} {escape_latex(description)}"
                    lines.append(res)
                    continue

                indent = '  ' * level
                clean_title = clean_text(title, args.strip_tags)
                lines.append(fr"{indent}\item {clean_title}")
                if args.include_notes:
                    if child.note:
                        note = clean_text(child.note, args.strip_tags)
                        lines.append(fr"{indent}\begin{{quote}}")
                        lines.append(fr"{indent}{note}")
                        lines.append(fr"{indent}\end{{quote}}")
                if child.children:
                    lines.append(fr"{indent}\begin{{itemize}}")
                    lines.extend(
                        render_latex_beamer(child, args=args, level=level+1, header_level=header_level))
                    lines.append(fr"{indent}\end{{itemize}}")


    level = level - 1
    if level == -1:
        if not args.fragment:
            lines.append(r"\end{document}")

    return lines














