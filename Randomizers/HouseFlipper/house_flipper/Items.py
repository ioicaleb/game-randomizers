from BaseClasses import Item

class HouseFlipperItem(Item):
    game: str = "House Flipper"

ITEM_TABLE = {
    "Tier 1 Contract Permit": 20001,
    "Tier 2 Contract Permit": 20002,
    "Tier 3 Contract Permit": 20003,
    "Tier 4 Contract Permit": 20004,
    "Mop & Window Squeegee": 20010,
    "Paint Roller": 20011,
    "Plaster Trowel": 20012,
    "Sledgehammer": 20013,
    "Building & Demolition Tool": 20014,
    "Progressive Cleaning": 20020,
    "Progressive Painting": 20021,
    "Progressive Demolition": 20022,
    "Progressive Handyman": 20023,
    "Progressive Negotiation": 20024,
    "Contractor Voucher (+$500)": 20030,
    "Client Bonus (+$1,500)": 20031,
    "Renovation Grant (+$5,000)": 20032,
}
