import sys
from pathlib import Path

from battle_env.main import load_team_from_file
from battle_env.battle import Battle


def choose_action(team, label):
    active = team.active()
    print(f"\nTeam {label} active: {active.name} HP {active.current_hp}/{active.stats['hp']}")
    for i, m in enumerate(active.moves, 1):
        print(f"  {i}. {m.name} ({m.current_pp}/{m.max_pp} PP)")
    print("Switch options: prefix with 's'")
    for i, mon in enumerate(team.members, 1):
        if i - 1 == team.active_index:
            continue
        status = 'fainted' if mon.is_fainted() else f"HP {mon.current_hp}/{mon.stats['hp']}"
        print(f"  s{i}: {mon.name} - {status}")
    while True:
        choice = input(f"Action for Team {label}: ").strip().lower()
        if choice.startswith('s'):
            try:
                idx = int(choice[1:]) - 1
                if idx < 0 or idx >= len(team.members):
                    raise ValueError
                if team.members[idx].is_fainted():
                    print("Cannot switch to a fainted Pokémon.")
                    continue
                return {'type': 'switch', 'index': idx}
            except ValueError:
                print("Invalid switch choice.")
        else:
            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(active.moves):
                    raise ValueError
                return {'type': 'move', 'index': idx}
            except ValueError:
                print("Invalid move choice.")


def force_switch(team, opponent_team, battle, label):
    if team.all_fainted():
        return
    while team.active().is_fainted():
        print(f"\nTeam {label}'s active Pokémon fainted. Choose a switch:")
        for i, mon in enumerate(team.members, 1):
            status = 'fainted' if mon.is_fainted() else f"HP {mon.current_hp}/{mon.stats['hp']}"
            print(f"  {i}. {mon.name} - {status}")
        choice = input(f"Switch choice for Team {label}: ").strip()
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(team.members) or team.members[idx].is_fainted():
                raise ValueError
        except ValueError:
            print("Invalid choice.")
            continue
        team.switch(idx)
        team.active().ability.on_switch_in(battle)
        team.active().item.on_switch_in(battle)
        opp_haz = opponent_team.hazards
        if 'spikes' in opp_haz:
            layers = opp_haz['spikes']
            dmg = max(1, team.active().stats['hp'] * layers // 8)
            team.active().apply_damage(dmg)
            print(f"{team.active().name} is hurt by Spikes!")
        break


def main(team1_path, team2_path):
    team1 = load_team_from_file(Path(team1_path))
    team2 = load_team_from_file(Path(team2_path))
    battle = Battle(team1, team2)
    battle.start()
    while not team1.all_fainted() and not team2.all_fainted():
        force_switch(team1, team2, battle, 1)
        force_switch(team2, team1, battle, 2)
        if team1.all_fainted() or team2.all_fainted():
            break
        action1 = choose_action(team1, 1)
        action2 = choose_action(team2, 2)
        battle.play_turn(action1, action2)
    winner = 'Team 1' if not team1.all_fainted() else 'Team 2'
    print("Battle ended, winner:", winner)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python battle_cli.py team1.txt team2.txt')
    else:
        main(sys.argv[1], sys.argv[2])

