from typing import List, Optional


class Node:
    def __init__(self, title: str):
        self.title: str = title
        self.children: List[Node] = []
        self.note: Optional[str] = None