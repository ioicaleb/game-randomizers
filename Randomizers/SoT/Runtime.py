"""
GameRuntime: everything the client does with the game, with no Archipelago code in it (so it can be tested alone).

Life cycle:
  prepare()  - patch the game's data for this seed (game must be closed) and load hash tables
  attach()   - find the running game and open its memory
  arm()      - the player has loaded a save: find the unlock table and remember what is already unlocked
  poll()     - called every second: deliver pending unlocks, notice new unlocks / pickups, return new check ids
"""
import json
import os
from typing import Callable, Dict, List, Optional, Set, Tuple

from . import GameData, GameMemory, GamePatcher, GameSaves
from .Friends import FRIEND_LIST
from .UnlockTable import UnlockTable

CONFIRM_POLLS = 2          # a new unlock must be seen on this many polls in a row before it becomes a check
FRIEND_BASE = 20000


class GameClosed(Exception):
    pass


class GameRuntime:
    def __init__(self, log: Callable[[str], None] = print):
        self.log = log
        self.cfg: Dict[str, str] = {}
        self.unlock_hashes_all: Set[int] = set()
        self.friend_hash: Dict[str, int] = {}                 # friend id -> hash
        self.tracked: Dict[int, int] = {}                     # unlock hash -> location id (friends + items)
        self.item_unlock_by_id: Dict[int, int] = {}           # item id -> unlock hash (deliverable items)
        self.friend_hashes: Set[int] = set()
        self.slot_hash_to_loc: Dict[int, int] = {}            # item blueprint hash -> location id (for saves)
        self.mem: Optional[GameMemory.ProcessMemory] = None
        self.table: Optional[UnlockTable] = None
        self.armed = False
        self.baseline: Set[int] = set()
        self.streak: Dict[int, int] = {}
        self.seen_unlocks: Set[int] = set()
        self.seen_inventory: Set[int] = set()
        self.last_save_stamp = None
        self.pending: List[Tuple[str, int, bool]] = []
        self.delivered: Set[int] = set()
        self.failed_deliveries: Dict[int, int] = {}

    # ------------------------------------------------------------------ preparation
    def prepare(self, slot_data: dict, my_slot: int) -> bool:
        self.cfg = GameData.load_config(self.log)
        game_dir = self.cfg.get("game_dir", "")
        if not game_dir or not os.path.isdir(game_dir):
            self.log(f"[SETUP] Game folder not found ('{game_dir}'). Edit {GameData.config_file()} and type /patch.")
            return False
        self.unlock_hashes_all = GameData.load_unlock_hashes()

        # which unlocks do we watch / deliver?
        item_unlocks = {int(k): int(v) for k, v in slot_data.get("unlock_hashes", {}).items()}
        self.tracked = {h: item_id for item_id, h in item_unlocks.items()}   # location id == item id for same index
        self.item_unlock_by_id = item_unlocks

        if slot_data.get("shuffle_friends"):
            if not self._load_friend_hashes(game_dir):
                self.log("[SETUP] Friend ids could not be read: friends will not be tracked or delivered this session.")
            for idx, name in enumerate(FRIEND_LIST):
                h = self.friend_hash.get(name)
                if h is not None:
                    self.tracked[h] = FRIEND_BASE + idx
                    self.friend_hashes.add(h)
        self.unlock_hashes_all |= set(self.tracked)

        # patch the archive (or just work out the item->location table if the game is already running)
        slot_mapping = {int(k): v for k, v in slot_data["slot_mapping"].items()}
        game_running = GameMemory.find_game_pid() is not None
        mapping = GamePatcher.patch_archive(
            game_dir, GameData.load_blueprint_hashes(), slot_mapping, my_slot, set(item_unlocks),
            patch_jimbo=os.environ.get("SOT_PATCH_JIMBO") != "0", dry_run=game_running, log=self.log)
        if mapping is None:
            return False
        self.slot_hash_to_loc = mapping
        return True

    def _load_friend_hashes(self, game_dir: str) -> bool:
        cache = GameData.friend_cache_file()
        try:
            with open(cache) as f:
                self.friend_hash = {k: int(v) for k, v in json.load(f).items()}
        except (OSError, ValueError):
            self.friend_hash = {}
        if all(n in self.friend_hash for n in FRIEND_LIST):
            return True
        self.log("[SETUP] Looking up friend ids in the game archive (first run only)...")
        found = GameData.friend_hashes_from_archive(os.path.join(game_dir, "data_archive.oaf"), FRIEND_LIST)
        missing = [n for n in FRIEND_LIST if n not in found]
        if missing:
            self.log(f"[SETUP] Could not identify {len(missing)} friends in the archive ({', '.join(missing[:4])}...). "
                     f"Friend delivery will skip them.")
        self.friend_hash = found
        try:
            with open(cache, "w") as f:
                json.dump(found, f)
        except OSError:
            pass
        return bool(found)

    # ------------------------------------------------------------------ attaching
    def attach(self) -> bool:
        if self.mem is not None and self.mem.alive():
            return True
        self.mem = None
        self.table = None
        self.armed = False
        pid = GameMemory.find_game_pid()
        if pid is None:
            return False
        try:
            self.mem = GameMemory.open_memory(pid)
        except OSError as e:
            self.log(f"[GAME] Found the game (pid {pid}) but could not open its memory: {e}")
            return False
        self.log(f"[GAME] Attached to the game (pid {pid}).")
        return True

    def arm(self) -> int:
        """Find the unlock table and remember what is already unlocked. Call with a save loaded."""
        self.table = UnlockTable(self.mem, self.unlock_hashes_all)
        n = self.table.discover()
        self.baseline = self.table.read_unlocked(self.tracked)
        self.streak.clear()
        self.seen_unlocks.clear()
        self.seen_inventory.clear()
        self.delivered.clear()
        self.failed_deliveries.clear()
        self.last_save_stamp = None
        self.armed = n > 0
        self.log(f"[ARMED] {n} unlock records found, {len(self.baseline)} tracked unlocks already owned (ignored).")
        if n == 0:
            self.log("[ARMED] No unlock table found. Is a save loaded? Load one and type /arm again.")
        return n

    # ------------------------------------------------------------------ deliveries
    def queue_delivery(self, label: str, unlock_hash: int, is_friend: bool):
        if unlock_hash not in self.delivered and all(unlock_hash != h for _, h, _ in self.pending):
            self.pending.append((label, unlock_hash, is_friend))

    def _deliver(self):
        still = []
        for label, h, is_friend in self.pending:
            self.baseline.add(h)                 # our own unlock must never come back as a check
            flags, slots = self.table.unlock(h, friend=is_friend)
            if flags:
                self.delivered.add(h)
                self.log(f"[UNLOCK] {label}: {flags} flag record(s)" + (f", {slots} list slot(s)" if is_friend else ""))
            else:
                n = self.failed_deliveries.get(h, 0) + 1
                self.failed_deliveries[h] = n
                if n == 1 or n % 30 == 0:
                    self.log(f"[UNLOCK] {label}: nowhere to write it yet (table not found for this unlock); will retry.")
                still.append((label, h, is_friend))
        self.pending = still

    # ------------------------------------------------------------------ polling
    def poll(self) -> List[int]:
        """Returns location ids that should now be checked."""
        if self.mem is None or not self.mem.alive():
            raise GameClosed()
        new: List[int] = []

        if self.table.is_stale(self.tracked):
            self.log("[GAME] The unlock table moved (save reloaded?). Searching again...")
            self.table.discover()

        if self.pending:
            self._deliver()

        unlocked = self.table.read_unlocked(self.tracked)
        for h in [h for h in self.streak if h not in unlocked]:
            del self.streak[h]
        for h in unlocked:
            if h in self.baseline or h in self.seen_unlocks:
                continue
            self.streak[h] = self.streak.get(h, 0) + 1
            if self.streak[h] >= CONFIRM_POLLS:
                self.seen_unlocks.add(h)
                new.append(self.tracked[h])
                self.log(f"[CHECK] Unlock 0x{h:08X} obtained in-game -> location {self.tracked[h]}")

        path = GameSaves.newest_save(self.cfg.get("save_dir", ""))
        if path:
            try:
                st = os.stat(path)
                stamp = (path, st.st_mtime_ns, st.st_size)
            except OSError:
                stamp = None
            if stamp and stamp != self.last_save_stamp:
                owned = GameSaves.read_inventory(path, self.slot_hash_to_loc)
                if owned is not None:
                    self.last_save_stamp = stamp
                    for h in owned:
                        if h not in self.seen_inventory:
                            self.seen_inventory.add(h)
                            new.append(self.slot_hash_to_loc[h])
                            self.log(f"[CHECK] Picked up item 0x{h:08X} -> location {self.slot_hash_to_loc[h]}")
        return new
