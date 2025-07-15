from typing import List, Optional


class Node:
    def __init__(self, title: str):
        self.title: str = title
        self.children: List[Node] = []
        self.parent: Optional[Node] = None
        self.note: Optional[str] = None