from dataclasses import dataclass
from Options import Range, PerGameCommonOptions

class TargetStoreLevel(Range):
    """Target Store Level required to complete the seed."""
    display_name = "Target Store Level"
    range_start = 5
    range_end = 20
    default = 15

@dataclass
class RetroRewindOptions(PerGameCommonOptions):
    target_store_level: TargetStoreLevel
