from typing import Dict, List
from BaseClasses import Region, ItemClassification, Tutorial
from worlds.AutoWorld import World, WebWorld
from .Options import GraveyardKeeperOptions
from .Items import GraveyardKeeperItem, ITEM_TABLE
from .Locations import GraveyardKeeperLocation, LOCATION_TABLE

class GraveyardKeeperWeb(WebWorld):
    theme = 'dirt'
    tutorials = [Tutorial('Setup Guide', 'Setup Graveyard Keeper.', 'English', 'setup_en.md', 'setup/en', ['SoT_Rando'])]

class GraveyardKeeperWorld(World):
    game = 'Graveyard Keeper'
    web = GraveyardKeeperWeb()
    options_dataclass = GraveyardKeeperOptions
    options: GraveyardKeeperOptions
    item_name_to_id: Dict[str, int] = ITEM_TABLE
    location_name_to_id: Dict[str, int] = LOCATION_TABLE

    def create_item(self, name: str) -> GraveyardKeeperItem:
        code = self.item_name_to_id[name]
        cls = ItemClassification.progression if code < 20020 else (ItemClassification.useful if code < 20030 else ItemClassification.filler)
        return GraveyardKeeperItem(name, cls, code, self.player)

    def create_regions(self) -> None:
        menu = Region('Menu', self.player, self.multiworld)
        reg_names = ['Graveyard & Church', 'The Village', 'Witch Hill & Swamp', 'The Quarry', 'The Dungeon', 'Fort & Town Gate']
        regs = {r: Region(r, self.player, self.multiworld) for r in reg_names}
        self.multiworld.regions.extend([menu] + list(regs.values()))
        loc_regs = {'Technology Unlocked #01': 'Graveyard & Church', 'Technology Unlocked #02': 'The Village', 'Technology Unlocked #03': 'Witch Hill & Swamp', 'Technology Unlocked #04': 'The Quarry', 'Technology Unlocked #05': 'The Dungeon', 'Technology Unlocked #06': 'Fort & Town Gate', 'Technology Unlocked #07': 'Graveyard & Church', 'Technology Unlocked #08': 'The Village', 'Technology Unlocked #09': 'Witch Hill & Swamp', 'Technology Unlocked #10': 'The Quarry', 'Technology Unlocked #11': 'The Dungeon', 'Technology Unlocked #12': 'Fort & Town Gate', 'Technology Unlocked #13': 'Graveyard & Church', 'Technology Unlocked #14': 'The Village', 'Technology Unlocked #15': 'Witch Hill & Swamp', 'Technology Unlocked #16': 'The Quarry', 'Technology Unlocked #17': 'The Dungeon', 'Technology Unlocked #18': 'Fort & Town Gate', 'Technology Unlocked #19': 'Graveyard & Church', 'Technology Unlocked #20': 'The Village', 'Technology Unlocked #21': 'Witch Hill & Swamp', 'Technology Unlocked #22': 'The Quarry', 'Technology Unlocked #23': 'The Dungeon', 'Technology Unlocked #24': 'Fort & Town Gate', 'Technology Unlocked #25': 'Graveyard & Church', 'Technology Unlocked #26': 'The Village', 'Technology Unlocked #27': 'Witch Hill & Swamp', 'Technology Unlocked #28': 'The Quarry', 'Technology Unlocked #29': 'The Dungeon', 'Technology Unlocked #30': 'Fort & Town Gate', 'Technology Unlocked #31': 'Graveyard & Church', 'Technology Unlocked #32': 'The Village', 'Technology Unlocked #33': 'Witch Hill & Swamp', 'Technology Unlocked #34': 'The Quarry', 'Technology Unlocked #35': 'The Dungeon', 'Technology Unlocked #36': 'Fort & Town Gate', 'Technology Unlocked #37': 'Graveyard & Church', 'Technology Unlocked #38': 'The Village', 'Technology Unlocked #39': 'Witch Hill & Swamp', 'Technology Unlocked #40': 'The Quarry', 'Technology Unlocked #41': 'The Dungeon', 'Technology Unlocked #42': 'Fort & Town Gate', 'Technology Unlocked #43': 'Graveyard & Church', 'Technology Unlocked #44': 'The Village', 'Technology Unlocked #45': 'Witch Hill & Swamp', 'Technology Unlocked #46': 'The Quarry', 'Technology Unlocked #47': 'The Dungeon', 'Technology Unlocked #48': 'Fort & Town Gate', 'Technology Unlocked #49': 'Graveyard & Church', 'Technology Unlocked #50': 'The Village', 'Technology Unlocked #51': 'Witch Hill & Swamp', 'Technology Unlocked #52': 'The Quarry', 'Technology Unlocked #53': 'The Dungeon', 'Technology Unlocked #54': 'Fort & Town Gate', 'Technology Unlocked #55': 'Graveyard & Church', 'Technology Unlocked #56': 'The Village', 'Technology Unlocked #57': 'Witch Hill & Swamp', 'Technology Unlocked #58': 'The Quarry', 'Technology Unlocked #59': 'The Dungeon', 'Technology Unlocked #60': 'Fort & Town Gate', 'NPC Quest Milestone #01': 'Graveyard & Church', 'NPC Quest Milestone #02': 'The Village', 'NPC Quest Milestone #03': 'Witch Hill & Swamp', 'NPC Quest Milestone #04': 'The Quarry', 'NPC Quest Milestone #05': 'The Dungeon', 'NPC Quest Milestone #06': 'Fort & Town Gate', 'NPC Quest Milestone #07': 'Graveyard & Church', 'NPC Quest Milestone #08': 'The Village', 'NPC Quest Milestone #09': 'Witch Hill & Swamp', 'NPC Quest Milestone #10': 'The Quarry', 'NPC Quest Milestone #11': 'The Dungeon', 'NPC Quest Milestone #12': 'Fort & Town Gate', 'NPC Quest Milestone #13': 'Graveyard & Church', 'NPC Quest Milestone #14': 'The Village', 'NPC Quest Milestone #15': 'Witch Hill & Swamp', 'NPC Quest Milestone #16': 'The Quarry', 'NPC Quest Milestone #17': 'The Dungeon', 'NPC Quest Milestone #18': 'Fort & Town Gate', 'NPC Quest Milestone #19': 'Graveyard & Church', 'NPC Quest Milestone #20': 'The Village', 'NPC Quest Milestone #21': 'Witch Hill & Swamp', 'NPC Quest Milestone #22': 'The Quarry', 'NPC Quest Milestone #23': 'The Dungeon', 'NPC Quest Milestone #24': 'Fort & Town Gate', 'NPC Quest Milestone #25': 'Graveyard & Church', 'NPC Quest Milestone #26': 'The Village', 'NPC Quest Milestone #27': 'Witch Hill & Swamp', 'NPC Quest Milestone #28': 'The Quarry', 'NPC Quest Milestone #29': 'The Dungeon', 'NPC Quest Milestone #30': 'Fort & Town Gate', 'NPC Quest Milestone #31': 'Graveyard & Church', 'NPC Quest Milestone #32': 'The Village', 'NPC Quest Milestone #33': 'Witch Hill & Swamp', 'NPC Quest Milestone #34': 'The Quarry', 'NPC Quest Milestone #35': 'The Dungeon', 'NPC Quest Milestone #36': 'Fort & Town Gate', 'NPC Quest Milestone #37': 'Graveyard & Church', 'NPC Quest Milestone #38': 'The Village', 'NPC Quest Milestone #39': 'Witch Hill & Swamp', 'NPC Quest Milestone #40': 'The Quarry', 'NPC Quest Milestone #41': 'The Dungeon', 'NPC Quest Milestone #42': 'Fort & Town Gate', 'NPC Quest Milestone #43': 'Graveyard & Church', 'NPC Quest Milestone #44': 'The Village', 'NPC Quest Milestone #45': 'Witch Hill & Swamp', 'Dungeon Floor 01 Cleared': 'The Dungeon', 'Dungeon Floor 02 Cleared': 'The Dungeon', 'Dungeon Floor 03 Cleared': 'The Dungeon', 'Dungeon Floor 04 Cleared': 'The Dungeon', 'Dungeon Floor 05 Cleared': 'The Dungeon', 'Dungeon Floor 06 Cleared': 'The Dungeon', 'Dungeon Floor 07 Cleared': 'The Dungeon', 'Dungeon Floor 08 Cleared': 'The Dungeon', 'Dungeon Floor 09 Cleared': 'The Dungeon', 'Dungeon Floor 10 Cleared': 'The Dungeon', 'Dungeon Floor 11 Cleared': 'The Dungeon', 'Dungeon Floor 12 Cleared': 'The Dungeon', 'Dungeon Floor 13 Cleared': 'The Dungeon', 'Dungeon Floor 14 Cleared': 'The Dungeon', 'Dungeon Floor 15 Cleared': 'The Dungeon'}
        for loc_name, loc_id in LOCATION_TABLE.items():
            r_obj = regs[loc_regs[loc_name]]
            r_obj.locations.append(GraveyardKeeperLocation(self.player, loc_name, loc_id, r_obj))
        menu.connect(regs[reg_names[0]])
        regs['Graveyard & Church'].connect(regs['The Village'])
        regs['The Village'].connect(regs['Witch Hill & Swamp'], rule=lambda state: state.has('Witch Hill Bridge Repair', self.player))
        regs['The Village'].connect(regs['The Quarry'], rule=lambda state: state.has('Quarry Pass', self.player))
        regs['Graveyard & Church'].connect(regs['The Dungeon'], rule=lambda state: state.has('Dungeon Key', self.player))
        regs['The Village'].connect(regs['Fort & Town Gate'], rule=lambda state: state.has('Royal Stamp', self.player))

    def create_items(self) -> None:
        pool: List[GraveyardKeeperItem] = []
        spec = [('Church Key', 1), ('Witch Hill Bridge Repair', 1), ('Quarry Pass', 1), ('Dungeon Key', 1), ('Royal Stamp', 1), ('Town Pass', 1), ('Progressive Tool Upgrade', 4), ('Red Tech Point Bundle (+25)', 5), ('Green Tech Point Bundle (+25)', 5), ('Blue Tech Point Bundle (+25)', 5)]
        for name, cnt in spec:
            pool.extend(self.create_item(name) for _ in range(cnt))
        total = len(self.multiworld.get_locations(self.player))
        fillers = ['Silver Coins (+15 Silver)', 'Faith Bundle (+10 Faith)', 'Gold Coin (+1 Gold)']
        while len(pool) < total:
            pool.append(self.create_item(fillers[len(pool) % len(fillers)]))
        self.multiworld.itempool.extend(pool)

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: state.has('Town Pass', self.player)
