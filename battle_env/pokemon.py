class StatStage:
    """Helper to compute Gen 3 stat and accuracy/evasion multipliers for stages (−6 to +6)."""
    @staticmethod
    def multiplier(stage: int, is_accuracy: bool = False) -> float:
        # For attack/def/spa/spd/spe:
        if not is_accuracy:
            if stage >= 0:
                return (2 + stage) / 2
            else:
                return 2 / (2 - stage)
        # For accuracy/evasion:
        else:
            if stage >= 0:
                return (3 + stage) / 3
            else:
                return 3 / (3 - stage)


class Pokemon:
    """
    Represents a Gen 3 Pokémon with stats, stat stages, status, ability, item, and moveset.
    """
    def __init__(
        self,
        name: str,
        level: int,
        types: list[str],
        base_stats: dict,
        ivs: dict[str, int] = None,
        evs: dict[str, int] = None,
        ability: str = None,
        item: str = None,
        moves: list = None,
        gender: str | None = None,
    ):
        self.name = name
        self.level = level
        self.types = types
        self.base_stats = base_stats
        self.ivs = ivs or {stat: 31 for stat in base_stats}
        self.evs = evs or {stat: 0 for stat in base_stats}
        self.ability = ability
        self.item = item
        self.gender = gender

        # Calculate actual stats
        self.stats = self._calc_actual_stats()
        self.current_hp = self.stats['hp']

        # Stat stages: -6 to +6 for atk, def, spa, spd, spe, accuracy, evasion
        self.stages: dict[str, int] = {stat: 0 for stat in [
            'atk', 'def', 'spa', 'spd', 'spe', 'accuracy', 'evasion'
        ]}

        # Status condition: None or one of 'brn', 'par', 'psn', 'tox', 'slp', 'frz'
        self.status: str | None = None
        self.toxic_counter: int = 0
        self.sleep_counter: int = 0

        # Moveset: list of Move objects
        self.moves = moves or []

        # Volatile conditions such as "attract" or "substitute"
        self.volatiles: dict[str, dict] = {}

    def _calc_actual_stats(self) -> dict[str, int]:
        """Calculate actual HP, atk, def, spa, spd, spe using Gen 3 formulas."""
        stats: dict[str, int] = {}
        for stat, base in self.base_stats.items():
            iv = self.ivs.get(stat, 0)
            ev = self.evs.get(stat, 0)
            if stat == 'hp':
                stats['hp'] = ((2 * base + iv + ev // 4) * self.level) // 100 + self.level + 10
            else:
                stats[stat] = ((2 * base + iv + ev // 4) * self.level) // 100 + 5
        return stats

    def get_modified_stat(self, stat: str) -> int:
        """Return a stat value after applying its stage multiplier."""
        base_value = self.stats[stat]
        stage = self.stages.get(stat, 0)
        is_acc_eva = stat in ['accuracy', 'evasion']
        return int(base_value * StatStage.multiplier(stage, is_acc_eva))

    def apply_damage(self, amount: int) -> int:
        """Subtract HP by amount (min 0) and return new HP."""
        self.current_hp = max(0, self.current_hp - amount)
        return self.current_hp

    def is_fainted(self) -> bool:
        """Check if the Pokémon has fainted."""
        return self.current_hp == 0

    def set_status(self, status: str):
        """Set a status condition if none is currently applied."""
        if self.status:
            raise ValueError(f"{self.name} already has status {self.status}.")
        self.status = status
        if status == 'tox':
            self.toxic_counter = 1
        if status == 'slp':
            self.sleep_counter = 2

    def heal_status(self):
        """Clear any status condition."""
        self.status = None
        self.toxic_counter = 0
        self.sleep_counter = 0

    def change_stage(self, stat: str, delta: int):
        """Modify a stat stage by delta, clamped between -6 and +6."""
        new_stage = max(-6, min(6, self.stages.get(stat, 0) + delta))
        self.stages[stat] = new_stage

    def choose_move(self, index: int):
        """Select a move by index and decrement its PP."""
        if not self.moves:
            from .moves_loader import load_moves
            struggle = load_moves().get("struggle")
            return struggle
        if index < 0 or index >= len(self.moves):
            raise IndexError("Invalid move index.")
        move = self.moves[index]
        try:
            move.use_pp()
        except ValueError:
            pass
        return move

    # --- Volatile Conditions Helpers ---
    def add_volatile(self, name: str, source=None, duration: int | None = None):
        """Add a volatile condition with optional duration."""
        self.volatiles[name] = {
            "source": source,
            "duration": duration,
        }

    def remove_volatile(self, name: str):
        self.volatiles.pop(name, None)

    # --- Misc Helpers ---
    def heal(self, amount: int):
        self.current_hp = min(self.stats['hp'], self.current_hp + amount)
        return self.current_hp

    def try_set_status(self, status: str, source=None) -> bool:
        if self.status:
            return False
        self.set_status(status)
        return True

    def remove_item(self):
        from .item import Item
        self.item = Item(self)
