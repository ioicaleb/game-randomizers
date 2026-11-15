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
            burned = 0
            for i in range(min(200, rec_cnt)):
                t_hash, burn_c, _, _ = struct.unpack_from("<IIII", data, b + 0x164 + i * 16)
                if t_hash != 0 and burn_c >= 1:
                    burned += 1
            combos = next(iter(struct.unpack_from("<I", data, b + 0x3C00)))
            slots[b] = {
                "slot_num": idx, "act": act, "sid": sid,
                "coins": coins, "stamps": stamps,
                "burned": min(140, burned), "combos": min(99, combos)
            }
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

def read_live_progress(pid, p_addr):
    try:
        with open(f"/proc/{pid}/mem", "rb", buffering=0) as mem:
            mem.seek(p_addr)
            buf = mem.read(0x3C20)
            rec_cnt = next(iter(struct.unpack_from("<I", buf, 0x160)))
            burned_toys = 0
            for i in range(min(200, rec_cnt)):
                t_hash, burn_c, _, _ = struct.unpack_from("<IIII", buf, 0x164 + i * 16)
                if t_hash != 0 and burn_c >= 1:
                    burned_toys += 1
            combo_cnt = next(iter(struct.unpack_from("<I", buf, 0x3C00)))
            return min(140, burned_toys), min(99, combo_cnt)
    except Exception:
        return None

def apply_ram_reward(pid, p_addr, add_c=0, add_s=0, set_cat=0, add_sl=0):
    try:
        with open(f"/proc/{pid}/mem", "r+b", buffering=0) as mem:
            mem.seek(p_addr + 0x008)
            coins, stamps = struct.unpack("<II", mem.read(8))
            if add_c or add_s:
                mem.seek(p_addr + 0x008)
                mem.write(struct.pack("<II", min(999, coins + add_c), min(99, stamps + add_s)))
            if set_cat > 0:
                mem.seek(p_addr + 0x018)
                cur_cat = next(iter(struct.unpack("<I", mem.read(4))))
                if set_cat > cur_cat:
                    mem.seek(p_addr + 0x018)
                    mem.write(struct.pack("<I", set_cat))
            if add_sl > 0:
                mem.seek(p_addr + 0x16C)
                cur_sl = next(iter(struct.unpack("<I", mem.read(4))))
                mem.seek(p_addr + 0x16C)
                mem.write(struct.pack("<I", min(8, cur_sl + add_sl)))
            print(f"[AP REWARD] Coins={min(999, coins+add_c)}, Stamps={min(99, stamps+add_s)}")
            return True
    except Exception:
        return False

async def main():
    prof_path = find_profiles_bin()
    if not prof_path:
        print("[ERROR] Could not find Little Inferno profiles.bin!")
        return

    url = input("Archipelago Server (default ws://localhost:38281): ").strip() or "ws://localhost:38281"
    slot = input("Slot Name (default inferno): ").strip() or "inferno"
    pw = input("Password (blank if none): ").strip()

    checked = set()
    pending = []
    initial_slots = read_all_slots(prof_path)
    active_base = None
    live_addr = None
    was_running = False

    async with websockets.connect(url) as ws:
        await ws.recv()
        await ws.send(json.dumps([{
            "cmd": "Connect", "password": pw, "game": "Little Inferno",
            "name": slot, "uuid": "li-ap-auto",
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
                            pending.append(it["item"])
            except asyncio.TimeoutError:
                pass

            pid = get_game_pid()
            if pid:
                was_running = True
            elif was_running:
                print("\n[GAME CLOSED] Little Inferno exited. Disconnecting...")
                break

            cur_slots = read_all_slots(prof_path)
            # Auto-detect whichever save slot changed since startup
            if active_base is None:
                for b, cur in cur_slots.items():
                    old = initial_slots.get(b)
                    if cur["act"] == 1 and cur["sid"] != 0 and old != cur:
                        active_base = b
                        print(f"[AUTO-DETECTED] Locked onto Fireplace Slot {cur['slot_num']} (SID=0x{cur['sid']:X})!")
                        break

            if pid and active_base is not None:
                prof = cur_slots[active_base]
                if not live_addr:
                    live_addr = find_live_profile_addr(pid, prof["sid"], prof["coins"])
                    if live_addr:
                        print(f"[AUTO-SYNC] Live RAM profile locked at 0x{live_addr:X}!")

                if live_addr:
                    if pending:
                        for code in pending:
                            if 20002 <= code <= 20007:
                                apply_ram_reward(pid, live_addr, set_cat=code - 20000)
                            elif code == 20010:
                                apply_ram_reward(pid, live_addr, add_sl=1)
                            elif code == 20030:
                                apply_ram_reward(pid, live_addr, add_c=50)
                            elif code == 20031:
                                apply_ram_reward(pid, live_addr, add_c=150)
                            elif code == 20032:
                                apply_ram_reward(pid, live_addr, add_s=5)
                        pending.clear()

                    res = read_live_progress(pid, live_addr)
                    if res:
                        burned_cnt, combo_cnt = res
                        new_locs = []
                        for b_i in range(burned_cnt):
                            lid = 10000 + b_i
                            if lid not in checked: checked.add(lid); new_locs.append(lid)
                        for c_i in range(combo_cnt):
                            lid = 11000 + c_i
                            if lid not in checked: checked.add(lid); new_locs.append(lid)
                        if new_locs:
                            print(f"[SEND CHECKS] {new_locs}")
                            await ws.send(json.dumps([{"cmd": "LocationChecks", "locations": new_locs}]))

asyncio.run(main())