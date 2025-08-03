import argparse
from inspect import cleandoc
from typing import List
import re

from .models import Node
from .utils import clean_text, link_replacer, escape_markdown


def render_latex(forest: List[Node], args: argparse.Namespace) -> List[str]:
    lines: List[str] = []
    lines.extend([
        r"\documentclass{article}",
        r"\usepackage{enumitem}",
        r"\usepackage[T1]{fontenc}",
        r"\begin{document}",
        r"\newlist{tree}{itemize}{10}",
        r"\setlistdepth{10}",
        r"\setlist[tree]{label=\textbullet}",
    ])
    lines.append(r"\begin{tree}")
    for tree in forest:
        lines.extend(render_latex_tree(tree, args))

    lines.append(r"\end{tree}")
    lines.append(r"\end{document}")

    return lines


def render_latex_tree(node: Node, args: argparse.Namespace, level: int = 0) -> List[str]:
    lines: List[str] = []
    if level == 0:
        title = node.title.strip()
        if args.strip_tags:
            title = ' '.join(part for part in title.split() if not part.startswith('#'))
        title = clean_text(title, args)
        #if title.startswith('[COMPLETE]'):
        #    lines.append(r"\color{lightgray}")
        lines.append(fr"\item {title}")

    has_children = node.children
    if has_children:
        lines.append(fr"\begin{{tree}}")
    for child in node.children:
        title = child.title.strip()
        if args.strip_tags:
            title = ' '.join(part for part in title.split() if not part.startswith('#'))
        title = clean_text(title, args)
        indent = '  ' * level
        lines.append(fr"{indent}\item {title}")
        if child.note:
            lines.append(fr"{indent}\begin{{quote}}")
            lines.append(fr"{indent}{child.note}")
            lines.append(fr"{indent}\end{{quote}}")
        if child.children:
            lines.extend(render_latex_tree(child, args=args, level=level+1))
    if has_children:
        lines.append(fr"\end{{tree}}")

    return lines


IMAGE_RE = re.compile(r'!\[([^\]]+)\]\(([^\)]+)\)')
LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')


def render_latex_beamer(forest: List[Node], args: argparse.Namespace) -> List[str]:
    lines: List[str] = []
    if not args.fragment:
        doc_title = clean_text(forest[0].title, args)
        lines.extend([
            r"\documentclass{beamer}",
            r"\usepackage[T1]{fontenc}",
            r"\usepackage{graphicx}",
            r"\usetheme{Goettingen}",
            r"\usepackage{enumitem}",
            r"\newlist{tree}{itemize}{10}",
            r"\setlistdepth{10}",
            r"\setlist[tree]{label=\usebeamercolor[fg]{itemize item}\usebeamertemplate{itemize item}}",
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
        ])

    i = 0
    for tree in forest:
        if i!=0:
            doc_title = clean_text(tree.title, args)
            lines.extend([
            fr"\title{{{doc_title}}}",
            r"\begin{frame}",
            r"  \titlepage",
            r"\end{frame}",
            ])
        lines.extend(render_latex_beamer_tree(tree, args))
        i+=1

    if not args.fragment:
        lines.append(r"\end{document}")

    return lines


def render_latex_beamer_tree(node: Node, args: argparse.Namespace, level: int = 0, header_level: int = 0) -> List[str]:
    lines: List[str] = []

    for child in node.children:
        title = child.title.strip()
        tags = [part for part in title.split() if part.startswith('#')]
        if args.expert_mode:
            if "#h" in tags:
                clean_title = clean_text(title, args)
                if header_level == 0:
                    lines.append(fr"\section{{{clean_title}}}")
                    lines.extend(
                        render_latex_beamer_tree(child, args=args, level=level + 1, header_level=header_level + 1))

                elif header_level == 1:
                    lines.append(fr"\subsection{{{clean_title}}}")
                    lines.extend(
                        render_latex_beamer_tree(child, args=args, level=level + 1, header_level=header_level + 1))
                else:
                    lines.append(fr"\subsubsection{{{clean_title}}}")
                    lines.extend(
                        render_latex_beamer_tree(child, args=args, level=level + 1, header_level=header_level + 1))

            # There should not be any #h inside a slide node

            elif "#slide" in tags or level == 0:
                clean_title = clean_text(title, args)
                lines.append(fr"\begin{{frame}}{{{clean_title}}}")
                if child.children:
                    lines.append(r"\begin{tree}")
                    lines.extend(render_latex_beamer_tree(child, args=args, level=level + 1, header_level=header_level))
                    lines.append(r"\end{tree}")
                lines.append(r"\end{frame}")

            else:
                if args.parse_markdown:
                    i = IMAGE_RE.match(title)
                    if i:
                        file_location = i.group(2)
                        lines.extend([
                            r"\begin{figure}[t]",
                            fr"\includegraphics[width=.75\textwidth]{{{file_location}}}",
                            r"\centering",
                            r"\end{figure}",
                        ])
                        continue

                    res = LINK_RE.sub(link_replacer, title)
                    if res != title:
                        lines.append(fr'\item {res}')
                        continue

                indent = '  ' * level
                print(title)
                clean_title = clean_text(title, args)
                #if clean_title.startswith('[COMPLETE]'):
                #    print("complete item", clean_title)
                #    lines.append(r"\color{lightgray}")
                lines.append(fr"{indent}\item {clean_title}")
                if args.include_notes:
                    if child.note:
                        note = clean_text(child.note, args)
                        lines.append(fr"{indent}\begin{{quote}}")
                        lines.append(fr"{indent}{note}")
                        lines.append(fr"{indent}\end{{quote}}")
                if child.children:
                    lines.append(fr"{indent}\begin{{tree}}")
                    lines.extend(render_latex_beamer_tree(child, args=args, level=level + 1, header_level=header_level))
                    lines.append(fr"{indent}\end{{tree}}")
        else:
            if level == 0:
                clean_title = clean_text(title, args)
                lines.append(fr"\begin{{frame}}{{{clean_title}}}")
                if child.children:
                    lines.append(r"\begin{tree}")
                    lines.extend(
                        render_latex_beamer_tree(child, args=args, level=level + 1, header_level=header_level))
                    lines.append(r"\end{tree}")
                lines.append(r"\end{frame}")
            else:
                i = IMAGE_RE.match(title)
                if i:
                    file_location = i.group(2)
                    lines.extend([
                        r"\begin{figure}[t]",
                        fr"\includegraphics[width=.75\textwidth]{{{file_location}}}",
                        r"\centering",
                        r"\end{figure}",
                    ])
                    continue

                res = LINK_RE.sub(link_replacer, title)
                if res != title:
                    lines.append(fr'\item {res}')
                    continue

                indent = '  ' * level
                clean_title = clean_text(title, args)
                lines.append(fr"{indent}\item {clean_title}")
                if args.include_notes:
                    if child.note:
                        note = clean_text(child.note, args)
                        lines.append(fr"{indent}\begin{{quote}}")
                        lines.append(fr"{indent}{note}")
                        lines.append(fr"{indent}\end{{quote}}")
                if child.children:
                    lines.append(fr"{indent}\begin{{tree}}")
                    lines.extend(
                        render_latex_beamer_tree(child, args=args, level=level + 1, header_level=header_level))
                    lines.append(fr"{indent}\end{{tree}}")

    return lines
