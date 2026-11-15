from dataclasses import dataclass
from Options import Toggle, PerGameCommonOptions

class IncludeCombos(Toggle):
    """Include all 99 Combo completions as Multiworld checks."""
    display_name = "Include Combos"
    default = 1

@dataclass
class LittleInfernoOptions(PerGameCommonOptions):
    include_combos: IncludeCombos
