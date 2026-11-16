"""
The Archipelago client for South Park: The Stick of Truth (launched from the Archipelago Launcher).

This file is only the "network side": it talks to the multiworld server (using Archipelago's CommonClient),
and hands everything game-related to GameRuntime (Runtime.py).

How to use it:
  1. Open the client, connect to the server.            -> the game's data is patched for your seed
  2. Start the game, load or start a save.
  3. Type /arm in the client.                           -> it starts watching the game
  (type /arm again whenever you load a different save)
"""
import asyncio
import typing

import Utils
from CommonClient import ClientCommandProcessor, CommonContext, get_base_parser, gui_enabled, logger, server_loop
from NetUtils import ClientStatus

from .Runtime import GameClosed, GameRuntime

GAME_NAME = "South Park: The Stick of Truth"
GOAL_ITEMS = ("Passport", "Princess's Letter")      # must match the apworld's completion condition
FRIEND_PREFIX = "Friend: "


class SoTCommandProcessor(ClientCommandProcessor):
    def _cmd_arm(self):
        """Start watching the game. Load your save first, then type this."""
        self.ctx.arm_requested = True
        self.ctx.runtime.armed = False
        self.ctx.items_done = 0
        logger.info("Arming... (the game must be running with a save loaded)")

    def _cmd_patch(self):
        """Patch the game's data again for the current seed (close the game first)."""
        self.ctx.prepared_seed = None
        self.ctx.prepare_failed = False
        logger.info("Will patch the game again.")

    def _cmd_status(self):
        """Show what the client is doing."""
        r = self.ctx.runtime
        logger.info(f"patched seed: {self.ctx.prepared_seed} | game attached: {r.mem is not None} | "
                    f"armed: {r.armed} | pending unlocks: {len(r.pending)} | items processed: {self.ctx.items_done}")

    def _cmd_rescan(self):
        """Search the game's memory for the unlock table again."""
        if self.ctx.runtime.table:
            n = self.ctx.runtime.table.discover()
            logger.info(f"{n} unlock records found.")


class SoTContext(CommonContext):
    game = GAME_NAME
    command_processor = SoTCommandProcessor
    items_handling = 0b111              # we want every item, including our own, so we can deliver them

    def __init__(self, server_address, password):
        super().__init__(server_address, password)
        self.runtime = GameRuntime(log=logger.info)
        self.slot_data: dict = {}
        self.prepared_seed = None
        self.prepare_failed = False
        self.arm_requested = False
        self.items_done = 0
        self.goal_sent = False
        self.waiting_logged = False

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict):
        if cmd == "Connected":
            self.slot_data = args.get("slot_data", {}) or {}
            self.items_done = 0
            self.goal_sent = False

    def item_label(self, item_id: int) -> str:
        try:
            return self.item_names.lookup_in_game(item_id)
        except Exception:
            try:
                return self.item_names[item_id]
            except Exception:
                return f"item {item_id}"

    def run_gui(self):
        from kvui import GameManager

        class SoTManager(GameManager):
            logging_pairs = [("Client", "Archipelago")]
            base_title = "Archipelago South Park: The Stick of Truth Client"

        self.ui = SoTManager(self)
        self.ui_task = asyncio.create_task(self.ui.async_run(), name="UI")

    async def send_checks(self, locations: typing.Iterable[int]):
        fresh = [loc for loc in set(locations) if loc not in self.locations_checked]
        if fresh:
            self.locations_checked.update(fresh)
            await self.send_msgs([{"cmd": "LocationChecks", "locations": fresh}])


async def watcher_step(ctx: SoTContext, loop: asyncio.AbstractEventLoop):
    rt = ctx.runtime
    seed = ctx.slot_data.get("seed")

    # 1. patch the game's data once per seed
    if ctx.prepared_seed != seed and not ctx.prepare_failed:
        logger.info("Preparing the game for this seed (patching game data)...")
        ok = await loop.run_in_executor(None, rt.prepare, ctx.slot_data, ctx.slot)
        if ok:
            ctx.prepared_seed = seed
            logger.info("Game data ready. Start the game, load a save, then type /arm.")
        else:
            ctx.prepare_failed = True
            logger.info("Patching failed (see messages above). Fix the problem, then type /patch.")
        return
    if ctx.prepared_seed != seed or not ctx.arm_requested:
        return

    # 2. goal (independent of the game)
    names = {ctx.item_label(i.item) for i in ctx.items_received}
    if not ctx.goal_sent and all(g in names for g in GOAL_ITEMS):
        ctx.goal_sent = True
        logger.info("Goal items collected - reporting completion!")
        await ctx.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])

    # 3. attach to the game, then find its unlock table
    if not await loop.run_in_executor(None, rt.attach):
        if not ctx.waiting_logged:
            logger.info("Waiting for the game to start...")
            ctx.waiting_logged = True
        return
    ctx.waiting_logged = False
    if not rt.armed:
        await loop.run_in_executor(None, rt.arm)
        return

    # 4. queue newly received items for delivery
    while ctx.items_done < len(ctx.items_received):
        item = ctx.items_received[ctx.items_done]
        ctx.items_done += 1
        name = ctx.item_label(item.item)
        h = rt.item_unlock_by_id.get(item.item)
        if h is not None:
            rt.queue_delivery(name, h, is_friend=False)
        elif name.startswith(FRIEND_PREFIX):
            fh = rt.friend_hash.get(name[len(FRIEND_PREFIX):])
            if fh is not None:
                rt.queue_delivery(name, fh, is_friend=True)

    # 5. watch the game; send any new checks
    try:
        new_locations = await loop.run_in_executor(None, rt.poll)
    except GameClosed:
        logger.info("The game closed. Start it again, load a save and type /arm.")
        rt.mem = None
        rt.armed = False
        ctx.arm_requested = False
        return
    await ctx.send_checks(new_locations)


async def game_watcher(ctx: SoTContext):
    loop = asyncio.get_running_loop()
    while not ctx.exit_event.is_set():
        await asyncio.sleep(1.0)
        if not ctx.slot_data or ctx.server is None or ctx.slot is None:
            continue
        try:
            await watcher_step(ctx, loop)
        except Exception:
            logger.exception("Client error (it will keep trying)")


def launch(*launch_args: str):
    async def main(args):
        ctx = SoTContext(args.connect, args.password)
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="ServerLoop")
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()
        ctx.watcher_task = asyncio.create_task(game_watcher(ctx), name="GameWatcher")
        await ctx.exit_event.wait()
        ctx.server_address = None
        await ctx.shutdown()

    import colorama
    parser = get_base_parser(description="South Park: The Stick of Truth client")
    args = parser.parse_args(launch_args)
    colorama.init()
    asyncio.run(main(args))
    colorama.deinit()
