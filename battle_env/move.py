import json
from pathlib import Path


class Move:
    """
    Represents a Pokémon move in Gen 3 battle simulation, with PP management.
    """

    def __init__(
        self,
        name: str,
        move_type: str,
        power: int,
        category: str,
        accuracy: int,
        priority: int = 0,
        max_pp: int = 1,
    ):
        self.name = name
        self.type = move_type
        self.power = power
        self.category = category  # 'Physical' or 'Special'
        self.accuracy = accuracy  # Base accuracy percentage (e.g., 100)
        self.priority = priority
        self.max_pp = max_pp
        self.current_pp = max_pp
        self.metadata: dict = {}
        self.id: str | None = None
        self.flags: dict | None = None

    def use_pp(self):
        """Consume 1 PP; raise if no PP remains."""
        if self.current_pp <= 0:
            raise ValueError(f"No PP left for move {self.name}.")
        self.current_pp -= 1

    def __repr__(self):
        return (
            f"<Move {self.name}: {self.type} {self.category}, Power={self.power}, "
            f"Acc={self.accuracy}%, PP={self.current_pp}/{self.max_pp}, Pri={self.priority}>"
        )


def load_moves(json_path: Path | str = None) -> dict[str, "Move"]:
    """Load move metadata from JSON into Move objects."""
    if json_path is None:
        json_path = Path(__file__).parent.parent / "data" / "moves.json"
    data = json.loads(Path(json_path).read_text())
    registry: dict[str, Move] = {}
    for name, meta in data.items():
        mv = Move(
            name=meta.get("name", name),
            move_type=meta.get("type", "Normal"),
            power=meta.get("basePower", 0) or 0,
            category=meta.get("category", "Physical"),
            accuracy=meta.get("accuracy", 100),
            priority=meta.get("priority", 0),
            max_pp=meta.get("pp", 1),
        )
        mv.metadata = meta
        mv.id = meta.get("id", name)
        mv.flags = meta.get("flags", {})
        registry[name] = mv
    return registry
