from typing import Dict, List
from BaseClasses import Region, ItemClassification, Tutorial
from worlds.AutoWorld import World, WebWorld
from .Options import HouseFlipperOptions
from .Items import HouseFlipperItem, ITEM_TABLE
from .Locations import HouseFlipperLocation, LOCATION_TABLE

class HouseFlipperWeb(WebWorld):
    theme = "dirt"
    tutorials = [Tutorial("Setup Guide", "Setup House Flipper for Archipelago.", "English", "setup_en.md", "setup/en", ["SoT_Rando"])]

class HouseFlipperWorld(World):
    """House Flipper: Clean, renovate, and flip houses across Archipelago!"""
    game = "House Flipper"
    web = HouseFlipperWeb()
    options_dataclass = HouseFlipperOptions
    options: HouseFlipperOptions
    item_name_to_id: Dict[str, int] = ITEM_TABLE
    location_name_to_id: Dict[str, int] = LOCATION_TABLE

    def create_item(self, name: str) -> HouseFlipperItem:
        code = self.item_name_to_id[name]
        if code < 20020:
            cls = ItemClassification.progression
        elif code < 20030:
            cls = ItemClassification.useful
        else:
            cls = ItemClassification.filler
        return HouseFlipperItem(name, cls, code, self.player)

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        t0 = Region("Starter Jobs", self.player, self.multiworld)
        t1 = Region("Tier 1 Contracts", self.player, self.multiworld)
        t2 = Region("Tier 2 Contracts", self.player, self.multiworld)
        t3 = Region("Tier 3 Contracts", self.player, self.multiworld)
        t4 = Region("Tier 4 Contracts", self.player, self.multiworld)
        self.multiworld.regions.extend([menu, t0, t1, t2, t3, t4])

        for loc_name, loc_id in LOCATION_TABLE.items():
            idx = (loc_id - 10000) if loc_id < 10100 else ((loc_id - 10100) // 3 if loc_id < 10200 else (loc_id - 10200))
            if idx < 4: reg = t0
            elif idx < 8: reg = t1
            elif idx < 12: reg = t2
            elif idx < 16: reg = t3
            else: reg = t4
            reg.locations.append(HouseFlipperLocation(self.player, loc_name, loc_id, reg))

        menu.connect(t0)
        t0.connect(t1, rule=lambda state: state.has("Tier 1 Contract Permit", self.player) and state.has("Mop & Window Squeegee", self.player))
        t1.connect(t2, rule=lambda state: state.has("Tier 2 Contract Permit", self.player) and state.has("Paint Roller", self.player))
        t2.connect(t3, rule=lambda state: state.has("Tier 3 Contract Permit", self.player) and state.has("Sledgehammer", self.player))
        t3.connect(t4, rule=lambda state: state.has("Tier 4 Contract Permit", self.player) and state.has("Building & Demolition Tool", self.player))

    def create_items(self) -> None:
        pool: List[HouseFlipperItem] = []
        for k in ("Tier 1 Contract Permit", "Tier 2 Contract Permit", "Tier 3 Contract Permit", "Tier 4 Contract Permit",
                  "Mop & Window Squeegee", "Paint Roller", "Plaster Trowel", "Sledgehammer", "Building & Demolition Tool"):
            pool.append(self.create_item(k))
        for p in ("Progressive Cleaning", "Progressive Painting", "Progressive Demolition", "Progressive Handyman", "Progressive Negotiation"):
            for _ in range(3):
                pool.append(self.create_item(p))
        total = len(self.multiworld.get_locations(self.player))
        fillers = ["Contractor Voucher (+$500)", "Client Bonus (+$1,500)", "Renovation Grant (+$5,000)"]
        while len(pool) < total:
            pool.append(self.create_item(fillers[len(pool) % len(fillers)]))
        self.multiworld.itempool.extend(pool)

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: state.has("Tier 4 Contract Permit", self.player)
