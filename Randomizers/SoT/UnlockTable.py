"""
The game's "unlock table" in memory: one 16-byte record per unlockable thing (friends, dyes, keys,
quest items, Chinpokomon ...):

        [ hash ][ flag1 ][ flag2 ][ 0 ]        flag1 = flag2 = 1  means "unlocked"

We use it two ways: READ it to notice the player unlocked something in-game (-> send a check),
and WRITE it to unlock something the multiworld gave the player.

Finding the table is the expensive part (it means scanning the game's memory), so we do that ONCE
("discovery"), remember the addresses, and afterwards only read those few addresses.

Friends additionally get appended to a 24-slot "recently unlocked" list whose header ends with
[0x18][0x3EA]; empty slots hold 0xDEADBF19.
"""
import struct
import sys
from array import array
from typing import Dict, Iterator, List, Set, Tuple

from .GameMemory import ProcessMemory

CHUNK = 1024 * 1024
OVERLAP = 1024
EMPTY_SLOT = 0xDEADBF19
LIST_MARK = 0x3EA
LIST_SLOTS = 24
NEIGHBOUR_RECORDS = 8       # a real table record has another known unlockable within +/- 8 records


def iter_chunks(mem: ProcessMemory) -> Iterator[Tuple[int, bytes]]:
    """Walk all writable memory in overlapping chunks. Unreadable pages are skipped."""
    for start, end in mem.regions():
        addr = start
        while addr < end:
            size = min(CHUNK, end - addr)
            data = mem.read(addr, size)
            if len(data) < size:                       # some page in here is unreadable: go page by page
                data = b""
                for page in range(addr, addr + size, 4096):
                    part = mem.read(page, min(4096, addr + size - page))
                    if len(part) == min(4096, addr + size - page):
                        yield page, part
            if data:
                yield addr, data
            if addr + size >= end:
                break
            addr += size - OVERLAP


def _dwords(data: bytes) -> array:
    arr = array("I")
    arr.frombytes(data[: len(data) // 4 * 4])
    if sys.byteorder == "big":
        arr.byteswap()
    return arr


class UnlockTable:
    def __init__(self, mem: ProcessMemory, all_hashes: Set[int]):
        self.mem = mem
        self.all_hashes = set(all_hashes)
        self.records: Dict[int, List[int]] = {}    # unlock hash -> addresses of its flag records
        self.lists: List[int] = []                 # addresses of the first slot of each unlock list

    # ------------------------------------------------------------------ discovery
    def discover(self) -> int:
        """Scan all memory for flag records and unlock lists. Returns the number of records found."""
        found: Dict[int, Set[int]] = {}
        lists: Set[int] = set()
        targets = self.all_hashes
        for base, data in iter_chunks(self.mem):
            arr = _dwords(data)
            n = len(arr)
            if n < 8:
                continue
            if not targets.isdisjoint(arr):            # fast C-speed skip of chunks with nothing of interest
                for i in [i for i, v in enumerate(arr) if v in targets]:
                    if i + 3 >= n:
                        continue
                    f1, f2, p3 = arr[i + 1], arr[i + 2], arr[i + 3]
                    if f1 > 1 or f2 > 1 or p3 != 0:
                        continue
                    if not self._has_neighbour(arr, i, n):
                        continue
                    found.setdefault(arr[i], set()).add(base + 4 * i)
            if LIST_MARK in arr:
                for j in [j for j, v in enumerate(arr) if v == LIST_MARK]:
                    if j >= 1 and arr[j - 1] == 0x18 and j + 1 + LIST_SLOTS * 2 <= n:
                        lists.add(base + 4 * (j + 1))
        self.records = {h: sorted(a) for h, a in found.items()}
        self.lists = sorted(lists)
        return sum(len(a) for a in self.records.values())

    def _has_neighbour(self, arr: array, i: int, n: int) -> bool:
        for k in range(-NEIGHBOUR_RECORDS, NEIGHBOUR_RECORDS + 1):
            j = i + 4 * k
            if k and 0 <= j < n and arr[j] in self.all_hashes:
                return True
        return False

    # ------------------------------------------------------------------ reading
    def read_unlocked(self, hashes) -> Set[int]:
        """Which of the given unlocks are currently unlocked? Uses the remembered addresses only."""
        unlocked: Set[int] = set()
        for h in hashes:
            for addr in self.records.get(h, ()):
                raw = self.mem.read(addr, 16)
                if len(raw) == 16:
                    rh, f1, f2, _ = struct.unpack("<4I", raw)
                    if rh == h and f1 == 1:
                        unlocked.add(h)
                        break
        return unlocked

    def is_stale(self, sample_hashes) -> bool:
        """True if remembered records no longer hold their hash (game reloaded / memory moved)."""
        for h in list(sample_hashes)[:5]:
            for addr in self.records.get(h, ())[:1]:
                raw = self.mem.read(addr, 4)
                if len(raw) == 4 and struct.unpack("<I", raw)[0] != h:
                    return True
        return False

    # ------------------------------------------------------------------ writing
    def unlock(self, h: int, friend: bool = False) -> Tuple[int, int]:
        """Unlock hash h. Returns (flag records written, list slots written)."""
        flags = 0
        for addr in self.records.get(h, ()):
            raw = self.mem.read(addr, 4)
            if len(raw) == 4 and struct.unpack("<I", raw)[0] == h:
                if self.mem.write(addr + 4, struct.pack("<II", 1, 1)):
                    flags += 1
        slots = 0
        if friend:
            for base in self.lists:
                raw = self.mem.read(base, LIST_SLOTS * 8)
                if len(raw) < LIST_SLOTS * 8:
                    continue
                for s in range(LIST_SLOTS):
                    sh = struct.unpack_from("<I", raw, s * 8)[0]
                    if sh == h:
                        break
                    if sh == EMPTY_SLOT:
                        if self.mem.write(base + s * 8, struct.pack("<II", h, 1)):
                            slots += 1
                        break
        return flags, slots
