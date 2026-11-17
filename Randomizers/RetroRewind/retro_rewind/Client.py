import asyncio
import glob
import os
import platform
import struct
import time
import Utils
from CommonClient import ClientCommandProcessor, CommonContext, get_base_parser, gui_enabled, logger, server_loop

PROP_MONEY = b"Money64_14_4E3C8A914A3F4058F90C30BD533FEF7E"
PROP_LEVEL = b"Level_4_D665A6394BEDE281DFD626929A94188A"
PROP_DAY   = b"AvailableingameDay_31_9E1A4B4040F7BA6592E2478027A378D7"
PROP_VAL   = b"StoreValue_9_B0D609D4496095B4BB5DD0B9FB214A7E"


def find_save_dir() -> str:
    if platform.system() == "Windows":
        return os.path.join(os.environ.get("LOCALAPPDATA", ""), "RetroRewind", "Saved", "SaveGames")
    for base in [
        os.path.expanduser("~/.local/share/Steam/steamapps/compatdata/3552140"),
        os.path.expanduser("~/.steam/steam/steamapps/compatdata/3552140"),
        "/mnt/E8A2D79FA2D77114/SteamLibrary/steamapps/compatdata/3552140",
    ]:
        p = os.path.join(base, "pfx/drive_c/users/steamuser/AppData/Local/RetroRewind/Saved/SaveGames")
        if os.path.isdir(p):
            return p
    return ""


def read_int_prop(data: bytes, prop_bytes: bytes, default: int = 0) -> int:
    p = data.find(prop_bytes)
    if p != -1 and p + len(prop_bytes) + 30 <= len(data):
        val, = struct.unpack_from("<I", data, p + len(prop_bytes) + 26)
        return val
    return default


def read_u64_prop(data: bytes, prop_bytes: bytes, default: int = 0) -> int:
    p = data.find(prop_bytes)
    if p != -1 and p + len(prop_bytes) + 36 <= len(data):
        val, = struct.unpack_from("<Q", data, p + len(prop_bytes) + 28)
        return val
    return default


def read_save_snapshot(sav_path: str) -> dict:
    with open(sav_path, "rb") as f:
        data = f.read()
    return {
        "day": max(1, read_int_prop(data, PROP_DAY, 1)),
        "level": min(20, max(1, read_int_prop(data, PROP_LEVEL, 1))),
        "store_value": read_int_prop(data, PROP_VAL, 0),
        "money": read_u64_prop(data, PROP_MONEY, 0),
    }


def patch_save_cash(sav_path: str, add_amount: int) -> bool:
    if add_amount <= 0 or not sav_path or not os.path.exists(sav_path):
        return False
    with open(sav_path, "rb") as f:
        raw = bytearray(f.read())
    p_m = raw.find(PROP_MONEY)
    if p_m != -1 and p_m + len(PROP_MONEY) + 36 <= len(raw):
        off = p_m + len(PROP_MONEY) + 28
        cur, = struct.unpack_from("<Q", raw, off)
        struct.pack_into("<Q", raw, off, cur + add_amount)
        with open(sav_path, "wb") as f:
            f.write(raw)
        return True
    return False


class RetroRewindContext(CommonContext):
    command_processor = ClientCommandProcessor
    game = "Retro Rewind"
    items_handling = 0b111

    def __init__(self, server_address: str | None, password: str | None) -> None:
        super().__init__(server_address, password)
        self.save_dir = find_save_dir()
        self.granted_indices: set[int] = set()
        self.received_permits: set[int] = set()
        self.received_licenses: set[int] = set()
        self.pending_cash = 0
        self.goal_mode = 0
        self.target_level = 15
        self.target_value = 25000
        self.goal_sent = False

    async def server_auth(self, password_requested: bool = False) -> None:
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict) -> None:
        if cmd == "Connected":
            sd = args.get("slot_data", {})
            self.goal_mode = int(sd.get("goal", 0))
            self.target_level = int(sd.get("target_store_level", 15))
            self.target_value = int(sd.get("target_store_value", 25000))
            if self.save_dir:
                bridge = os.path.join(self.save_dir, "AP_Bridge")
                os.makedirs(bridge, exist_ok=True)
                with open(os.path.join(bridge, "config.txt"), "w") as cf:
                    cf.write(f"auto_change={int(sd.get('auto_change', 1))}\n")
                    cf.write(f"auto_sort_returns={int(sd.get('auto_sort_returns', 1))}\n")
                    cf.write(f"arm_carry_limit={int(sd.get('arm_carry_limit', 20))}\n")
            logger.info("Connected to Retro Rewind! End-of-Day & UE4SS Bridge active.")

        elif cmd == "ReceivedItems":
            s_idx = args.get("index", 0)
            for off, it in enumerate(args.get("items", [])):
                idx = s_idx + off
                if idx in self.granted_indices:
                    continue
                self.granted_indices.add(idx)
                code = it.item if hasattr(it, "item") else it["item"]
                if 20001 <= code <= 20008:
                    self.received_permits.add(code)
                    self.pending_cash += 250
                elif 20010 <= code <= 20019:
                    self.received_licenses.add(code)
                    self.pending_cash += 250
                elif code == 20020:
                    self.pending_cash += 100
                elif code == 20030:
                    self.pending_cash += 50
                elif code == 20031:
                    self.pending_cash += 150
                elif code == 20032:
                    self.pending_cash += 500
                if self.save_dir:
                    bridge = os.path.join(self.save_dir, "AP_Bridge")
                    os.makedirs(bridge, exist_ok=True)
                    with open(os.path.join(bridge, "inbox.txt"), "a") as f:
                        f.write(f"{code}\n")


async def retro_rewind_sync_task(ctx: RetroRewindContext) -> None:
    active_sav = None
    baseline = None
    last_day = None
    known_mtimes: dict[str, float] = {}
    if ctx.save_dir:
        for s in glob.glob(os.path.join(ctx.save_dir, "Player_Save*.sav")):
            if "backup" not in os.path.basename(s) and not s.endswith(".ap_bak"):
                known_mtimes[s] = os.path.getmtime(s)

    while not ctx.exit_event.is_set():
        await asyncio.sleep(2.5)
        if not ctx.save_dir or not ctx.server or not ctx.slot:
            continue

        bridge = os.path.join(ctx.save_dir, "AP_Bridge")
        os.makedirs(bridge, exist_ok=True)
        outbox = os.path.join(bridge, "outbox.txt")
        if os.path.exists(outbox):
            with open(outbox, "r") as f:
                lines = [x.strip() for x in f.read().splitlines() if x.strip().isdigit()]
            open(outbox, "w").close()
            ue_locs = [int(x) for x in lines if int(x) not in ctx.checked_locations]
            if ue_locs:
                await ctx.send_msgs([{"cmd": "LocationChecks", "locations": ue_locs}])

        changed_savs = []
        for s in glob.glob(os.path.join(ctx.save_dir, "Player_Save*.sav")):
            if "backup" in os.path.basename(s) or s.endswith(".ap_bak"):
                continue
            mt = os.path.getmtime(s)
            if (s not in known_mtimes or mt > known_mtimes[s]) and (time.time() - mt >= 1.5):
                changed_savs.append((mt, s))
        if not changed_savs:
            continue
        changed_savs.sort()
        mt, newest = changed_savs[-1]
        if True:
            known_mtimes[newest] = mt
            snap = await asyncio.to_thread(read_save_snapshot, newest)
            if active_sav != newest:
                active_sav = newest
                baseline = snap
                last_day = snap["day"]
                logger.info(f"Locked onto {os.path.basename(newest)} (Day {last_day}, Level {snap['level']})")
                continue

            if snap["day"] > last_day:
                logger.info(f"End of Day {last_day} -> Day {snap['day']}: syncing checks & rewards...")
                last_day = snap["day"]
                new_locs = []
                for l_i in range(max(0, snap["level"] - 1)):
                    lid = 10000 + l_i
                    if lid not in ctx.checked_locations:
                        new_locs.append(lid)
                for d_i in range(min(25, max(0, snap["day"] - baseline["day"]))):
                    lid = 10100 + d_i
                    if lid not in ctx.checked_locations:
                        new_locs.append(lid)
                val_steps = min(20, max(0, (snap["store_value"] - baseline["store_value"]) // 1000))
                for v_i in range(val_steps):
                    lid = 10200 + v_i
                    if lid not in ctx.checked_locations:
                        new_locs.append(lid)
                cash_steps = min(26, max(0, int(snap["money"] - baseline["money"]) // 500))
                for m_i in range(cash_steps):
                    lid = 10300 + m_i
                    if lid not in ctx.checked_locations:
                        new_locs.append(lid)

                if new_locs:
                    await ctx.send_msgs([{"cmd": "LocationChecks", "locations": new_locs}])

                if ctx.pending_cash > 0:
                    if await asyncio.to_thread(patch_save_cash, active_sav, ctx.pending_cash):
                        logger.info(f"Added +${ctx.pending_cash} End-of-Day reward!")
                        ctx.pending_cash = 0
                        known_mtimes[active_sav] = os.path.getmtime(active_sav)

                if not ctx.goal_sent:
                    won = (
                        (ctx.goal_mode == 0 and snap["level"] >= ctx.target_level)
                        or (ctx.goal_mode == 1 and len(ctx.received_permits) >= 4)
                        or (ctx.goal_mode == 2 and len(ctx.received_licenses) >= 7)
                        or (ctx.goal_mode == 3 and snap["store_value"] >= ctx.target_value)
                    )
                    if won:
                        ctx.goal_sent = True
                        await ctx.send_msgs([{"cmd": "StatusUpdate", "status": 30}])


def launch(*args: str) -> None:
    async def _main() -> None:
        parser = get_base_parser()
        parsed = parser.parse_args(args)
        ctx = RetroRewindContext(parsed.connect, parsed.password)
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
        sync_task = asyncio.create_task(retro_rewind_sync_task(ctx), name="retro_rewind_sync")
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()
        await ctx.exit_event.wait()
        sync_task.cancel()
        await ctx.shutdown()

    Utils.init_logging("RetroRewindClient", exception_logger="Client")
    asyncio.run(_main())
