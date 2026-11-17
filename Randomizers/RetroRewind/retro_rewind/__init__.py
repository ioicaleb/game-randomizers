from typing import Any, Dict, List
from BaseClasses import Region, ItemClassification, Tutorial
from worlds.AutoWorld import World, WebWorld
from .Options import RetroRewindOptions
from .Items import RetroRewindItem, ITEM_TABLE
from .Locations import RetroRewindLocation, LOCATION_TABLE

PROG_ITEMS = ['Store Expansion Permit #1', 'Store Expansion Permit #2', 'Store Expansion Permit #3', 'Store Expansion Permit #4', 'Backroom Storage Expansion', 'Neon Storefront Sign Upgrade', 'Security Gate & Anti-Theft Upgrade', 'Carpet & Lighting Remodel', 'Action & Sci-Fi License', 'Horror & Thriller License', 'Comedy & Romance License', 'Family & Animation License', 'Drama & Classics License', 'Documentary & Cult License', 'Video Game & Console Rental License', 'Concessions & Popcorn License', 'Arcade Cabinet License', 'New Releases License', 'Double-Sided Tape Rack', 'Deluxe Wooden Display Shelf', 'Corner Movie Rack', 'Glass Video Game Display Case', 'New Releases Feature Stand', 'Checkout Counter Upgrade', 'Return Drop-Box Bin', 'Popcorn Warmer Cart', 'Soda Cooler Fridge', 'Candy & Snack Display Rack', 'Retro Arcade Cabinet #1', 'Retro Arcade Cabinet #2', 'Poster Display Spinner', 'Cardboard Standee Display', 'VHS Rewinder Station', 'VIP Membership Desk', 'Hire Cashier #1', 'Hire Cashier #2', 'Hire Shelf Stocker #1', 'Hire Shelf Stocker #2', 'Hire Tape Rewinder & Cleaner', 'Hire Night Shift Manager', 'Sci-Fi Movie Poster Pack', 'Horror Movie Poster Pack', 'Comedy Movie Poster Pack', 'Neon OPEN Window Sign', 'Neon VHS Logo Sign', 'Retro Carpet Runner', 'Potted Indoor Palm Plant', 'Ceiling String Lights', 'Classic Movie Cardboard Cutout', 'Vintage TV Wall Monitor', 'Arcade Token Banner', '90s Boombox Stereo', 'Golden VHS Trophy', 'Checkered Floor Tiles', 'Wall Shelf Diorama']

class RetroRewindWeb(WebWorld):
    theme = "partyTime"
    tutorials = [Tutorial("Setup Guide", "Setup Retro Rewind for Archipelago.", "English", "setup_en.md", "setup/en", ["SoT_Rando"])]

class RetroRewindWorld(World):
    """Retro Rewind - Video Store Simulator: Manage your 90s video store, unlock furniture, staff, genres, and expand!"""
    game = "Retro Rewind"
    web = RetroRewindWeb()
    options_dataclass = RetroRewindOptions
    options: RetroRewindOptions
    item_name_to_id: Dict[str, int] = ITEM_TABLE
    location_name_to_id: Dict[str, int] = LOCATION_TABLE

    def create_item(self, name: str) -> RetroRewindItem:
        code = self.item_name_to_id[name]
        if code in (20020, 20030, 20031, 20032):
            cls = ItemClassification.useful if code == 20020 else ItemClassification.filler
        else:
            cls = ItemClassification.progression
        return RetroRewindItem(name, cls, code, self.player)

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        starter = Region("Starter Store", self.player, self.multiworld)
        expanded = Region("Expanded Store", self.player, self.multiworld)
        deluxe = Region("Deluxe Video Empire", self.player, self.multiworld)
        self.multiworld.regions.extend([menu, starter, expanded, deluxe])

        for loc_name, loc_id in LOCATION_TABLE.items():
            if loc_id < 10008 or (10100 <= loc_id < 10112) or (10200 <= loc_id < 10208) or (10300 <= loc_id < 10310):
                reg = starter
            elif loc_id < 10014 or (10112 <= loc_id < 10120) or (10208 <= loc_id < 10215) or (10310 <= loc_id < 10320):
                reg = expanded
            else:
                reg = deluxe
            reg.locations.append(RetroRewindLocation(self.player, loc_name, loc_id, reg))

        menu.connect(starter)
        starter.connect(expanded, rule=lambda state: state.has("Store Expansion Permit #1", self.player) or state.has("Video Game & Console Rental License", self.player))
        expanded.connect(deluxe, rule=lambda state: state.has("Store Expansion Permit #2", self.player) and state.has("New Releases License", self.player))

    def create_items(self) -> None:
        pool: List[RetroRewindItem] = [self.create_item(name) for name in PROG_ITEMS]
        for _ in range(8):
            pool.append(self.create_item("Store XP Boost (+250 XP)"))

        total_locs = len(self.multiworld.get_locations(self.player))
        fillers = ["Late Fee Windfall (+$50)", "Cash Register Bundle (+$150)", "Safe Deposit Bundle (+$500)"]
        while len(pool) < total_locs:
            pool.append(self.create_item(fillers[len(pool) % len(fillers)]))
        self.multiworld.itempool.extend(pool)

    def set_rules(self) -> None:
        g = self.options.goal.value
        if g == 1:
            self.multiworld.completion_condition[self.player] = lambda state: all(state.has(f"Store Expansion Permit #{i}", self.player) for i in range(1, 5))
        elif g == 2:
            self.multiworld.completion_condition[self.player] = lambda state: all(state.has(lic, self.player) for lic in (
                "Action & Sci-Fi License", "Horror & Thriller License", "Comedy & Romance License",
                "Video Game & Console Rental License", "Concessions & Popcorn License",
                "Arcade Cabinet License", "New Releases License"
            ))
        elif g == 3:
            self.multiworld.completion_condition[self.player] = lambda state: state.has("Store Expansion Permit #2", self.player) and state.has("New Releases License", self.player)
        else:
            target = int(self.options.target_store_level.value)
            self.multiworld.completion_condition[self.player] = lambda state: state.can_reach(f"Store Level {target:02d}", "Location", self.player)

    def fill_slot_data(self) -> Dict[str, Any]:
        return {
            "goal": self.options.goal.value,
            "target_store_level": self.options.target_store_level.value,
            "target_store_value": self.options.target_store_value.value,
            "auto_change": int(self.options.auto_change.value),
            "auto_sort_returns": int(self.options.auto_sort_returns.value),
            "arm_carry_limit": int(self.options.arm_carry_limit.value),
        }


def _launch_retro_rewind_client(*args):
    import subprocess, sys
    client_py = "/mnt/E8A2D79FA2D77114/Source/repos/GameRandomizers/Randomizers/RetroRewind/rr_client.py"
    subprocess.Popen([sys.executable, client_py, *args])

try:
    from worlds.LauncherComponents import Component, components, Type
    components.append(Component(
        "Retro Rewind Client",
        func=_launch_retro_rewind_client,
        component_type=Type.CLIENT,
    ))
except Exception:
    pass
