from typing import Any, Dict, List

from BaseClasses import Region, ItemClassification, Tutorial
from worlds.AutoWorld import World, WebWorld

from .Data import (
    UNIQUE_ITEMS, ITEM_BY_LABEL, ItemData, FRIEND_LIST, FRIEND_ITEM_NAMES,
    FRIEND_LOCATION_NAMES, PROGRESSION_POOLS, USEFUL_POOLS, LOGIC_ITEMS, location_name,
)
from .Items import SouthParkSoTItem, item_name_to_id
from .Locations import SouthParkSoTLocation, location_name_to_id
from .Options import SouthParkSoTOptions


class SouthParkSoTWeb(WebWorld):
    theme = "grass"
    tutorials = [Tutorial(
        "Multiworld Setup Guide",
        "A guide to setting up South Park: The Stick of Truth for Archipelago Multiworld.",
        "English",
        "setup_en.md",
        "setup/en",
        ["SoT_Rando"],
    )]


class SouthParkSoTWorld(World):
    """
    South Park: The Stick of Truth is a turn-based RPG set in South Park, Colorado.
    Collect weapons, armor, straps, Chinpokomon, and Facebook friends across the town!
    """
    game = "South Park: The Stick of Truth"
    web = SouthParkSoTWeb()
    options_dataclass = SouthParkSoTOptions
    options: SouthParkSoTOptions

    item_name_to_id = item_name_to_id
    location_name_to_id = location_name_to_id

    def _active_items(self) -> List[ItemData]:
        return [d for d in UNIQUE_ITEMS
                if self.options.shuffle_chinpokomon or d.pool != "Chinpokomon"]

    def create_item(self, name: str) -> SouthParkSoTItem:
        data = ITEM_BY_LABEL.get(name)
        if data is None:                                   # friend request item
            cls = ItemClassification.useful
        elif data.name in LOGIC_ITEMS:
            cls = ItemClassification.progression
        elif data.pool in PROGRESSION_POOLS or data.pool in USEFUL_POOLS:
            cls = ItemClassification.useful
        else:
            cls = ItemClassification.filler
        return SouthParkSoTItem(name, cls, self.item_name_to_id[name], self.player)

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        spheres = [Region(n, self.player, self.multiworld) for n in (
            "South Park Town (Sphere 0)",
            "School & Dungeons (Sphere 1)",
            "Canada & Endgame (Sphere 2)",
        )]
        self.multiworld.regions.extend([menu, *spheres])

        for d in self._active_items():
            region = spheres[min(d.sphere, 2)]
            name = location_name(d)
            region.locations.append(
                SouthParkSoTLocation(self.player, name, self.location_name_to_id[name], region))

        if self.options.shuffle_friends:
            for f in FRIEND_LIST:
                name = FRIEND_LOCATION_NAMES[f]
                spheres[0].locations.append(
                    SouthParkSoTLocation(self.player, name, self.location_name_to_id[name], spheres[0]))

        menu.connect(spheres[0])
        spheres[0].connect(
            spheres[1],
            rule=lambda s: s.has("Community Center Key", self.player)
            or s.has("4th Grade Classroom Key", self.player))
        spheres[1].connect(
            spheres[2],
            rule=lambda s: s.has("Passport", self.player) and s.has("Clinic Records", self.player))

    def create_items(self) -> None:
        pool = [self.create_item(d.label) for d in self._active_items()]
        if self.options.shuffle_friends:
            pool += [self.create_item(FRIEND_ITEM_NAMES[f]) for f in FRIEND_LIST]
        self.multiworld.itempool += pool                   # item count == location count

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda s: (
            s.has("Passport", self.player) and s.has("Princess's Letter", self.player))

    def fill_slot_data(self) -> Dict[str, Any]:
        slot_mapping = {}
        for loc in self.multiworld.get_locations(self.player):
            if loc.address is not None and loc.item is not None:
                slot_mapping[str(loc.address)] = {
                    "item_id": loc.item.code,
                    "item_name": loc.item.name,
                    "player": loc.item.player,
                }
        return {
            "seed": self.multiworld.seed_name,
            "shuffle_friends": bool(self.options.shuffle_friends),
            "shuffle_chinpokomon": bool(self.options.shuffle_chinpokomon),
            "slot_mapping": slot_mapping,
        }