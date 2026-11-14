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
        static readonly string ExtractedFolder = "/mnt/E8A2D79FA2D77114/Source/repos/GameRandomizers/Unpacked Games/SoT";
        static readonly string GameDir = "/mnt/E8A2D79FA2D77114/SteamLibrary/steamapps/common/South Park - The Stick of Truth";
        static readonly HashSet<int> AlwaysVanilla = new() { 917,918,919, 927,928,929, 937,938,939, 947,948,949 };
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

            session.Items.ItemReceived += (ReceivedItemsHelper helper) =>
            {
                while (helper.Index > processedReceivedCount)
                {
                    ItemInfo item = helper.DequeueItem();
                    processedReceivedCount++;
                    string itemName = item.ItemName;
                    Console.WriteLine($"[AP ITEM RECEIVED] {itemName} (ID {item.ItemId}) from Player #{item.Player}");

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

            Console.WriteLine($"[ARMED] Baseline: {bagBaseline.Count} bag hashes, {friendIgnore.Count} friends already unlocked (ignored).");
            Console.WriteLine("Tip: press D at any time to write a memory dump (dump_*.txt) for debugging.\n");

            while (Directory.Exists($"/proc/{gamePid}"))
            {
                try
                {
                    var key = Console.ReadKey(true).Key;
                    if (key == ConsoleKey.D)
                    {
                        string dumpFile = $"dump_{DateTime.Now:HHmmss}.txt";
                        DumpHits(mem, gamePid, pageBuf, blueprintHashToLocations, friendHashToId, dumpFile);
                        Console.WriteLine($"[DUMP] Wrote {dumpFile}");
                    }
                    else if (key == ConsoleKey.R)
                    {
                        string f = $"refs_{DateTime.Now:HHmmss}.txt";
                        DumpReferrers(mem, gamePid, pageBuf, blueprintHashToLocations, f);
                        Console.WriteLine($"[REFS] Wrote {f}");
                    }
                }
                catch (InvalidOperationException) { /* console input is redirected; no hotkey */ }

                ScanMemory(mem, gamePid, pageBuf, blueprintHashToLocations, friendHashToId, bagHits, friendHits);

                // --- Loot: a hash must be new (not in baseline) and seen on 3 consecutive scans ---
                foreach (uint h in bagStreak.Keys.Where(k => !bagHits.ContainsKey(k)).ToList()) bagStreak.Remove(h);
                foreach (var (h, info) in bagHits)
                {
                    if (bagBaseline.Contains(h) || seenBagHashes.Contains(h)) continue;
                    bagStreak[h] = bagStreak.GetValueOrDefault(h) + 1;
                    if (bagStreak[h] < ConfirmScans) continue;

                    seenBagHashes.Add(h);
                    foreach (long locId in blueprintHashToLocations[h])
                    {
                        if (checkedLocations.Add(locId))
                        {
                            Console.WriteLine($"[SEND CHECK] Loot 0x{h:X8} @0x{info.addr:X} qty {info.qty} -> Location ID {locId}");
                            session.Locations.CompleteLocationChecks(locId);
                        }
                    }
                }

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
                            InjectFriendUnlockLive(mem, gamePid, targetFriend, targetHash);
                        }
                    }
                }
                Thread.Sleep(500);
            }
            Console.WriteLine("\nGame closed. Disconnecting from Archipelago...");
            await session.Socket.DisconnectAsync();
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
                if (slotIdx <= 27 || (slotIdx >= 53 && slotIdx <= 57) || slotIdx >= 995 || AlwaysVanilla.Contains(slotIdx)) continue;

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

        static void InjectFriendUnlockLive(FileStream mem, int pid, string friendId, uint friendHash)
        {
            byte[] pageBuf = new byte[4096];
            foreach (var (start, end) in WritableRegions(pid))
            {

                if (start >= 0x7F0000000000L) continue;
                for (long addr = start; addr < end; addr += 4096)
                {
                    try
                    {
                        mem.Seek(addr, SeekOrigin.Begin);
                        int read = mem.Read(pageBuf, 0, 4096);
                        for (int off = 0; off <= read - 16; off += 4)
                        {
                            if (BitConverter.ToUInt32(pageBuf, off) == friendHash)
                            {
                                int f1 = BitConverter.ToInt32(pageBuf, off + 4);
                                int f2 = BitConverter.ToInt32(pageBuf, off + 8);
                                int p3 = BitConverter.ToInt32(pageBuf, off + 12);
                                if ((f1 == 0 || f1 == 1) && (f2 == 0 || f2 == 1) && p3 == 0)
                                {
                                    mem.Seek(addr + off + 4, SeekOrigin.Begin);
                                    mem.Write(BitConverter.GetBytes(1), 0, 4);
                                    mem.Write(BitConverter.GetBytes(1), 0, 4);
                                    Console.WriteLine($"[UNLOCKED IN-GAME] {friendId} (0x{friendHash:X8}) unlocked on Facebook!");
                                    return;
                                }
                            }
                        }
                    }
                    catch { }
                }
            }
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
        static void DumpReferrers(FileStream mem, int pid, byte[] pageBuf,
            Dictionary<uint, List<long>> blueprintMap, string file)
        {
            // Pass 1: find template objects ([hash, id, id, vtable] with a known vtable)
            var templates = new List<(long addr, uint hash)>();
            foreach (var (start, end) in WritableRegions(pid))
                for (long addr = start; addr < end; addr += 4096)
                {
                    try
                    {
                        mem.Seek(addr, SeekOrigin.Begin);
                        int read = mem.Read(pageBuf, 0, 4096);
                        for (int off = 0; off <= read - 16; off += 4)
                        {
                            uint val = BitConverter.ToUInt32(pageBuf, off);
                            if (!blueprintMap.ContainsKey(val)) continue;
                            uint vt = BitConverter.ToUInt32(pageBuf, off + 12);
                            if ((vt == 0x00B9F750 || vt == 0x00B9DECC) &&
                                BitConverter.ToUInt32(pageBuf, off + 4) == BitConverter.ToUInt32(pageBuf, off + 8))
                                templates.Add((addr + off, val));
                        }
                    }
                    catch { }
                }
            templates.Sort((a, b) => a.addr.CompareTo(b.addr));
            if (templates.Count == 0) return;
            long[] keys = templates.Select(t => t.addr).ToArray();

            // Pass 2: every dword that points at (or within 16 bytes of) a template
            using var w = new StreamWriter(file);
            w.WriteLine($"# {templates.Count} templates");
            foreach (var (start, end) in WritableRegions(pid))
                for (long addr = start; addr < end; addr += 4096)
                {
                    try
                    {
                        mem.Seek(addr, SeekOrigin.Begin);
                        int read = mem.Read(pageBuf, 0, 4096);
                        for (int off = 0; off <= read - 4; off += 4)
                        {
                            uint v = BitConverter.ToUInt32(pageBuf, off);
                            if (v < keys[0] - 16 || v > keys[^1] + 16) continue;
                            int i = Array.BinarySearch(keys, (long)v);
                            if (i < 0) i = ~i;
                            for (int j = Math.Max(0, i - 1); j <= Math.Min(keys.Length - 1, i); j++)
                            {
                                if (Math.Abs(keys[j] - (long)v) > 16) continue;
                                int from = Math.Max(0, off - 16), len = Math.Min(48, read - from);
                                w.WriteLine($"{addr + off:X8} -> {v:X8} hash {templates[j].hash:X8} {BitConverter.ToString(pageBuf, from, len)}");
                            }
                        }
                    }
                    catch { }
                }
        }
        static Dictionary<uint, int> ReadSaveInventory(string saveDir, Dictionary<uint, List<long>> known)
        {
            var file = new DirectoryInfo(saveDir).GetFiles("*.sav", SearchOption.AllDirectories)
                .OrderByDescending(f => f.LastWriteTimeUtc).FirstOrDefault();
            if (file == null) return null;

            byte[] data;
            using (var fs = new FileStream(file.FullName, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
            {
                data = new byte[fs.Length];
                int n = 0; while (n < data.Length) { int r = fs.Read(data, n, data.Length - n); if (r <= 0) break; n += r; }
            }

            var owned = new Dictionary<uint, int>();
            byte[] tag = { (byte)'i', (byte)'t', (byte)'e', (byte)'m', (byte)'2', (byte)'0' };
            for (int o = 0; o <= data.Length - 0x2C; o++)
            {
                if (data[o] != tag[0] || data[o + 1] != tag[1] || data[o + 2] != tag[2] ||
                    data[o + 3] != tag[3] || data[o + 4] != tag[4] || data[o + 5] != tag[5]) continue;
                uint hash = BitConverter.ToUInt32(data, o + 32);
                int q1 = BitConverter.ToInt32(data, o + 36), q2 = BitConverter.ToInt32(data, o + 40);
                if (q1 == q2 && q1 >= 1 && known.ContainsKey(hash))
                    owned[hash] = Math.Max(owned.GetValueOrDefault(hash), q1);
            }
            return owned;
        }
    }
}