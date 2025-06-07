import random
from typing import Optional

from .pokemon import Pokemon, StatStage
from .move import Move
from .team import Team
from .damage import calculate_initial_damage, get_damage_range
from .ability import abilities_map, Ability
from .item import items_map, Item


class Battle:
    """
    Core Gen 3 battle loop for two Pokémon.
    """
    def __init__(
        self,
        team1: Team,
        team2: Team,
        weather: Optional[str] = None,
    ):
        self.team1 = team1
        self.team2 = team2
        self.p1 = team1.active()
        self.p2 = team2.active()
        self.weather = weather
        self.weather_turns = 0
        self.turn = 0
        self.log_messages: list[str] = []

        # Instantiate abilities
        cls1 = abilities_map.get(self.p1.ability, Ability)
        cls2 = abilities_map.get(self.p2.ability, Ability)
        self.p1.ability = cls1(self.p1)
        self.p2.ability = cls2(self.p2)
        # Instantiate held items
        itm1 = items_map.get(self.p1.item, Item)
        itm2 = items_map.get(self.p2.item, Item)
        self.p1.item = itm1(self.p1)
        self.p2.item = itm2(self.p2)

    def update_actives(self):
        """Refresh references to the teams' active Pokémon."""
        self.p1 = self.team1.active()
        self.p2 = self.team2.active()

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
        for item in (self.p1.item, self.p2.item):
            item.on_start(self)

    def play_turn(self, action1: dict, action2: dict):
        """Execute one turn given two player actions."""
        self.update_actives()
        # decrement volatile durations
        for mon in (self.p1, self.p2):
            for v in list(mon.volatiles.keys()):
                data = mon.volatiles[v]
                if data.get('duration') is not None:
                    data['duration'] -= 1
                    if data['duration'] <= 0:
                        mon.remove_volatile(v)
        if action1.get('type') == 'switch':
            self.team1.switch(action1['index'])
            self.team1.active().ability.on_switch_in(self)
            self.team1.active().item.on_switch_in(self)
            opp_haz = self.team1.hazards
            if 'spikes' in opp_haz:
                layers = opp_haz['spikes']
                dmg = max(1, self.team1.active().stats['hp'] * layers // 8)
                self.team1.active().apply_damage(dmg)
                self.log(f"{self.team1.active().name} is hurt by Spikes!")
        else:
            move1: Move = self.p1.choose_move(action1['index'])

        if action2.get('type') == 'switch':
            self.team2.switch(action2['index'])
            self.team2.active().ability.on_switch_in(self)
            self.team2.active().item.on_switch_in(self)
            opp_haz = self.team2.hazards
            if 'spikes' in opp_haz:
                layers = opp_haz['spikes']
                dmg = max(1, self.team2.active().stats['hp'] * layers // 8)
                self.team2.active().apply_damage(dmg)
                self.log(f"{self.team2.active().name} is hurt by Spikes!")
        else:
            move2: Move = self.p2.choose_move(action2['index'])

        # refresh after potential switching
        self.update_actives()
        if action1.get('type') == 'switch' or action2.get('type') == 'switch':
            self.log('A switch occurred.')
            return

        move1 = self.p1.moves[action1['index']]
        move2 = self.p2.moves[action2['index']]

        # Determine action order by priority (with item bonuses), then speed
        prio1 = move1.priority + self.p1.item.get_priority_bonus(move1, self)
        prio2 = move2.priority + self.p2.item.get_priority_bonus(move2, self)
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

            if attacker.volatiles.get('flinch'):
                attacker.remove_volatile('flinch')
                self.log(f"{attacker.name} flinched and couldn't move!")
                continue

            # on_before_move hook
            if not attacker.ability.on_before_move(move, attacker, defender, self):
                continue
            if not attacker.item.on_before_move(move, attacker, defender, self):
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
            dmg = attacker.item.modify_damage(move, attacker, target, dmg, self)
            dmg = defender.item.modify_damage(move, attacker, target, dmg, self)
            # Screens reduce damage
            def_team = self.team1 if defender is self.team1.active() else self.team2
            if def_team.screens.get('reflect') and move.category == 'Physical':
                dmg //= 2
            if def_team.screens.get('lightscreen') and move.category == 'Special':
                dmg //= 2
            target.apply_damage(dmg)
            self.log(f"{attacker.name} used {move.name} and dealt {dmg} damage to {target.name}!")

            # on_after_damage hooks
            attacker.ability.on_after_damage(move, attacker, target, dmg, self)
            defender.ability.on_after_damage(move, attacker, target, dmg, self)
            attacker.item.on_after_damage(move, attacker, target, dmg, self)
            defender.item.on_after_damage(move, attacker, target, dmg, self)

            if target.is_fainted():
                self.log(f"{target.name} fainted!")

        # End of turn effects
        for ability in (self.p1.ability, self.p2.ability):
            ability.on_end_of_turn(self)
        for item in (self.p1.item, self.p2.item):
            item.on_end_of_turn(self)

        # Status residual damage
        for mon in (self.p1, self.p2):
            if mon.status == 'brn':
                dmg = max(1, mon.stats['hp'] // 16)
                mon.apply_damage(dmg)
                self.log(f"{mon.name} is hurt by its burn!")
            elif mon.status == 'psn':
                dmg = max(1, mon.stats['hp'] // 8)
                mon.apply_damage(dmg)
                self.log(f"{mon.name} is hurt by poison!")
            elif mon.status == 'tox':
                mon.toxic_counter += 1
                dmg = max(1, mon.stats['hp'] * mon.toxic_counter // 16)
                mon.apply_damage(dmg)
                self.log(f"{mon.name} is hurt by toxic poison!")
            elif mon.status == 'slp':
                if mon.sleep_counter > 0:
                    mon.sleep_counter -= 1
                if mon.sleep_counter == 0:
                    mon.heal_status()
                    self.log(f"{mon.name} woke up!")
            elif mon.status == 'frz':
                if random.random() < 0.2:
                    mon.heal_status()
                    self.log(f"{mon.name} thawed out!")

        # Weather duration
        if self.weather_turns > 0:
            self.weather_turns -= 1
            if self.weather_turns == 0:
                self.log(f"The {self.weather} has ended.")
                self.weather = None

        self.turn += 1
