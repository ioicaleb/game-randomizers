import asyncio, glob, json, os, websockets

APPIDS = ['820540']

def find_save_files():
    roots = [
        "/mnt/E8A2D79FA2D77114/SteamLibrary/steamapps/compatdata",
        os.path.expanduser("~/.local/share/Steam/steamapps/compatdata"),
    ]
    found = []
    for r in roots:
        for aid in APPIDS:
            base = os.path.join(r, aid, "pfx/drive_c/users/steamuser")
            if os.path.isdir(base):
                found.extend(glob.glob(os.path.join(base, "**", "*.sav"), recursive=True))
    return found

async def main():
    url = input("Server (default ws://localhost:38281): ").strip() or "ws://localhost:38281"
    slot = input("Slot Name: ").strip() or 'TreasureHunter'
    pw = input("Password (blank if none): ").strip()

    checked = set()
    mtimes = {f: os.path.getmtime(f) for f in find_save_files()}
    base_size = None

    async with websockets.connect(url) as ws:
        await ws.recv()
        await ws.send(json.dumps([{
            "cmd": "Connect", "password": pw, "game": 'Treasure Hunter Simulator',
            "name": slot, "uuid": "treasurehunter-ap-auto",
            "version": {"major": 0, "minor": 5, "build": 0, "class": "Version"},
            "items_handling": 7, "tags": ["AP"]
        }]))
        print(f"[CONNECTED] Auto-watching Treasure Hunter Simulator save files for '{slot}'...")

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

            for f in find_save_files():
                mt = os.path.getmtime(f)
                if f not in mtimes or mt > mtimes[f]:
                    mtimes[f] = mt
                    sz = os.path.getsize(f)
                    if base_size is None:
                        base_size = sz
                        print(f"[AUTO-DETECTED] Locked onto {os.path.basename(f)}!")
                    steps = max(0, (sz - base_size) // 256)
                    new_locs = []
                    for i in range(min(100, steps)):
                        lid = 10000 + i
                        if lid not in checked:
                            checked.add(lid)
                            new_locs.append(lid)
                    if new_locs:
                        print(f"[SEND CHECKS] {new_locs}")
                        await ws.send(json.dumps([{"cmd": "LocationChecks", "locations": new_locs}]))

asyncio.run(main())
