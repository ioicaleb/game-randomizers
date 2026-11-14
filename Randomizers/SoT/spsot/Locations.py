from BaseClasses import Location
from .Data import UNIQUE_ITEMS, FRIEND_LIST, ITEM_BASE, FRIEND_BASE, FRIEND_LOCATION_NAMES, location_name


class SouthParkSoTLocation(Location):
    game: str = "South Park: The Stick of Truth"


location_name_to_id = {location_name(d): ITEM_BASE + d.index for d in UNIQUE_ITEMS}
location_name_to_id.update({FRIEND_LOCATION_NAMES[f]: FRIEND_BASE + n for n, f in enumerate(FRIEND_LIST)})