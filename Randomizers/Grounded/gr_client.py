import asyncio, json, os, websockets

MOD_DIR = "/mnt/E8A2D79FA2D77114/SteamLibrary/steamapps/common/Grounded/Maine/Binaries/Win64/Mods/GroundedArchipelago"
OUTBOX = os.path.join(MOD_DIR, "outbox.txt")
INBOX = os.path.join(MOD_DIR, "inbox.txt")
CFG = os.path.join(MOD_DIR, "config.txt")

async def main():
    os.makedirs(MOD_DIR, exist_ok=True)
    url = input("Server (default ws://localhost:38281): ").strip() or "ws://localhost:38281"
    slot = input("Slot Name (default ground): ").strip() or "ground"
    pw = input("Password (blank if none): ").strip()
    open(CFG, "w").write(f"{url}\n{slot}\n{pw}\n")

    checked = set()
    async with websockets.connect(url) as ws:
        await ws.recv()
        await ws.send(json.dumps([{
            "cmd": "Connect", "password": pw, "game": "Grounded",
            "name": slot, "uuid": "grounded-ue4ss-v1",
            "version": {"major": 0, "minor": 5, "build": 0, "class": "Version"},
            "items_handling": 7, "tags": ["AP"]
        }]))
        print(f"[CONNECTED] Grounded UE4SS Bridge active for '{slot}'! Launch Grounded in Steam.")

        while True:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=0.25)
                for pkt in json.loads(raw):
                    if pkt.get("cmd") == "Connected":
                        checked.update(pkt.get("checked_locations", []))
                    elif pkt.get("cmd") == "ReceivedItems":
                        with open(INBOX, "a") as f:
                            for it in pkt.get("items", []):
                                f.write(f"{it['item']}\n")
                                print(f"[AP -> GROUNDED] Queued Item ID {it['item']}")
            except asyncio.TimeoutError:
                pass

            if os.path.exists(OUTBOX):
                data = open(OUTBOX, "r").read().strip()
                if data:
                    open(OUTBOX, "w").close()
                    locs = []
                    for line in data.splitlines():
                        if line.isdigit():
                            lid = int(line)
                            if lid not in checked:
                                checked.add(lid)
                                locs.append(lid)
                    if locs:
                        print(f"[GROUNDED -> AP] Sending Checks: {locs}")
                        await ws.send(json.dumps([{"cmd": "LocationChecks", "locations": locs}]))

asyncio.run(main())
