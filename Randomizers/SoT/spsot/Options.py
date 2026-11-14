from dataclasses import dataclass
from Options import Toggle, PerGameCommonOptions


class ShuffleFriends(Toggle):
    """Include Facebook Friend Requests in the Multiworld pool (cross-shuffled with items)."""
    display_name = "Shuffle Friend Requests"
    default = 1


class ShuffleChinpokomon(Toggle):
    """Include all 30 unique Chinpokomon in the Multiworld pool. If off they stay where the vanilla game puts them."""
    display_name = "Shuffle Chinpokomon"
    default = 1


@dataclass
class SouthParkSoTOptions(PerGameCommonOptions):
    shuffle_friends: ShuffleFriends
    shuffle_chinpokomon: ShuffleChinpokomon