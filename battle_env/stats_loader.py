from __future__ import annotations
from pathlib import Path
import pandas as pd

_base_stats_df = None

def _load_df(path: str | Path | None = None):
    global _base_stats_df
    if _base_stats_df is None:
        if path is None:
            path = Path(__file__).parent.parent / 'Base_Stats_Gen3.xlsx'
        _base_stats_df = pd.read_excel(path)


def get_base_stats(pokemon_name: str) -> dict[str, int]:
    """Return base stats dict for the given Pokémon name."""
    _load_df()
    row = _base_stats_df[_base_stats_df['Pokémon_1'].str.lower() == pokemon_name.lower()]
    if row.empty:
        raise ValueError(f"Unknown Pokémon {pokemon_name}")
    r = row.iloc[0]
    return {
        'hp': int(r['HP']),
        'atk': int(r['Attack']),
        'def': int(r['Defense']),
        'spa': int(r['Sp. Attack']),
        'spd': int(r['Sp. Defense']),
        'spe': int(r['Speed'])
    }
