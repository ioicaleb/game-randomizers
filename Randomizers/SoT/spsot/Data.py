"""Single source of truth: everything is derived from logic_rules.json here."""
import json
import pkgutil
from collections import Counter
from typing import Dict, List, NamedTuple, Optional

from .Friends import FRIEND_LIST

_rules = json.loads(pkgutil.get_data(__name__, "logic_rules.json").decode("utf-8-sig"))
_unlock = json.loads(pkgutil.get_data(__name__, "unlock_map.json").decode("utf-8-sig"))
try:                                                # optional: items the game's own scripts reference
    SCRIPT_REFERENCED = {int(k) for k in json.loads(
        pkgutil.get_data(__name__, "script_items.json").decode("utf-8-sig"))["referenced"]}
except (OSError, ValueError, KeyError):
    SCRIPT_REFERENCED = set()
START_OWNED = set(_unlock["start_owned"])          # unlocks you already own in a new game: never checkable
_UNLOCK_BY_INDEX = {int(k): v["hash"] for k, v in _unlock["unlocks"].items()}

ITEM_BASE = 10000      # item/location id = 10000 + blueprint ItemIndex (matches the C# client)
FRIEND_BASE = 20000    # friend id = 20000 + index in FRIEND_LIST (matches the C# client)

# Quest / key items. They only enter the pool when they can be DELIVERED through an unlock (see unlock_map.json),
# or when the logic needs them as a token. Everything else stays vanilla, because a cloned copy has the wrong
# identity and would only clutter the key-item list.
QUEST_POOLS = {"QuestItem", "QuestEntryKey", "QuestTier1", "QuestTier2"}

PROGRESSION_POOLS = {"QuestEntryKey", "QuestItem", "QuestTier1", "QuestTier2"}
USEFUL_POOLS = {"Chinpokomon", "Weapon", "Armor", "StrapOrPatch"}

# The 12 class weapons (Warrior / Jew / Mage / Thief, tiers 1-3). The game hands these out around the
# Clyde tutorial and then removes the tutorial weapon. If they are shuffled the player can end up with
# no weapon (soft lock), so they always stay vanilla.
ALWAYS_VANILLA_ITEM_INDICES = {917, 918, 919, 927, 928, 929, 937, 938, 939, 947, 948, 949}

# Tier-1 gear of each class (Fighter / Jew / Mage / Thief: gloves-or-ring, headgear, body). Your own save shows the
# Warrior set (#198, #202, #206) was owned very early, and the game equips the starting kit by hash; if that data is
# swapped for a different kind of item, combat can fail to start. Like the class weapons, they stay vanilla.
CLASS_STARTER_GEAR = {198, 202, 206, 228, 232, 236, 249, 253, 257, 307, 311, 315}
ALWAYS_VANILLA_ITEM_INDICES |= CLASS_STARTER_GEAR

# Jimbo's Big Game Hunter baits (Cow Bell, Moldy Sausage, ...) are normal deliverable items now: the client
# patches his dialogue so he stops handing them out, and the AP item grants the unlock instead.

# Placeholder names in logic_rules.json that the item link identified (icon ic_item_slim_jim).
NAME_OVERRIDES = {83: "Slim Jim"}

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
    unlock_hash: Optional[int] = None   # set => deliverable: an AP item flips this in-game unlock when received


def _load() -> List[ItemData]:
    # Only unique, non-excluded blueprints can be 1-of-1 locations.
    # Consumables/junk are not unique, so they cannot be distinct checks.
    chosen = []
    used_unlocks = set()
    for i in _rules["Items"]:
        if not i["IsUnique"] or i["Excluded"]:
            continue
        idx = i["ItemIndex"]
        if idx in ALWAYS_VANILLA_ITEM_INDICES or i["BlueprintHash"] in START_OWNED:
            continue
        unlock = _UNLOCK_BY_INDEX.get(idx)
        if unlock is not None and unlock in used_unlocks:
            continue                      # two items claiming the same unlock: keep the first, rest stay vanilla
        if i["Pool"] in QUEST_POOLS and unlock is None and i["Name"] not in LOGIC_ITEMS:
            continue                      # cannot be delivered and not needed for logic: stays vanilla
        if unlock is None and idx in SCRIPT_REFERENCED and i["Pool"] not in QUEST_POOLS:
            continue                      # a script equips / gives / removes this item: leave it exactly as it is
        if unlock is not None:
            used_unlocks.add(unlock)
        chosen.append((i, unlock))

    counts = Counter(NAME_OVERRIDES.get(i["ItemIndex"], i["Name"]) for i, _ in chosen)
    out = []
    for i, unlock in chosen:
        label = NAME_OVERRIDES.get(i["ItemIndex"], i["Name"])
        if counts[label] > 1:  # e.g. both "Holy Ring"s -> "Holy Ring (#210)"
            label = f"{label} (#{i['ItemIndex']:03d})"
        out.append(ItemData(i["ItemIndex"], NAME_OVERRIDES.get(i["ItemIndex"], i["Name"]), label, i["Pool"], int(i["Sphere"]), unlock))
    return out


UNIQUE_ITEMS: List[ItemData] = _load()
ITEM_BY_LABEL: Dict[str, ItemData] = {d.label: d for d in UNIQUE_ITEMS}


def is_deliverable(d: ItemData) -> bool:
    """Deliverable items can travel to any world and are granted by flipping an in-game unlock.
    Everything else (weapons, armor, cosmetics, patches, logic tokens) only works as a local clone."""
    return d.unlock_hash is not None


def location_name(d: ItemData) -> str:
    return f"Check #{d.index:03d}: {d.label}"


FRIEND_ITEM_NAMES = {f: f"Friend: {f}" for f in FRIEND_LIST}
FRIEND_LOCATION_NAMES = {f: f"Friend Request: {f}" for f in FRIEND_LIST}
