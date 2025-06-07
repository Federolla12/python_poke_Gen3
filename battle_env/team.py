from __future__ import annotations
from dataclasses import dataclass
from typing import List
from .pokemon import Pokemon

@dataclass
class Team:
    members: List[Pokemon]
    active_index: int = 0
    hazards: dict[str, int] = None
    screens: dict[str, int] = None

    def active(self) -> Pokemon:
        return self.members[self.active_index]

    def __post_init__(self):
        if self.hazards is None:
            self.hazards = {}
        if self.screens is None:
            self.screens = {}

    def all_fainted(self) -> bool:
        return all(p.is_fainted() for p in self.members)

    def switch(self, index: int):
        if index < 0 or index >= len(self.members):
            raise IndexError('Invalid switch index')
        if self.members[index].is_fainted():
            raise ValueError('Cannot switch to a fainted Pokémon')
        self.active_index = index

    def clear_hazards(self):
        self.hazards.clear()
