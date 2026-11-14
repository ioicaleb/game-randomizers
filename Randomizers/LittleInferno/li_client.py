import asyncio, json, os, struct, subprocess, websockets

PROF_PATH = os.path.expanduser(
    "~/.local/share/Tomorrow Corporation/Little Inferno/profiles.bin"
)
PROFILE_BASES = (0x08520,)

def get_pid():
    best_pid, best_rss = None, 0
    out = subprocess.check_output(["ps", "-eo", "pid,rss,args"], text=True)
    for line in out.splitlines():
        low = line.lower()
        if "littleinferno" in low and "python" not in low:
            parts = line.split()
            pid, rss = int(parts.pop(0)), int(parts.pop(0))
            if rss > best_rss:
                best_rss, best_pid = rss, pid
    return best_pid

def get_active_profile_from_disk():
    if not os.path.exists(PROF_PATH):
        return None
    data = open(PROF_PATH, "rb").read()
    for b in PROFILE_BASES:
        if b + 0x4000 <= len(data):
            act, sid, coins, stamps = struct.unpack_from("<IIII", data, b)
            if act == 1 and sid != 0:
                return {"base": b, "sid": sid, "coins": coins, "stamps": stamps}
    return None

def find_live_profile_addr(pid, sid, expected_coins):
    needle = struct.pack("<I", sid)
    maps_file = f"/proc/{pid}/maps"
    mem_file = f"/proc/{pid}/mem"
    if not os.path.exists(maps_file):
        return None
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
    return None

def read_live_progress(pid, p_addr):
    with open(f"/proc/{pid}/mem", "rb", buffering=0) as mem:
        mem.seek(p_addr)
        buf = mem.read(0x3C20)
        rec_cnt = next(iter(struct.unpack_from("<I", buf, 0x160)))
        burned_toys = 0
        for i in range(min(200, rec_cnt)):
            t_hash, burn_c, buy_c, _ = struct.unpack_from("<IIII", buf, 0x164 + i * 16)
            # Only count actual toys that have been burned (burn_c >= 1)
            if t_hash != 0 and burn_c >= 1:
                burned_toys += 1
        combo_cnt = next(iter(struct.unpack_from("<I", buf, 0x3C00)))
        return min(140, burned_toys), min(99, combo_cnt)

def apply_ram_reward(pid, p_addr, add_c=0, add_s=0, set_cat=0, add_sl=0):
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
        print(f"[RAM SYNC] Coins={coins+add_c}, Stamps={stamps+add_s}, Cat={max(set_cat, 1)}")

async def main():
    url = input("Server (default ws://localhost:38281): ").strip() or "ws://localhost:38281"
    slot = input("Slot Name (default inferno): ").strip() or "inferno"
    pw = input("Password (blank if none): ").strip()

    checked = set()
    pending = []
    live_addr = None
    was_running = False

    async with websockets.connect(url) as ws:
        await ws.recv()
        await ws.send(json.dumps([{
            "cmd": "Connect", "password": pw, "game": "Little Inferno",
            "name": slot, "uuid": "li-ap-client",
            "version": {"major": 0, "minor": 5, "build": 0, "class": "Version"},
            "items_handling": 7, "tags": ["AP"]
        }]))
        print(f"[CONNECTED] Syncing Little Inferno as '{slot}'...")

        while True:
            try:
                raw_msg = await asyncio.wait_for(ws.recv(), timeout=0.5)
                for pkt in json.loads(raw_msg):
                    if pkt.get("cmd") == "Connected":
                        checked.update(pkt.get("checked_locations", []))
                    elif pkt.get("cmd") == "ReceivedItems":
                        for it in pkt.get("items", []):
                            print(f"[AP ITEM RECEIVED] Item ID {it['item']}")
                            pending.append(it["item"])
            except asyncio.TimeoutError:
                pass

            pid = get_pid()
            prof = get_active_profile_from_disk()
            if pid:
                was_running = True
            elif was_running:
                print("\n[GAME CLOSED] Little Inferno exited. Disconnecting...")
                break
            if pid and prof:
                if not live_addr:
                    live_addr = find_live_profile_addr(pid, prof["sid"], prof["coins"])
                    if live_addr:
                        print(f"[LOCKED ON] Live Profile Struct at 0x{live_addr:X} (SID=0x{prof['sid']:X})!")

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

                    burned_cnt, combo_cnt = read_live_progress(pid, live_addr)
                    new_locs = []
                    for b_i in range(burned_cnt):
                        lid = 10000 + b_i
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
