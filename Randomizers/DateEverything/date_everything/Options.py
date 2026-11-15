from dataclasses import dataclass
from Options import Choice, PerGameCommonOptions
class VictoryGoal(Choice):
    display_name = 'Date Everything Goal'
    option_standard = 0
    default = 0
@dataclass
class DateEverythingOptions(PerGameCommonOptions):
    victory_goal: VictoryGoal
