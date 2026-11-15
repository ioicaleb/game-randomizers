from typing import Dict, List
from BaseClasses import Region, ItemClassification, Tutorial
from worlds.AutoWorld import World, WebWorld
from .Options import ShadowsOverLoathingOptions
from .Items import ShadowsOverLoathingItem, ITEM_TABLE
from .Locations import ShadowsOverLoathingLocation, LOCATION_TABLE

class ShadowsOverLoathingWeb(WebWorld):
    theme = 'stone'
    tutorials = [Tutorial('Setup Guide', 'Setup Shadows Over Loathing.', 'English', 'setup_en.md', 'setup/en', ['SoT_Rando'])]

class ShadowsOverLoathingWorld(World):
    game = 'Shadows Over Loathing'
    web = ShadowsOverLoathingWeb()
    options_dataclass = ShadowsOverLoathingOptions
    options: ShadowsOverLoathingOptions
    item_name_to_id: Dict[str, int] = ITEM_TABLE
    location_name_to_id: Dict[str, int] = LOCATION_TABLE

    def create_item(self, name: str) -> ShadowsOverLoathingItem:
        code = self.item_name_to_id[name]
        cls = ItemClassification.progression if code < 20020 else (ItemClassification.useful if code < 20030 else ItemClassification.filler)
        return ShadowsOverLoathingItem(name, cls, code, self.player)

    def create_regions(self) -> None:
        menu = Region('Menu', self.player, self.multiworld)
        ch_names = ['Prologue - Gilmore Antiques', 'Chapter 1 - Ocean City', 'Chapter 2 - Crystaldream Lake', 'Chapter 3 - The Big Moist', 'Chapter 4 - Gray County', 'Chapter 5 - Black Gold', 'Chapter 6 - Government Valley']
        regs = {c: Region(c, self.player, self.multiworld) for c in ch_names}
        self.multiworld.regions.extend([menu] + list(regs.values()))
        for loc_name, loc_id in LOCATION_TABLE.items():
            matched = next((c for c in ch_names if loc_name.startswith(c)), 'Chapter 2 - Crystaldream Lake')
            loc = ShadowsOverLoathingLocation(self.player, loc_name, loc_id, regs[matched])
            if 'Shadow Rift' in loc_name:
                loc.access_rule = lambda state: state.has('Shadow Taint Ward', self.player)
            regs[matched].locations.append(loc)
        menu.connect(regs['Prologue - Gilmore Antiques'])
        regs['Prologue - Gilmore Antiques'].connect(regs['Chapter 1 - Ocean City'], rule=lambda state: state.has('Ocean City Bus Pass', self.player))
        regs['Chapter 1 - Ocean City'].connect(regs['Chapter 2 - Crystaldream Lake'], rule=lambda state: state.has('Crystaldream Lake Map', self.player))
        regs['Chapter 2 - Crystaldream Lake'].connect(regs['Chapter 3 - The Big Moist'], rule=lambda state: state.has('Big Moist Swamp Pass', self.player))
        regs['Chapter 3 - The Big Moist'].connect(regs['Chapter 4 - Gray County'], rule=lambda state: state.has('Gray County Rail Ticket', self.player))
        regs['Chapter 4 - Gray County'].connect(regs['Chapter 5 - Black Gold'], rule=lambda state: state.has('Black Gold Oil Permit', self.player))
        regs['Chapter 5 - Black Gold'].connect(regs['Chapter 6 - Government Valley'], rule=lambda state: state.has('Government Valley Clearance', self.player))

    def create_items(self) -> None:
        pool: List[ShadowsOverLoathingItem] = [self.create_item(k) for k in ('Ocean City Bus Pass', 'Crystaldream Lake Map', 'Big Moist Swamp Pass', 'Gray County Rail Ticket', 'Black Gold Oil Permit', 'Government Valley Clearance', 'Partner: Alphonse', 'Partner: Gabby', 'Partner: Molly', 'Partner: Barker', 'Partner: Obie', 'Partner: Simone', 'Partner: Adams', 'Hobo Glyph Decoder', 'Shadow Taint Ward', 'Lockpicking Kit')]
        for st in ('Progressive Muscle', 'Progressive Mysticality', 'Progressive Moxie', 'Progressive Maximum HP', 'Progressive Maximum AP'):
            pool.extend(self.create_item(st) for _ in range(4))
        total = len(self.multiworld.get_locations(self.player))
        fillers = ['Meat Pouch (+250 Meat)', 'Big Meat Stash (+1,000 Meat)', 'Shadow Booze Ration']
        while len(pool) < total:
            pool.append(self.create_item(fillers[len(pool) % len(fillers)]))
        self.multiworld.itempool.extend(pool)

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: state.has('Government Valley Clearance', self.player) and state.has('Shadow Taint Ward', self.player)
