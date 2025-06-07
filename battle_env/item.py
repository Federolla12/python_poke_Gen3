from __future__ import annotations
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pokemon import Pokemon
    from .battle import Battle


def load_items(path: str | Path | None = None) -> dict[str, type]:
    if path is None:
        path = Path(__file__).parent.parent / 'data' / 'items.json'
    data = json.loads(Path(path).read_text())
    registry: dict[str, type] = {}
    for name, meta in data.items():
        cls = type(name, (Item,), {})
        cls.name = name
        cls.metadata = meta
        registry[name] = cls
    return registry


class Item:
    name: str
    metadata: dict

    def __init__(self, owner: 'Pokemon'):
        self.owner = owner
        self.name = self.metadata.get('name', self.name)

    # Hooks similar to abilities
    def on_start(self, battle: 'Battle'):
        pass

    def on_switch_in(self, battle: 'Battle'):
        pass

    def on_before_move(self, move, attacker: 'Pokemon', defender: 'Pokemon', battle: 'Battle') -> bool:
        return True

    def on_after_damage(self, move, attacker: 'Pokemon', defender: 'Pokemon', damage: int, battle: 'Battle'):
        pass

    def on_end_of_turn(self, battle: 'Battle'):
        pass


items_map = load_items()
