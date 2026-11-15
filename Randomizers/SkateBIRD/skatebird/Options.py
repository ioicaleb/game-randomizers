from dataclasses import dataclass
from Options import Choice, PerGameCommonOptions

class GoalLevels(Choice):
    """Number of levels whose story missions must be beaten to win."""
    display_name = "Victory Goal"
    option_skatepark_clear = 0
    option_all_5_levels = 1
    default = 1

@dataclass
class SkateBirdOptions(PerGameCommonOptions):
    goal: GoalLevels
