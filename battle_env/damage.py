import math

# --- Gen 3 Type Effectiveness Chart ---
TYPE_CHART = {
    'Normal': {'Rock': 0.5, 'Ghost': 0, 'Steel': 0.5},
    'Fire': {'Fire': 0.5, 'Water': 0.5, 'Grass': 2, 'Ice': 2, 'Bug': 2, 'Rock': 0.5, 'Dragon': 0.5, 'Steel': 2},
    'Water': {'Fire': 2, 'Water': 0.5, 'Grass': 0.5, 'Ground': 2, 'Rock': 2, 'Dragon': 0.5},
    'Electric': {'Water': 2, 'Electric': 0.5, 'Grass': 0.5, 'Ground': 0, 'Flying': 2, 'Dragon': 0.5},
    'Grass': {'Fire': 0.5, 'Water': 2, 'Electric': 0.5, 'Grass': 0.5, 'Poison': 0.5, 'Ground': 2, 'Flying': 0.5, 'Bug': 0.5, 'Rock': 2, 'Dragon': 0.5, 'Steel': 0.5},
    'Ice': {'Fire': 0.5, 'Water': 0.5, 'Grass': 2, 'Ice': 0.5, 'Ground': 2, 'Flying': 2, 'Dragon': 2, 'Steel': 0.5},
    'Fighting': {'Normal': 2, 'Ice': 2, 'Poison': 0.5, 'Flying': 0.5, 'Psychic': 0.5, 'Bug': 0.5, 'Rock': 2, 'Ghost': 0, 'Dark': 2, 'Steel': 2},
    'Poison': {'Grass': 2, 'Poison': 0.5, 'Ground': 0.5, 'Rock': 0.5, 'Ghost': 0.5, 'Steel': 0},
    'Ground': {'Fire': 2, 'Electric': 2, 'Grass': 0.5, 'Poison': 2, 'Flying': 0, 'Bug': 0.5, 'Rock': 2, 'Steel': 2},
    'Flying': {'Electric': 0.5, 'Grass': 2, 'Fighting': 2, 'Bug': 2, 'Rock': 0.5, 'Steel': 0.5},
    'Psychic': {'Fighting': 2, 'Poison': 2, 'Psychic': 0.5, 'Dark': 0, 'Steel': 0.5},
    'Bug': {'Fire': 0.5, 'Grass': 2, 'Fighting': 0.5, 'Poison': 0.5, 'Flying': 0.5, 'Psychic': 2, 'Ghost': 0.5, 'Dark': 2, 'Steel': 0.5},
    'Rock': {'Fire': 2, 'Ice': 2, 'Fighting': 0.5, 'Ground': 0.5, 'Flying': 2, 'Bug': 2, 'Steel': 0.5},
    'Ghost': {'Normal': 0, 'Psychic': 2, 'Ghost': 2, 'Dark': 0.5},
    'Dragon': {'Dragon': 2, 'Steel': 0.5},
    'Dark': {'Psychic': 2, 'Ghost': 2, 'Fighting': 0.5, 'Dark': 0.5, 'Steel': 0.5},
    'Steel': {'Fire': 0.5, 'Water': 0.5, 'Electric': 0.5, 'Ice': 2, 'Rock': 2, 'Steel': 0.5},
}

def get_type_effectiveness(move_type, defender_types):
    """
    Calculates the type effectiveness multiplier for a move against a defender.
    Returns a float (e.g., 2.0, 0.5, 0.0).
    """
    if not move_type or move_type == '???':
        return 1.0

    effectiveness = 1.0
    attack_type_chart = TYPE_CHART.get(move_type, {})

    for def_type in defender_types:
        multiplier = attack_type_chart.get(def_type, 1.0)
        effectiveness *= multiplier

    return effectiveness

def calculate_initial_damage(level, power, attack, defense):
    """
    Calculates the initial damage value before most modifiers are applied.
    """
    if attack == 0 or power == 0:
        return 0
        
    part1 = math.floor((2 * level) / 5) + 2
    part2 = part1 * power * attack
    part3 = math.floor(part2 / defense)
    initial_damage = math.floor(part3 / 50)
    
    return initial_damage


def get_damage_range(initial_damage, attacker, defender, move, is_crit=False, weather=None):
    """
    Calculates the final damage range based on the full Gen 3 formula.
    """
    # --- New: Handle Immunities Early ---
    # Before any calculation, check if the move is immune. If so, damage is 0.
    type_effectiveness = get_type_effectiveness(move['type'], defender.get('types', []))
    if type_effectiveness == 0:
        return 0, 0

    # --- Step 1: Apply initial modifiers (e.g., Burn) ---
    modified_damage = float(initial_damage)
    
    if attacker.get('status') == 'brn' and move.get('category') == 'Physical' and attacker.get('ability') != 'Guts':
        modified_damage = math.floor(modified_damage * 0.5)

    modified_damage = max(1, modified_damage)
    
    # --- Step 2: Add 2 (The critical Gen 3 step) ---
    modified_damage += 2

    # --- Step 3: Apply main multipliers (post-+2) ---
    modifier = 1.0

    if weather:
        if weather == 'sun' and move['type'] == 'Fire': modifier *= 1.5
        elif weather == 'sun' and move['type'] == 'Water': modifier *= 0.5
        elif weather == 'rain' and move['type'] == 'Water': modifier *= 1.5
        elif weather == 'rain' and move['type'] == 'Fire': modifier *= 0.5

    if is_crit:
        modifier *= move.get('critModifier', 2)

    if move['type'] in attacker.get('types', []):
        modifier *= 1.5
        
    # --- New: Apply the type effectiveness multiplier to the chain ---
    modifier *= type_effectiveness

    modified_damage *= modifier

    # --- Step 4: Apply the GBA random damage roll ---
    damage_rolls = []
    final_base_damage = math.floor(modified_damage)
    
    for r in range(217, 256):
        dmg = math.floor(final_base_damage * r / 255)
        damage_rolls.append(max(1, dmg))
        
    unique_rolls = sorted(list(set(damage_rolls)))
    return unique_rolls[0], unique_rolls[-1]
