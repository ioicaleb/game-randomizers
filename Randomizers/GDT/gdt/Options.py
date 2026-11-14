from dataclasses import dataclass
from Options import Choice, PerGameCommonOptions


class GoalTarget(Choice):
    """Victory goal for Game Dev Tycoon."""
    display_name = "Victory Goal"
    option_millionaire = 0   # $10M Cash + 100K Fans
    option_tycoon = 1        # $100M Cash + 1M Fans
    default = 1


@dataclass
class GDTOptions(PerGameCommonOptions):
    goal: GoalTarget