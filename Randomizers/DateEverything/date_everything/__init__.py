from typing import Dict, List
from BaseClasses import Region, ItemClassification, Tutorial
from worlds.AutoWorld import World, WebWorld
from .Options import DateEverythingOptions
from .Items import DateEverythingItem, ITEM_TABLE
from .Locations import DateEverythingLocation, LOCATION_TABLE

class DateEverythingWeb(WebWorld):
    theme = 'partyTime'
    tutorials = [Tutorial('Setup Guide', 'Setup Date Everything.', 'English', 'setup_en.md', 'setup/en', ['SoT_Rando'])]

class DateEverythingWorld(World):
    game = 'Date Everything'
    web = DateEverythingWeb()
    options_dataclass = DateEverythingOptions
    options: DateEverythingOptions
    item_name_to_id: Dict[str, int] = ITEM_TABLE
    location_name_to_id: Dict[str, int] = LOCATION_TABLE

    def create_item(self, name: str) -> DateEverythingItem:
        code = self.item_name_to_id[name]
        cls = ItemClassification.progression if code < 20020 else (ItemClassification.useful if code < 20030 else ItemClassification.filler)
        return DateEverythingItem(name, cls, code, self.player)

    def create_regions(self) -> None:
        menu = Region('Menu', self.player, self.multiworld)
        reg_names = ['Living Room & Hallway', 'Kitchen & Dining', 'Bedroom & Closet', 'Bathroom & Laundry', 'Basement & Attic']
        regs = {r: Region(r, self.player, self.multiworld) for r in reg_names}
        self.multiworld.regions.extend([menu] + list(regs.values()))
        loc_regs = {'Dateable Ending #001': 'Living Room & Hallway', 'Dateable Ending #002': 'Kitchen & Dining', 'Dateable Ending #003': 'Bedroom & Closet', 'Dateable Ending #004': 'Bathroom & Laundry', 'Dateable Ending #005': 'Basement & Attic', 'Dateable Ending #006': 'Living Room & Hallway', 'Dateable Ending #007': 'Kitchen & Dining', 'Dateable Ending #008': 'Bedroom & Closet', 'Dateable Ending #009': 'Bathroom & Laundry', 'Dateable Ending #010': 'Basement & Attic', 'Dateable Ending #011': 'Living Room & Hallway', 'Dateable Ending #012': 'Kitchen & Dining', 'Dateable Ending #013': 'Bedroom & Closet', 'Dateable Ending #014': 'Bathroom & Laundry', 'Dateable Ending #015': 'Basement & Attic', 'Dateable Ending #016': 'Living Room & Hallway', 'Dateable Ending #017': 'Kitchen & Dining', 'Dateable Ending #018': 'Bedroom & Closet', 'Dateable Ending #019': 'Bathroom & Laundry', 'Dateable Ending #020': 'Basement & Attic', 'Dateable Ending #021': 'Living Room & Hallway', 'Dateable Ending #022': 'Kitchen & Dining', 'Dateable Ending #023': 'Bedroom & Closet', 'Dateable Ending #024': 'Bathroom & Laundry', 'Dateable Ending #025': 'Basement & Attic', 'Dateable Ending #026': 'Living Room & Hallway', 'Dateable Ending #027': 'Kitchen & Dining', 'Dateable Ending #028': 'Bedroom & Closet', 'Dateable Ending #029': 'Bathroom & Laundry', 'Dateable Ending #030': 'Basement & Attic', 'Dateable Ending #031': 'Living Room & Hallway', 'Dateable Ending #032': 'Kitchen & Dining', 'Dateable Ending #033': 'Bedroom & Closet', 'Dateable Ending #034': 'Bathroom & Laundry', 'Dateable Ending #035': 'Basement & Attic', 'Dateable Ending #036': 'Living Room & Hallway', 'Dateable Ending #037': 'Kitchen & Dining', 'Dateable Ending #038': 'Bedroom & Closet', 'Dateable Ending #039': 'Bathroom & Laundry', 'Dateable Ending #040': 'Basement & Attic', 'Dateable Ending #041': 'Living Room & Hallway', 'Dateable Ending #042': 'Kitchen & Dining', 'Dateable Ending #043': 'Bedroom & Closet', 'Dateable Ending #044': 'Bathroom & Laundry', 'Dateable Ending #045': 'Basement & Attic', 'Dateable Ending #046': 'Living Room & Hallway', 'Dateable Ending #047': 'Kitchen & Dining', 'Dateable Ending #048': 'Bedroom & Closet', 'Dateable Ending #049': 'Bathroom & Laundry', 'Dateable Ending #050': 'Basement & Attic', 'Dateable Ending #051': 'Living Room & Hallway', 'Dateable Ending #052': 'Kitchen & Dining', 'Dateable Ending #053': 'Bedroom & Closet', 'Dateable Ending #054': 'Bathroom & Laundry', 'Dateable Ending #055': 'Basement & Attic', 'Dateable Ending #056': 'Living Room & Hallway', 'Dateable Ending #057': 'Kitchen & Dining', 'Dateable Ending #058': 'Bedroom & Closet', 'Dateable Ending #059': 'Bathroom & Laundry', 'Dateable Ending #060': 'Basement & Attic', 'Dateable Ending #061': 'Living Room & Hallway', 'Dateable Ending #062': 'Kitchen & Dining', 'Dateable Ending #063': 'Bedroom & Closet', 'Dateable Ending #064': 'Bathroom & Laundry', 'Dateable Ending #065': 'Basement & Attic', 'Dateable Ending #066': 'Living Room & Hallway', 'Dateable Ending #067': 'Kitchen & Dining', 'Dateable Ending #068': 'Bedroom & Closet', 'Dateable Ending #069': 'Bathroom & Laundry', 'Dateable Ending #070': 'Basement & Attic', 'Dateable Ending #071': 'Living Room & Hallway', 'Dateable Ending #072': 'Kitchen & Dining', 'Dateable Ending #073': 'Bedroom & Closet', 'Dateable Ending #074': 'Bathroom & Laundry', 'Dateable Ending #075': 'Basement & Attic', 'Dateable Ending #076': 'Living Room & Hallway', 'Dateable Ending #077': 'Kitchen & Dining', 'Dateable Ending #078': 'Bedroom & Closet', 'Dateable Ending #079': 'Bathroom & Laundry', 'Dateable Ending #080': 'Basement & Attic', 'Dateable Ending #081': 'Living Room & Hallway', 'Dateable Ending #082': 'Kitchen & Dining', 'Dateable Ending #083': 'Bedroom & Closet', 'Dateable Ending #084': 'Bathroom & Laundry', 'Dateable Ending #085': 'Basement & Attic', 'Dateable Ending #086': 'Living Room & Hallway', 'Dateable Ending #087': 'Kitchen & Dining', 'Dateable Ending #088': 'Bedroom & Closet', 'Dateable Ending #089': 'Bathroom & Laundry', 'Dateable Ending #090': 'Basement & Attic', 'Dateable Ending #091': 'Living Room & Hallway', 'Dateable Ending #092': 'Kitchen & Dining', 'Dateable Ending #093': 'Bedroom & Closet', 'Dateable Ending #094': 'Bathroom & Laundry', 'Dateable Ending #095': 'Basement & Attic', 'Dateable Ending #096': 'Living Room & Hallway', 'Dateable Ending #097': 'Kitchen & Dining', 'Dateable Ending #098': 'Bedroom & Closet', 'Dateable Ending #099': 'Bathroom & Laundry', 'Dateable Ending #100': 'Basement & Attic', 'SPECS Milestone #01': 'Living Room & Hallway', 'SPECS Milestone #02': 'Kitchen & Dining', 'SPECS Milestone #03': 'Bedroom & Closet', 'SPECS Milestone #04': 'Bathroom & Laundry', 'SPECS Milestone #05': 'Basement & Attic', 'SPECS Milestone #06': 'Living Room & Hallway', 'SPECS Milestone #07': 'Kitchen & Dining', 'SPECS Milestone #08': 'Bedroom & Closet', 'SPECS Milestone #09': 'Bathroom & Laundry', 'SPECS Milestone #10': 'Basement & Attic', 'SPECS Milestone #11': 'Living Room & Hallway', 'SPECS Milestone #12': 'Kitchen & Dining', 'SPECS Milestone #13': 'Bedroom & Closet', 'SPECS Milestone #14': 'Bathroom & Laundry', 'SPECS Milestone #15': 'Basement & Attic', 'SPECS Milestone #16': 'Living Room & Hallway', 'SPECS Milestone #17': 'Kitchen & Dining', 'SPECS Milestone #18': 'Bedroom & Closet', 'SPECS Milestone #19': 'Bathroom & Laundry', 'SPECS Milestone #20': 'Basement & Attic'}
        for loc_name, loc_id in LOCATION_TABLE.items():
            r_obj = regs[loc_regs[loc_name]]
            r_obj.locations.append(DateEverythingLocation(self.player, loc_name, loc_id, r_obj))
        menu.connect(regs[reg_names[0]])
        regs['Living Room & Hallway'].connect(regs['Kitchen & Dining'], rule=lambda state: state.has('Kitchen Key', self.player))
        regs['Living Room & Hallway'].connect(regs['Bedroom & Closet'], rule=lambda state: state.has('Bedroom Key', self.player))
        regs['Bedroom & Closet'].connect(regs['Bathroom & Laundry'], rule=lambda state: state.has('Bathroom Key', self.player))
        regs['Living Room & Hallway'].connect(regs['Basement & Attic'], rule=lambda state: state.has('Attic & Basement Key', self.player))

    def create_items(self) -> None:
        pool: List[DateEverythingItem] = []
        spec = [('Kitchen Key', 1), ('Bedroom Key', 1), ('Bathroom Key', 1), ('Attic & Basement Key', 1), ('Dateviator Battery Upgrade', 4), ('Progressive Smarts (+10)', 3), ('Progressive Poise (+10)', 3), ('Progressive Empathy (+10)', 3), ('Progressive Charm (+10)', 3), ('Progressive Sass (+10)', 3)]
        for name, cnt in spec:
            pool.extend(self.create_item(name) for _ in range(cnt))
        total = len(self.multiworld.get_locations(self.player))
        fillers = ['Love Letter Keepsake', 'Dateviator Recharge Token', 'Cozy Room Trinket']
        while len(pool) < total:
            pool.append(self.create_item(fillers[len(pool) % len(fillers)]))
        self.multiworld.itempool.extend(pool)

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: state.has('Attic & Basement Key', self.player)
