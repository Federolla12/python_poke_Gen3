from __future__ import annotations
from pathlib import Path
from .stats_loader import get_base_stats
from .pokemon import Pokemon
from .moves_loader import load_moves
from .team import Team


def parse_showdown(text: str, moves_db: dict[str, Pokemon]|None=None) -> Team:
    """Parse a Showdown-exported team string into a Team."""
    if moves_db is None:
        moves_db = load_moves()
    blocks = [b.strip() for b in text.strip().split('\n\n') if b.strip()]
    team_members = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        header = lines[0]
        name, item = (header.split('@',1)+[None])[:2]
        name = name.strip()
        item = item.strip() if item else None
        ability = None
        moves = []
        for line in lines[1:]:
            if line.startswith('Ability:'):
                ability = line.split(':',1)[1].strip()
            elif line.startswith('-'):
                move_name = line[1:].strip().lower()
                if move_name in moves_db:
                    moves.append(moves_db[move_name])
        base_stats = get_base_stats(name)
        p = Pokemon(name=name, level=100, types=['Normal'], base_stats=base_stats,
                    ability=ability, item=item, moves=moves)
        team_members.append(p)
    return Team(team_members)
