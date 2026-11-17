# South Park: The Stick of Truth — Setup Guide

## What you need
* A Steam copy of *South Park: The Stick of Truth* (Windows, or Linux with Proton).
* Archipelago (0.5 or newer) with `spsot.apworld` installed (double-click it, or put it in `custom_worlds`).
* The game must be **closed** while the client patches its data.

## One-time setup
1. Install the apworld, then open the **Archipelago Launcher**. You should see **South Park SoT Client**.
2. Start the client once. It writes a small config file (`spsot_client.json`, in your Archipelago user folder) with the
   game folder and save folder it detected. If either is wrong, edit the file and restart the client.
   Typical locations:
   * Game: `…/Steam/steamapps/common/South Park - The Stick of Truth`
   * Saves (Windows): `Documents/My Games/South Park - The Stick of Truth/save`
   * Saves (Linux/Proton): `…/steamapps/compatdata/213670/pfx/drive_c/users/steamuser/Documents/My Games/South Park - The Stick of Truth/save`
3. The first connection makes a pristine backup of `data_archive.oaf` (`data_archive.oaf.clean`) next to it. **Keep it.**
   It is how the game is restored and how every new seed is patched from a clean start.

## Playing
1. Generate your multiworld (put your YAML in `Players`), host it, and connect the client to the server.
2. The client patches the game's data for your seed. Wait for *"Game data ready"*.
3. Start the game and **start a new game or load a save**.
4. Type **`/arm`** in the client. It finds the game's unlock table (a few seconds) and starts watching.
5. Play. Checks are sent when you unlock something in-game, and when the game **saves** (pickups are read from your
   save files, so save often — autosave counts).
6. If you load a different save, type `/arm` again.

## Client commands
| Command | What it does |
|---|---|
| `/arm` | Start (or restart) watching the game. Do this after loading a save. |
| `/patch` | Patch the game data again for the current seed (game must be closed). |
| `/status` | Show what the client is doing. |
| `/rescan` | Search the game's memory for the unlock table again. |

## Things to know
* Weapons, armor, patches and cosmetics only ever appear in **your own** world (they cannot be delivered to you).
* Friends, dyes, keys, quest items and Chinpokomon can come from any world and are unlocked for you when received.
* The four summon items (Rosary, Piece of Poo, Miniature Gong, Rawhide Whip) are not randomized.
* To undo everything: Steam → Properties → Installed Files → *Verify integrity of game files*, and delete `data_archive.oaf.clean`.
