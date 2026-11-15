import os, zipfile

base_dir = "/mnt/E8A2D79FA2D77114/Source/repos/GameRandomizers/Randomizers/HouseFlipper/house_flipper"
os.makedirs(base_dir, exist_ok=True)

HOUSES = [
    "First Office", "Abandoned House", "Burned House", "Hacker Loft", "Samarta Myers House",
    "Family House", "Garden After Building", "Just Married House", "Pink Kingdom", "Train Car",
    "Man Cave", "Uninhabited House", "House on the Moon", "Connoisseur House", "Cache in a Bunker",
    "13th Floor", "Castle", "Cyberpunk Loft", "Huckster House", "Luxury Villa"
]

with open(os.path.join(base_dir, "Options.py"), "w") as f:
    f.write('''from dataclasses import dataclass
from Options import Range, PerGameCommonOptions

class ContractsToWin(Range):
    """Number of contracts/houses completed to win the seed."""
    display_name = "Contracts To Win"
    range_start = 5
    range_end = 20
    default = 15

@dataclass
class HouseFlipperOptions(PerGameCommonOptions):
    contracts_to_win: ContractsToWin
''')

with open(os.path.join(base_dir, "Items.py"), "w") as f:
    f.write('''from BaseClasses import Item

class HouseFlipperItem(Item):
    game: str = "House Flipper"

ITEM_TABLE = {
    "Tier 1 Contract Permit": 20001,
    "Tier 2 Contract Permit": 20002,
    "Tier 3 Contract Permit": 20003,
    "Tier 4 Contract Permit": 20004,
    "Mop & Window Squeegee": 20010,
    "Paint Roller": 20011,
    "Plaster Trowel": 20012,
    "Sledgehammer": 20013,
    "Building & Demolition Tool": 20014,
    "Progressive Cleaning": 20020,
    "Progressive Painting": 20021,
    "Progressive Demolition": 20022,
    "Progressive Handyman": 20023,
    "Progressive Negotiation": 20024,
    "Contractor Voucher (+$500)": 20030,
    "Client Bonus (+$1,500)": 20031,
    "Renovation Grant (+$5,000)": 20032,
}
''')

with open(os.path.join(base_dir, "Locations.py"), "w") as f:
    lines = ['from BaseClasses import Location\n\nclass HouseFlipperLocation(Location):\n    game: str = "House Flipper"\n\nLOCATION_TABLE = {']
    for i, h in enumerate(HOUSES):
        lines.append(f'    "{h} - Contract Complete": {10000 + i},')
        for r in range(1, 4):
            lines.append(f'    "{h} - Room Task #{r}": {10100 + i * 3 + (r - 1)},')
    for p in range(1, 21):
        lines.append(f'    "Skill & Perk Milestone #{p:02d}": {10200 + p - 1},')
    lines.append('}\n')
    f.write("\n".join(lines))

with open(os.path.join(base_dir, "__init__.py"), "w") as f:
    f.write('''from typing import Dict, List
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
''')

out = "/mnt/E8A2D79FA2D77114/Games/Archipelago/custom_worlds/house_flipper.apworld"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for fn in os.listdir(base_dir):
        zf.write(os.path.join(base_dir, fn), arcname=f"house_flipper/{fn}")
print("[SUCCESS] Built", out)
