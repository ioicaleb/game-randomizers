from dataclasses import dataclass
from Options import Choice, PerGameCommonOptions
class VictoryGoal(Choice):
    display_name = 'Papers, Please Goal'
    option_standard = 0
    default = 0
@dataclass
class PapersPleaseOptions(PerGameCommonOptions):
    victory_goal: VictoryGoal
