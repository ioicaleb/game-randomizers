from dataclasses import dataclass
from Options import Choice, PerGameCommonOptions

class VictoryGoal(Choice):
    display_name = 'Victory Goal'
    option_chapter_4_clear = 0
    option_government_valley_finale = 1
    default = 1

@dataclass
class ShadowsOverLoathingOptions(PerGameCommonOptions):
    victory_goal: VictoryGoal
