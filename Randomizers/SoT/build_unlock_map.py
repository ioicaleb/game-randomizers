#!/usr/bin/env python3
"""
Builds sot_world/unlock_map.json: which AP items can be DELIVERED by flipping an in-game unlock.

Usage:
    python3 build_unlock_map.py <unlockables.ogd> <generated_item_blueprints.ogd> <logic_rules.json> <new_game.sav> <out.json>

Every item blueprint stores the hash of the unlock it grants (dword 10 of its 88-byte record, record table at
0x5768). That link is exact, so no name or icon guessing is needed. An item is deliverable when
  * it is in a deliverable pool (quest items, keys, Chinpokomon, dyes), and
  * its link hash is a real record in unlockables.ogd, and
  * that unlock is not already owned in a brand-new game (those can never be checks).
Weapons / armor link to appearance unlocks (record type 18), which do not grant the item, so they are not mapped.
"""
import json, struct, sys

DELIVERABLE_POOLS = {"Cosmetic", "QuestEntryKey", "QuestItem", "QuestTier1", "QuestTier2", "Chinpokomon"}
DYE_RECORD_TYPE = 17          # Cosmetic items are only deliverable when they are dyes
TABLE, STRIDE, LINK_OFFSET = 0x5768, 88, 0x28

def read_unlockables(path):
    u = open(path, "rb").read(); POOL = 0x86C0
    def cs(o):
        e = u.find(b"\0", o); return u[o:e].decode("latin1")
    recs = {}
    for o in range(0x600, len(u) - 52, 4):
        if struct.unpack_from("<I", u, o + 48)[0] == o and struct.unpack_from("<I", u, o + 36)[0] == 0xDEADBF19:
            r = struct.unpack_from("<13I", u, o); off = r[8]
            recs[r[0]] = (r[3], cs(POOL + off) if off != 0xFFFFFFFF and POOL + off < len(u) else "")
    return recs

def main(unl, gen, rules, newgame, out):
    recs = read_unlockables(unl)
    g = open(gen, "rb").read()
    items = json.load(open(rules, encoding="utf-8-sig"))["Items"]

    ng = open(newgame, "rb").read(); start_owned = set()
    for o in range(0, len(ng) - 16, 4):
        h, f1, f2, p3 = struct.unpack_from("<4I", ng, o)
        if h in recs and f1 == 1 and p3 == 0 and f2 in (0, 1): start_owned.add(h)

    result, skipped = {}, []
    for it in items:
        idx = it["ItemIndex"]
        if idx >= 995 or not it["IsUnique"] or it["Excluded"] or it["Pool"] not in DELIVERABLE_POOLS: continue
        link = struct.unpack_from("<I", g, TABLE + idx * STRIDE + LINK_OFFSET)[0]
        rtype, icon = recs.get(link, (None, ""))
        if rtype is None or link in start_owned: skipped.append((idx, it["Name"], it["Pool"])); continue
        if it["Pool"] == "Cosmetic" and rtype != DYE_RECORD_TYPE: skipped.append((idx, it["Name"], it["Pool"])); continue
        result[str(idx)] = {"hash": link, "name": it["Name"], "icon": icon, "type": rtype}
    json.dump({"unlocks": result, "start_owned": sorted(start_owned)}, open(out, "w"), indent=1)
    print(f"mapped {len(result)} items; {len(skipped)} deliverable-pool items not deliverable")
    for s in skipped:
        if s[2] != "Cosmetic": print("   not deliverable:", s)

if __name__ == "__main__":
    if len(sys.argv) != 6: print(__doc__); sys.exit(1)
    main(*sys.argv[1:])