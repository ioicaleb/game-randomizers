from dataclasses import dataclass
from Options import Choice, DefaultOnToggle, Range, PerGameCommonOptions

class Goal(Choice):
    """Victory condition for Retro Rewind."""
    display_name = "Goal"
    option_store_level = 0
    option_all_store_upgrades = 1
    option_all_genres = 2
    option_store_tape_value = 3
    default = 0

class TargetStoreLevel(Range):
    """Target Store Level required when Goal is Store Level."""
    display_name = "Target Store Level"
    range_start = 5
    range_end = 20
    default = 15

class TargetStoreValue(Range):
    """Target Store Tape & Inventory Value ($) required when Goal is Store Tape Value."""
    display_name = "Target Store Value"
    range_start = 5000
    range_end = 100000
    step = 5000
    default = 25000

class AutoChange(DefaultOnToggle):
    """Automatically give exact change at the cash register to speed up checkouts."""
    display_name = "QoL: Auto-Change at Checkout"

class AutoSortReturns(DefaultOnToggle):
    """Automatically route returned and reserved videos from the dropbox to matching racks."""
    display_name = "QoL: Auto-Sort Returned & Reserved Videos"

class ArmCarryLimit(Range):
    """Maximum number of movies/items the player can carry in hand at once (vanilla is 5)."""
    display_name = "QoL: Arm Carry Limit"
    range_start = 5
    range_end = 30
    default = 20

@dataclass
class RetroRewindOptions(PerGameCommonOptions):
    goal: Goal
    target_store_level: TargetStoreLevel
    target_store_value: TargetStoreValue
    auto_change: AutoChange
    auto_sort_returns: AutoSortReturns
    arm_carry_limit: ArmCarryLimit
