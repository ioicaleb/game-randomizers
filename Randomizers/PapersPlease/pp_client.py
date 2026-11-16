import asyncio, glob, json, os, websockets

SAVE_DIR = os.path.expanduser("~/.local/share/3909/PapersPlease")

async def main():
    url = input("Server (default ws://localhost:38281): ").strip() or "ws://localhost:38281"
    slot = input("Slot Name (default papers): ").strip() or "papers"
    pw = input("Password (blank if none): ").strip()

    checked = set()
    shift_counter = 0
    bonus_counter = 0
    mtimes = {f: os.path.getmtime(f) for f in glob.glob(os.path.join(SAVE_DIR, "*.sav"))}
    locked_on = False

    while True:
        try:
            async with websockets.connect(url, ping_interval=None, ping_timeout=None) as ws:
                await ws.recv()
                await ws.send(json.dumps([{
                    "cmd": "Connect", "password": pw, "game": "Papers, Please",
                    "name": slot, "uuid": "pp-ap-v2",
                    "version": {"major": 0, "minor": 5, "build": 0, "class": "Version"},
                    "items_handling": 7, "tags": ["AP"]
                }]))
                print(f"[CONNECTED] Watching {SAVE_DIR} for '{slot}'...")

                while True:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=0.5)
                        for pkt in json.loads(raw):
                            if pkt.get("cmd") == "Connected":
                                checked.update(pkt.get("checked_locations", []))
                            elif pkt.get("cmd") == "ReceivedItems":
                                for it in pkt.get("items", []):
                                    print(f"[AP ITEM RECEIVED] Item ID {it['item']}")
                    except asyncio.TimeoutError:
                        pass

                    for f in glob.glob(os.path.join(SAVE_DIR, "*.sav")):
                        bn = os.path.basename(f)
                        if bn == "settings.sav":
                            continue
                        mt = os.path.getmtime(f)
                        if f not in mtimes or mt > mtimes[f]:
                            mtimes[f] = mt
                            if not locked_on:
                                locked_on = True
                                print(f"[AUTO-DETECTED] Locked onto {bn}! New game / active shift detected.")
                                continue
                            # Each end-of-day / stats save sends the next Shift Complete & Milestone check
                            new_locs = []
                            lid_shift = 10000 + (shift_counter % 31)
                            shift_counter += 1
                            if lid_shift not in checked:
                                checked.add(lid_shift)
                                new_locs.append(lid_shift)
                            if shift_counter % 2 == 0:
                                lid_bonus = 10100 + (bonus_counter % 24)
                                bonus_counter += 1
                                if lid_bonus not in checked:
                                    checked.add(lid_bonus)
                                    new_locs.append(lid_bonus)
                            if new_locs:
                                print(f"[SEND CHECKS] {new_locs}")
                                await ws.send(json.dumps([{"cmd": "LocationChecks", "locations": new_locs}]))
        except Exception as e:
            print(f"[RECONNECTING] ({e}), retrying in 3s...")
            await asyncio.sleep(3)

asyncio.run(main())
