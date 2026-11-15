from typing import Dict, List
from BaseClasses import Region, ItemClassification, Tutorial
from worlds.AutoWorld import World, WebWorld
from .Options import PapersPleaseOptions
from .Items import PapersPleaseItem, ITEM_TABLE
from .Locations import PapersPleaseLocation, LOCATION_TABLE

class PapersPleaseWeb(WebWorld):
    theme = 'stone'
    tutorials = [Tutorial('Setup Guide', 'Setup Papers, Please.', 'English', 'setup_en.md', 'setup/en', ['SoT_Rando'])]

class PapersPleaseWorld(World):
    game = 'Papers, Please'
    web = PapersPleaseWeb()
    options_dataclass = PapersPleaseOptions
    options: PapersPleaseOptions
    item_name_to_id: Dict[str, int] = ITEM_TABLE
    location_name_to_id: Dict[str, int] = LOCATION_TABLE

    def create_item(self, name: str) -> PapersPleaseItem:
        code = self.item_name_to_id[name]
        cls = ItemClassification.progression if code < 20020 else (ItemClassification.useful if code < 20030 else ItemClassification.filler)
        return PapersPleaseItem(name, cls, code, self.player)

    def create_regions(self) -> None:
        menu = Region('Menu', self.player, self.multiworld)
        reg_names = ['Week 1 (Days 1-7)', 'Week 2 (Days 8-14)', 'Week 3 (Days 15-21)', 'Week 4 (Days 22-31)']
        regs = {r: Region(r, self.player, self.multiworld) for r in reg_names}
        self.multiworld.regions.extend([menu] + list(regs.values()))
        loc_regs = {'Shift Complete - Day 01': 'Week 1 (Days 1-7)', 'Shift Complete - Day 02': 'Week 1 (Days 1-7)', 'Shift Complete - Day 03': 'Week 1 (Days 1-7)', 'Shift Complete - Day 04': 'Week 1 (Days 1-7)', 'Shift Complete - Day 05': 'Week 1 (Days 1-7)', 'Shift Complete - Day 06': 'Week 1 (Days 1-7)', 'Shift Complete - Day 07': 'Week 1 (Days 1-7)', 'Shift Complete - Day 08': 'Week 2 (Days 8-14)', 'Shift Complete - Day 09': 'Week 2 (Days 8-14)', 'Shift Complete - Day 10': 'Week 2 (Days 8-14)', 'Shift Complete - Day 11': 'Week 2 (Days 8-14)', 'Shift Complete - Day 12': 'Week 2 (Days 8-14)', 'Shift Complete - Day 13': 'Week 2 (Days 8-14)', 'Shift Complete - Day 14': 'Week 2 (Days 8-14)', 'Shift Complete - Day 15': 'Week 3 (Days 15-21)', 'Shift Complete - Day 16': 'Week 3 (Days 15-21)', 'Shift Complete - Day 17': 'Week 3 (Days 15-21)', 'Shift Complete - Day 18': 'Week 3 (Days 15-21)', 'Shift Complete - Day 19': 'Week 3 (Days 15-21)', 'Shift Complete - Day 20': 'Week 3 (Days 15-21)', 'Shift Complete - Day 21': 'Week 3 (Days 15-21)', 'Shift Complete - Day 22': 'Week 4 (Days 22-31)', 'Shift Complete - Day 23': 'Week 4 (Days 22-31)', 'Shift Complete - Day 24': 'Week 4 (Days 22-31)', 'Shift Complete - Day 25': 'Week 4 (Days 22-31)', 'Shift Complete - Day 26': 'Week 4 (Days 22-31)', 'Shift Complete - Day 27': 'Week 4 (Days 22-31)', 'Shift Complete - Day 28': 'Week 4 (Days 22-31)', 'Shift Complete - Day 29': 'Week 4 (Days 22-31)', 'Shift Complete - Day 30': 'Week 4 (Days 22-31)', 'Shift Complete - Day 31': 'Week 4 (Days 22-31)', 'Country Token & Special Entrant #01': 'Week 1 (Days 1-7)', 'Country Token & Special Entrant #02': 'Week 2 (Days 8-14)', 'Country Token & Special Entrant #03': 'Week 3 (Days 15-21)', 'Country Token & Special Entrant #04': 'Week 4 (Days 22-31)', 'Country Token & Special Entrant #05': 'Week 1 (Days 1-7)', 'Country Token & Special Entrant #06': 'Week 2 (Days 8-14)', 'Country Token & Special Entrant #07': 'Week 3 (Days 15-21)', 'Country Token & Special Entrant #08': 'Week 4 (Days 22-31)', 'Country Token & Special Entrant #09': 'Week 1 (Days 1-7)', 'Country Token & Special Entrant #10': 'Week 2 (Days 8-14)', 'Country Token & Special Entrant #11': 'Week 3 (Days 15-21)', 'Country Token & Special Entrant #12': 'Week 4 (Days 22-31)', 'Country Token & Special Entrant #13': 'Week 1 (Days 1-7)', 'Country Token & Special Entrant #14': 'Week 2 (Days 8-14)', 'Country Token & Special Entrant #15': 'Week 3 (Days 15-21)', 'Country Token & Special Entrant #16': 'Week 4 (Days 22-31)', 'Country Token & Special Entrant #17': 'Week 1 (Days 1-7)', 'Country Token & Special Entrant #18': 'Week 2 (Days 8-14)', 'Country Token & Special Entrant #19': 'Week 3 (Days 15-21)', 'Country Token & Special Entrant #20': 'Week 4 (Days 22-31)', 'Country Token & Special Entrant #21': 'Week 1 (Days 1-7)', 'Country Token & Special Entrant #22': 'Week 2 (Days 8-14)', 'Country Token & Special Entrant #23': 'Week 3 (Days 15-21)', 'Country Token & Special Entrant #24': 'Week 4 (Days 22-31)', 'EZIC & Ending Milestone #01': 'Week 1 (Days 1-7)', 'EZIC & Ending Milestone #02': 'Week 2 (Days 8-14)', 'EZIC & Ending Milestone #03': 'Week 3 (Days 15-21)', 'EZIC & Ending Milestone #04': 'Week 4 (Days 22-31)', 'EZIC & Ending Milestone #05': 'Week 1 (Days 1-7)', 'EZIC & Ending Milestone #06': 'Week 2 (Days 8-14)', 'EZIC & Ending Milestone #07': 'Week 3 (Days 15-21)', 'EZIC & Ending Milestone #08': 'Week 4 (Days 22-31)', 'EZIC & Ending Milestone #09': 'Week 1 (Days 1-7)', 'EZIC & Ending Milestone #10': 'Week 2 (Days 8-14)', 'EZIC & Ending Milestone #11': 'Week 3 (Days 15-21)', 'EZIC & Ending Milestone #12': 'Week 4 (Days 22-31)', 'EZIC & Ending Milestone #13': 'Week 1 (Days 1-7)', 'EZIC & Ending Milestone #14': 'Week 2 (Days 8-14)'}
        for loc_name, loc_id in LOCATION_TABLE.items():
            r_obj = regs[loc_regs[loc_name]]
            r_obj.locations.append(PapersPleaseLocation(self.player, loc_name, loc_id, r_obj))
        menu.connect(regs[reg_names[0]])
        regs['Week 1 (Days 1-7)'].connect(regs['Week 2 (Days 8-14)'], rule=lambda state: state.has('Week 2 Border Directive', self.player))
        regs['Week 2 (Days 8-14)'].connect(regs['Week 3 (Days 15-21)'], rule=lambda state: state.has('Week 3 Border Directive', self.player))
        regs['Week 3 (Days 15-21)'].connect(regs['Week 4 (Days 22-31)'], rule=lambda state: state.has('Week 4 Border Directive', self.player))

    def create_items(self) -> None:
        pool: List[PapersPleaseItem] = []
        spec = [('Week 2 Border Directive', 1), ('Week 3 Border Directive', 1), ('Week 4 Border Directive', 1), ('Booth Upgrade: Audio Transcript', 1), ('Booth Upgrade: Discrepancy Detector', 1), ('Booth Upgrade: Key & Dart Gun', 1), ('Booth Upgrade: Thermal Scanner', 1), ('Progressive Apartment Class', 4), ('EZIC Cipher Note', 3)]
        for name, cnt in spec:
            pool.extend(self.create_item(name) for _ in range(cnt))
        total = len(self.multiworld.get_locations(self.player))
        fillers = ['Ministry Bonus (+20 Credits)', 'Heating & Food Voucher', 'Arstotzkan Plaque']
        while len(pool) < total:
            pool.append(self.create_item(fillers[len(pool) % len(fillers)]))
        self.multiworld.itempool.extend(pool)

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: state.has('Week 4 Border Directive', self.player)
