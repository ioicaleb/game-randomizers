import asyncio, json, os, platform, re, websockets

def find_save_file():
    if platform.system() == "Windows":
        p = os.path.join(os.environ.get("LOCALAPPDATA", ""), "3909", "PapersPlease", "Save.dat")
        if os.path.exists(p): return p
    for p in [
        os.path.expanduser("~/.local/share/3909/PapersPlease/Save.dat"),
        os.path.expanduser("~/.config/unity3d/3909/PapersPlease/Save.dat"),
    ]:
        if os.path.exists(p): return p
    return os.path.expanduser("~/.local/share/3909/PapersPlease/Save.dat")

async def main():
    sav = find_save_file()
    url = input("Server (default ws://localhost:38281): ").strip() or "ws://localhost:38281"
    slot = input("Slot Name (default Inspector): ").strip() or "Inspector"
    pw = input("Password (blank if none): ").strip()

    checked = set()
    last_mt = os.path.getmtime(sav) if os.path.exists(sav) else 0

    async with websockets.connect(url) as ws:
        await ws.recv()
        await ws.send(json.dumps([{
            "cmd": "Connect", "password": pw, "game": "Papers, Please",
            "name": slot, "uuid": "pp-ap-auto",
            "version": {"major": 0, "minor": 5, "build": 0, "class": "Version"},
            "items_handling": 7, "tags": ["AP"]
        }]))
        print(f"[CONNECTED] Watching Papers, Please Save.dat for '{slot}'...")

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

            if os.path.exists(sav):
                mt = os.path.getmtime(sav)
                if mt > last_mt:
                    last_mt = mt
                    txt = open(sav, "r", errors="ignore").read()
                    m_day = re.search(r'"day"\s*:\s*(\d+)', txt)
                    day = int(m_day.group(1)) if m_day else 1
                    new_locs = []
                    for d in range(min(31, max(0, day - 1))):
                        lid = 10000 + d
                        if lid not in checked:
                            checked.add(lid)
                            new_locs.append(lid)
                    if new_locs:
                        print(f"[SEND CHECKS] {new_locs}")
                        await ws.send(json.dumps([{"cmd": "LocationChecks", "locations": new_locs}]))

asyncio.run(main())
