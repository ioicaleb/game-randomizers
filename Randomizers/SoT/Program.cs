using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Archipelago.MultiClient.Net;
using Archipelago.MultiClient.Net.Enums;
using Archipelago.MultiClient.Net.Helpers;
using Archipelago.MultiClient.Net.Models;
using Newtonsoft.Json.Linq;

namespace SoT
{
    class SlotTargetInfo
    {
        public long item_id { get; set; }
        public string item_name { get; set; } = "";
        public int player { get; set; }
    }

    class Program
    {
        // Folder that contains the extracted game files ("global/loot_system/...").
        // Override with the SOT_EXTRACTED_DIR environment variable; otherwise it is auto-detected.
        static readonly string ExtractedFolder = ResolveExtractedFolder();
        static readonly string GameDir = Environment.GetEnvironmentVariable("SOT_GAME_DIR")
            ?? "/mnt/E8A2D79FA2D77114/SteamLibrary/steamapps/common/South Park - The Stick of Truth";

        const string BlueprintRelPath = "global/loot_system/generated_item_blueprints.ogd";

        static string ResolveExtractedFolder()
        {
            var candidates = new List<string>();
            string? env = Environment.GetEnvironmentVariable("SOT_EXTRACTED_DIR");
            if (!string.IsNullOrWhiteSpace(env)) candidates.Add(env);
            candidates.Add("/mnt/E8A2D79FA2D77114/Source/repos/SoT_Rando/SoT");
            candidates.Add("/mnt/E8A2D79FA2D77114/Source/repos/GameRandomizers/Randomizers/SoT");
            foreach (string start in new[] { Directory.GetCurrentDirectory(), AppContext.BaseDirectory })
                for (var dir = new DirectoryInfo(start); dir != null; dir = dir.Parent)
                {
                    candidates.Add(dir.FullName);
                    candidates.Add(Path.Combine(dir.FullName, "SoT"));
                }

            foreach (string c in candidates)
                if (File.Exists(Path.Combine(c, BlueprintRelPath))) return c;

            // Last resort: look for the file anywhere under the repos folder.
            try
            {
                var opts = new EnumerationOptions { RecurseSubdirectories = true, IgnoreInaccessible = true };
                foreach (string f in Directory.EnumerateFiles("/mnt/E8A2D79FA2D77114/Source/repos",
                             "generated_item_blueprints.ogd", opts))
                {
                    DirectoryInfo? root = Directory.GetParent(f)?.Parent?.Parent;   // file -> loot_system -> global -> root
                    if (root != null && File.Exists(Path.Combine(root.FullName, BlueprintRelPath))) return root.FullName;
                }
            }
            catch { }

            return candidates[0];   // Main() prints a clear error if this is wrong
        }

        static readonly string[] FriendList = {
            "friend_tweek", "friend_token", "friend_craig", "friend_barbrady",
            "friend_bartender", "friend_beary", "friend_big_gay_al", "friend_bill",
            "friend_bishop_of_banff", "friend_chickadeey", "friend_crab_general",
            "friend_frog_king", "friend_mr_broflovski", "friend_red_goth",
            "friend_mr_hankey", "friend_jesus", "friend_jimbo", "friend_jimmy",
            "friend_kelly_g", "friend_kevin_stoley", "friend_kindergoth",
            "friend_mayor", "friend_mr_kim", "friend_mr_stotch", "friend_mrs_hankey",
            "friend_ned", "friend_polly", "friend_rabbity", "friend_randy",
            "friend_scott_malkinson", "friend_skeeter", "friend_squirrely",
            "friend_Timmy", "friend_wendy", "friend_yates", "friend_chris_donnely",
            "friend_deery", "friend_al_gore", "friend_dougie"
        };

        static IEnumerable<(long start, long end)> WritableRegions(int pid)
        {
            foreach (string line in File.ReadLines($"/proc/{pid}/maps"))
            {
                string[] p = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                if (p.Length < 2 || !p[1].StartsWith("rw")) continue;   // perms are column 1
                string[] r = p[0].Split('-');
                long s = Convert.ToInt64(r[0], 16), e = Convert.ToInt64(r[1], 16);
                if (s >= 0x7F0000000000L) continue;
                yield return (s, e);
            }
        }

        static async Task Main(string[] args)
        {
            Console.WriteLine("=== South Park: The Stick of Truth Archipelago MultiClient ===");
            Console.Write("Server Address (default: localhost:38281): ");
            string? serverInput = Console.ReadLine()?.Trim();
            if (string.IsNullOrWhiteSpace(serverInput)) serverInput = "localhost:38281";

            string host = serverInput.Contains(':') ? serverInput.Split(':')[0] : serverInput;
            int port = serverInput.Contains(':') && int.TryParse(serverInput.Split(':')[1], out int p) ? p : 38281;

            Console.Write("Slot Name (Player Name from YAML): ");
            string slotName = Console.ReadLine()?.Trim() ?? "SoT";

            Console.Write("Room Password (leave blank if none): ");
            string? password = Console.ReadLine();
            if (string.IsNullOrWhiteSpace(password)) password = null;

            var session = ArchipelagoSessionFactory.CreateSession(host, port);
            LoginResult loginResult;
            try
            {
                loginResult = session.TryConnectAndLogin(
                    "South Park: The Stick of Truth",
                    slotName,
                    ItemsHandlingFlags.AllItems,
                    password: password
                );
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[CONNECTION ERROR] {ex.Message}");
                return;
            }

            if (!loginResult.Successful)
            {
                var failure = (LoginFailure)loginResult;
                Console.WriteLine($"[LOGIN FAILED] {string.Join(", ", failure.Errors)}");
                return;
            }

            var success = (LoginSuccessful)loginResult;
            int myPlayerSlot = success.Slot;
            Console.WriteLine($"\n[CONNECTED] Logged into Multiworld as '{slotName}' (Slot #{myPlayerSlot})!");

            var slotMapping = new Dictionary<long, SlotTargetInfo>();
            if (success.SlotData.TryGetValue("slot_mapping", out object? rawMapObj) && rawMapObj != null)
            {
                JObject jObj = rawMapObj as JObject ?? JObject.Parse(rawMapObj.ToString()!);
                foreach (var prop in jObj.Properties())
                {
                    if (long.TryParse(prop.Name, out long locId) && prop.Value is JObject valObj)
                    {
                        slotMapping[locId] = new SlotTargetInfo
                        {
                            item_id = valObj["item_id"]?.Value<long>() ?? 0,
                            item_name = valObj["item_name"]?.Value<string>() ?? "",
                            player = valObj["player"]?.Value<int>() ?? 0
                        };
                    }
                }
            }
            Console.WriteLine($"Loaded {slotMapping.Count} randomized Multiworld location assignments.");

            // Seed diagnostics: lets you see at a glance whether you are connected to a NEW multiworld.
            string seedFromSlot = success.SlotData.TryGetValue("seed", out object? seedObj) ? seedObj?.ToString() ?? "?" : "?";
            string seedFromRoom = "?";
            try { seedFromRoom = session.RoomState.Seed ?? "?"; } catch { }
            Console.WriteLine($"[SEED] multiworld seed: {seedFromRoom}  (slot data seed: {seedFromSlot})");
            try
            {
                string seedFile = Path.Combine(AppContext.BaseDirectory, "last_seed.txt");
                string previous = File.Exists(seedFile) ? File.ReadAllText(seedFile).Trim() : "";
                if (previous == seedFromRoom)
                    Console.WriteLine("[SEED] NOTE: same seed as the previous run. If you expected a new multiworld, the server is still hosting the old one.");
                File.WriteAllText(seedFile, seedFromRoom);
            }
            catch { }

            if (!File.Exists(Path.Combine(ExtractedFolder, BlueprintRelPath)))
            {
                Console.WriteLine($"[ERROR] Extracted game files not found. Looked in: {ExtractedFolder}");
                Console.WriteLine($"        Expected: {Path.Combine(ExtractedFolder, BlueprintRelPath)}");
                Console.WriteLine("        Set SOT_EXTRACTED_DIR to the folder that contains 'global/loot_system/', e.g.:");
                Console.WriteLine("        SOT_EXTRACTED_DIR=/path/to/extracted dotnet run");
                return;
            }
            Console.WriteLine($"Using extracted game files from: {ExtractedFolder}");

            byte[] origGen = File.ReadAllBytes(Path.Combine(ExtractedFolder, "global", "loot_system", "generated_item_blueprints.ogd"));
            byte[] origSocial = File.ReadAllBytes(Path.Combine(ExtractedFolder, "global", "social_network", "social_network.ogd"));

            var indexToBlueprintHash = new Dictionary<int, uint>();
            var blueprintHashToLocations = new Dictionary<uint, List<long>>();
            for (int idx = 0; idx < 995; idx++)
            {
                uint h = BitConverter.ToUInt32(origGen, 0x05768 + (idx * 88));
                indexToBlueprintHash[idx] = h;
            }

            var friendIdToHash = new Dictionary<string, uint>(StringComparer.OrdinalIgnoreCase);
            var friendHashToId = new Dictionary<uint, string>();
            byte[] prefix = Encoding.ASCII.GetBytes("friend_");
            int searchPos = 0;
            while (searchPos < origSocial.Length)
            {
                int found = ((ReadOnlySpan<byte>)origSocial).Slice(searchPos).IndexOf(prefix);
                if (found == -1) break;
                int strStart = searchPos + found;
                int len = 0;
                while (strStart + len < origSocial.Length && origSocial[strStart + len] >= 32 && origSocial[strStart + len] <= 126) len++;
                if (len >= 8 && strStart >= 12 && BitConverter.ToInt32(origSocial, strStart - 8) == len)
                {
                    string fId = Encoding.ASCII.GetString(origSocial, strStart, len);
                    uint fHash = BitConverter.ToUInt32(origSocial, strStart - 12);
                    friendIdToHash.TryAdd(fId, fHash);
                    friendHashToId.TryAdd(fHash, fId);
                }
                searchPos = strStart + Math.Max(1, len);
            }

            ApplyMultiworldPatchToArchive(origGen, slotMapping, myPlayerSlot, indexToBlueprintHash, blueprintHashToLocations);

            var pendingFriendUnlocks = new Queue<string>();
            int processedReceivedCount = 0;
            var receivedNames = new HashSet<string>();
            bool goalSent = false;

            session.Items.ItemReceived += (ReceivedItemsHelper helper) =>
            {
                while (helper.Index > processedReceivedCount)
                {
                    ItemInfo item = helper.DequeueItem();
                    processedReceivedCount++;
                    string itemName = item.ItemName;
                    Console.WriteLine($"[AP ITEM RECEIVED] {itemName} (ID {item.ItemId}) from Player #{item.Player}");

                    // Matches the apworld's completion condition: hold both "Passport" and "Princess's Letter".
                    receivedNames.Add(itemName);
                    if (!goalSent && receivedNames.Contains("Passport") && receivedNames.Contains("Princess's Letter"))
                    {
                        goalSent = true;
                        Console.WriteLine("[GOAL] Passport + Princess's Letter collected - reporting completion!");
                        session.SetGoalAchieved();
                    }

                    if (itemName.StartsWith("Friend: ", StringComparison.OrdinalIgnoreCase))
                    {
                        string fId = itemName.Substring("Friend: ".Length).Trim();
                        lock (pendingFriendUnlocks) pendingFriendUnlocks.Enqueue(fId);
                    }
                }
            };

            Console.WriteLine("\nPatch applied! Launch South Park: The Stick of Truth from Steam now.");
            Console.WriteLine("Waiting for game process to start...");

            int gamePid = -1;
            while (gamePid == -1)
            {
                gamePid = FindTrueGamePid();
                if (gamePid == -1) Thread.Sleep(1500);
            }

            Console.WriteLine($"[LOCKED ON] Game Engine PID: {gamePid} — Multiworld Sync Active! (Press Ctrl+C to exit)\n");

            var checkedLocations = new HashSet<long>(session.Locations.AllLocationsChecked);
            var seenFriendHashes = new HashSet<uint>();
            var seenBagHashes = new HashSet<uint>();

            // Inventory is read from the game's save files (they list only items you actually own).
            string saveDir = Environment.GetEnvironmentVariable("SOT_SAVE_DIR")
                ?? "/mnt/E8A2D79FA2D77114/SteamLibrary/steamapps/compatdata/213670/pfx/drive_c/users/steamuser/Documents/My Games/South Park - The Stick of Truth/save";
            string lastSaveStamp = "";
            Console.WriteLine($"[SAVE WATCH] {saveDir}  (checks are sent each time the game writes a save)");

            using FileStream mem = new FileStream($"/proc/{gamePid}/mem", FileMode.Open, FileAccess.ReadWrite);
            byte[] pageBuf = new byte[4096];

            // ---- ARMING: wait until the save is loaded, then snapshot what already exists ----
            Console.WriteLine("Load your save and wait until you can walk around in-game.");
            Console.WriteLine("Then press ENTER here to arm the tracker (anything already owned is ignored).");
            Console.ReadLine();
            if (!Directory.Exists($"/proc/{gamePid}")) return;

            var bagHits = new Dictionary<uint, (long addr, int qty)>();
            var friendHits = new HashSet<uint>();
            ScanMemory(mem, gamePid, pageBuf, blueprintHashToLocations, friendHashToId, bagHits, friendHits);

            var bagBaseline = new HashSet<uint>(bagHits.Keys);
            // Friends unlocked before arming, plus any friend we inject from AP, are never reported as checks.
            var friendIgnore = new HashSet<uint>(friendHits);
            var bagStreak = new Dictionary<uint, int>();
            var friendStreak = new Dictionary<uint, int>();
            const int ConfirmScans = 3;

            Console.WriteLine($"[ARMED] {friendIgnore.Count} friends already unlocked (ignored). Loot checks come from save files.");
            Console.WriteLine("Tip: press D at any time to write a memory dump (dump_*.txt) for debugging.\n");

            while (Directory.Exists($"/proc/{gamePid}"))
            {
                try
                {
                    if (Console.KeyAvailable && Console.ReadKey(true).Key == ConsoleKey.D)
                    {
                        string dumpFile = $"dump_{DateTime.Now:HHmmss}.txt";
                        DumpHits(mem, gamePid, pageBuf, blueprintHashToLocations, friendHashToId, dumpFile);
                        Console.WriteLine($"[DUMP] Wrote {dumpFile}");
                    }
                }
                catch (InvalidOperationException) { /* console input is redirected; no hotkey */ }

                ScanMemory(mem, gamePid, pageBuf, blueprintHashToLocations, friendHashToId, bagHits, friendHits);

                // --- Loot: read the newest save whenever it changes; every owned mapped hash is a check ---
                try
                {
                    var newest = Directory.Exists(saveDir)
                        ? new DirectoryInfo(saveDir).GetFiles("*.sav", SearchOption.AllDirectories)
                              .OrderByDescending(f => f.LastWriteTimeUtc).FirstOrDefault()
                        : null;
                    if (newest != null)
                    {
                        string stamp = $"{newest.FullName}|{newest.LastWriteTimeUtc.Ticks}|{newest.Length}";
                        if (stamp != lastSaveStamp)
                        {
                            var owned = ReadSaveInventory(newest.FullName, blueprintHashToLocations);
                            if (owned != null)
                            {
                                lastSaveStamp = stamp;
                                Console.WriteLine($"[SAVE] {newest.Name}: {owned.Count} known items in inventory");
                                foreach (var (h, qty) in owned)
                                {
                                    if (!seenBagHashes.Add(h)) continue;
                                    foreach (long locId in blueprintHashToLocations[h])
                                    {
                                        if (checkedLocations.Add(locId))
                                        {
                                            Console.WriteLine($"[SEND CHECK] Loot 0x{h:X8} qty {qty} -> Location ID {locId}");
                                            session.Locations.CompleteLocationChecks(locId);
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                catch (IOException) { /* save is being written; try again next tick */ }

                // --- Friends: unlocked after arming, not injected by us, confirmed on 3 scans ---
                foreach (uint h in friendStreak.Keys.Where(k => !friendHits.Contains(k)).ToList()) friendStreak.Remove(h);
                foreach (uint h in friendHits)
                {
                    if (friendIgnore.Contains(h) || seenFriendHashes.Contains(h)) continue;
                    friendStreak[h] = friendStreak.GetValueOrDefault(h) + 1;
                    if (friendStreak[h] < ConfirmScans) continue;

                    seenFriendHashes.Add(h);
                    string fId = friendHashToId[h];
                    int fIdx = Array.FindIndex(FriendList, x => x.Equals(fId, StringComparison.OrdinalIgnoreCase));
                    if (fIdx < 0) continue;
                    long locId = 20000 + fIdx;
                    if (checkedLocations.Add(locId))
                    {
                        Console.WriteLine($"[SEND CHECK] Friend Request Unlocked: {fId} -> Location ID {locId}");
                        session.Locations.CompleteLocationChecks(locId);
                    }
                }

                // --- Deliver friends received from the multiworld ---
                lock (pendingFriendUnlocks)
                {
                    while (pendingFriendUnlocks.Count > 0)
                    {
                        string targetFriend = pendingFriendUnlocks.Dequeue();
                        if (friendIdToHash.TryGetValue(targetFriend, out uint targetHash))
                        {
                            friendIgnore.Add(targetHash);   // our own injection must not come back as a check
                            InjectFriendUnlockLive(mem, gamePid, targetFriend, targetHash, new HashSet<uint>(friendHashToId.Keys));
                        }
                    }
                }
                Thread.Sleep(500);
            }
            Console.WriteLine("\nGame closed. Disconnecting from Archipelago...");
            await session.Socket.DisconnectAsync();
        }

        /// <summary>
        /// Parses the item-instance table of a Stick of Truth save. Each record starts with an
        /// "item20..." id string; at +32 are [blueprint hash][qty][qty] (qty fields match).
        /// Returns hash -> qty for hashes present in <paramref name="known"/>, or null if unreadable.
        /// </summary>
        static Dictionary<uint, int> ReadSaveInventory(string path, Dictionary<uint, List<long>> known)
        {
            byte[] data;
            using (var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
            {
                data = new byte[fs.Length];
                int n = 0;
                while (n < data.Length) { int r = fs.Read(data, n, data.Length - n); if (r <= 0) break; n += r; }
                if (n < data.Length) return null;
            }
            if (data.Length < 4 || data[0] != (byte)'S' || data[1] != (byte)'A' || data[2] != (byte)'V' || data[3] != (byte)'E')
                return null;

            var owned = new Dictionary<uint, int>();
            for (int o = 0; o <= data.Length - 0x2C; o++)
            {
                if (data[o] != (byte)'i' || data[o + 1] != (byte)'t' || data[o + 2] != (byte)'e' ||
                    data[o + 3] != (byte)'m' || data[o + 4] != (byte)'2' || data[o + 5] != (byte)'0') continue;
                uint hash = BitConverter.ToUInt32(data, o + 32);
                int q1 = BitConverter.ToInt32(data, o + 36), q2 = BitConverter.ToInt32(data, o + 40);
                if (q1 == q2 && q1 >= 1 && known.ContainsKey(hash))
                    owned[hash] = Math.Max(owned.GetValueOrDefault(hash), q1);
            }
            return owned;
        }

        /// <summary>
        /// One pass over the game's writable memory. Fills bagHits with candidate inventory entries
        /// (blueprint hash followed by qty 1..99) and friendHits with friend hashes whose flag is 1.
        /// </summary>
        static void ScanMemory(
            FileStream mem, int pid, byte[] pageBuf,
            Dictionary<uint, List<long>> blueprintMap,
            Dictionary<uint, string> friendMap,
            Dictionary<uint, (long addr, int qty)> bagHits,
            HashSet<uint> friendHits)
        {
            bagHits.Clear();
            friendHits.Clear();
            foreach (var (start, end) in WritableRegions(pid))
            {
                for (long addr = start; addr < end; addr += 4096)
                {
                    try
                    {
                        mem.Seek(addr, SeekOrigin.Begin);
                        int read = mem.Read(pageBuf, 0, 4096);
                        for (int off = 0; off <= read - 16; off += 4)
                        {
                            uint val = BitConverter.ToUInt32(pageBuf, off);

                            // Friend table entry: 0x10 stride, (hash, flag, flag, 0)
                            if (friendMap.ContainsKey(val))
                            {
                                int f1 = BitConverter.ToInt32(pageBuf, off + 4);
                                int f2 = BitConverter.ToInt32(pageBuf, off + 8);
                                int p3 = BitConverter.ToInt32(pageBuf, off + 12);
                                if ((f1 == 0 || f1 == 1) && (f2 == 0 || f2 == 1) && p3 == 0 && f1 == 1)
                                    friendHits.Add(val);
                            }

                            // Inventory entry: (slotHash, qty 1..99), excluding vtable 0x00BE177C template objects
                            if (blueprintMap.ContainsKey(val))
                            {
                                int qty = BitConverter.ToInt32(pageBuf, off + 4);
                                uint maybeVtable = (off >= 24) ? BitConverter.ToUInt32(pageBuf, off - 24) : 0;
                                if (maybeVtable != 0x00BE177C && qty >= 1 && qty <= 99)
                                    bagHits.TryAdd(val, (addr + off, qty));
                            }
                        }
                    }
                    catch { }
                }
            }
        }

        /// <summary>Writes every candidate hit with 16 bytes before / 32 bytes after, for offline analysis.</summary>
        static void DumpHits(
            FileStream mem, int pid, byte[] pageBuf,
            Dictionary<uint, List<long>> blueprintMap,
            Dictionary<uint, string> friendMap,
            string file)
        {
            using var w = new StreamWriter(file);
            foreach (var (start, end) in WritableRegions(pid))
            {
                for (long addr = start; addr < end; addr += 4096)
                {
                    try
                    {
                        mem.Seek(addr, SeekOrigin.Begin);
                        int read = mem.Read(pageBuf, 0, 4096);
                        for (int off = 0; off <= read - 16; off += 4)
                        {
                            uint val = BitConverter.ToUInt32(pageBuf, off);
                            bool isItem = blueprintMap.ContainsKey(val);
                            bool isFriend = friendMap.ContainsKey(val);
                            if (!isItem && !isFriend) continue;
                            int from = Math.Max(0, off - 16);
                            int len = Math.Min(48, read - from);
                            w.WriteLine($"{addr + off:X8} {(isFriend ? "F" : "I")} {val:X8} {BitConverter.ToString(pageBuf, from, len)}");
                        }
                    }
                    catch { }
                }
            }
        }

        
        static void ApplyMultiworldPatchToArchive(
            byte[] origGen,
            Dictionary<long, SlotTargetInfo> slotMapping,
            int myPlayerSlot,
            Dictionary<int, uint> indexToBlueprintHash,
            Dictionary<uint, List<long>> blueprintHashToLocations)
        {
            string oafPath = Path.Combine(GameDir, "data_archive.oaf");
            string cleanOafPath = oafPath + ".clean";
            if (!File.Exists(cleanOafPath))
            {
                Console.WriteLine($"[ERROR] Clean archive backup not found at {cleanOafPath}");
                return;
            }
            byte[] patchedGen = (byte[])origGen.Clone();
            int tableStart = 0x05768;
            // Remove level caps (+0x44 = 1) & make Clyde's 4 tutorial rack weapons (#978-#981) $0.00
            for (int idx = 0; idx < 995; idx++)
            {
                int structStart = tableStart + (idx * 88);
                int reqLv = BitConverter.ToInt32(patchedGen, structStart + 0x44);
                if (idx >= 978 && idx <= 981)
                {
                    BitConverter.GetBytes(0).CopyTo(patchedGen, structStart + 0x0C);
                    BitConverter.GetBytes(1).CopyTo(patchedGen, structStart + 0x44);
                }
                else if (reqLv > 1 && reqLv <= 20)
                {
                    BitConverter.GetBytes(1).CopyTo(patchedGen, structStart + 0x44);
                }
            }
            int localPatched = 0, remoteTokenPatched = 0;
            // Diverse pool of 30 fun collectible/junk visuals so remote/friend checks never look like identical Baseball Cards!
            // 1. Inside ApplyMultiworldPatchToArchive:
            //    Never overwrite Cash (#000-#027) or Nose Jobs (#053-#057)!
            int[] mysteryVisualIndices = {
                601, 602, 603, 604, 605, 606, 607, 608, 609, 610,
                611, 612, 613, 614, 615, 616, 617, 618, 619, 620
            };

            foreach (var kv in slotMapping)
            {
                long locId = kv.Key;
                if (locId < 10000 || locId >= 20000) continue;

                int slotIdx = (int)(locId - 10000);
                // Protect Cash (#000-#027) and Nose Jobs (#053-#057) from ever being overwritten
                if (slotIdx <= 27 || (slotIdx >= 53 && slotIdx <= 57) || slotIdx >= 995) continue;

                int dstOffset = tableStart + (slotIdx * 88) + 4;
                uint slotHash = indexToBlueprintHash[slotIdx];
                blueprintHashToLocations[slotHash] = new List<long> { locId };

                SlotTargetInfo target = kv.Value;
                if (target.player == myPlayerSlot && target.item_id >= 10000 && target.item_id < 20000)
                {
                    int targetItemIdx = (int)(target.item_id - 10000);
                    int srcOffset = tableStart + (targetItemIdx * 88) + 4;
                    Array.Copy(origGen, srcOffset, patchedGen, dstOffset, 0x54);
                    localPatched++;
                }
                else
                {
                    int visualIdx = mysteryVisualIndices[slotIdx % mysteryVisualIndices.Length];
                    int srcOffset = tableStart + (visualIdx * 88) + 4;
                    Array.Copy(origGen, srcOffset, patchedGen, dstOffset, 0x54);
                    remoteTokenPatched++;
                }
            }

            File.Copy(cleanOafPath, oafPath, overwrite: true);
            byte[] oafBytes = File.ReadAllBytes(oafPath);
            int genOff = ((ReadOnlySpan<byte>)oafBytes).IndexOf(origGen);
            using FileStream fs = new FileStream(oafPath, FileMode.Open, FileAccess.Write);
            if (genOff != -1)
            {
                fs.Seek(genOff, SeekOrigin.Begin);
                fs.Write(patchedGen, 0, patchedGen.Length);
                Console.WriteLine($"[ARCHIVE PATCHED at 0x{genOff:X8}] {localPatched} local items placed, {remoteTokenPatched} AP remote/friend checks armed!");
            }
            else
            {
                Console.WriteLine("[ERROR] Could not locate generated_item_blueprints.ogd inside data_archive.oaf!");
            }
        }

        /// <summary>
        /// Unlocks a friend the way a natural unlock changes memory:
        ///  (a) every flag-table record [hash][f1][f2][0] that has other friend records next to it gets f1=f2=1;
        ///  (b) the hash is appended to the 24-slot unlock list (header [.. .. 0x18 0x3EA], empty slots 0xDEADBF19).
        /// Logs every address it touched so a failed unlock can be diagnosed.
        /// </summary>
        static void InjectFriendUnlockLive(FileStream mem, int pid, string friendId, uint friendHash,
                                           HashSet<uint> allFriendHashes)
        {
            const int Chunk = 256 * 1024, Overlap = 1024;
            byte[] buf = new byte[Chunk];
            var tableWrites = new HashSet<long>();
            var listWrites = new HashSet<long>();
            var listAlready = 0;

            foreach (var (start, end) in WritableRegions(pid))
            {
                for (long addr = start; addr < end; addr += Chunk - Overlap)
                {
                    int read;
                    try
                    {
                        mem.Seek(addr, SeekOrigin.Begin);
                        read = mem.Read(buf, 0, (int)Math.Min(Chunk, end - addr));
                    }
                    catch { continue; }
                    if (read < 32) continue;

                    for (int off = 0; off <= read - 16; off += 4)
                    {
                        // (a) flag-table record with a friend record close by
                        if (BitConverter.ToUInt32(buf, off) == friendHash)
                        {
                            int f1 = BitConverter.ToInt32(buf, off + 4);
                            int f2 = BitConverter.ToInt32(buf, off + 8);
                            int p3 = BitConverter.ToInt32(buf, off + 12);
                            if ((f1 == 0 || f1 == 1) && (f2 == 0 || f2 == 1) && p3 == 0 &&
                                HasFriendNeighbour(buf, read, off, allFriendHashes) &&
                                tableWrites.Add(addr + off))
                            {
                                try
                                {
                                    mem.Seek(addr + off + 4, SeekOrigin.Begin);
                                    mem.Write(BitConverter.GetBytes(1), 0, 4);
                                    mem.Write(BitConverter.GetBytes(1), 0, 4);
                                }
                                catch { tableWrites.Remove(addr + off); }
                            }
                        }

                        // (b) 24-slot unlock list: header [?][?][0x18][0x3EA] then (hash, qty) slots
                        if (off + 16 + 24 * 8 <= read &&
                            BitConverter.ToUInt32(buf, off + 8) == 0x18 &&
                            BitConverter.ToUInt32(buf, off + 12) == 0x3EA)
                        {
                            int slots = off + 16;
                            for (int i = 0; i < 24; i++)
                            {
                                uint h = BitConverter.ToUInt32(buf, slots + i * 8);
                                if (h == friendHash) { listAlready++; break; }
                                if (h == 0xDEADBF19)
                                {
                                    long target = addr + slots + i * 8;
                                    if (listWrites.Add(target))
                                    {
                                        try
                                        {
                                            mem.Seek(target, SeekOrigin.Begin);
                                            mem.Write(BitConverter.GetBytes(friendHash), 0, 4);
                                            mem.Write(BitConverter.GetBytes(1), 0, 4);
                                        }
                                        catch { listWrites.Remove(target); }
                                    }
                                    break;
                                }
                            }
                        }
                    }
                }
            }

            Console.WriteLine($"[INJECT] {friendId} (0x{friendHash:X8}): flag records set: {tableWrites.Count}" +
                              (tableWrites.Count > 0 ? " @ " + string.Join(", ", tableWrites.Select(a => "0x" + a.ToString("X"))) : "") +
                              $"; unlock-list slots written: {listWrites.Count} (already present: {listAlready})");
            if (tableWrites.Count == 0)
                Console.WriteLine($"[INJECT] WARNING: no live friend table found for {friendId}; nothing was unlocked.");
        }

        static bool HasFriendNeighbour(byte[] buf, int read, int off, HashSet<uint> friendHashes)
        {
            for (int k = -8; k <= 8; k++)
            {
                if (k == 0) continue;
                int o = off + k * 16;
                if (o < 0 || o + 4 > read) continue;
                if (friendHashes.Contains(BitConverter.ToUInt32(buf, o))) return true;
            }
            return false;
        }

        static int FindTrueGamePid()
        {
            int bestPid = -1;
            long maxRss = 0;
            foreach (string procDir in Directory.GetDirectories("/proc"))
            {
                if (!int.TryParse(Path.GetFileName(procDir), out int pid)) continue;
                string cmdFile = Path.Combine(procDir, "cmdline");
                string statusFile = Path.Combine(procDir, "status");
                if (!File.Exists(cmdFile) || !File.Exists(statusFile)) continue;
                string cmd = File.ReadAllText(cmdFile).Replace('\0', ' ');
                if (cmd.Contains("South Park - The Stick of Truth.exe", StringComparison.OrdinalIgnoreCase) &&
                !cmd.Contains("steam.exe", StringComparison.OrdinalIgnoreCase) &&
                !cmd.Contains("proton", StringComparison.OrdinalIgnoreCase) &&
                !cmd.Contains("steam-runtime", StringComparison.OrdinalIgnoreCase))
                {
                    string rssLine = File.ReadLines(statusFile).FirstOrDefault(l => l.StartsWith("VmRSS:")) ?? "";
                    string digits = new string(rssLine.Where(char.IsDigit).ToArray());
                    if (long.TryParse(digits, out long rss) && rss > maxRss)
                    {
                        maxRss = rss;
                        bestPid = pid;
                    }
                }
            }
            return bestPid;
        }
    }
}