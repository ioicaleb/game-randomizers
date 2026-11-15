import asyncio, glob, json, os, platform, struct, time, websockets

PROP_MONEY = b"Money64_14_4E3C8A914A3F4058F90C30BD533FEF7E"
PROP_LEVEL = b"Level_4_D665A6394BEDE281DFD626929A94188A"
PROP_QUEST = b"QuestDone_4_5224F922428CA5DFA7E86B9ED8E88D90"
PROP_UNLCK = b"Unlocked_1_A29582E64DE8D2675CBC1AB7D44C8C4C"
PROP_ACHV  = b"Unlocked_5_457535AC4191AF9B76F91391BA221BB1"

def find_save_dir():
    if platform.system() == "Windows":
        return os.path.join(os.environ.get("LOCALAPPDATA", ""), "RetroRewind", "Saved", "SaveGames")
    # Search standard Steam library locations on Linux for AppID 3552140
    candidates = [
        os.path.expanduser("~/.local/share/Steam/steamapps/compatdata/3552140"),
        os.path.expanduser("~/.steam/steam/steamapps/compatdata/3552140"),
        "/mnt/E8A2D79FA2D77114/SteamLibrary/steamapps/compatdata/3552140"
    ]
    for base in candidates:
        p = os.path.join(base, "pfx/drive_c/users/steamuser/AppData/Local/RetroRewind/Saved/SaveGames")
        if os.path.isdir(p):
            return p
    return ""

def get_game_pid():
    best_pid, best_rss = None, 0
    for pid in os.listdir("/proc"):
        if pid.isdigit():
            try:
                cmd = open(f"/proc/{pid}/cmdline", "rb").read().lower()
                if b"retrorewind-win64-shipping" in cmd:
                    rss = int(open(f"/proc/{pid}/statm").read().split().pop(1))
                    if rss > best_rss:
                        best_rss, best_pid = rss, int(pid)
            except Exception:
                pass
    return best_pid

def count_true_bools(data, prop_bytes):
    cnt, pos = 0, 0
    while True:
        idx = data.find(prop_bytes, pos)
        if idx == -1: break
        pos = idx + len(prop_bytes)
        if pos + 25 <= len(data) and data[pos + 24] == 1:
            cnt += 1
    return cnt

def read_save_snapshot(sav_path):
    data = open(sav_path, "rb").read()
    lvl = 1
    p_lvl = data.find(PROP_LEVEL)
    if p_lvl != -1 and p_lvl + len(PROP_LEVEL) + 30 <= len(data):
        lvl = next(iter(struct.unpack_from("<I", data, p_lvl + len(PROP_LEVEL) + 26)))
    money = 0
    p_m = data.find(PROP_MONEY)
    if p_m != -1 and p_m + len(PROP_MONEY) + 36 <= len(data):
        money = next(iter(struct.unpack_from("<Q", data, p_m + len(PROP_MONEY) + 28)))
    return {
        "money": money,
        "level": min(20, max(1, lvl)),
        "quests": min(25, count_true_bools(data, PROP_QUEST)),
        "unlocks": min(20, count_true_bools(data, PROP_UNLCK)),
        "milestones": min(26, count_true_bools(data, PROP_ACHV))
    }

def auto_lock_cash_addresses(pid, cash_val):
    if cash_val <= 0:
        return []
    needles = [("q", struct.pack("<Q", cash_val)), ("i", struct.pack("<I", cash_val))]
    hits = []
    try:
        with open(f"/proc/{pid}/mem", "rb", buffering=0) as mem:
            for line in open(f"/proc/{pid}/maps"):
                parts = line.split()
                if len(parts) < 2: continue
                addr_s, perms = parts.pop(0), parts.pop(0)
                if not perms.startswith("rw"): continue
                s, e = [int(x, 16) for x in addr_s.split("-")]
                if s >= 0x7F0000000000: continue
                try:
                    mem.seek(s)
                    buf = mem.read(e - s)
                    for tag, ndl in needles:
                        pos = 0
                        while True:
                            idx = buf.find(ndl, pos)
                            if idx == -1: break
                            pos = idx + 4
                            hits.append((tag, s + idx))
                except Exception:
                    pass
    except PermissionError:
        pass
    return hits

def add_live_cash(pid, addrs, amount):
    try:
        with open(f"/proc/{pid}/mem", "r+b", buffering=0) as mem:
            for tag, addr in addrs:
                mem.seek(addr)
                cur = next(iter(struct.unpack("<Q" if tag == "q" else "<I", mem.read(8 if tag == "q" else 4))))
                mem.seek(addr)
                mem.write(struct.pack("<Q" if tag == "q" else "<I", cur + amount))
            print(f"[AP REWARD] Added +${amount} live in-game!")
    except Exception:
        pass

async def main():
    save_dir = find_save_dir()
    if not save_dir:
        print("[ERROR] Could not locate Retro Rewind SaveGames folder.")
        return

    url = input("Archipelago Server (default ws://localhost:38281): ").strip() or "ws://localhost:38281"
    slot = input("Slot Name: ").strip() or "videos"
    pw = input("Password (blank if none): ").strip()

    checked = set()
    pending_cash = 0
    active_sav = None
    baseline = None
    cash_cands = []
    exact_addrs = []
    last_cash_seen = None
    known_mtimes = {f: os.path.getmtime(f) for f in glob.glob(os.path.join(save_dir, "Player_Save*.sav")) if "backup" not in f}

    async with websockets.connect(url) as ws:
        await ws.recv()
        await ws.send(json.dumps([{
            "cmd": "Connect", "password": pw, "game": "Retro Rewind",
            "name": slot, "uuid": "rr-ap-auto",
            "version": {"major": 0, "minor": 5, "build": 0, "class": "Version"},
            "items_handling": 7, "tags": ["AP"]
        }]))
        print(f"[CONNECTED] Ready! Load or start ANY save slot in Retro Rewind...")

        while True:
            try:
                raw_msg = await asyncio.wait_for(ws.recv(), timeout=0.5)
                for pkt in json.loads(raw_msg):
                    if pkt.get("cmd") == "Connected":
                        checked.update(pkt.get("checked_locations", []))
                    elif pkt.get("cmd") == "ReceivedItems":
                        for it in pkt.get("items", []):
                            code = it["item"]
                            if code == 20020: pending_cash += 100
                            elif code == 20030: pending_cash += 50
                            elif code == 20031: pending_cash += 150
                            elif code == 20032: pending_cash += 500
                            elif 20001 <= code <= 20016: pending_cash += 250
            except asyncio.TimeoutError:
                pass

            pid = get_game_pid()

            # Auto-detect whichever save slot gets created or updated
            for f in glob.glob(os.path.join(save_dir, "Player_Save*.sav")):
                if "backup" in os.path.basename(f):
                    continue
                mt = os.path.getmtime(f)
                if f not in known_mtimes or mt > known_mtimes[f]:
                    known_mtimes[f] = mt
                    if active_sav != f:
                        active_sav = f
                        baseline = read_save_snapshot(f)
                        print(f"[AUTO-DETECTED] Locked onto {os.path.basename(f)}!")

                    snap = read_save_snapshot(f)
                    # Automatically isolate Cash address across two consecutive auto-saves
                    if pid and not exact_addrs:
                        if not cash_cands and snap["money"] > 0:
                            cash_cands = auto_lock_cash_addresses(pid, snap["money"])
                            last_cash_seen = snap["money"]
                        elif cash_cands and snap["money"] != last_cash_seen:
                            new_cands = set(auto_lock_cash_addresses(pid, snap["money"]))
                            exact_addrs = [c for c in cash_cands if c in new_cands]
                            if exact_addrs:
                                print("[AUTO-SYNC] Live Cash memory locked automatically!")

                    # Send any new checks earned since baseline
                    new_locs = []
                    for l_i in range(max(0, snap["level"] - 1)):
                        lid = 10000 + l_i
                        if lid not in checked: checked.add(lid); new_locs.append(lid)
                    for q_i in range(max(0, snap["quests"] - baseline["quests"])):
                        lid = 10100 + q_i
                        if lid not in checked: checked.add(lid); new_locs.append(lid)
                    for u_i in range(max(0, snap["unlocks"] - baseline["unlocks"])):
                        lid = 10200 + u_i
                        if lid not in checked: checked.add(lid); new_locs.append(lid)
                    for m_i in range(max(0, snap["milestones"] - baseline["milestones"])):
                        lid = 10300 + m_i
                        if lid not in checked: checked.add(lid); new_locs.append(lid)
                    if new_locs:
                        print(f"[SEND CHECKS] {new_locs}")
                        await ws.send(json.dumps([{"cmd": "LocationChecks", "locations": new_locs}]))

            if pid and exact_addrs and pending_cash > 0:
                add_live_cash(pid, exact_addrs, pending_cash)
                pending_cash = 0

asyncio.run(main())