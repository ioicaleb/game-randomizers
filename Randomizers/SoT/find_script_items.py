#!/usr/bin/env python3
"""
Find which items the game's OWN SCRIPTS touch (equip, give, remove, check, spawn on an enemy ...).

Those items must not be shuffled: the game expects them to be exactly what they were. Swapping their data is what
caused the earlier softlocks (class weapons, tutorial items, Gas Mask) and can crash the game when a fight starts.

Usage:
    python3 find_script_items.py "<extracted game folder>" <logic_rules.json> <out script_items.json>

How it works: every item has a 32-bit hash. We look for each item's hash inside every extracted game file
(dialogue, level scripts, actors, encounters...), skipping the item tables / loot tables / audio / textures, where
every item naturally appears. An item that shows up somewhere else is "referenced by a script".
(A few hits will be coincidences; excluding a few extra items from the shuffle is harmless.)

Copy the resulting script_items.json into sot_world/ and rebuild the apworld.
"""
import json, os, sys
from array import array
from collections import defaultdict

SKIP_EXT = {".gfx", ".dds", ".tga", ".wem", ".bnk", ".bik", ".usm", ".png", ".jpg", ".jpeg", ".wav", ".ogg"}
SKIP_NAMES = {"generated_item_blueprints.ogd", "base_item_blueprints.ogd", "loot_templates.ogd", "unlockables.ogd"}
MAX_SIZE = 300 * 1024 * 1024


def main(root, rules_path, out_path):
    items = json.load(open(rules_path, encoding="utf-8-sig"))["Items"]
    by_hash = defaultdict(list)
    for it in items:
        by_hash[it["BlueprintHash"]].append(it["ItemIndex"])
    targets = set(by_hash)

    referenced = defaultdict(set)
    scanned = skipped = 0
    for dirpath, _, files in os.walk(root):
        for fn in files:
            path = os.path.join(dirpath, fn)
            ext = os.path.splitext(fn)[1].lower()
            if ext in SKIP_EXT or fn.lower() in SKIP_NAMES:
                skipped += 1
                continue
            try:
                if os.path.getsize(path) > MAX_SIZE:
                    skipped += 1
                    continue
                data = open(path, "rb").read()
            except OSError:
                continue
            scanned += 1
            rel = os.path.relpath(path, root).replace("\\", "/")
            for k in range(4):                         # the hash can sit at any byte alignment
                n = (len(data) - k) // 4
                if n <= 0:
                    continue
                arr = array("I")
                arr.frombytes(data[k:k + 4 * n])
                if sys.byteorder == "big":
                    arr.byteswap()
                for h in targets.intersection(arr):
                    for idx in by_hash[h]:
                        referenced[idx].add(rel)

    names = {it["ItemIndex"]: it for it in items}
    out = {str(i): sorted(files)[:6] for i, files in sorted(referenced.items())}
    json.dump({"referenced": out}, open(out_path, "w"), indent=1)
    print(f"scanned {scanned} files ({skipped} skipped); {len(out)} items are referenced outside the item/loot tables")
    by_pool = defaultdict(int)
    for i in referenced:
        by_pool[names[i]["Pool"]] += 1
    print("by pool:", dict(sorted(by_pool.items())))
    print("examples:")
    for i in sorted(referenced)[:25]:
        print(f"   #{i:<4} {names[i]['Name']:<34} {names[i]['Pool']:<13} {sorted(referenced[i])[0]}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__); sys.exit(1)
    main(*sys.argv[1:])