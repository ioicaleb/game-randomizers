from BaseClasses import Item
from .Data import UNIQUE_ITEMS, FRIEND_LIST, ITEM_BASE, FRIEND_BASE, FRIEND_ITEM_NAMES


class SouthParkSoTItem(Item):
    game: str = "South Park: The Stick of Truth"


item_name_to_id = {d.label: ITEM_BASE + d.index for d in UNIQUE_ITEMS}
item_name_to_id.update({FRIEND_ITEM_NAMES[f]: FRIEND_BASE + n for n, f in enumerate(FRIEND_LIST)})