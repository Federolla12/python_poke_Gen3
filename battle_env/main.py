from __future__ import annotations
import sys
from pathlib import Path
from .team_builder import parse_showdown
from .moves_loader import load_moves
from .team import Team
from .battle import Battle


def load_team_from_file(path: Path) -> Team:
    text = Path(path).read_text()
    moves_db = load_moves()
    return parse_showdown(text, moves_db)


def main(team1_path: str, team2_path: str):
    team1 = load_team_from_file(Path(team1_path))
    team2 = load_team_from_file(Path(team2_path))
    battle = Battle(team1, team2)
    battle.start()
    while not team1.all_fainted() and not team2.all_fainted():
        # very naive CLI
        action1 = {'type': 'move', 'index': 0}
        action2 = {'type': 'move', 'index': 0}
        battle.play_turn(action1, action2)
    winner = 'Team 1' if not team1.all_fainted() else 'Team 2'
    print('Battle ended, winner:', winner)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python -m battle_env.main team1.txt team2.txt')
    else:
        main(sys.argv[1], sys.argv[2])
