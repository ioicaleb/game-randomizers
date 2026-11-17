"""
Reading the player's inventory from the game's save files.

A save is a plain binary file. Inside it is a table of item instances; each record starts with the text
"item20..." and, 32 bytes later, holds  [blueprint hash][quantity][quantity].  Only items the player really
owns are in there, which makes it a reliable "did you pick this up?" signal. The downside: the game only
writes it when it saves, so checks arrive at save time, not at pickup time.
"""
import os
import re
import struct
from typing import Dict, Iterable, Optional

_ITEM_TAG = re.compile(rb"item20")


def newest_save(save_dir: str) -> Optional[str]:
    best, best_t = None, -1.0
    if not save_dir or not os.path.isdir(save_dir):
        return None
    for root, _, files in os.walk(save_dir):
        for name in files:
            if name.lower().endswith(".sav"):
                path = os.path.join(root, name)
                try:
                    t = os.path.getmtime(path)
                except OSError:
                    continue
                if t > best_t:
                    best, best_t = path, t
    return best


def read_inventory(path: str, known_hashes: Iterable[int]) -> Optional[Dict[int, int]]:
    """Return {blueprint hash: quantity} for owned items whose hash is in known_hashes (None if unreadable)."""
    known = set(known_hashes)
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return None
    if data[:4] != b"SAVE":
        return None
    owned: Dict[int, int] = {}
    for m in _ITEM_TAG.finditer(data):
        o = m.start()
        if o + 0x2C > len(data):
            continue
        h, q1, q2 = struct.unpack_from("<Iii", data, o + 32)
        if q1 == q2 and q1 >= 1 and h in known:
            owned[h] = max(owned.get(h, 0), q1)
    return owned
