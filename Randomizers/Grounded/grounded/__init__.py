from typing import Dict, List
from BaseClasses import Region, ItemClassification, Tutorial
from worlds.AutoWorld import World, WebWorld
from .Options import GroundedOptions
from .Items import GroundedItem, ITEM_TABLE
from .Locations import GroundedLocation, LOCATION_TABLE

class GroundedWeb(WebWorld):
    theme = 'grass'
    tutorials = [Tutorial('Setup Guide', 'Setup Grounded.', 'English', 'setup_en.md', 'setup/en', ['SoT_Rando'])]

class GroundedWorld(World):
    game = 'Grounded'
    web = GroundedWeb()
    options_dataclass = GroundedOptions
    options: GroundedOptions
    item_name_to_id: Dict[str, int] = ITEM_TABLE
    location_name_to_id: Dict[str, int] = LOCATION_TABLE

    def create_item(self, name: str) -> GroundedItem:
        code = self.item_name_to_id[name]
        cls = ItemClassification.progression if code < 20020 else (ItemClassification.useful if code < 20030 else ItemClassification.filler)
        return GroundedItem(name, cls, code, self.player)

    def create_regions(self) -> None:
        menu = Region('Menu', self.player, self.multiworld)
        reg_names = ['Lower Yard & Oak Lab', 'Hedge Lab', 'Pond Lab', 'Haze Lab', 'Black Anthill Lab', 'Upper Yard & Undershed']
        regs = {r: Region(r, self.player, self.multiworld) for r in reg_names}
        self.multiworld.regions.extend([menu] + list(regs.values()))
        loc_regs = {'BURG.L Chip & Lab Milestone #01': 'Lower Yard & Oak Lab', 'BURG.L Chip & Lab Milestone #02': 'Hedge Lab', 'BURG.L Chip & Lab Milestone #03': 'Pond Lab', 'BURG.L Chip & Lab Milestone #04': 'Haze Lab', 'BURG.L Chip & Lab Milestone #05': 'Black Anthill Lab', 'BURG.L Chip & Lab Milestone #06': 'Upper Yard & Undershed', 'BURG.L Chip & Lab Milestone #07': 'Lower Yard & Oak Lab', 'BURG.L Chip & Lab Milestone #08': 'Hedge Lab', 'BURG.L Chip & Lab Milestone #09': 'Pond Lab', 'BURG.L Chip & Lab Milestone #10': 'Haze Lab', 'BURG.L Chip & Lab Milestone #11': 'Black Anthill Lab', 'BURG.L Chip & Lab Milestone #12': 'Upper Yard & Undershed', 'BURG.L Chip & Lab Milestone #13': 'Lower Yard & Oak Lab', 'BURG.L Chip & Lab Milestone #14': 'Hedge Lab', 'BURG.L Chip & Lab Milestone #15': 'Pond Lab', 'BURG.L Chip & Lab Milestone #16': 'Haze Lab', 'BURG.L Chip & Lab Milestone #17': 'Black Anthill Lab', 'BURG.L Chip & Lab Milestone #18': 'Upper Yard & Undershed', 'BURG.L Chip & Lab Milestone #19': 'Lower Yard & Oak Lab', 'BURG.L Chip & Lab Milestone #20': 'Hedge Lab', 'BURG.L Chip & Lab Milestone #21': 'Pond Lab', 'BURG.L Chip & Lab Milestone #22': 'Haze Lab', 'BURG.L Chip & Lab Milestone #23': 'Black Anthill Lab', 'BURG.L Chip & Lab Milestone #24': 'Upper Yard & Undershed', 'BURG.L Chip & Lab Milestone #25': 'Lower Yard & Oak Lab', 'BURG.L Chip & Lab Milestone #26': 'Hedge Lab', 'BURG.L Chip & Lab Milestone #27': 'Pond Lab', 'BURG.L Chip & Lab Milestone #28': 'Haze Lab', 'BURG.L Chip & Lab Milestone #29': 'Black Anthill Lab', 'BURG.L Chip & Lab Milestone #30': 'Upper Yard & Undershed', 'Milk Molar Collected #01': 'Lower Yard & Oak Lab', 'Milk Molar Collected #02': 'Hedge Lab', 'Milk Molar Collected #03': 'Pond Lab', 'Milk Molar Collected #04': 'Haze Lab', 'Milk Molar Collected #05': 'Black Anthill Lab', 'Milk Molar Collected #06': 'Upper Yard & Undershed', 'Milk Molar Collected #07': 'Lower Yard & Oak Lab', 'Milk Molar Collected #08': 'Hedge Lab', 'Milk Molar Collected #09': 'Pond Lab', 'Milk Molar Collected #10': 'Haze Lab', 'Milk Molar Collected #11': 'Black Anthill Lab', 'Milk Molar Collected #12': 'Upper Yard & Undershed', 'Milk Molar Collected #13': 'Lower Yard & Oak Lab', 'Milk Molar Collected #14': 'Hedge Lab', 'Milk Molar Collected #15': 'Pond Lab', 'Milk Molar Collected #16': 'Haze Lab', 'Milk Molar Collected #17': 'Black Anthill Lab', 'Milk Molar Collected #18': 'Upper Yard & Undershed', 'Milk Molar Collected #19': 'Lower Yard & Oak Lab', 'Milk Molar Collected #20': 'Hedge Lab', 'Milk Molar Collected #21': 'Pond Lab', 'Milk Molar Collected #22': 'Haze Lab', 'Milk Molar Collected #23': 'Black Anthill Lab', 'Milk Molar Collected #24': 'Upper Yard & Undershed', 'Milk Molar Collected #25': 'Lower Yard & Oak Lab', 'Milk Molar Collected #26': 'Hedge Lab', 'Milk Molar Collected #27': 'Pond Lab', 'Milk Molar Collected #28': 'Haze Lab', 'Milk Molar Collected #29': 'Black Anthill Lab', 'Milk Molar Collected #30': 'Upper Yard & Undershed', 'Milk Molar Collected #31': 'Lower Yard & Oak Lab', 'Milk Molar Collected #32': 'Hedge Lab', 'Milk Molar Collected #33': 'Pond Lab', 'Milk Molar Collected #34': 'Haze Lab', 'Milk Molar Collected #35': 'Black Anthill Lab', 'Milk Molar Collected #36': 'Upper Yard & Undershed', 'Milk Molar Collected #37': 'Lower Yard & Oak Lab', 'Milk Molar Collected #38': 'Hedge Lab', 'Milk Molar Collected #39': 'Pond Lab', 'Milk Molar Collected #40': 'Haze Lab', 'Milk Molar Collected #41': 'Black Anthill Lab', 'Milk Molar Collected #42': 'Upper Yard & Undershed', 'Milk Molar Collected #43': 'Lower Yard & Oak Lab', 'Milk Molar Collected #44': 'Hedge Lab', 'Milk Molar Collected #45': 'Pond Lab', 'Milk Molar Collected #46': 'Haze Lab', 'Milk Molar Collected #47': 'Black Anthill Lab', 'Milk Molar Collected #48': 'Upper Yard & Undershed', 'Milk Molar Collected #49': 'Lower Yard & Oak Lab', 'Milk Molar Collected #50': 'Hedge Lab', 'MIX.R & Yard Boss #01': 'Lower Yard & Oak Lab', 'MIX.R & Yard Boss #02': 'Hedge Lab', 'MIX.R & Yard Boss #03': 'Pond Lab', 'MIX.R & Yard Boss #04': 'Haze Lab', 'MIX.R & Yard Boss #05': 'Black Anthill Lab', 'MIX.R & Yard Boss #06': 'Upper Yard & Undershed', 'MIX.R & Yard Boss #07': 'Lower Yard & Oak Lab', 'MIX.R & Yard Boss #08': 'Hedge Lab', 'MIX.R & Yard Boss #09': 'Pond Lab', 'MIX.R & Yard Boss #10': 'Haze Lab', 'MIX.R & Yard Boss #11': 'Black Anthill Lab', 'MIX.R & Yard Boss #12': 'Upper Yard & Undershed', 'MIX.R & Yard Boss #13': 'Lower Yard & Oak Lab', 'MIX.R & Yard Boss #14': 'Hedge Lab', 'MIX.R & Yard Boss #15': 'Pond Lab', 'MIX.R & Yard Boss #16': 'Haze Lab', 'MIX.R & Yard Boss #17': 'Black Anthill Lab', 'MIX.R & Yard Boss #18': 'Upper Yard & Undershed', 'MIX.R & Yard Boss #19': 'Lower Yard & Oak Lab', 'MIX.R & Yard Boss #20': 'Hedge Lab'}
        for loc_name, loc_id in LOCATION_TABLE.items():
            r_obj = regs[loc_regs[loc_name]]
            r_obj.locations.append(GroundedLocation(self.player, loc_name, loc_id, r_obj))
        menu.connect(regs[reg_names[0]])
        regs['Lower Yard & Oak Lab'].connect(regs['Hedge Lab'], rule=lambda state: state.has('Hedge Lab Keycard', self.player))
        regs['Lower Yard & Oak Lab'].connect(regs['Pond Lab'], rule=lambda state: state.has('Pond Lab Keycard', self.player))
        regs['Hedge Lab'].connect(regs['Haze Lab'], rule=lambda state: state.has('Haze Lab Keycard', self.player))
        regs['Haze Lab'].connect(regs['Black Anthill Lab'], rule=lambda state: state.has('Black Anthill Keycard', self.player))
        regs['Black Anthill Lab'].connect(regs['Upper Yard & Undershed'], rule=lambda state: state.has('Undershed Lab Keycard', self.player))

    def create_items(self) -> None:
        pool: List[GroundedItem] = []
        spec = [('Hedge Lab Keycard', 1), ('Pond Lab Keycard', 1), ('Haze Lab Keycard', 1), ('Black Anthill Keycard', 1), ('Undershed Lab Keycard', 1), ('Tier II Omni-Tool Permit', 1), ('Tier III Omni-Tool Permit', 1), ('Progressive Mutation Slot', 4), ('Milk Molar Stat Upgrade', 8)]
        for name, cnt in spec:
            pool.extend(self.create_item(name) for _ in range(cnt))
        total = len(self.multiworld.get_locations(self.player))
        fillers = ['Raw Science Cache (+500 RS)', 'BURG.L Science Grant (+1,500 RS)', 'Berry Leather Bundle']
        while len(pool) < total:
            pool.append(self.create_item(fillers[len(pool) % len(fillers)]))
        self.multiworld.itempool.extend(pool)

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: state.has('Undershed Lab Keycard', self.player)
