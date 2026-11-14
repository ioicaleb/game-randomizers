from typing import Dict, List
from BaseClasses import Region, ItemClassification, Tutorial
from worlds.AutoWorld import World, WebWorld
from .Options import GDTOptions
from .Items import GDTItem, ITEM_TABLE
from .Locations import GDTLocation, LOCATION_TABLE


class GDTWeb(WebWorld):
    theme = "ocean"
    tutorials = [Tutorial(
        "Multiworld Setup Guide",
        "Setup guide for Game Dev Tycoon in Archipelago.",
        "English",
        "setup_en.md",
        "setup/en"
    )]


class GDTWorld(World):
    """
    Game Dev Tycoon is a business simulation game where you build a video game studio from a garage in the 1980s.
    """
    game = "Game Dev Tycoon"
    web = GDTWeb()
    options_dataclass = GDTOptions
    options: GDTOptions

    item_name_to_id: Dict[str, int] = ITEM_TABLE
    location_name_to_id: Dict[str, int] = LOCATION_TABLE

    def create_item(self, name: str) -> GDTItem:
        item_id = self.item_name_to_id[name]
        if name.startswith("Genre:") or name == "Progressive Office Upgrade":
            classification = ItemClassification.progression
        elif name.startswith("Platform:") or name.startswith("Topic:"):
            classification = ItemClassification.useful
        else:
            classification = ItemClassification.filler
        return GDTItem(name, classification, item_id, self.player)

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        garage = Region("Garage Era (Sphere 0)", self.player, self.multiworld)
        office = Region("Office Era (Sphere 1)", self.player, self.multiworld)
        rd_lab = Region("R&D Era (Sphere 2)", self.player, self.multiworld)

        self.multiworld.regions.extend([menu, garage, office, rd_lab])

        for loc_name, loc_id in LOCATION_TABLE.items():
            if any(k in loc_name for k in ["$100M", "$250M", "$500M", "$1B", "1,000,000", "5,000,000", "30 Games"]):
                target = rd_lab
            elif any(k in loc_name for k in ["$2.5M", "$5M", "$10M", "$25M", "$50M", "50,000", "100,000", "250,000", "500,000", "15 Games", "20 Games"]):
                target = office
            else:
                target = garage
            target.locations.append(GDTLocation(self.player, loc_name, loc_id, target))

        menu.connect(garage)
        garage.connect(office, rule=lambda state: state.has("Progressive Office Upgrade", self.player, 1))
        office.connect(rd_lab, rule=lambda state: state.has("Progressive Office Upgrade", self.player, 2))

    def create_items(self) -> None:
        pool: List[GDTItem] = []
        # Add 3 Progressive Office Upgrades + all Genres, Topics, and Platforms
        pool.append(self.create_item("Progressive Office Upgrade"))
        pool.append(self.create_item("Progressive Office Upgrade"))
        pool.append(self.create_item("Progressive Office Upgrade"))

        for name in ITEM_TABLE:
            if name != "Progressive Office Upgrade" and not name.startswith("Filler:"):
                pool.append(self.create_item(name))

        # Pad remaining locations with Investor Cash Grants & Research Bundles
        fillers = [
            "Filler: Investor Cash Grant (+$250K)",
            "Filler: Research Bundle (+25 RP)",
            "Filler: Hype Campaign (+50 Hype)"
        ]
        while len(pool) < len(LOCATION_TABLE):
            pool.append(self.create_item(fillers[len(pool) % len(fillers)]))

        self.multiworld.itempool.extend(pool)

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: state.has("Progressive Office Upgrade", self.player, 2)
