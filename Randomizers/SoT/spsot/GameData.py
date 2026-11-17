"""
Game data the client needs besides the slot data, and where the player's files are.

  * unlock_hashes.json   - ships with the apworld: every unlockable's hash (to recognise the real table in memory)
  * friend hashes        - found inside the game's own archive the first time, then cached in a small JSON file
  * paths                - game folder + save folder, from a config file the player can edit, else auto-detected
"""
import json
import mmap
import os
import pkgutil
import re
import struct
import sys
from typing import Dict, List, Optional

GAME_FOLDER = "South Park - The Stick of Truth"
STEAM_APP_ID = "213670"


# --------------------------------------------------------------------------- shipped data
def load_unlock_hashes() -> set:
    raw = pkgutil.get_data(__package__, "unlock_hashes.json")
    return set(json.loads(raw.decode("utf-8"))["unlock_hashes"])


def load_blueprint_hashes() -> List[int]:
    """Blueprint hash of every item index 0..994, in order (used to find the item table in the archive)."""
    items = json.loads(pkgutil.get_data(__package__, "logic_rules.json").decode("utf-8-sig"))["Items"]
    by_index = {i["ItemIndex"]: i["BlueprintHash"] for i in items}
    return [by_index[i] for i in range(995)]


# --------------------------------------------------------------------------- friend hashes
def _friend_hash_at(buf, pos: int, name_len: int) -> Optional[int]:
    """If a friend record's name starts at pos, return its hash (the length field before the name must match)."""
    if pos < 12:
        return None
    nxt = buf[pos + name_len: pos + name_len + 1]
    if nxt and 32 <= nxt[0] <= 126:          # the name must end here (next byte not printable), as in the C# client
        return None
    if struct.unpack("<i", buf[pos - 8: pos - 4])[0] != name_len:
        return None
    return struct.unpack("<I", buf[pos - 12: pos - 8])[0]


def friend_hashes_from_archive(archive: str, friend_names: List[str]) -> Dict[str, int]:
    """
    social_network.ogd stores each friend as  [hash][name length][?][name text].  We look for a friend's name in the
    archive and accept it only where the length field before it matches. The first friend needs a whole-archive
    search; the rest are in the same small file, so they are searched for in a window around it.
    """
    found: Dict[str, int] = {}
    with open(archive, "rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        anchor = None
        for name in friend_names:
            variants = [v.encode("ascii") for v in dict.fromkeys([name, name.lower()])]
            if anchor is None:
                for needle in variants:
                    pos = mm.find(needle)
                    while pos != -1:
                        h = _friend_hash_at(mm, pos, len(needle))
                        if h is not None:
                            found[name], anchor = h, pos
                            break
                        pos = mm.find(needle, pos + 1)
                    if anchor is not None:
                        break
                continue
            lo = max(0, anchor - 262144)
            window = bytes(mm[lo: anchor + 262144])
            for needle in variants:
                idx = window.find(needle)
                while idx != -1:
                    h = _friend_hash_at(window, idx, len(needle))
                    if h is not None:
                        found[name] = h
                        break
                    idx = window.find(needle, idx + 1)
                if name in found:
                    break
    return found


# --------------------------------------------------------------------------- config
def _user_dir() -> str:
    try:
        import Utils
        return os.path.dirname(Utils.user_path("x"))
    except Exception:
        return os.path.expanduser("~")


def config_file() -> str:
    return os.path.join(_user_dir(), "spsot_client.json")


def friend_cache_file() -> str:
    return os.path.join(_user_dir(), "spsot_friend_hashes.json")


def _steam_libraries() -> List[str]:
    roots = []
    if sys.platform == "win32":
        for env in ("ProgramFiles(x86)", "ProgramFiles"):
            if os.environ.get(env):
                roots.append(os.path.join(os.environ[env], "Steam"))
    else:
        home = os.path.expanduser("~")
        roots += [os.path.join(home, ".steam", "steam"), os.path.join(home, ".local", "share", "Steam"),
                  os.path.join(home, ".var", "app", "com.valvesoftware.Steam", ".local", "share", "Steam")]
    libs = []
    for root in roots:
        if os.path.isdir(root):
            libs.append(root)
        vdf = os.path.join(root, "steamapps", "libraryfolders.vdf")
        if os.path.isfile(vdf):
            with open(vdf, encoding="utf-8", errors="ignore") as f:
                libs += [p.replace("\\\\", "\\") for p in re.findall(r'"path"\s+"([^"]+)"', f.read())]
    seen, out = set(), []
    for lib in libs:
        if lib not in seen:
            seen.add(lib)
            out.append(lib)
    return out


def autodetect() -> Dict[str, str]:
    cfg = {"game_dir": "", "save_dir": ""}
    for lib in _steam_libraries():
        game = os.path.join(lib, "steamapps", "common", GAME_FOLDER)
        if os.path.isdir(game) and not cfg["game_dir"]:
            cfg["game_dir"] = game
        proton = os.path.join(lib, "steamapps", "compatdata", STEAM_APP_ID, "pfx", "drive_c", "users", "steamuser",
                              "Documents", "My Games", GAME_FOLDER, "save")
        if os.path.isdir(proton) and not cfg["save_dir"]:
            cfg["save_dir"] = proton
    if not cfg["save_dir"]:
        win = os.path.join(os.path.expanduser("~"), "Documents", "My Games", GAME_FOLDER, "save")
        if os.path.isdir(win):
            cfg["save_dir"] = win
    return cfg


def load_config(log=print) -> Dict[str, str]:
    """Config file wins; missing values are auto-detected; environment variables override both."""
    cfg = {"game_dir": "", "save_dir": ""}
    path = config_file()
    if os.path.isfile(path):
        try:
            with open(path) as f:
                cfg.update({k: v for k, v in json.load(f).items() if v})
        except (OSError, ValueError):
            log(f"[CONFIG] Could not read {path}; using auto-detection.")
    for key, auto in autodetect().items():
        cfg[key] = cfg.get(key) or auto
    cfg["game_dir"] = os.environ.get("SOT_GAME_DIR") or cfg["game_dir"]
    cfg["save_dir"] = os.environ.get("SOT_SAVE_DIR") or cfg["save_dir"]
    if not os.path.isfile(path):
        try:
            with open(path, "w") as f:
                json.dump(cfg, f, indent=2)
            log(f"[CONFIG] Wrote {path}. Edit it if the game or save folder below is wrong.")
        except OSError:
            pass
    return cfg
