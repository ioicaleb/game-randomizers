from dataclasses import dataclass
from Randomizers.GraveyardKeeper.graveyard_keeper.Options import Choice, PerGameCommonOptions
class VictoryGoal(Choice):
    display_name = 'Graveyard Keeper Goal'
    option_standard = 0
    default = 0
@dataclass
class GraveyardKeeperOptions(PerGameCommonOptions):
    victory_goal: VictoryGoal
