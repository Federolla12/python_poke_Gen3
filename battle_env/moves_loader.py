from __future__ import annotations
import json
from pathlib import Path
from .move import Move


def load_moves(path: str | Path | None = None) -> dict[str, Move]:
    """Load moves from JSON file and instantiate Move objects."""
    if path is None:
        path = Path(__file__).parent.parent / 'data' / 'moves.json'
    data = json.loads(Path(path).read_text())
    moves: dict[str, Move] = {}
    for ident, meta in data.items():
        mv = Move(
            name=meta.get('name', ident),
            move_type=meta.get('type', 'Normal'),
            power=meta.get('basePower', 0) or 0,
            category=meta.get('category', 'Physical'),
            accuracy=meta.get('accuracy', 100),
            priority=meta.get('priority', 0),
            max_pp=meta.get('pp', 1)
        )
        mv.id = meta.get('id', ident)
        mv.flags = meta.get('flags', {})
        mv.metadata = meta
        moves[mv.name.lower()] = mv
    return moves
