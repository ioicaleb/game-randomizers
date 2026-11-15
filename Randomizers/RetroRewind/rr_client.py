import asyncio, json, os, struct, websockets

SAVE_DIR = "/mnt/E8A2D79FA2D77114/SteamLibrary/steamapps/compatdata/3552140/pfx/drive_c/users/steamuser/AppData/Local/RetroRewind/Saved/SaveGames"

PROP_LEVEL = b"Level_4_D665A6394BEDE281DFD626929A94188A"
PROP_QUEST = b"QuestDone_4_5224F922428CA5DFA7E86B9ED8E88D90"
PROP_UNLCK = b"Unlocked_1_A29582E64DE8D2675CBC1AB7D44C8C4C"
PROP_ACHV  = b"Unlocked_5_457535AC4191AF9B76F91391BA221BB1"

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

def scan_cash_candidates(pid, cash_val):
    cands = []
    # Scan for both int64 and int32 representations of current Cash
    needles = [("q", struct.pack("<Q", cash_val)), ("i", struct.pack("<I", cash_val))]
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
                        cands.append((tag, s + idx))
            except Exception:
                pass
    return cands

def filter_cash_candidates(pid, cands, new_cash):
    exact = []
    with open(f"/proc/{pid}/mem", "rb", buffering=0) as mem:
        for tag, addr in cands:
            try:
                mem.seek(addr)
                val = next(iter(struct.unpack("<Q" if tag == "q" else "<I", mem.read(8 if tag == "q" else 4))))
                if val == new_cash:
                    exact.append((tag, addr))
            except Exception:
                pass
    return exact

def add_live_cash(pid, exact_addrs, amount):
    with open(f"/proc/{pid}/mem", "r+b", buffering=0) as mem:
        for tag, addr in exact_addrs:
            mem.seek(addr)
            cur = next(iter(struct.unpack("<Q" if tag == "q" else "<I", mem.read(8 if tag == "q" else 4))))
            mem.seek(addr)
            mem.write(struct.pack("<Q" if tag == "q" else "<I", cur + amount))
            print(f"[LIVE RAM SYNC] Cash updated in-game: ${cur} -> ${cur + amount}")

def count_true_bools(data, prop_bytes):
    cnt = 0
    pos = 0
    while True:
        idx = data.find(prop_bytes, pos)
        if idx == -1: break
        pos = idx + len(prop_bytes)
        if pos + 25 <= len(data) and data[pos + 24] == 1:
            cnt += 1
    return cnt

def parse_gvas_progress(sav_path):
    if not sav_path or not os.path.exists(sav_path):
        return None
    data = open(sav_path, "rb").read()
    lvl = 1
    p_lvl = data.find(PROP_LEVEL)
    if p_lvl != -1 and p_lvl + len(PROP_LEVEL) + 30 <= len(data):
        lvl = next(iter(struct.unpack_from("<I", data, p_lvl + len(PROP_LEVEL) + 26)))
    return {
        "level": min(20, max(1, lvl)),
        "quests": min(25, count_true_bools(data, PROP_QUEST)),
        "unlocks": min(20, count_true_bools(data, PROP_UNLCK)),
        "milestones": min(26, count_true_bools(data, PROP_ACHV))
    }

async def main():
    url = input("Server (default ws://localhost:38281): ").strip() or "ws://localhost:38281"
    slot = input("Slot Name (default videos): ").strip() or "videos"
    pw = input("Password (blank if none): ").strip()
    save_num = input("Save Slot Number (default 2 -> Player_Save2.sav): ").strip() or "2"
    sav_path = os.path.join(SAVE_DIR, f"Player_Save{save_num}.sav")

    pid = get_game_pid()
    if not pid:
        print("[ERROR] Launch Retro Rewind and load into your store first!")
        return

    c1 = int(input("Step 1 - Enter your exact current Cash in-game (whole dollars, e.g. 500): ").strip())
    cands = scan_cash_candidates(pid, c1)
    print(f"Found {len(cands)} candidate addresses.")
    c2 = int(input("Step 2 - Rent/buy 1 item so Cash changes, then enter new Cash: ").strip())
    exact_addrs = filter_cash_candidates(pid, cands, c2)
    if not exact_addrs:
        print("[ERROR] Could not isolate Cash address. Try again with a unique Cash value!")
        return
    print(f"[LOCKED ON] Exact Live Cash Address(es): {[(t, hex(a)) for t, a in exact_addrs]}")

    checked = set()
    pending_cash = 0
    baseline = parse_gvas_progress(sav_path) if os.path.exists(sav_path) else {"level": 1, "quests": 0, "unlocks": 0, "milestones": 0}
    last_mtime = os.path.getmtime(sav_path) if os.path.exists(sav_path) else 0

    async with websockets.connect(url) as ws:
        await ws.recv()
        await ws.send(json.dumps([{
            "cmd": "Connect", "password": pw, "game": "Retro Rewind",
            "name": slot, "uuid": "rr-ap-client",
            "version": {"major": 0, "minor": 5, "build": 0, "class": "Version"},
            "items_handling": 7, "tags": ["AP"]
        }]))
        print(f"[CONNECTED] Live syncing Retro Rewind as '{slot}'...")

        while True:
            try:
                raw_msg = await asyncio.wait_for(ws.recv(), timeout=0.5)
                for pkt in json.loads(raw_msg):
                    if pkt.get("cmd") == "Connected":
                        checked.update(pkt.get("checked_locations", []))
                    elif pkt.get("cmd") == "ReceivedItems":
                        for it in pkt.get("items", []):
                            code = it["item"]
                            print(f"[AP ITEM RECEIVED] Item ID {code}")
                            if code == 20020: pending_cash += 100
                            elif code == 20030: pending_cash += 50
                            elif code == 20031: pending_cash += 150
                            elif code == 20032: pending_cash += 500
                            elif 20001 <= code <= 20016: pending_cash += 250
            except asyncio.TimeoutError:
                pass

            cur_pid = get_game_pid()
            if not cur_pid:
                print("\n[GAME CLOSED] Retro Rewind exited. Disconnecting...")
                break

            if pending_cash > 0:
                add_live_cash(cur_pid, exact_addrs, pending_cash)
                pending_cash = 0

            if os.path.exists(sav_path):
                cur_mtime = os.path.getmtime(sav_path)
                if cur_mtime > last_mtime:
                    last_mtime = cur_mtime
                    st = parse_gvas_progress(sav_path)
                    if st:
                        new_locs = []
                        for l_i in range(max(0, st["level"] - 1)):
                            lid = 10000 + l_i
                            if lid not in checked: checked.add(lid); new_locs.append(lid)
                        for q_i in range(max(0, st["quests"] - baseline["quests"])):
                            lid = 10100 + q_i
                            if lid not in checked: checked.add(lid); new_locs.append(lid)
                        for u_i in range(max(0, st["unlocks"] - baseline["unlocks"])):
                            lid = 10200 + u_i
                            if lid not in checked: checked.add(lid); new_locs.append(lid)
                        for m_i in range(max(0, st["milestones"] - baseline["milestones"])):
                            lid = 10300 + m_i
                            if lid not in checked: checked.add(lid); new_locs.append(lid)
                        if new_locs:
                            print(f"[SEND CHECKS] {new_locs}")
                            await ws.send(json.dumps([{"cmd": "LocationChecks", "locations": new_locs}]))

asyncio.run(main())
