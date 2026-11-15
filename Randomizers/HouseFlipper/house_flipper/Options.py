from dataclasses import dataclass
from Options import Range, PerGameCommonOptions

class ContractsToWin(Range):
    """Number of contracts/houses completed to win the seed."""
    display_name = "Contracts To Win"
    range_start = 5
    range_end = 20
    default = 15

@dataclass
class HouseFlipperOptions(PerGameCommonOptions):
    contracts_to_win: ContractsToWin
