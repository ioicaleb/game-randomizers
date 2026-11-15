from typing import Dict, List
from BaseClasses import Region, ItemClassification, Tutorial
from worlds.AutoWorld import World, WebWorld
from .Options import SkateBirdOptions
from .Items import SkateBirdItem, ITEM_TABLE
from .Locations import SkateBirdLocation, LOCATION_TABLE

class SkateBirdWeb(WebWorld):
    theme = "grass"
    tutorials = [Tutorial("Setup Guide", "Setup SkateBIRD for Archipelago.", "English", "setup_en.md", "setup/en", ["SoT_Rando"])]

class SkateBirdWorld(World):
    """SkateBIRD: Skate tiny parks as a birb, unlock tricks and levels, and complete bird missions!"""
    game = "SkateBIRD"
    web = SkateBirdWeb()
    options_dataclass = SkateBirdOptions
    options: SkateBirdOptions
    item_name_to_id: Dict[str, int] = ITEM_TABLE
    location_name_to_id: Dict[str, int] = LOCATION_TABLE

    def create_item(self, name: str) -> SkateBirdItem:
        code = self.item_name_to_id[name]
        if name.endswith("Key") or code in (20010, 20011, 20012, 20013):
            cls = ItemClassification.progression
        elif name.startswith("Progressive "):
            cls = ItemClassification.useful
        else:
            cls = ItemClassification.filler
        return SkateBirdItem(name, cls, code, self.player)

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        regs = {lvl: Region(lvl, self.player, self.multiworld) for lvl in ["Bedroom", "Office", "Rooftop", "Skatepark", "Warehouse"]}
        self.multiworld.regions.extend([menu] + list(regs.values()))

        for loc_name, loc_id in LOCATION_TABLE.items():
            lvl = loc_name.split(" - ").pop(0)
            reg = regs[lvl]
            loc = SkateBirdLocation(self.player, loc_name, loc_id, reg)
            if "Gold Score" in loc_name:
                loc.access_rule = lambda state: state.has("Grinds", self.player) and state.has("Manuals", self.player)
            elif "Silver Score" in loc_name:
                loc.access_rule = lambda state: state.has("Grinds", self.player) or state.has("Manuals", self.player)
            elif any(m in loc_name for m in ("Mission #04", "Mission #05")):
                loc.access_rule = lambda state: state.has("Grinds", self.player)
            elif any(m in loc_name for m in ("Mission #06", "Mission #07")):
                loc.access_rule = lambda state: state.has("Manuals", self.player)
            elif any(m in loc_name for m in ("Mission #08", "Mission #09", "Mission #10")):
                loc.access_rule = lambda state: state.has("Wing Flap (Air Ollie)", self.player)
            reg.locations.append(loc)

        menu.connect(regs["Bedroom"])
        regs["Bedroom"].connect(regs["Office"], rule=lambda state: state.has("Office Key", self.player))
        regs["Bedroom"].connect(regs["Rooftop"], rule=lambda state: state.has("Rooftop Key", self.player))
        regs["Office"].connect(regs["Skatepark"], rule=lambda state: state.has("Skatepark Key", self.player))
        regs["Rooftop"].connect(regs["Warehouse"], rule=lambda state: state.has("Warehouse Key", self.player))

    def create_items(self) -> None:
        pool: List[SkateBirdItem] = []
        for k in ("Office Key", "Rooftop Key", "Skatepark Key", "Warehouse Key",
                  "Flip Tricks", "Grinds", "Manuals", "Wing Flap (Air Ollie)"):
            pool.append(self.create_item(k))
        for stat in ("Progressive Air", "Progressive Speed", "Progressive Ollie Height", "Progressive Spin", "Progressive Balance"):
            for _ in range(3):
                pool.append(self.create_item(stat))

        total_locs = len(self.multiworld.get_locations(self.player))
        fillers = ["Fancy Boost (+500 Fancy)", "Birdseed Treat", "Stylish Feather"]
        while len(pool) < total_locs:
            pool.append(self.create_item(fillers[len(pool) % len(fillers)]))
        self.multiworld.itempool.extend(pool)

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: all(
            state.has(k, self.player) for k in ("Office Key", "Rooftop Key", "Skatepark Key", "Warehouse Key", "Wing Flap (Air Ollie)")
        )
