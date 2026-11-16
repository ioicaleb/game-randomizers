from typing import Dict, List
from BaseClasses import Region, ItemClassification, Tutorial
from worlds.AutoWorld import World, WebWorld
from .Options import GroundedOptions
from .Items import GroundedItem, ITEM_TABLE
from .Locations import GroundedLocation, LOCATION_TABLE

RECIPE_ITEMS = ['Recipe: Workbench & Basic Tools', 'Recipe: Grass Plank Building', 'Recipe: Weed Stem Building', 'Recipe: Storage Chest & Basket', 'Recipe: Dew Collector & Canteen', 'Recipe: Roasting Spit & Jerky Rack', 'Recipe: Spinning Wheel & Silk Rope', 'Recipe: Tanning Rack & Berry Leather', 'Recipe: Grinder & Slurry', 'Recipe: Smithing Station & Brittle Whetstone', 'Recipe: Sturdy Whetstone & Plating', 'Recipe: Supreme Whetstone & Plating', 'Recipe: Oven & Mushroom Bricks', 'Recipe: Smoothie Station', 'Recipe: Cookery & Meals', 'Recipe: Zipline Anchor & Silk Rope', 'Recipe: Bounce Web & Elevator', 'Recipe: Sap Catcher', 'Recipe: Acorn Armor Set', 'Recipe: Clover Armor Set', 'Recipe: Grub Armor Set', 'Recipe: Red Ant Armor Set', 'Recipe: Ladybug Armor Set', 'Recipe: Spider Armor Set', 'Recipe: Bee Armor Set', 'Recipe: Koi Scale Armor Set', 'Recipe: Antlion Armor Set', 'Recipe: Black Ox Armor Set', 'Recipe: Roly Poly Armor Set', 'Recipe: Termite Armor & Fin Flops', 'Recipe: Gas Mask & Diving Gear', 'Recipe: Torch & Firefly Headlamp', 'Recipe: Sprig Bow & Arrows', 'Recipe: Insect Bow & Crow Crossbow', 'Recipe: Black Ox Crossbow', 'Recipe: Pebblet Spear & Spike Strip', 'Recipe: Larva Blade & Stinger Spear', 'Recipe: Mosquito Needle & Tiger Rapier', 'Recipe: Red Ant Club & Bone Trident', 'Recipe: Insect Axe & Insect Hammer', 'Recipe: Termite Axe & Black Ox Hammer', 'Recipe: Bone Dagger & Widow Dagger', 'Recipe: Mint Mace', 'Recipe: Spicy Coaltana', 'Recipe: Salt Morning Star', 'Recipe: Sour Battle-axe', 'Recipe: Healing Basalt & Bandages', 'Recipe: Splint & Repair Glue', 'Recipe: Broodmother BLT Summon', 'Recipe: Mantis & Wasp Queen Summons']

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
        if code < 20020 or code >= 20040:
            cls = ItemClassification.progression
        elif code < 20030:
            cls = ItemClassification.useful
        else:
            cls = ItemClassification.filler
        return GroundedItem(name, cls, code, self.player)

    def create_regions(self) -> None:
        menu = Region('Menu', self.player, self.multiworld)
        reg_names = ['Lower Yard & Oak Lab', 'Hedge Lab', 'Pond Lab', 'Haze Lab', 'Black Anthill Lab', 'Upper Yard & Undershed']
        regs = {r: Region(r, self.player, self.multiworld) for r in reg_names}
        self.multiworld.regions.extend([menu] + list(regs.values()))

        for loc_name, loc_id in LOCATION_TABLE.items():
            if loc_name.startswith('Analyzed Resource #'):
                idx = int(loc_name.split('#')[1]) - 1
                r_name = 'Lower Yard & Oak Lab' if idx < 18 else reg_names[(idx - 18) % len(reg_names)]
            else:
                r_name = reg_names[loc_id % len(reg_names)]
            r_obj = regs[r_name]
            r_obj.locations.append(GroundedLocation(self.player, loc_name, loc_id, r_obj))

        menu.connect(regs[reg_names[0]])
        regs['Lower Yard & Oak Lab'].connect(regs['Hedge Lab'], rule=lambda state: state.has('Hedge Lab Keycard', self.player))
        regs['Lower Yard & Oak Lab'].connect(regs['Pond Lab'], rule=lambda state: state.has('Pond Lab Keycard', self.player))
        regs['Hedge Lab'].connect(regs['Haze Lab'], rule=lambda state: state.has('Haze Lab Keycard', self.player))
        regs['Haze Lab'].connect(regs['Black Anthill Lab'], rule=lambda state: state.has('Black Anthill Keycard', self.player))
        regs['Black Anthill Lab'].connect(regs['Upper Yard & Undershed'], rule=lambda state: state.has('Undershed Lab Keycard', self.player))

    def create_items(self) -> None:
        pool: List[GroundedItem] = []
        spec = [
            ('Hedge Lab Keycard', 1), ('Pond Lab Keycard', 1), ('Haze Lab Keycard', 1),
            ('Black Anthill Keycard', 1), ('Undershed Lab Keycard', 1),
            ('Tier II Omni-Tool Permit', 1), ('Tier III Omni-Tool Permit', 1),
            ('Progressive Mutation Slot', 4), ('Milk Molar Stat Upgrade', 8)
        ]
        for name, cnt in spec:
            pool.extend(self.create_item(name) for _ in range(cnt))
        for rname in RECIPE_ITEMS:
            pool.append(self.create_item(rname))

        total = len(self.multiworld.get_locations(self.player))
        fillers = ['Raw Science Cache (+500 RS)', 'BURG.L Science Grant (+1,500 RS)', 'Berry Leather Bundle']
        while len(pool) < total:
            pool.append(self.create_item(fillers[len(pool) % len(fillers)]))
        self.multiworld.itempool.extend(pool)

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: state.has('Undershed Lab Keycard', self.player)
