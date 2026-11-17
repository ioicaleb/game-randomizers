import argparse, asyncio, glob, json, os, platform, struct, sys, time, websockets

PROP_MONEY = b"Money64_14_4E3C8A914A3F4058F90C30BD533FEF7E"
PROP_LEVEL = b"Level_4_D665A6394BEDE281DFD626929A94188A"
PROP_DAY   = b"AvailableingameDay_31_9E1A4B4040F7BA6592E2478027A378D7"
PROP_VAL   = b"StoreValue_9_B0D609D4496095B4BB5DD0B9FB214A7E"

def find_save_dir():
    if platform.system() == "Windows":
        return os.path.join(os.environ.get("LOCALAPPDATA", ""), "RetroRewind", "Saved", "SaveGames")
    for base in [
        os.path.expanduser("~/.local/share/Steam/steamapps/compatdata/3552140"),
        os.path.expanduser("~/.steam/steam/steamapps/compatdata/3552140"),
        "/mnt/E8A2D79FA2D77114/SteamLibrary/steamapps/compatdata/3552140"
    ]:
        p = os.path.join(base, "pfx/drive_c/users/steamuser/AppData/Local/RetroRewind/Saved/SaveGames")
        if os.path.isdir(p):
            return p
    return ""

def is_game_running():
    if not os.path.isdir("/proc"):
        return True
    for pid in os.listdir("/proc"):
        if pid.isdigit():
            try:
                if b"retrorewind" in open(f"/proc/{pid}/cmdline", "rb").read().lower():
                    return True
            except Exception:
                pass
    return False

def read_int_prop(data, prop_bytes, default=0):
    p = data.find(prop_bytes)
    if p != -1 and p + len(prop_bytes) + 30 <= len(data):
        val, = struct.unpack_from("<I", data, p + len(prop_bytes) + 26)
        return val
    return default

def read_u64_prop(data, prop_bytes, default=0):
    p = data.find(prop_bytes)
    if p != -1 and p + len(prop_bytes) + 36 <= len(data):
        val, = struct.unpack_from("<Q", data, p + len(prop_bytes) + 28)
        return val
    return default

def read_save_snapshot(sav_path):
    data = open(sav_path, "rb").read()
    return {
        "day": max(1, read_int_prop(data, PROP_DAY, 1)),
        "level": min(20, max(1, read_int_prop(data, PROP_LEVEL, 1))),
        "store_value": read_int_prop(data, PROP_VAL, 0),
        "money": read_u64_prop(data, PROP_MONEY, 0),
    }

def patch_save_cash(sav_path, add_amount):
    if add_amount <= 0 or not sav_path or not os.path.exists(sav_path):
        return False
    raw = bytearray(open(sav_path, "rb").read())
    p_m = raw.find(PROP_MONEY)
    if p_m != -1 and p_m + len(PROP_MONEY) + 36 <= len(raw):
        off = p_m + len(PROP_MONEY) + 28
        cur, = struct.unpack_from("<Q", raw, off)
        struct.pack_into("<Q", raw, off, cur + add_amount)
        open(sav_path, "wb").write(raw)
        print(f"[END-OF-DAY REWARD] Added +${add_amount} to {os.path.basename(sav_path)}!")
        return True
    return False

async def main():
    game_seen = False
    save_dir = find_save_dir()
    if not save_dir:
        print("[ERROR] Could not locate Retro Rewind SaveGames folder.")
        return

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--connect", default="")
    parser.add_argument("--name", default="")
    parser.add_argument("--password", default="")
    args, _ = parser.parse_known_args()

    url = args.connect.strip() or input("Archipelago Server (default ws://localhost:38281): ").strip() or "ws://localhost:38281"
    slot = args.name.strip() or input("Slot Name (default retro): ").strip() or "retro"
    pw = args.password.strip() if args.connect else input("Password (blank if none): ").strip()

    checked = set()
    granted_indices = set()
    received_permits = set()
    received_licenses = set()
    pending_cash = 0
    active_sav = None
    baseline = None
    last_day = None
    goal_mode, target_level, target_value, goal_sent = 0, 15, 25000, False
    known_mtimes = {f: os.path.getmtime(f) for f in glob.glob(os.path.join(save_dir, "Player_Save*.sav")) if "backup" not in f}

    while True:
        try:
            async with websockets.connect(url, ping_interval=None, ping_timeout=None) as ws:
                await ws.recv()
                await ws.send(json.dumps([{
                    "cmd": "Connect", "password": pw, "game": "Retro Rewind",
                    "name": slot, "uuid": "rr-ap-eod3",
                    "version": {"major": 0, "minor": 5, "build": 0, "class": "Version"},
                    "items_handling": 7, "tags": ["AP"]
                }]))

                auth_ok = False
                while not auth_ok:
                    for pkt in json.loads(await ws.recv()):
                        if pkt.get("cmd") == "ConnectionRefused":
                            print(f"[LOGIN FAILED] Refused by server: {pkt.get('errors')} (check slot name or password!)")
                            return
                        elif pkt.get("cmd") == "Connected":
                            checked.update(pkt.get("checked_locations", []))
                            sd = pkt.get("slot_data", {})
                            goal_mode = int(sd.get("goal", 0))
                            target_level = int(sd.get("target_store_level", 15))
                            target_value = int(sd.get("target_store_value", 25000))
                            os.makedirs(os.path.join(save_dir, "AP_Bridge"), exist_ok=True)
                            with open(os.path.join(save_dir, "AP_Bridge", "config.txt"), "w") as cf:
                                cf.write(f"auto_change={int(sd.get('auto_change', 1))}\n")
                                cf.write(f"auto_sort_returns={int(sd.get('auto_sort_returns', 1))}\n")
                                cf.write(f"arm_carry_limit={int(sd.get('arm_carry_limit', 20))}\n")
                            auth_ok = True

                print(f"[CONNECTED] End-of-Day Sync active for '{slot}'!")

                while True:
                    try:
                        raw_msg = await asyncio.wait_for(ws.recv(), timeout=2.5)
                        for pkt in json.loads(raw_msg):
                            if pkt.get("cmd") == "ReceivedItems":
                                s_idx = pkt.get("index", 0)
                                for off, it in enumerate(pkt.get("items", [])):
                                    idx = s_idx + off
                                    if idx in granted_indices: continue
                                    granted_indices.add(idx)
                                    code = it["item"]
                                    if 20001 <= code <= 20004: received_permits.add(code); pending_cash += 250
                                    elif 20010 <= code <= 20016: received_licenses.add(code); pending_cash += 250
                                    elif code == 20020: pending_cash += 100
                                    elif code == 20030: pending_cash += 50
                                    elif code == 20031: pending_cash += 150
                                    elif code == 20032: pending_cash += 500
                                    open(os.path.join(save_dir, "AP_Bridge", "inbox.txt"), "a").write(f"{code}\n")
                                    print(f"[SENT TO GAME + QUEUED] Received Item {code} (Pending Cash: +${pending_cash})")
                    except asyncio.TimeoutError:
                        pass

                    if is_game_running():
                        game_seen = True
                    elif game_seen:
                        print("[GAME CLOSED] Detected game exit. Disconnecting and closing client...")
                        return

                    bridge_dir = os.path.join(save_dir, "AP_Bridge")
                    os.makedirs(bridge_dir, exist_ok=True)
                    outbox = os.path.join(bridge_dir, "outbox.txt")
                    if os.path.exists(outbox):
                        lines = [x.strip() for x in open(outbox).read().splitlines() if x.strip().isdigit()]
                        open(outbox, "w").close()
                        ue_locs = [int(x) for x in lines if int(x) not in checked]
                        if ue_locs:
                            checked.update(ue_locs)
                            print(f"[UE4SS CHECK] {ue_locs}")
                            await ws.send(json.dumps([{"cmd": "LocationChecks", "locations": ue_locs}]))

                    all_savs = [s for s in glob.glob(os.path.join(save_dir, "Player_Save*.sav")) if "backup" not in os.path.basename(s) and not s.endswith(".ap_bak")]
                    newest_sav = [max(all_savs, key=os.path.getmtime)] if all_savs else []
                    for f in newest_sav:
                        if "backup" in os.path.basename(f): continue
                        mt = os.path.getmtime(f)
                        if (f not in known_mtimes or mt > known_mtimes[f]) and (time.time() - mt >= 1.5):
                            known_mtimes[f] = mt
                            snap = await asyncio.to_thread(read_save_snapshot, f)
                            if active_sav != f:
                                active_sav = f
                                baseline = snap
                                last_day = snap["day"]
                                print(f"[AUTO-DETECTED] Locked onto {os.path.basename(f)} (Day {last_day}, Level {snap['level']}, Value ${snap['store_value']:,})!")
                                continue

                            if snap["day"] > last_day:
                                print(f"[END OF DAY {last_day} -> DAY {snap['day']}] Level {snap['level']}, Store Value ${snap['store_value']:,}")
                                last_day = snap["day"]

                                new_locs = []
                                for l_i in range(max(0, snap["level"] - 1)):
                                    lid = 10000 + l_i
                                    if lid not in checked: checked.add(lid); new_locs.append(lid)
                                for d_i in range(min(25, max(0, snap["day"] - baseline["day"]))):
                                    lid = 10100 + d_i
                                    if lid not in checked: checked.add(lid); new_locs.append(lid)
                                val_steps = min(20, max(0, (snap["store_value"] - baseline["store_value"]) // 1000))
                                for v_i in range(val_steps):
                                    lid = 10200 + v_i
                                    if lid not in checked: checked.add(lid); new_locs.append(lid)
                                cash_steps = min(26, max(0, int(snap["money"] - baseline["money"]) // 500))
                                for m_i in range(cash_steps):
                                    lid = 10300 + m_i
                                    if lid not in checked: checked.add(lid); new_locs.append(lid)

                                if new_locs:
                                    print(f"[SEND CHECKS] {new_locs}")
                                    await ws.send(json.dumps([{"cmd": "LocationChecks", "locations": new_locs}]))

                                if pending_cash > 0:
                                    if await asyncio.to_thread(patch_save_cash, active_sav, pending_cash):
                                        pending_cash = 0
                                        known_mtimes[active_sav] = os.path.getmtime(active_sav)

                                if not goal_sent:
                                    won = (goal_mode == 0 and snap["level"] >= target_level) or \
                                          (goal_mode == 1 and len(received_permits) >= 4) or \
                                          (goal_mode == 2 and len(received_licenses) >= 7) or \
                                          (goal_mode == 3 and snap["store_value"] >= target_value)
                                    if won:
                                        goal_sent = True
                                        print("[VICTORY] Goal condition met! Sending Victory to Archipelago!")
                                        await ws.send(json.dumps([{"cmd": "StatusUpdate", "status": 30}]))
        except Exception as e:
            print(f"[RECONNECTING] ({e}), retrying in 3s...")
            await asyncio.sleep(3)

if __name__ == "__main__":
    asyncio.run(main())
