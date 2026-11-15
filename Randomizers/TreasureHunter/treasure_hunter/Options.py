from dataclasses import dataclass
from Options import Choice, PerGameCommonOptions
class VictoryGoal(Choice):
    display_name = 'Treasure Hunter Simulator Goal'
    option_standard = 0
    default = 0
@dataclass
class TreasureHunterOptions(PerGameCommonOptions):
    victory_goal: VictoryGoal
