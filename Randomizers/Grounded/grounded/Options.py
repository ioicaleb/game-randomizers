from dataclasses import dataclass
from Options import Choice, PerGameCommonOptions
class VictoryGoal(Choice):
    display_name = 'Grounded Goal'
    option_standard = 0
    default = 0
@dataclass
class GroundedOptions(PerGameCommonOptions):
    victory_goal: VictoryGoal
