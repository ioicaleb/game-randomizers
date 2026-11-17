"""
Changing the game's data so the shuffle shows up in-game.

The game keeps almost everything in one big file, data_archive.oaf (not compressed). Inside it is the
"item blueprint table": 995 records of 88 bytes, one per item, each starting with the item's hash.
We change it in memory-safe, same-size ways and write it back:

  * a chest slot whose item goes to YOU  -> copy the other item's data over this slot (it looks like that item)
  * a chest slot whose item is delivered by an unlock, or goes to someone else -> a plain "junk" look-alike
  * remove level caps, and make Clyde's four starter weapons free (so you can never be left without a weapon)
  * Jimbo's dialogue: stop him handing out the six hunting baits (they arrive through the multiworld)

Safety: the first time we run we keep a pristine copy next to the archive (data_archive.oaf.clean). Every later
patch is built from that copy, so patching again with a new seed never stacks changes.
"""
import mmap
import os
import shutil
import struct
from typing import Callable, Dict, List, Optional, Tuple

TABLE_IN_FILE = 0x5768        # offset of the record table inside generated_item_blueprints.ogd
RECORD = 88
COUNT = 995
COPY = 0x54                   # bytes copied after the 4-byte hash (the item's looks and stats)
MYSTERY = list(range(601, 621))
TOKEN_SOURCE = 615            # "Crumpled Paper": the one junk item every placeholder is copied from when it gets a custom label
CLYDE_WEAPONS = range(978, 982)

JIMBO_NAMES = [b"102_p_bait_tubesteak", b"102_p_bait_orange", b"102_p_bait_fro_cheese",
               b"102_p_bait_poutine", b"102_p_bait_alcohol", b"102_p_bait_bell"]
JIMBO_REPLACEMENT = b"10256_p_hunters_guide"


def protected(idx: int) -> bool:
    """Cash (#0-27) and Nose Jobs (#53-57) must never be overwritten; nothing past the table either."""
    return idx <= 27 or 53 <= idx <= 57 or idx >= COUNT


# --------------------------------------------------------------------------- locating the table
def table_matches(buf, pos: int, hashes: List[int]) -> bool:
    if pos < 0 or pos + COUNT * RECORD > len(buf):
        return False
    for i, h in enumerate(hashes):
        if buf[pos + i * RECORD: pos + i * RECORD + 4] != struct.pack("<I", h):
            return False
    return True


def find_table(buf, hashes: List[int]) -> int:
    """Offset of the blueprint table inside the archive (or -1). Validated against all 995 known hashes."""
    needle = struct.pack("<I", hashes[0])
    pos = buf.find(needle)
    while pos != -1:
        if table_matches(buf, pos, hashes):
            return pos
        pos = buf.find(needle, pos + 1)
    return -1


# --------------------------------------------------------------------------- building the patched table
ALL_STAGES = frozenset({"caps", "clyde", "slots", "jimbo"})


def build_patched_table(orig: bytes, slot_mapping: Dict[int, dict], my_slot: int, deliverable_ids: set,
                        stages=ALL_STAGES, skip_indices=frozenset(), token_text=None) -> Tuple[bytearray, Dict[int, int], Dict[str, int]]:
    """
    orig: the pristine 995*88-byte table.
    slot_mapping: {location id: {"item_id", "player"}}.
    stages: which changes to make (for tracking down a crash):
        "caps"  remove level requirements        "clyde" make Clyde's four starter weapons free
        "slots" clone / token the shuffled slots  "tokens" (instead of "slots") make EVERY slot a plain token
    skip_indices: slots left exactly as the game has them (their pickups still count as checks).
    token_text: (name string id, description string id) for the placeholder label; when given, every placeholder is a
        copy of ONE junk item that uses those strings (see GameText.py).
    Returns (patched table, {blueprint hash: location id}, stats).
    """
    patched = bytearray(orig)
    stats = {"local": 0, "token": 0, "deliverable_tokens": 0}
    for idx in range(COUNT):
        s = idx * RECORD
        req_lv = struct.unpack_from("<i", patched, s + 0x44)[0]
        if idx in CLYDE_WEAPONS:
            if "clyde" in stages:
                struct.pack_into("<i", patched, s + 0x0C, 0)      # free
                struct.pack_into("<i", patched, s + 0x44, 1)      # level 1
        elif "caps" in stages and 1 < req_lv <= 20:
            struct.pack_into("<i", patched, s + 0x44, 1)          # remove level cap

    # Clone from this cap-free copy, not from `orig`: otherwise every cloned slot would bring its original
    # level requirement back and the cap removal above would only apply to untouched items.
    source = bytes(patched)

    hash_to_loc: Dict[int, int] = {}
    for loc_id, target in slot_mapping.items():
        if not 10000 <= loc_id < 20000:
            continue
        idx = loc_id - 10000
        if protected(idx):
            continue
        hash_to_loc[struct.unpack_from("<I", orig, idx * RECORD)[0]] = loc_id
        if idx in skip_indices or not ({"slots", "tokens"} & set(stages)):
            continue
        dst = idx * RECORD + 4
        item_id = target["item_id"]
        deliverable = item_id in deliverable_ids
        if deliverable and target["player"] == my_slot:
            stats["deliverable_tokens"] += 1
        if "slots" in stages and target["player"] == my_slot and 10000 <= item_id < 20000 and not deliverable:
            src = (item_id - 10000) * RECORD + 4
            patched[dst:dst + COPY] = source[src:src + COPY]
            stats["local"] += 1
        elif token_text:
            src = TOKEN_SOURCE * RECORD + 4
            patched[dst:dst + COPY] = source[src:src + COPY]
            struct.pack_into("<II", patched, idx * RECORD + 0x14, token_text[0], token_text[1])   # name id, description id
            stats["token"] += 1
        else:
            src = MYSTERY[idx % len(MYSTERY)] * RECORD + 4
            patched[dst:dst + COPY] = source[src:src + COPY]
            stats["token"] += 1
    return patched, hash_to_loc, stats


# --------------------------------------------------------------------------- Jimbo
def plan_jimbo_patches(clean) -> List[Tuple[int, bytes]]:
    """Find each bait name in the pristine archive and return (offset, replacement bytes) pairs.
    Only the first name needs a whole-archive search (which also proves it is unique); the others sit within a
    few KB of it in the same file, so they are searched for in a small window."""
    plans = []
    anchor = None
    for name in JIMBO_NAMES:
        needle = name + b"\0"
        if anchor is None:
            pos = clean.find(needle)
            if pos == -1 or clean.find(needle, pos + 1) != -1:
                continue                                  # missing or ambiguous: leave it alone
            anchor = pos
        else:
            lo = max(0, anchor - 65536)
            window = bytes(clean[lo: anchor + 65536])
            idx = window.find(needle)
            if idx == -1 or window.find(needle, idx + 1) != -1:
                continue
            pos = lo + idx
        span = max(len(name), len(JIMBO_REPLACEMENT))
        tail = clean[pos + len(name): pos + span + 1]
        if any(tail):                                     # the buffer after the name must be zero padding
            continue
        plans.append((pos, JIMBO_REPLACEMENT + b"\0" * (span - len(JIMBO_REPLACEMENT))))
    return plans


# --------------------------------------------------------------------------- whole archive
def patch_archive(game_dir: str, blueprint_hashes: List[int], slot_mapping, my_slot: int, deliverable_ids: set,
                  patch_jimbo: bool = True, dry_run: bool = False, stages=ALL_STAGES,
                  skip_indices=frozenset(), token_text=None, log: Callable[[str], None] = print) -> Optional[Dict[int, int]]:
    """Patch data_archive.oaf for this seed. Returns {blueprint hash: location id}, or None on failure."""
    live = os.path.join(game_dir, "data_archive.oaf")
    clean = live + ".clean"
    if not os.path.isfile(live):
        log(f"[PATCH] {live} not found. Check your game folder setting.")
        return None
    if not os.path.isfile(clean):
        log("[PATCH] First run: making a pristine backup of data_archive.oaf (this can take a minute)...")
        shutil.copyfile(live, clean)
    if os.path.getsize(live) != os.path.getsize(clean):
        log("[PATCH] data_archive.oaf and its .clean backup differ in size (game updated?). "
            "Use Steam > Verify integrity of game files, delete data_archive.oaf.clean, and try again.")
        return None

    with open(clean, "rb") as cf, mmap.mmap(cf.fileno(), 0, access=mmap.ACCESS_READ) as cm:
        pos = find_table(cm, blueprint_hashes)
        if pos < 0:
            log("[PATCH] Could not find the item table in the archive; this game version is not recognised.")
            return None
        orig_table = bytes(cm[pos: pos + COUNT * RECORD])
        jimbo = plan_jimbo_patches(cm) if (patch_jimbo and "jimbo" in stages) else []

    patched, hash_to_loc, stats = build_patched_table(orig_table, slot_mapping, my_slot, deliverable_ids,
                                                      stages, skip_indices, token_text)
    if dry_run:
        log("[PATCH] Game is running: archive left untouched (assuming it was already patched for this seed).")
        return hash_to_loc
    with open(live, "r+b") as lf:
        lf.seek(pos)
        lf.write(patched)
        for off, data in jimbo:
            lf.seek(off)
            lf.write(data)
    log(f"[PATCH] Table at 0x{pos:08X}: {stats['local']} local items placed, {stats['token']} tokens armed "
        f"({stats['deliverable_tokens']} of them deliverable).")
    if patch_jimbo and "jimbo" in stages:
        log(f"[PATCH] Jimbo: {len(jimbo)}/{len(JIMBO_NAMES)} bait gives removed.")
    return hash_to_loc
