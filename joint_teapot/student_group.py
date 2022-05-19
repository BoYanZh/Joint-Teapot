from dataclasses import dataclass
from typing import List


@dataclass
class StudentGroup:
    name: str
    members: List[str]

    def __init__(self, name: str, members: List[str]):
        self.name = name
        self.members = members
