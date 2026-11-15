from BaseClasses import Location


class GDTLocation(Location):
    game: str = "Game Dev Tycoon"


LOCATION_TABLE = {
    "Cash: $100K": 10001,
    "Cash: $250K": 10002,
    "Cash: $500K": 10003,
    "Cash: $1M": 10004,
    "Cash: $2.5M": 10005,
    "Cash: $5M": 10006,
    "Cash: $10M": 10007,
    "Cash: $25M": 10008,
    "Cash: $50M": 10009,
    "Cash: $100M": 10010,
    "Cash: $250M": 10011,
    "Cash: $500M": 10012,
    "Cash: $1B": 10013,
    "Fans: 1,000": 10101,
    "Fans: 5,000": 10102,
    "Fans: 10,000": 10103,
    "Fans: 25,000": 10104,
    "Fans: 50,000": 10105,
    "Fans: 100,000": 10106,
    "Fans: 250,000": 10107,
    "Fans: 500,000": 10108,
    "Fans: 1,000,000": 10109,
    "Fans: 5,000,000": 10110,
    "Release 1st Game": 10201,
    "Release 3 Games": 10202,
    "Release 5 Games": 10203,
    "Release 10 Games": 10204,
    "Release 15 Games": 10205,
    "Release 20 Games": 10206,
    "Release 30 Games": 10207,
}

for _i in range(35):
    LOCATION_TABLE[f"Achievement #{_i + 1:02d}"] = 10300 + _i
