from __future__ import annotations
import json
from pathlib import Path
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
                    "name": str(row["Name"]),
                    "type": str(row["Type"]).capitalize(),
                    "power": power,
                    "accuracy": acc,
                    "pp": pp,
                }
            _xlsx_data = data
        else:
            _xlsx_data = {}


def _load_name_map() -> None:
    """Previously loaded move name aliases from the network.

    The new spreadsheet contains all Gen 1-3 moves so this mapping is now
    unnecessary. The function is kept for backward compatibility but simply
    initializes an empty dictionary without performing any network calls.
    """
    global _name_map
    if _name_map is None:
        _name_map = {}


def _save_cache() -> None:
    if _cache is not None:
        CACHE_FILE.write_text(json.dumps(_cache, indent=2))


def _fetch_move(name: str) -> dict:
    """Retrieve move data from the local spreadsheet only.

    Network access to the PokeAPI was previously used as a fall back, but the
    updated ``Moves_list.xlsx`` file already contains all move data for
    generations 1 through 3.  If a move is missing from the spreadsheet this
    function simply returns an empty dictionary.
    """
    slug = name.lower()
    _load_xlsx_data()
    canon = slug.replace(" ", "").replace("-", "")
    if canon in _xlsx_data:
        return _xlsx_data[canon]
    return {}


def _get_move(name: str) -> dict:
    _load_cache()
    _load_xlsx_data()
    ident = name.lower()
    if ident in _cache:
        return _cache[ident]
    canon = ident.replace(" ", "").replace("-", "")
    if canon in _xlsx_data:
        return _xlsx_data[canon]
    # If the move was not found in the JSON file or the spreadsheet simply
    # return an empty dictionary. Previously this attempted a network lookup
    # using the PokeAPI, but the local spreadsheet now contains all required
    # data for generations 1-3.
    return {}


def load_moves(path: str | Path | None = None) -> dict[str, Move]:
    """Load moves from JSON file and instantiate Move objects."""
    if path is None:
        path = Path(__file__).parent.parent / "data" / "moves.json"
    _load_xlsx_data()
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

    # Add any additional moves present in the spreadsheet but missing from the
    # JSON file.  This avoids the need for network lookups.
    for ident, meta in _xlsx_data.items():
        if ident not in moves:
            mv_power = meta.get("power", 0)
            mv_type = meta.get("type", "Normal")
            mv = Move(
                name=meta.get("name", ident),
                move_type=mv_type,
                power=mv_power,
                category=(
                    "Status"
                    if mv_power == 0
                    else ("Physical" if mv_type in PHYSICAL_TYPES else "Special")
                ),
                accuracy=meta.get("accuracy", 100),
                priority=meta.get("priority", 0),
                max_pp=meta.get("pp", 1),
            )
            moves[mv.name.lower()] = mv

    return moves
