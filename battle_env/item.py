from __future__ import annotations
import json
import random
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
    name: str = "(none)"
    metadata: dict = {}

    def __init__(self, owner: 'Pokemon'):
        self.owner = owner
        self.name = self.metadata.get('name', self.name)

    # Hooks similar to abilities
    def on_start(self, battle: 'Battle'):
        boosts = self.metadata.get('boost_stats')
        allowed = self.metadata.get('species_only')
        if boosts and (allowed is None or self.owner.name == allowed):
            for stat, mult in boosts.items():
                self.owner.stats[stat] = int(self.owner.stats[stat] * mult)

    def on_switch_in(self, battle: 'Battle'):
        self.on_start(battle)

    def on_before_move(self, move, attacker: 'Pokemon', defender: 'Pokemon', battle: 'Battle') -> bool:
        return True

    def on_after_damage(self, move, attacker: 'Pokemon', defender: 'Pokemon', damage: int, battle: 'Battle'):
        chance = self.metadata.get('flinch_chance')
        if chance and attacker is self.owner and damage > 0:
            if random.random() < chance:
                defender.add_volatile('flinch', self.owner, duration=1)
                battle.log(f"{defender.name} flinched due to {self.name}!")

    def on_end_of_turn(self, battle: 'Battle'):
        threshold = self.metadata.get('heal_threshold')
        if threshold is not None:
            if self.owner.current_hp <= self.owner.stats['hp'] * threshold:
                amount = self.metadata.get('heal_amount')
                if amount is None:
                    fraction = self.metadata.get('heal_fraction')
                    if fraction:
                        amount = self.owner.stats['hp'] // fraction
                if amount:
                    self.owner.heal(amount)
                    battle.log(f"{self.owner.name} restored HP with {self.name}!")
                    if self.metadata.get('consume'):
                        self.owner.remove_item()

    def get_priority_bonus(self, move, battle: 'Battle') -> float:
        """Return a fractional priority bonus for this turn."""
        chance = self.metadata.get('quickclaw_chance')
        if chance and random.random() < chance:
            return 0.1
        return 0.0

    def modify_damage(self, move, attacker: 'Pokemon', defender: 'Pokemon', damage: int, battle: 'Battle') -> int:
        """Modify damage if this item boosts certain move types."""
        boost_type = self.metadata.get('boost_type')
        if boost_type and attacker is self.owner and move.type == boost_type:
            mult = self.metadata.get('boost_multiplier', 1.0)
            return int(damage * mult)
        return damage


items_map = load_items()
