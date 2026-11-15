from BaseClasses import Item

class RetroRewindItem(Item):
    game: str = "Retro Rewind"

ITEM_TABLE = {
    "Store Expansion Permit #1": 20001,
    "Store Expansion Permit #2": 20002,
    "Store Expansion Permit #3": 20003,
    "Store Expansion Permit #4": 20004,
    "Action & Sci-Fi License": 20010,
    "Horror & Thriller License": 20011,
    "Comedy & Romance License": 20012,
    "Video Game & Console Rental License": 20013,
    "Concessions & Popcorn License": 20014,
    "Arcade Cabinet License": 20015,
    "New Releases License": 20016,
    "Store XP Boost (+250 XP)": 20020,
    "Late Fee Windfall (+$50)": 20030,
    "Cash Register Bundle (+$150)": 20031,
    "Safe Deposit Bundle (+$500)": 20032,
}
