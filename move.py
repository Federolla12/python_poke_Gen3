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
