from __future__ import annotations
import json
from pathlib import Path
from urllib.request import urlopen
import pandas as pd

_cache: dict[str, dict] | None = None
CACHE_FILE = Path(__file__).parent.parent / "data" / "pokeapi_cache.json"
_base_stats_df = None


def _load_cache() -> None:
    global _cache
    if _cache is None:
        if CACHE_FILE.exists():
            _cache = json.loads(CACHE_FILE.read_text())
        else:
            _cache = {}


def _load_df(path: str | Path | None = None):
    global _base_stats_df
    if _base_stats_df is None:
        if path is None:
            path = Path(__file__).parent.parent / "Base_Stats_Gen3.xlsx"
        _base_stats_df = pd.read_excel(path)


def _save_cache() -> None:
    if _cache is not None:
        CACHE_FILE.write_text(json.dumps(_cache, indent=2))


def _fetch_from_api(name: str) -> dict:
    url = f"https://pokeapi.co/api/v2/pokemon/{name.lower()}"
    with urlopen(url) as resp:
        data = json.load(resp)
    stats = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}
    types = [
        t["type"]["name"].capitalize()
        for t in sorted(data["types"], key=lambda x: x["slot"])
    ]
    entry = {
        "base_stats": {
            "hp": stats["hp"],
            "atk": stats["attack"],
            "def": stats["defense"],
            "spa": stats["special-attack"],
            "spd": stats["special-defense"],
            "spe": stats["speed"],
        },
        "types": types,
    }
    _cache[name.lower()] = entry
    _save_cache()
    return entry


def _get_entry(name: str) -> dict:
    _load_cache()
    _load_df()
    ident = name.lower()
    if ident in _cache:
        return _cache[ident]
    # get base stats from spreadsheet if available
    row = _base_stats_df[_base_stats_df["Pokémon_1"].str.lower() == ident]
    if not row.empty:
        r = row.iloc[0]
        stats = {
            "hp": int(r["HP"]),
            "atk": int(r["Attack"]),
            "def": int(r["Defense"]),
            "spa": int(r["Sp. Attack"]),
            "spd": int(r["Sp. Defense"]),
            "spe": int(r["Speed"]),
        }
    else:
        stats = None
    try:
        api = _fetch_from_api(ident)
        if stats:
            api["base_stats"] = stats
        return api
    except Exception as exc:  # pragma: no cover - network errors
        if stats:
            return {"base_stats": stats, "types": ["Normal"]}
        raise ValueError(f"Unknown Pokémon {name}") from exc


def get_base_stats(name: str) -> dict[str, int]:
    return _get_entry(name)["base_stats"]


def get_pokemon_types(name: str) -> list[str]:
    return _get_entry(name)["types"]
