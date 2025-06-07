from __future__ import annotations
import json
from pathlib import Path
from urllib.request import urlopen
import pandas as pd
from .move import Move

PHYSICAL_TYPES = [
    "Normal",
    "Fighting",
    "Flying",
    "Poison",
    "Ground",
    "Rock",
    "Bug",
    "Ghost",
    "Steel",
]

_cache: dict[str, dict] | None = None
CACHE_FILE = Path(__file__).parent.parent / "data" / "move_cache.json"
_name_map: dict[str, str] | None = None
_xlsx_data: dict[str, dict] | None = None


def _load_cache() -> None:
    global _cache
    if _cache is None:
        if CACHE_FILE.exists():
            _cache = json.loads(CACHE_FILE.read_text())
        else:
            _cache = {}


def _load_xlsx_data() -> None:
    """Load move info from Moves_list.xlsx for Gen3."""
    global _xlsx_data
    if _xlsx_data is None:
        xlsx = Path(__file__).parent.parent / "Moves_list.xlsx"
        if xlsx.exists():
            df = pd.read_excel(xlsx)
            data = {}
            for _, row in df.iterrows():
                key = str(row["Name"]).lower().replace(" ", "").replace("-", "")
                try:
                    power = int(row["Power"])
                except (ValueError, TypeError):
                    power = 0
                try:
                    acc = int(row["Acc."])
                except (ValueError, TypeError):
                    acc = 100
                try:
                    pp = int(row["PP"])
                except (ValueError, TypeError):
                    pp = 1
                data[key] = {
                    "type": str(row["Type"]).capitalize(),
                    "power": power,
                    "accuracy": acc,
                    "pp": pp,
                }
            _xlsx_data = data
        else:
            _xlsx_data = {}


def _load_name_map() -> None:
    global _name_map
    if _name_map is None:
        try:
            with urlopen("https://pokeapi.co/api/v2/move?limit=1000") as resp:
                data = json.load(resp)
            _name_map = {m["name"].replace("-", ""): m["name"] for m in data["results"]}
        except Exception:  # pragma: no cover - network
            _name_map = {}


def _save_cache() -> None:
    if _cache is not None:
        CACHE_FILE.write_text(json.dumps(_cache, indent=2))


def _fetch_move(name: str) -> dict:
    slug = name.lower()
    _load_xlsx_data()
    if slug.replace(" ", "").replace("-", "") in _xlsx_data:
        return _xlsx_data[slug.replace(" ", "").replace("-", "")]
    try:
        with urlopen(f"https://pokeapi.co/api/v2/move/{slug}") as resp:
            data = json.load(resp)
    except Exception:
        _load_name_map()
        slug = _name_map.get(slug, slug)
        with urlopen(f"https://pokeapi.co/api/v2/move/{slug}") as resp:
            data = json.load(resp)
    entry = {
        "type": data["type"]["name"].capitalize(),
        "power": data["power"] or 0,
        "accuracy": data["accuracy"] or 100,
        "pp": data["pp"] or 1,
        "priority": data["priority"] or 0,
        "damage_class": data["damage_class"]["name"],
    }
    _cache[name.lower()] = entry
    _save_cache()
    return entry


def _get_move(name: str) -> dict:
    _load_cache()
    _load_xlsx_data()
    ident = name.lower()
    if ident in _cache:
        return _cache[ident]
    canon = ident.replace(" ", "").replace("-", "")
    if canon in _xlsx_data:
        return _xlsx_data[canon]
    try:
        return _fetch_move(ident)
    except Exception:  # pragma: no cover - network errors
        return {}


def load_moves(path: str | Path | None = None) -> dict[str, Move]:
    """Load moves from JSON file and instantiate Move objects."""
    if path is None:
        path = Path(__file__).parent.parent / "data" / "moves.json"
    data = json.loads(Path(path).read_text())
    moves: dict[str, Move] = {}
    for ident, meta in data.items():
        mv = Move(
            name=meta.get("name", ident),
            move_type=meta.get("type", "Normal"),
            power=meta.get("basePower", 0) or 0,
            category=meta.get("category", "Physical"),
            accuracy=meta.get("accuracy", 100),
            priority=meta.get("priority", 0),
            max_pp=meta.get("pp", 1),
        )
        mv.id = meta.get("id", ident)
        mv.flags = meta.get("flags", {})
        mv.metadata = meta
        # fill missing data via local spreadsheet or PokeAPI
        if not mv.power or mv.accuracy is None:
            fetched = _get_move(mv.name)
            if fetched:
                mv.power = mv.power or fetched.get("power", 0)
                mv.accuracy = (
                    mv.accuracy
                    if mv.accuracy is not None
                    else fetched.get("accuracy", 100)
                )
                mv.type = fetched.get("type", mv.type)
                mv.max_pp = mv.max_pp or fetched.get("pp", 1)
                mv.priority = mv.priority or fetched.get("priority", 0)
        # determine category using Gen 3 rules
        mv.category = (
            "Status"
            if mv.power == 0
            else ("Physical" if mv.type in PHYSICAL_TYPES else "Special")
        )
        moves[mv.name.lower()] = mv
    return moves
