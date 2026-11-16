import asyncio, json, os, platform, struct, websockets

PROFILE_BASES = (0x00020, 0x08520, 0x10A20)

def find_profiles_bin():
    if platform.system() == "Windows":
        p = os.path.join(os.environ.get("APPDATA", ""), "Tomorrow Corporation", "Little Inferno", "profiles.bin")
        if os.path.exists(p): return p
    p = os.path.expanduser("~/.local/share/Tomorrow Corporation/Little Inferno/profiles.bin")
    return p if os.path.exists(p) else ""

def get_game_pid():
    if platform.system() != "Linux":
        return None
    best_pid, best_rss = None, 0
    for pid in os.listdir("/proc"):
        if pid.isdigit():
            try:
                cmd = open(f"/proc/{pid}/cmdline", "rb").read().lower()
                if b"littleinferno" in cmd and b"python" not in cmd:
                    rss = int(open(f"/proc/{pid}/statm").read().split().pop(1))
                    if rss > best_rss:
                        best_rss, best_pid = rss, int(pid)
            except Exception:
                pass
    return best_pid

def read_all_slots(prof_path):
    slots = {}
    if not prof_path or not os.path.exists(prof_path):
        return slots
    data = open(prof_path, "rb").read()
    for idx, b in enumerate(PROFILE_BASES, 1):
        if b + 0x4000 <= len(data):
            act, sid, coins, stamps = struct.unpack_from("<IIII", data, b)
            rec_cnt = next(iter(struct.unpack_from("<I", data, b + 0x160)))
            slots[b] = {"slot_num": idx, "act": act, "sid": sid, "coins": coins, "stamps": stamps, "rec_cnt": rec_cnt}
    return slots

def find_live_profile_addr(pid, sid, expected_coins):
    if not pid or sid == 0:
        return None
    needle = struct.pack("<I", sid)
    maps_file, mem_file = f"/proc/{pid}/maps", f"/proc/{pid}/mem"
    if not os.path.exists(maps_file):
        return None
    try:
        with open(mem_file, "rb", buffering=0) as mem:
            for line in open(maps_file):
                parts = line.split()
                if len(parts) < 2: continue
                addr_s, perms = parts.pop(0), parts.pop(0)
                if not perms.startswith("rw"): continue
                s, e = [int(x, 16) for x in addr_s.split("-")]
                if s >= 0x7F0000000000: continue
                try:
                    mem.seek(s)
                    buf = mem.read(e - s)
                    pos = 0
                    while True:
                        idx = buf.find(needle, pos)
                        if idx == -1: break
                        pos = idx + 4
                        if idx >= 4 and idx + 0x4000 <= len(buf):
                            c_val = next(iter(struct.unpack_from("<I", buf, idx + 4)))
                            if c_val == expected_coins:
                                return s + idx - 4
                except Exception:
                    pass
    except PermissionError:
        pass
    return None

def sync_live_ram(pid, p_addr, unlocked_toys, max_cat, add_c=0, add_s=0, add_sl=0):
    purchased_indices = set()
    combo_cnt = 0
    try:
        with open(f"/proc/{pid}/mem", "r+b", buffering=0) as mem:
            mem.seek(p_addr + 0x008)
            coins, stamps = struct.unpack("<II", mem.read(8))
            if add_c or add_s:
                mem.seek(p_addr + 0x008)
                mem.write(struct.pack("<II", min(999, coins + add_c), min(99, stamps + add_s)))

            # Enforce received Catalog level (1..7)
            mem.seek(p_addr + 0x018)
            mem.write(struct.pack("<I", max_cat))

            if add_sl > 0:
                mem.seek(p_addr + 0x16C)
                cur_sl = next(iter(struct.unpack("<I", mem.read(4))))
                mem.seek(p_addr + 0x16C)
                mem.write(struct.pack("<I", min(8, cur_sl + add_sl)))

            # Enforce individual Toy unlocks by catalog slot index (0..139) & detect purchases
            mem.seek(p_addr + 0x160)
            rec_cnt = next(iter(struct.unpack("<I", mem.read(4))))
            for i in range(min(140, rec_cnt)):
                rec_off = p_addr + 0x164 + i * 16
                mem.seek(rec_off)
                th, unl, purch, res = struct.unpack("<IIII", mem.read(16))
                if th != 0:
                    if purch >= 1:
                        purchased_indices.add(i)
                    should_unl = 1 if (i < 4 or i in unlocked_toys) else 0
                    if unl != should_unl:
                        mem.seek(rec_off + 4)
                        mem.write(struct.pack("<I", should_unl))

            mem.seek(p_addr + 0x3C00)
            combo_cnt = min(99, next(iter(struct.unpack("<I", mem.read(4)))))
    except Exception:
        return None
    return purchased_indices, combo_cnt

async def main():
    prof_path = find_profiles_bin()
    if not prof_path:
        print("[ERROR] Could not find Little Inferno profiles.bin!")
        return

    url = input("Archipelago Server (default ws://localhost:38281): ").strip() or "ws://localhost:38281"
    slot = input("Slot Name (default inferno): ").strip() or "inferno"
    pw = input("Password (blank if none): ").strip()

    checked = set()
    unlocked_toys = {0, 1, 2, 3}
    max_cat = 1
    pending_c, pending_s, pending_sl = 0, 0, 0
    initial_slots = read_all_slots(prof_path)
    active_base = None
    live_addr = None
    was_running = False

    async with websockets.connect(url) as ws:
        await ws.recv()
        await ws.send(json.dumps([{
            "cmd": "Connect", "password": pw, "game": "Little Inferno",
            "name": slot, "uuid": "li-ap-toys",
            "version": {"major": 0, "minor": 5, "build": 0, "class": "Version"},
            "items_handling": 7, "tags": ["AP"]
        }]))
        print(f"[CONNECTED] Ready! Load or start ANY fireplace slot in Little Inferno...")

        while True:
            try:
                raw_msg = await asyncio.wait_for(ws.recv(), timeout=0.5)
                for pkt in json.loads(raw_msg):
                    if pkt.get("cmd") == "Connected":
                        checked.update(pkt.get("checked_locations", []))
                    elif pkt.get("cmd") == "ReceivedItems":
                        for it in pkt.get("items", []):
                            code = it["item"]
                            if 20002 <= code <= 20007:
                                max_cat = max(max_cat, code - 20000)
                                print(f"[UNLOCK] Catalog {max_cat} Unlocked!")
                            elif 21000 <= code <= 21139:
                                t_idx = code - 21000
                                unlocked_toys.add(t_idx)
                                print(f"[UNLOCK] Toy #{t_idx+1:03d} Unlocked in Catalog!")
                            elif code == 20010:
                                pending_sl += 1
                            elif code == 20030:
                                pending_c += 10
                            elif code == 20031:
                                pending_c += 25
                            elif code == 20032:
                                pending_s += 1
            except asyncio.TimeoutError:
                pass

            pid = get_game_pid()
            if pid:
                was_running = True
            elif was_running:
                print("\n[GAME CLOSED] Little Inferno exited. Disconnecting...")
                break

            cur_slots = read_all_slots(prof_path)
            if active_base is None:
                for b, cur in cur_slots.items():
                    old = initial_slots.get(b)
                    if cur["act"] == 1 and cur["sid"] != 0 and old != cur:
                        active_base = b
                        print(f"[AUTO-DETECTED] Locked onto Fireplace Slot {cur['slot_num']}!")
                        break

            if pid and active_base is not None:
                prof = cur_slots[active_base]
                if not live_addr:
                    live_addr = find_live_profile_addr(pid, prof["sid"], prof["coins"])
                    if live_addr:
                        print(f"[AUTO-SYNC] Live Catalog & Toy RAM locked at 0x{live_addr:X}!")

                if live_addr:
                    res = sync_live_ram(pid, live_addr, unlocked_toys, max_cat, pending_c, pending_s, pending_sl)
                    pending_c, pending_s, pending_sl = 0, 0, 0
                    if res:
                        purch_set, combo_cnt = res
                        new_locs = []
                        for t_idx in sorted(purch_set):
                            lid = 10000 + t_idx
                            if lid not in checked:
                                checked.add(lid)
                                new_locs.append(lid)
                        for c_i in range(combo_cnt):
                            lid = 11000 + c_i
                            if lid not in checked:
                                checked.add(lid)
                                new_locs.append(lid)
                        if new_locs:
                            print(f"[SEND CHECKS] {new_locs}")
                            await ws.send(json.dumps([{"cmd": "LocationChecks", "locations": new_locs}]))

asyncio.run(main())
