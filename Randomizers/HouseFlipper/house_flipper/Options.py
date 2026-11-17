from dataclasses import dataclass
from Options import Choice, Range, PerGameCommonOptions

class Goal(Choice):
    """Victory condition for House Flipper."""
    display_name = "Goal"
    option_net_worth = 0
    option_all_story_missions = 1
    option_buy_all_houses = 2
    default = 0

class NetWorthTarget(Range):
    """Total Net Worth (Cash + Owned Property Value) required when Goal is Net Worth."""
    display_name = "Net Worth Target"
    range_start = 250000
    range_end = 5000000
    step = 250000
    default = 1500000

class ContractsToWin(Range):
    """Number of story contracts required when Goal is All Story Missions."""
    display_name = "Contracts To Win"
    range_start = 5
    range_end = 20
    default = 20

@dataclass
class HouseFlipperOptions(PerGameCommonOptions):
    goal: Goal
    net_worth_target: NetWorthTarget
    contracts_to_win: ContractsToWin
