"""Single source of truth: everything is derived from logic_rules.json here."""
import json
import pkgutil
from collections import Counter
from typing import Dict, List, NamedTuple

from .Friends import FRIEND_LIST

ITEM_BASE = 10000      # item/location id = 10000 + blueprint ItemIndex (matches the C# client)
FRIEND_BASE = 20000    # friend id = 20000 + index in FRIEND_LIST (matches the C# client)

PROGRESSION_POOLS = {"QuestEntryKey", "QuestItem", "QuestTier1", "QuestTier2"}
USEFUL_POOLS = {"Chinpokomon", "Weapon", "Armor", "StrapOrPatch"}

# Items the region rules / goal actually depend on. Only these are marked progression.
LOGIC_ITEMS = {
    "Community Center Key", "4th Grade Classroom Key",
    "Passport", "Clinic Records", "Princess's Letter",
}


class ItemData(NamedTuple):
    index: int
    name: str      # raw in-game name
    label: str     # unique AP item name
    pool: str
    sphere: int


def _load() -> List[ItemData]:
    raw = pkgutil.get_data(__name__, "logic_rules.json")
    rules = json.loads(raw.decode("utf-8-sig"))
    # Only unique, non-excluded blueprints can be 1-of-1 locations.
    # Consumables/junk are not unique, so they cannot be distinct checks.
    items = [i for i in rules["Items"] if i["IsUnique"] and not i["Excluded"]]
    counts = Counter(i["Name"] for i in items)
    out = []
    for i in items:
        label = i["Name"]
        if counts[label] > 1:  # e.g. both "Holy Ring"s -> "Holy Ring (#210)"
            label = f"{label} (#{i['ItemIndex']:03d})"
        out.append(ItemData(i["ItemIndex"], i["Name"], label, i["Pool"], int(i["Sphere"])))
    return out


UNIQUE_ITEMS: List[ItemData] = _load()
ITEM_BY_LABEL: Dict[str, ItemData] = {d.label: d for d in UNIQUE_ITEMS}


def location_name(d: ItemData) -> str:
    return f"Check #{d.index:03d}: {d.label}"


FRIEND_ITEM_NAMES = {f: f"Friend: {f}" for f in FRIEND_LIST}
FRIEND_LOCATION_NAMES = {f: f"Friend Request: {f}" for f in FRIEND_LIST}