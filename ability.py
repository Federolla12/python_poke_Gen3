import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from battle_env.pokemon import Pokemon  # noqa: F401
    from battle_env.battle import Battle  # noqa: F401


def load_abilities(json_path: Path | str = None) -> dict[str, type]:
    """Load abilities metadata from JSON and build subclasses dynamically."""
    if json_path is None:
        # Default to the abilities.json file located alongside this module
        json_path = Path(__file__).with_name('abilities.json')
    data = json.loads(Path(json_path).read_text())
    registry: dict[str, type] = {}
    for name, meta in data.items():
        cls = type(name, (Ability,), {})
        cls.name = name
        cls.metadata = meta
        registry[name] = cls
    return registry


class Ability:
    """
    Generic Gen 3 Ability loaded from metadata.
    Hooks: on_start, on_switch_in, on_before_move, on_try_hit,
           on_foe_redirect, on_foe_trap_pokemon, on_after_damage,
           on_end_of_turn
    """
    name: str
    metadata: dict

    def __init__(self, owner: 'Pokemon'):
        self.owner = owner
        self.name = self.metadata.get('name', self.name)

    def on_start(self, battle: 'Battle'):
        data = self.metadata.get('on_start', {})
        # pressure silent announce
        if data.get('silent'):
            battle.log(f"[silent] {self.owner.name}'s {self.name} activated silently.")
        # trap all foes (Shadow Tag)
        if data.get('trap_all_foes'):
            foes = battle.get_opponents(self.owner)
            for foe in foes:
                foe.trapped = True
            battle.log(f"{self.owner.name}'s {self.name} traps all foes!")
        # init truant turn
        if data.get('init_truant_turn'):
            self.owner.truantTurn = False

    def on_switch_in(self, battle: 'Battle'):
        data = self.metadata.get('on_switch_in', {})
        # weather changes
        weather = data.get('weather')
        if weather:
            battle.weather = weather
            battle.weather_turns = data.get('weather_turns', 5)
            battle.log(f"{self.owner.name} sets {weather} thanks to {self.name}!")
        # attack drop
        atk_drop = data.get('atk_drop')
        if atk_drop:
            foes = battle.get_opponents(self.owner)
            valid = False
            # Intimidate: ignore if all behind substitute
            if data.get('ignore_if_all_foes_have_substitute'):
                for foe in foes:
                    if not foe.volatiles.get('substitute'):
                        valid = True
                        break
            else:
                valid = True
            if valid:
                for foe in foes:
                    foe.change_stage('atk', -atk_drop)
                battle.log(f"{self.owner.name}'s {self.name} lowers opponents' Attack!")

    def on_before_move(self, move, attacker: 'Pokemon', defender: 'Pokemon', battle: 'Battle') -> bool:
        data = self.metadata.get('on_before_move', {})
        # type immunity (Levitate)
        immune = data.get('immune_type')
        if immune and defender is self.owner and move.type == immune:
            battle.log(f"{self.owner.name} is immune to {move.type}-type moves thanks to {self.name}!")
            return False
        # hustle accuracy
        if data.get('accuracy_multiplier') and attacker is self.owner:
            if move.type in data.get('physical_types', []):
                num, den = data['accuracy_multiplier'].values()
                move.accuracy = move.accuracy * num // den
        return True

    def on_try_hit(self, move, target: 'Pokemon', source: 'Pokemon', battle: 'Battle'):
        data = self.metadata.get('on_try_hit', {})
        mt = data.get('move_type')
        if mt and move.type == mt:
            excludes = data.get('exclude_moves', [])
            if move.id in excludes:
                return True
            # flash fire or volt absorb
            if data.get('add_volatile'):
                target.add_volatile(data['add_volatile'], source)
                battle.log(f"{target.name} absorbs {move.type} with {self.name}!")
                return None
        return True

    def on_foe_redirect(self, move, target: 'Pokemon', source: 'Pokemon', battle: 'Battle'):
        data = self.metadata.get('on_foe_redirect', {})
        mt = data.get('move_type')
        if mt and move.type == mt and target is not source:
            # redirect to self.owner
            return self.owner
        return None

    def on_foe_trap_pokemon(self, pokemon: 'Pokemon', battle: 'Battle'):
        data = self.metadata.get('on_foe_trap_pokemon', {})
        if data.get('trap_all_foes') and pokemon is not self.owner:
            pokemon.trapped = True
            battle.log(f"{pokemon.name} is trapped by {self.owner.name}'s {self.name}!")

    def on_after_damage(self, move, attacker: 'Pokemon', defender: 'Pokemon', damage: int, battle: 'Battle'):
        data = self.metadata.get('on_after_damage', {})
        if data.get('makes_contact') and defender is self.owner and damage > 0:
            # chance-based volatile or status
            chance = data.get('chance')
            if chance:
                if battle.random_chance(chance['numerator'], chance['denominator']):
                    if data.get('add_volatile'):
                        attacker.add_volatile(data['add_volatile'], self.owner)
                        battle.log(f"{self.owner.name}'s {self.name} inflicts {data['add_volatile']}!")
                    if data.get('inflict_status'):
                        attacker.try_set_status(data['inflict_status'], self.owner)
            # recoil or static-like damage
            recoil = data.get('recoil_frac')
            if recoil:
                amt = attacker.stats['hp'] // recoil if data.get('inflict_status') is None else 0
                attacker.apply_damage(amt)
                battle.log(f"{self.owner.name}'s {self.name} hurts {attacker.name}!")

    def on_end_of_turn(self, battle: 'Battle'):
        data = self.metadata.get('on_end_of_turn', {})
        # leftovers / rain dish healing
        if data.get('recover_frac') and battle.weather in data.get('weather_only', []):
            heal = self.owner.stats['hp'] // data['recover_frac']
            self.owner.current_hp = min(self.owner.stats['hp'], self.owner.current_hp + heal)
            battle.log(f"{self.owner.name} recovers HP with {self.name}!")
        # truant toggle
        if data.get('toggle_truant_turn'):
            self.owner.truantTurn = not self.owner.truantTurn


# build map
abilities_map = load_abilities()
