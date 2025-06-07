from __future__ import annotations
from pathlib import Path
from copy import deepcopy

from .stats_loader import get_base_stats, get_pokemon_types
from .pokemon import Pokemon
from .moves_loader import load_moves
from .team import Team


def _canon(name: str) -> str:
    """Return identifier style used in data JSON (lowercase no spaces/hyphens)."""
    return name.lower().replace(" ", "").replace("-", "").replace("'", "").replace(".", "")


def parse_showdown(text: str, moves_db: dict[str, Pokemon]|None=None) -> Team:
    """Parse a Showdown-exported team string into a Team."""
    if moves_db is None:
        moves_db = load_moves()
    canon_map = { _canon(name): mv for name, mv in moves_db.items() }
    blocks = [b.strip() for b in text.strip().split('\n\n') if b.strip()]
    team_members = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        header = lines[0]
        name, item = (header.split('@',1)+[None])[:2]
        name = name.strip()
        gender = None
        if name.endswith('(F)') or name.endswith('(M)'):
            gender = name[-2]
            name = name[:-3].strip()
        item = _canon(item) if item else None
        ability = None
        level = 100
        evs = {}
        nature = None
        moves = []
        for line in lines[1:]:
            if line.startswith('Ability:'):
                ability = _canon(line.split(':',1)[1].strip())
            elif line.startswith('Level:'):
                try:
                    level = int(line.split(':',1)[1].strip())
                except ValueError:
                    level = 100
            elif line.startswith('EVs:'):
                parts = line.split(':',1)[1].split('/')
                for part in parts:
                    part = part.strip()
                    if not part:
                        continue
                    amt, stat = part.split(' ',1)
                    key = stat.strip().lower().replace(' ', '')
                    key = {'hp':'hp','atk':'atk','def':'def','spa':'spa','spd':'spd','spe':'spe'}.get(key,key)
                    try:
                        evs[key] = int(amt)
                    except ValueError:
                        pass
            elif line.endswith('Nature'):
                nature = line.split()[0]
            elif line.startswith('-'):
                move_name = line[1:].strip()
                canon = _canon(move_name)
                mv = canon_map.get(canon)
                if mv:
                    moves.append(deepcopy(mv))
        base_stats = get_base_stats(name)
        types = get_pokemon_types(name)
        p = Pokemon(name=name, level=level, types=types, base_stats=base_stats,
                    evs=evs, ability=ability, item=item, moves=moves,
                    gender=gender, nature=nature)
        team_members.append(p)
    return Team(team_members)
