from typing import Dict, List
from BaseClasses import Region, ItemClassification, Tutorial
from worlds.AutoWorld import World, WebWorld
from .Options import TreasureHunterOptions
from .Items import TreasureHunterItem, ITEM_TABLE
from .Locations import TreasureHunterLocation, LOCATION_TABLE

class TreasureHunterWeb(WebWorld):
    theme = 'grass'
    tutorials = [Tutorial('Setup Guide', 'Setup Treasure Hunter Simulator.', 'English', 'setup_en.md', 'setup/en', ['SoT_Rando'])]

class TreasureHunterWorld(World):
    game = 'Treasure Hunter Simulator'
    web = TreasureHunterWeb()
    options_dataclass = TreasureHunterOptions
    options: TreasureHunterOptions
    item_name_to_id: Dict[str, int] = ITEM_TABLE
    location_name_to_id: Dict[str, int] = LOCATION_TABLE

    def create_item(self, name: str) -> TreasureHunterItem:
        code = self.item_name_to_id[name]
        cls = ItemClassification.progression if code < 20020 else (ItemClassification.useful if code < 20030 else ItemClassification.filler)
        return TreasureHunterItem(name, cls, code, self.player)

    def create_regions(self) -> None:
        menu = Region('Menu', self.player, self.multiworld)
        reg_names = ['Bavarian Forest', 'Scottish Highlands', 'Sahara Desert', 'Eastern Front', 'Pacific Atoll', 'Mayan Jungle']
        regs = {r: Region(r, self.player, self.multiworld) for r in reg_names}
        self.multiworld.regions.extend([menu] + list(regs.values()))
        loc_regs = {'Artifact Recovered #01': 'Bavarian Forest', 'Artifact Recovered #02': 'Scottish Highlands', 'Artifact Recovered #03': 'Sahara Desert', 'Artifact Recovered #04': 'Eastern Front', 'Artifact Recovered #05': 'Pacific Atoll', 'Artifact Recovered #06': 'Mayan Jungle', 'Artifact Recovered #07': 'Bavarian Forest', 'Artifact Recovered #08': 'Scottish Highlands', 'Artifact Recovered #09': 'Sahara Desert', 'Artifact Recovered #10': 'Eastern Front', 'Artifact Recovered #11': 'Pacific Atoll', 'Artifact Recovered #12': 'Mayan Jungle', 'Artifact Recovered #13': 'Bavarian Forest', 'Artifact Recovered #14': 'Scottish Highlands', 'Artifact Recovered #15': 'Sahara Desert', 'Artifact Recovered #16': 'Eastern Front', 'Artifact Recovered #17': 'Pacific Atoll', 'Artifact Recovered #18': 'Mayan Jungle', 'Artifact Recovered #19': 'Bavarian Forest', 'Artifact Recovered #20': 'Scottish Highlands', 'Artifact Recovered #21': 'Sahara Desert', 'Artifact Recovered #22': 'Eastern Front', 'Artifact Recovered #23': 'Pacific Atoll', 'Artifact Recovered #24': 'Mayan Jungle', 'Artifact Recovered #25': 'Bavarian Forest', 'Artifact Recovered #26': 'Scottish Highlands', 'Artifact Recovered #27': 'Sahara Desert', 'Artifact Recovered #28': 'Eastern Front', 'Artifact Recovered #29': 'Pacific Atoll', 'Artifact Recovered #30': 'Mayan Jungle', 'Artifact Recovered #31': 'Bavarian Forest', 'Artifact Recovered #32': 'Scottish Highlands', 'Artifact Recovered #33': 'Sahara Desert', 'Artifact Recovered #34': 'Eastern Front', 'Artifact Recovered #35': 'Pacific Atoll', 'Artifact Recovered #36': 'Mayan Jungle', 'Artifact Recovered #37': 'Bavarian Forest', 'Artifact Recovered #38': 'Scottish Highlands', 'Artifact Recovered #39': 'Sahara Desert', 'Artifact Recovered #40': 'Eastern Front', 'Artifact Recovered #41': 'Pacific Atoll', 'Artifact Recovered #42': 'Mayan Jungle', 'Artifact Recovered #43': 'Bavarian Forest', 'Artifact Recovered #44': 'Scottish Highlands', 'Artifact Recovered #45': 'Sahara Desert', 'Artifact Recovered #46': 'Eastern Front', 'Artifact Recovered #47': 'Pacific Atoll', 'Artifact Recovered #48': 'Mayan Jungle', 'Artifact Recovered #49': 'Bavarian Forest', 'Artifact Recovered #50': 'Scottish Highlands', 'Artifact Recovered #51': 'Sahara Desert', 'Artifact Recovered #52': 'Eastern Front', 'Artifact Recovered #53': 'Pacific Atoll', 'Artifact Recovered #54': 'Mayan Jungle', 'Artifact Recovered #55': 'Bavarian Forest', 'Artifact Recovered #56': 'Scottish Highlands', 'Artifact Recovered #57': 'Sahara Desert', 'Artifact Recovered #58': 'Eastern Front', 'Artifact Recovered #59': 'Pacific Atoll', 'Artifact Recovered #60': 'Mayan Jungle', 'Client Mail Contract #01': 'Bavarian Forest', 'Client Mail Contract #02': 'Scottish Highlands', 'Client Mail Contract #03': 'Sahara Desert', 'Client Mail Contract #04': 'Eastern Front', 'Client Mail Contract #05': 'Pacific Atoll', 'Client Mail Contract #06': 'Mayan Jungle', 'Client Mail Contract #07': 'Bavarian Forest', 'Client Mail Contract #08': 'Scottish Highlands', 'Client Mail Contract #09': 'Sahara Desert', 'Client Mail Contract #10': 'Eastern Front', 'Client Mail Contract #11': 'Pacific Atoll', 'Client Mail Contract #12': 'Mayan Jungle', 'Client Mail Contract #13': 'Bavarian Forest', 'Client Mail Contract #14': 'Scottish Highlands', 'Client Mail Contract #15': 'Sahara Desert', 'Client Mail Contract #16': 'Eastern Front', 'Client Mail Contract #17': 'Pacific Atoll', 'Client Mail Contract #18': 'Mayan Jungle', 'Client Mail Contract #19': 'Bavarian Forest', 'Client Mail Contract #20': 'Scottish Highlands', 'Client Mail Contract #21': 'Sahara Desert', 'Client Mail Contract #22': 'Eastern Front', 'Client Mail Contract #23': 'Pacific Atoll', 'Client Mail Contract #24': 'Mayan Jungle', 'Prestige Level 01': 'Bavarian Forest', 'Prestige Level 02': 'Scottish Highlands', 'Prestige Level 03': 'Scottish Highlands', 'Prestige Level 04': 'Sahara Desert', 'Prestige Level 05': 'Sahara Desert', 'Prestige Level 06': 'Eastern Front', 'Prestige Level 07': 'Eastern Front', 'Prestige Level 08': 'Pacific Atoll', 'Prestige Level 09': 'Pacific Atoll', 'Prestige Level 10': 'Mayan Jungle'}
        for loc_name, loc_id in LOCATION_TABLE.items():
            r_obj = regs[loc_regs[loc_name]]
            r_obj.locations.append(TreasureHunterLocation(self.player, loc_name, loc_id, r_obj))
        menu.connect(regs[reg_names[0]])
        regs['Bavarian Forest'].connect(regs['Scottish Highlands'], rule=lambda state: state.has('Highlands Travel Permit', self.player))
        regs['Scottish Highlands'].connect(regs['Sahara Desert'], rule=lambda state: state.has('Sahara Travel Permit', self.player))
        regs['Sahara Desert'].connect(regs['Eastern Front'], rule=lambda state: state.has('Eastern Front Travel Permit', self.player))
        regs['Eastern Front'].connect(regs['Pacific Atoll'], rule=lambda state: state.has('Pacific Atoll Travel Permit', self.player))
        regs['Pacific Atoll'].connect(regs['Mayan Jungle'], rule=lambda state: state.has('Mayan Jungle Travel Permit', self.player))

    def create_items(self) -> None:
        pool: List[TreasureHunterItem] = []
        spec = [('Highlands Travel Permit', 1), ('Sahara Travel Permit', 1), ('Eastern Front Travel Permit', 1), ('Pacific Atoll Travel Permit', 1), ('Mayan Jungle Travel Permit', 1), ('Progressive Metal Detector', 5), ('Progressive Shovel Speed', 4)]
        for name, cnt in spec:
            pool.extend(self.create_item(name) for _ in range(cnt))
        total = len(self.multiworld.get_locations(self.player))
        fillers = ['Auction Payout (+$500)', 'Collector Bonus (+$1,500)', 'Prestige Relic XP']
        while len(pool) < total:
            pool.append(self.create_item(fillers[len(pool) % len(fillers)]))
        self.multiworld.itempool.extend(pool)

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: state.has('Mayan Jungle Travel Permit', self.player)
