from typing import Any, Dict, List
from BaseClasses import Region, ItemClassification, Tutorial
from worlds.AutoWorld import World, WebWorld
from .Options import HouseFlipperOptions
from .Items import HouseFlipperItem, ITEM_TABLE
from .Locations import HouseFlipperLocation, LOCATION_TABLE

HOUSES = ['First Office', 'Abandoned House', 'Burned House', 'Hacker Loft', 'Samarta Myers House', 'Family House', 'Garden After Building', 'Just Married House', 'Pink Kingdom', 'Train Car', 'Man Cave', 'Uninhabited House', 'House on the Moon', 'Connoisseur House', 'Cache in a Bunker', '13th Floor', 'Castle', 'Cyberpunk Loft', 'Huckster House', 'Luxury Villa']
PERKS = ['Progressive Fast Hands (Cleaning)', 'Progressive Long Distance', 'Progressive Eye of the Mother-in-Law', 'Progressive Tempo', 'Progressive Muscle', 'Progressive Bigger Hammer', 'Progressive Painting Base', 'Progressive Fast Hands (Painting)', 'Progressive Paint More', 'Progressive Fitter', 'Progressive Plasterer', 'Progressive Tiler', 'Progressive Bricklayer', 'Progressive Mason', 'Progressive Fixer', 'Progressive Negotiate Price', 'Progressive Faster Order', 'Progressive Higher Payment']

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
        if code < 20020 or code >= 20070:
            cls = ItemClassification.progression
        elif code < 20060:
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
            if loc_id < 10100: idx = loc_id - 10000
            elif loc_id < 10200: idx = loc_id - 10100
            elif loc_id < 10300: idx = (loc_id - 10200) * 20 // 30
            else: idx = (loc_id - 10300) * 20 // 15
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
        for p in PERKS:
            for _ in range(3):
                pool.append(self.create_item(p))
        for h in HOUSES:
            pool.append(self.create_item(f"Deed: {h}"))

        total = len(self.multiworld.get_locations(self.player))
        fillers = ["Contractor Voucher (+$500)", "Client Bonus (+$1,500)", "Renovation Grant (+$5,000)"]
        while len(pool) < total:
            pool.append(self.create_item(fillers[len(pool) % len(fillers)]))
        self.multiworld.itempool.extend(pool)

    def set_rules(self) -> None:
        if self.options.goal.value == 2:
            self.multiworld.completion_condition[self.player] = lambda state: all(state.has(f"Deed: {h}", self.player) for h in HOUSES)
        else:
            self.multiworld.completion_condition[self.player] = lambda state: state.has("Tier 4 Contract Permit", self.player)

    def fill_slot_data(self) -> Dict[str, Any]:
        return {
            "goal": self.options.goal.value,
            "net_worth_target": self.options.net_worth_target.value,
            "contracts_to_win": self.options.contracts_to_win.value,
        }
