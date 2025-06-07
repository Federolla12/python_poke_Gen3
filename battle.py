import random
from typing import Optional

from .pokemon import Pokemon, StatStage
from .move import Move
from .damage import calculate_initial_damage, get_damage_range
from .ability import abilities_map, Ability


class Battle:
    """
    Core Gen 3 battle loop for two Pokémon.
    """
    def __init__(
        self,
        p1: Pokemon,
        p2: Pokemon,
        weather: Optional[str] = None,
    ):
        self.p1 = p1
        self.p2 = p2
        self.weather = weather
        self.weather_turns = 0
        self.turn = 0
        self.log_messages: list[str] = []

        # Instantiate abilities
        cls1 = abilities_map.get(p1.ability, Ability)
        cls2 = abilities_map.get(p2.ability, Ability)
        self.p1.ability = cls1(p1)
        self.p2.ability = cls2(p2)

    def log(self, message: str):
        self.log_messages.append(message)
        print(message)

    def random_chance(self, numerator: int, denominator: int) -> bool:
        return random.randrange(denominator) < numerator

    def get_opponents(self, pokemon: Pokemon) -> list[Pokemon]:
        return [self.p2] if pokemon is self.p1 else [self.p1]

    def start(self):
        """Begin battle: trigger on_start hooks."""
        self.turn = 1
        for ability in (self.p1.ability, self.p2.ability):
            ability.on_start(self)

    def play_turn(self, idx1: int, idx2: int):
        """
        Execute one turn: each side picks a move index.
        """
        # Choose moves and deduct PP
        move1: Move = self.p1.choose_move(idx1)
        move2: Move = self.p2.choose_move(idx2)

        # Determine action order by priority, then speed
        prio1, prio2 = move1.priority, move2.priority
        if prio1 != prio2:
            first, second = (self.p1, move1, self.p2, move2) if prio1 > prio2 else (self.p2, move2, self.p1, move1)
        else:
            sp1 = self.p1.get_modified_stat('spe')
            sp2 = self.p2.get_modified_stat('spe')
            if self.p1.status == 'par':
                sp1 //= 4
            if self.p2.status == 'par':
                sp2 //= 4
            if sp1 > sp2:
                first, second = (self.p1, move1, self.p2, move2)
            else:
                first, second = (self.p2, move2, self.p1, move1)

        # Execute actions in order
        for attacker, move, defender in [(first[0], first[1], first[2]), (second[0], second[1], second[2])]:
            if attacker.is_fainted() or defender.is_fainted():
                continue

            # on_before_move hook
            if not attacker.ability.on_before_move(move, attacker, defender, self):
                continue

            # on_try_hit hook
            try_hit = attacker.ability.on_try_hit(move, defender, attacker, self)
            if try_hit is None:
                continue

            # on_foe_redirect hook
            redirect = defender.ability.on_foe_redirect(move, defender, attacker, self)
            target = redirect if redirect else defender

            # Accuracy check
            acc_stage = attacker.stages['accuracy']
            eva_stage = target.stages['evasion']
            acc_mult = StatStage.multiplier(acc_stage, is_accuracy=True)
            eva_mult = StatStage.multiplier(eva_stage, is_accuracy=True)
            effective_acc = move.accuracy * acc_mult / eva_mult
            if random.uniform(0, 100) > effective_acc:
                self.log(f"{attacker.name}'s {move.name} missed!")
                continue

            # Damage calculation
            atk_stat = attacker.get_modified_stat('atk') if move.category == 'Physical' else attacker.get_modified_stat('spa')
            def_stat = target.get_modified_stat('def') if move.category == 'Physical' else target.get_modified_stat('spd')
            initial = calculate_initial_damage(attacker.level, move.power, atk_stat, def_stat)

            # Build minimal dicts for damage calc
            atk_data = {
                'level': attacker.level,
                'types': attacker.types,
                'status': attacker.status,
                'ability': attacker.ability.name,
                'atk': atk_stat,
                'def': def_stat,
                'spa': attacker.get_modified_stat('spa'),
                'spd': attacker.get_modified_stat('spd')
            }
            def_data = {
                'types': target.types,
                'status': target.status,
                'ability': target.ability.name,
                'atk': attacker.get_modified_stat('atk'),
                'def': target.get_modified_stat('def'),
                'spa': target.get_modified_stat('spa'),
                'spd': def_stat
            }
            move_data = move.__dict__

            low, high = get_damage_range(initial, atk_data, def_data, move_data, is_crit=False, weather=self.weather)
            dmg = random.choice(range(low, high + 1))
            target.apply_damage(dmg)
            self.log(f"{attacker.name} used {move.name} and dealt {dmg} damage to {target.name}!")

            # on_after_damage hooks
            attacker.ability.on_after_damage(move, attacker, target, dmg, self)
            defender.ability.on_after_damage(move, attacker, target, dmg, self)

            if target.is_fainted():
                self.log(f"{target.name} fainted!")

        # End of turn effects
        for ability in (self.p1.ability, self.p2.ability):
            ability.on_end_of_turn(self)

        # Weather duration
        if self.weather_turns > 0:
            self.weather_turns -= 1
            if self.weather_turns == 0:
                self.log(f"The {self.weather} has ended.")
                self.weather = None

        self.turn += 1
