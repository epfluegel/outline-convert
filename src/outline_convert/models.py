from typing import List, Optional
from dataclasses import dataclass


class Node:
    def __init__(self, title: str):
        self.title: str = title
        self.children: List[Node] = []
        self.parent: Optional[Node] = None
        self.note: Optional[str] = None
        self.style: str = 'item' # moomin 


@dataclass
class TextSegment:
    text: str
    type: str # 'plain', 'markdown', 'latex', etc.