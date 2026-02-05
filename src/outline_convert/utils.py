# from openai import OpenAI
import time
import os
import argparse
from math import gcd
from typing import List, Optional


from .models import Node, TextSegment
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

def compute_level(line: str, indent_size: int) -> int:
    leading = line.expandtabs(indent_size)
    space_count = len(leading) - len(leading.lstrip(' '))
    extra = indent_size if leading.lstrip().startswith('-') else 0
    level = (space_count + extra) // indent_size
    return level

# -- TREE UTILITIES ---------------------------------------------------------

def find_node(forest: List[Node], prefix: str) -> List[Node]:
    for tree in forest:
        result = find_node_tree(tree, prefix)
        if result is not None:
            return [result]
    return []

def find_node_tree(node: Node, prefix: str) -> Optional[Node]:
    if node.title.startswith(prefix):
        return node
    for child in node.children:
        result = find_node_tree(child, prefix)
        if result is not None:
            return result
    return None
#find all the nodes with this substring
def find_sub_string(node: Node, substring: str) -> List[Node]:
    res = []
    if substring in node.title:
        res.append(node)
    for child in node.children:
        res.extend(find_sub_string(child, substring))
    return res

#returns the path to the node including its subtree
def get_path(node: Node) -> List[Node]:
    res = []
    if node:
        current = node
        while node.parent is not None:
            #here is the line that keeps the subTree
            #use current = node.title if we only want to keep the title
            parent = Node(node.parent.title)
            parent.children.append(current)
            current = parent
            node = node.parent
        res.append(current)
    return res


def copy_subtree(node: Node) -> Node:
    new_node = Node(node.title)
    for child in node.children:
        copied_child = copy_subtree(child)
        copied_child.parent = new_node
        new_node.children.append(copied_child)
    return new_node

def filter_tree(node: Node, substring: str) -> Optional[Node]:
    if substring in node.title:
        return copy_subtree(node)

    kept_children: List[Node] = []
    for child in node.children:
        filtered_child = filter_tree(child, substring)
        if filtered_child:
            #filtered_child.parent = None
            kept_children.append(filtered_child)

    if kept_children:
        new_node = Node(node.title)
        for c in kept_children:
            c.parent = new_node
            new_node.children.append(c)
        return new_node

    return None

def filter(forest: List[Node], substring: str) -> List[Node]:
    result: List[Node] = []
    for tree in forest:
        filtered = filter_tree(tree, substring)
        if filtered:
            result.append(filtered)
    return result


def parse_opml_children(elem: ET.Element, parent: Node):
    for child_elem in elem.findall('outline'):
        title = child_elem.get('text', '')
        node = Node(title)
        note = child_elem.get('_note')
        if note:
            node.note = note

        parent.children.append(node)
        node.parent = parent
        parse_opml_children(child_elem, node)
    
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


def escape_latex(text: str) -> str:
    return text.replace('\\', r'\textbackslash{}') \
        .replace('&', r'\&') \
        .replace('%', r'\%') \
        .replace('$', r'\$') \
        .replace('#', r'\#') \
        .replace('_', r'\_') \
        .replace('{', r'\{') \
        .replace('}', r'\}') \
        .replace('~', r'\textasciitilde{}') \
        .replace('^', r'\textasciicircum{}')

def convert_markdown_to_latex(s: str) -> str:
    s = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', s, flags=re.DOTALL) # markdown: **bold text**
    s = re.sub(r'\*(.*?)\*', r'\\textit{\1}', s, flags=re.DOTALL) # markdown: *italic text*
    s = re.sub(r'__(.*?)__', r'\\textit{\1}', s, flags=re.DOTALL) # markdown: __italic text__

    return s

def split_segments(segments: List[TextSegment], pattern: re.Pattern, new_type: str) -> List[TextSegment]:
    res: List[TextSegment] = []
    for segment in segments:
        if segment.type != 'plain':
            res.append(segment)
            continue

        parts = pattern.split(segment.text)
        for part in parts:
            if pattern.fullmatch(part):
                res.append(TextSegment(part, new_type))
            else:
                res.append(TextSegment(part, 'plain'))
    return res


def parse_item_text(title: str, args: argparse.Namespace) -> str:
    s = re.sub(r'\$\$(.*?)\$\$', r'$\1$', title, flags=re.DOTALL)
    # List of new types and RegExp
    patterns = [
        ('math', re.compile(r'(\$.*?\$)', flags=re.DOTALL)),
        ('citation', re.compile(r'(\\cite{.*?})', flags=re.DOTALL)),
        ('md_bold', re.compile(r'(\*\*.*?\*\*)', flags=re.DOTALL)),
        ('md_italic1', re.compile(r'(\*.*?\*)', flags=re.DOTALL)),
        ('md_italic2', re.compile(r'(__.*?__)', flags=re.DOTALL)),
    ]

    segments = [TextSegment(s, 'plain')]

    # Step 1: Splitting between laTeX and non LaTeX
    for (type, pattern) in patterns:
        segments = split_segments(segments, pattern, type)

    # Step 2: Markdown parsing
    if args.parse_markdown:
        for segment in segments:
            if segment.type.startswith('md_'):
                segment.text = convert_markdown_to_latex(segment.text)
                segment.type = 'markdown_parsed' # flag that there is no need to escape the converted markdown

    # Step 3: Flatten plain segments to words and remove #tags
    flattened: List[TextSegment] = []
    for seg in segments:
        if seg.type == 'plain':
            for word in seg.text.split():
                if args.strip_tags and word.startswith('#'):
                    continue
                flattened.append(TextSegment(word, 'plain'))
        else:
            flattened.append(seg)
    segments = flattened

    # Step 4: Non LaTeX escaping
    if args.format in ['latex', 'beamer']:
        for segment in segments:
            if segment.type == 'plain':
                segment.text = escape_latex(segment.text)

    # Step 5: Join back with spaces 
    return ' '.join(segment.text for segment in segments)


def link_replacer(match):
    text, url = match.group(1), match.group(2)
    return fr"\href{{{url}}}{{{escape_latex(text)}}}"

def node_to_outline_elem(node: Node, args: argparse.Namespace) -> ET.Element:
    """Convert a single node to an outline element (no children processing)"""
    elem = ET.Element('outline')
    title = node.title
    if args.strip_tags:
        title = ' '.join(part for part in title.split() if not part.startswith('#'))
    elem.set('text', title)
    if args.include_notes and node.note:
        elem.set('_note', node.note)
    return elem

IGNORE_OUTLINE_TAGS = {"#wfe-ignore-outline", "#ignore-outline"}
IGNORE_ITEM_TAGS = {"#wfe-ignore-item", "#ignore-item", "#hh"}


'''
I could be wrong, but the purpose of ignore_tree seems to be to process a tree in such a way that
any node not to be translated gets removed from the tree.
I suppose that's why it's called ignore_tree.
You could also think of it as pruning.
'''
def ignore_tree(node: Node, args: argparse.Namespace):
    is_complete = node.title.startswith('[COMPLETE]')
    has_children = bool(node.children)
    children_copy = list(node.children) if has_children else []
    ignore_item = (args.hide_completed and is_complete) or \
        (args.completed_only and not is_complete) or \
        (args.expert_mode and any(tag in node.title for tag in IGNORE_ITEM_TAGS))

    # if this line to be ignored, then just process the children and return
    if ignore_item:
        if node.parent:
            parent = node.parent
            index = parent.children.index(node)
            parent.children[index:index + 1] = children_copy
            if has_children:
                for child in node.children:
                    child.parent = parent
            for child in children_copy:
                ignore_tree(child, args)
            return

    # if this whole subtree to be ignored then remove it and return
    if args.expert_mode and any(tag in node.title for tag in IGNORE_OUTLINE_TAGS):
        if node.parent:
            node.parent.children.remove(node)
            return

    # recurse
    if has_children:
        for child in children_copy:
            ignore_tree(child, args)

'''
ignore_forest is called once per separate tree, where the source contains more than one tree.  The 
collection of trees is not the same as children of a node: it refers to output from editors such as 
Dynalist, which uses documents rather than large subtrees.  
(So for example, a collection of documents corresponds to a forest.)
'''
def ignore_forest(forest: List[Node], args: argparse.Namespace) -> List[Node]:
    result = []
    for node in forest:
        is_complete = node.title.startswith('[COMPLETE]')
        ignore_item = (args.hide_completed and is_complete) or \
                      (args.completed_only and not is_complete) or \
                      (args.expert_mode and any(tag in node.title for tag in IGNORE_ITEM_TAGS))

        if ignore_item:
            result.extend(node.children if node.children else [])
            continue

        if args.expert_mode and any(tag in node.title for tag in IGNORE_OUTLINE_TAGS):
            continue

        # issue #65: deal with style to suppress item in beamer (more expected to come)
        # note, this only applies to the very top of a document tree -- 
        #   style setting for all sub-nodes is done else where: in preprocess_tree for now
        if args.expert_mode and any(tag in node.title for tag in ['#style:normal']):
            node.style = "normal"

        result.append(node)

    for tree in result:
        ignore_tree(tree, args)

    return result


def link_parent(parent: Node):
    for child in parent.children:
        child.parent = parent
        link_parent(child)

def print_forest(forest: List[Node]):
    for tree in forest:
        print_tree(tree)
        print("#################################################")

def print_tree(node: Node, level: int = 0):
    if node.parent:
        print('  ' * level,"title:",node.title,"|","note:", node.note, "|", "parent:", node.parent.title, "|", "children:", print_children(node))
    else:
        print('  ' * level,"title:",node.title,"|","note:", node.note, "|", "children:", print_children(node))
    for child in node.children:
        print_tree(child, level + 1)

def print_children(node:Node) -> str:
    res = ""
    for child in node.children:
        res += f"{child.title}/"
    return res
    
    
    


# Issue 65 (enhancement): set styles to normal when required
'''
Walk the tree specified by node iteratively, doing preprocessing as needed.
One day this might include the 'ignore' stuff.
'''
def preprocess_tree(node: Node, args: argparse.Namespace):
    nodeStack = [node]

    while nodeStack:
        currentNode = nodeStack.pop()
        
        if args.expert_mode and any(tag in currentNode.title for tag in ['#style:normal']):
            currentNode.style = "normal"

        for child in reversed(currentNode.children):
            nodeStack.append(child)
    
    return

# Issue 65 (enhancement): allow set style in trees to normal when required
'''
Preprocess all the trees in the forest
'''
def preprocess_forest(forest: List[Node], args: argparse.Namespace):
    retval = []
    for oneTree in forest:
        preprocess_tree(oneTree, args)
        retval.append(oneTree)

    return retval


