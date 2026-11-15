import os, zipfile

base_dir = "/mnt/E8A2D79FA2D77114/Source/repos/GameRandomizers/Randomizers/RetroRewind/retro_rewind"
os.makedirs(base_dir, exist_ok=True)

with open(os.path.join(base_dir, "Options.py"), "w") as f:
    f.write('''from dataclasses import dataclass
from Options import Range, PerGameCommonOptions

class TargetStoreLevel(Range):
    """Target Store Level required to complete the seed."""
    display_name = "Target Store Level"
    range_start = 5
    range_end = 20
    default = 15

@dataclass
class RetroRewindOptions(PerGameCommonOptions):
    target_store_level: TargetStoreLevel
''')

with open(os.path.join(base_dir, "Items.py"), "w") as f:
    f.write('''from BaseClasses import Item

class RetroRewindItem(Item):
    game: str = "Retro Rewind"

ITEM_TABLE = {
    "Store Expansion Permit #1": 20001,
    "Store Expansion Permit #2": 20002,
    "Store Expansion Permit #3": 20003,
    "Store Expansion Permit #4": 20004,
    "Action & Sci-Fi License": 20010,
    "Horror & Thriller License": 20011,
    "Comedy & Romance License": 20012,
    "Video Game & Console Rental License": 20013,
    "Concessions & Popcorn License": 20014,
    "Arcade Cabinet License": 20015,
    "New Releases License": 20016,
    "Store XP Boost (+250 XP)": 20020,
    "Late Fee Windfall (+$50)": 20030,
    "Cash Register Bundle (+$150)": 20031,
    "Safe Deposit Bundle (+$500)": 20032,
}
''')

with open(os.path.join(base_dir, "Locations.py"), "w") as f:
    lines = ['from BaseClasses import Location\n\nclass RetroRewindLocation(Location):\n    game: str = "Retro Rewind"\n\nLOCATION_TABLE = {']
    for lvl in range(2, 21):
        lines.append(f'    "Store Level {lvl:02d}": {10000 + lvl - 2},')
    for q in range(1, 26):
        lines.append(f'    "Quest Completed #{q:02d}": {10100 + q - 1},')
    for u in range(1, 21):
        lines.append(f'    "Store Unlock #{u:02d}": {10200 + u - 1},')
    for m in range(1, 27):
        lines.append(f'    "Store Milestone #{m:02d}": {10300 + m - 1},')
    lines.append('}\n')
    f.write("\n".join(lines))

with open(os.path.join(base_dir, "__init__.py"), "w") as f:
    f.write('''from typing import Dict, List
from BaseClasses import Region, ItemClassification, Tutorial
from worlds.AutoWorld import World, WebWorld
from .Options import RetroRewindOptions
from .Items import RetroRewindItem, ITEM_TABLE
from .Locations import RetroRewindLocation, LOCATION_TABLE

class RetroRewindWeb(WebWorld):
    theme = "partyTime"
    tutorials = [Tutorial("Setup Guide", "Setup Retro Rewind for Archipelago.", "English", "setup_en.md", "setup/en", ["SoT_Rando"])]

class RetroRewindWorld(World):
    """Retro Rewind - Video Store Simulator: Manage your 90s video store, unlock licenses, and expand!"""
    game = "Retro Rewind"
    web = RetroRewindWeb()
    options_dataclass = RetroRewindOptions
    options: RetroRewindOptions
    item_name_to_id: Dict[str, int] = ITEM_TABLE
    location_name_to_id: Dict[str, int] = LOCATION_TABLE

    def create_item(self, name: str) -> RetroRewindItem:
        code = self.item_name_to_id[name]
        if "Permit" in name or "License" in name:
            cls = ItemClassification.progression
        elif "XP Boost" in name:
            cls = ItemClassification.useful
        else:
            cls = ItemClassification.filler
        return RetroRewindItem(name, cls, code, self.player)

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        starter = Region("Starter Store", self.player, self.multiworld)
        expanded = Region("Expanded Store", self.player, self.multiworld)
        deluxe = Region("Deluxe Video Empire", self.player, self.multiworld)
        self.multiworld.regions.extend([menu, starter, expanded, deluxe])

        for loc_name, loc_id in LOCATION_TABLE.items():
            if loc_id < 10008 or (10100 <= loc_id < 10112) or (10200 <= loc_id < 10208) or (10300 <= loc_id < 10310):
                reg = starter
            elif loc_id < 10014 or (10112 <= loc_id < 10120) or (10208 <= loc_id < 10215) or (10310 <= loc_id < 10320):
                reg = expanded
            else:
                reg = deluxe
            reg.locations.append(RetroRewindLocation(self.player, loc_name, loc_id, reg))

        menu.connect(starter)
        starter.connect(expanded, rule=lambda state: state.has("Store Expansion Permit #1", self.player) or state.has("Video Game & Console Rental License", self.player))
        expanded.connect(deluxe, rule=lambda state: state.has("Store Expansion Permit #2", self.player) and state.has("New Releases License", self.player))

    def create_items(self) -> None:
        pool: List[RetroRewindItem] = []
        for k in ("Store Expansion Permit #1", "Store Expansion Permit #2", "Store Expansion Permit #3", "Store Expansion Permit #4",
                  "Action & Sci-Fi License", "Horror & Thriller License", "Comedy & Romance License",
                  "Video Game & Console Rental License", "Concessions & Popcorn License",
                  "Arcade Cabinet License", "New Releases License"):
            pool.append(self.create_item(k))
        for _ in range(10):
            pool.append(self.create_item("Store XP Boost (+250 XP)"))

        total_locs = len(self.multiworld.get_locations(self.player))
        fillers = ["Late Fee Windfall (+$50)", "Cash Register Bundle (+$150)", "Safe Deposit Bundle (+$500)"]
        while len(pool) < total_locs:
            pool.append(self.create_item(fillers[len(pool) % len(fillers)]))
        self.multiworld.itempool.extend(pool)

    def set_rules(self) -> None:
        target = int(self.options.target_store_level)
        self.multiworld.completion_condition[self.player] = lambda state: state.can_reach(f"Store Level {target:02d}", "Location", self.player)
''')

apworld_path = "/mnt/E8A2D79FA2D77114/Games/Archipelago/custom_worlds/retro_rewind.apworld"
with zipfile.ZipFile(apworld_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for fn in os.listdir(base_dir):
        zf.write(os.path.join(base_dir, fn), arcname=f"retro_rewind/{fn}")

print(f"[SUCCESS] Built {apworld_path} with 90 locations & GVAS progression!")
