from typing import List, Optional
from dataclasses import dataclass


class Node:
    # default style is 'itemised' for LaTeX -- issue 65 (enhancement)
    _DEFAULT_STYLE = "itemised"

    def __init__(self, title: str):
        self.title: str = title
        self.children: List[Node] = []
        self.parent: Optional[Node] = None
        self.note: Optional[str] = None
        # self.style: str = 'itemised' # default style is 'itemised' for LaTeX 
        self.style: str = Node._DEFAULT_STYLE 

    def set_title(self, newTitle = ""):
        self.title = newTitle

    def set_style(self, newStyle = ""):
        if newStyle:
            self.style = newStyle
        else:
            self.style = Node._DEFAULT_STYLE

    def hasChildren(self) -> bool:
        if (self.children):
            return True
        else:
            return False

    '''
    For debug only: dump tree with root == self to a big string (with \n chars)
    (doesn't care about indenting)
    '''
    def dumpToString(self) -> str:
        newLine = "\n"
        retval = ""
        continuationLine = False
        nodeStack = [self]

        while nodeStack:
            currentNode = nodeStack.pop()
            theLine = fr"title={currentNode.title}, style={currentNode.style}"
            if continuationLine:
                retval += newLine
            else:
                continuationLine = True
            retval += theLine

            for child in reversed(currentNode.children):
                nodeStack.append(child)        

        return retval


@dataclass
class TextSegment:
    text: str
    type: str # 'plain', 'markdown', 'latex', etc.