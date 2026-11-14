from typing import Dict, List
from BaseClasses import Region, ItemClassification, Tutorial
from worlds.AutoWorld import World, WebWorld
from .Options import LittleInfernoOptions
from .Items import LittleInfernoItem, ITEM_TABLE
from .Locations import LittleInfernoLocation, LOCATION_TABLE

class LittleInfernoWeb(WebWorld):
    theme = "dirt"
    tutorials = [Tutorial("Setup Guide", "Setup Little Inferno for Archipelago.", "English", "setup_en.md", "setup/en", ["SoT_Rando"])]

class LittleInfernoWorld(World):
    """Little Inferno: Burn toys, discover 99 combos, and unlock all 7 Tomorrow Corporation catalogs!"""
    game = "Little Inferno"
    web = LittleInfernoWeb()
    options_dataclass = LittleInfernoOptions
    options: LittleInfernoOptions
    item_name_to_id: Dict[str, int] = ITEM_TABLE
    location_name_to_id: Dict[str, int] = LOCATION_TABLE

    def create_item(self, name: str) -> LittleInfernoItem:
        code = self.item_name_to_id[name]
        if "Catalog" in name:
            cls = ItemClassification.progression
        elif "Delivery Slot" in name or "Combo Hint" in name:
            cls = ItemClassification.useful
        else:
            cls = ItemClassification.filler
        return LittleInfernoItem(name, cls, code, self.player)

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        cat_regions = [Region(f"Catalog {i}", self.player, self.multiworld) for i in range(1, 8)]
        self.multiworld.regions.extend([menu] + cat_regions)

        for loc_name, loc_id in LOCATION_TABLE.items():
            if loc_name.startswith("Catalog "):
                c_num = int(loc_name.split()[1])
                reg = cat_regions[c_num - 1]
                reg.locations.append(LittleInfernoLocation(self.player, loc_name, loc_id, reg))
            elif self.options.include_combos and loc_name.startswith("Combo "):
                c_idx = loc_id - 11000
                reg = cat_regions[min(6, c_idx // 15)]
                reg.locations.append(LittleInfernoLocation(self.player, loc_name, loc_id, reg))

        menu.connect(cat_regions[0])
        for i in range(2, 8):
            cat_regions[0].connect(
                cat_regions[i - 1],
                rule=lambda state, num=i: state.has(f"Catalog {num} Unlock", self.player)
            )

    def create_items(self) -> None:
        pool: List[LittleInfernoItem] = []
        for i in range(2, 8):
            pool.append(self.create_item(f"Catalog {i} Unlock"))
        for _ in range(6):
            pool.append(self.create_item("Progressive Delivery Slot"))

        total_locs = len(self.multiworld.get_locations(self.player))
        fillers = ["Tomorrow Bucks (+$50)", "Tomorrow Bucks (+$150)", "Order Form Stamps (+5)", "Combo Hint Scroll"]
        while len(pool) < total_locs:
            pool.append(self.create_item(fillers[len(pool) % len(fillers)]))
        self.multiworld.itempool.extend(pool)

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: all(
            state.has(f"Catalog {i} Unlock", self.player) for i in range(2, 8)
        )
