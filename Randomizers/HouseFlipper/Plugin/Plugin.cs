using System;
using System.Collections;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using System.Net.WebSockets;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using BepInEx;
using HarmonyLib;
using UnityEngine;

namespace HouseFlipperArchipelago
{
    [BepInPlugin("com.sotrando.houseflipper.ap", "House Flipper Archipelago", "2.3.0")]
    public class Plugin : BaseUnityPlugin
    {
        public static bool Connected = false;
        public static bool GoalSent = false;
        public static int GoalMode = 0;
        public static long NetWorthTarget = 1500000;
        public static int ContractsToWin = 15;
        public static int TotalItemsReceived = 0;

        public static HashSet<long> CheckedLocations = new HashSet<long>();
        public static ConcurrentQueue<string> Outgoing = new ConcurrentQueue<string>();
        public static ConcurrentQueue<long> PendingItems = new ConcurrentQueue<long>();
        public static Dictionary<string, int> GrantedPerks = new Dictionary<string, int>();
        public static HashSet<int> UnlockedToolEnums = new HashSet<int> { 0, 1, 3 };
        public static HashSet<int> UnlockedDeedIndices = new HashSet<int>();
        public static int ContractPermits = 0;

        public static int PerkCheckCounter = 0;
        public static int OrderCheckCounter = 0;
        public static float LastOrderCheckTime = -10f;
        public static float LastPerkCheckTime = -10f;
        private static bool _baselineCleared = false;
        private static double _pendingCash = 0.0;

        private bool _showConnGui = true;
        private string _url = "ws://localhost:38281";
        private string _slot = "flip";
        private string _pass = "";
        private string _status = "Disconnected (F1 to toggle)";
        private float _scanTimer = 0f;

        private void Awake()
        {
            var harmony = new Harmony("com.sotrando.houseflipper.ap");
            var asm = Assembly.Load("Assembly-CSharp");

            var utType = asm.GetType("UnlockedTools");
            if (utType != null)
            {
                foreach (var m in utType.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly))
                {
                    if (m.Name == "IsToolUnlocked")
                        harmony.Patch(m, postfix: new HarmonyMethod(typeof(Plugin), nameof(OnIsToolUnlocked)));
                    else if (m.Name == "UnlockTools" || m.Name == "UnlockAllTools")
                        harmony.Patch(m, prefix: new HarmonyMethod(typeof(Plugin), nameof(BlockVanillaUnlock)));
                }
            }

            var tcType = asm.GetType("Assets.Code.Player.Tools.ToolsChooser");
            if (tcType != null)
            {
                foreach (var m in tcType.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.DeclaredOnly))
                {
                    if (m.Name == "AddTemporaryAvailableTool" || m.Name == "UnlockAndGetTool" || m.Name == "UnlockTool" || m.Name == "SelectTool")
                        harmony.Patch(m, prefix: new HarmonyMethod(typeof(Plugin), nameof(OnToolsChooserGate)));
                }
            }

            var opType = asm.GetType("OrdersProgress");
            var mGetOrders = opType?.GetMethod("GetOrdersSortedByRequirements", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            if (mGetOrders != null)
                harmony.Patch(mGetOrders, postfix: new HarmonyMethod(typeof(Plugin), nameof(OnGetSortedOrders)));

            foreach (var t in asm.GetTypes())
            {
                var mClip = t.GetMethod("PlayCompleteOrderClip", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.DeclaredOnly);
                if (mClip != null) harmony.Patch(mClip, postfix: new HarmonyMethod(typeof(Plugin), nameof(OnOrderCompleted)));
                var mSell = t.GetMethod("HandleSellHouse", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.DeclaredOnly);
                if (mSell != null) harmony.Patch(mSell, postfix: new HarmonyMethod(typeof(Plugin), nameof(OnHouseSold)));
            }
            Logger.LogInfo("House Flipper Archipelago 2.3.0 loaded!");
        }

        private static bool IsGatedTool(int toolVal)
        {
            return toolVal == 2 || toolVal == 4 || toolVal == 5 || toolVal == 6 || toolVal == 7 || toolVal == 8 || toolVal == 9 || toolVal == 10;
        }

        public static bool BlockVanillaUnlock() => !Connected;

        public static bool OnToolsChooserGate(object[] __args)
        {
            if (!Connected || __args == null || __args.Length == 0 || __args == null) return true;
            try
            {
                if (__args is Array arr)
                {
                    foreach (var item in arr)
                    {
                        int tv = Convert.ToInt32(item);
                        if (IsGatedTool(tv) && !UnlockedToolEnums.Contains(tv)) return false;
                    }
                    return true;
                }
                int toolVal = Convert.ToInt32(__args[0]);
                if (IsGatedTool(toolVal) && !UnlockedToolEnums.Contains(toolVal))
                    return false;
            }
            catch { }
            return true;
        }

        public static void OnIsToolUnlocked(object[] __args, ref bool __result)
        {
            if (!Connected || __args == null || __args.Length == 0 || __args == null) return;
            int toolVal = Convert.ToInt32(__args[0]);
            if (toolVal == 1) __result = true;
            else if (IsGatedTool(toolVal)) __result = UnlockedToolEnums.Contains(toolVal);
        }

        public static void OnGetSortedOrders(ref IList __result)
        {
            if (!Connected || __result == null) return;
            int maxAllowed = 4 + (ContractPermits * 4);
            while (__result.Count > maxAllowed)
                __result.RemoveAt(__result.Count - 1);
        }

        public static void SendCheck(long id)
        {
            if (!Connected) return;
            if (CheckedLocations.Add(id))
                Outgoing.Enqueue("[{\"cmd\":\"LocationChecks\",\"locations\":[" + id + "]}]");
        }

        public static void OnOrderCompleted()
        {
            if (Time.timeSinceLevelLoad < 5f) return;
            if (Time.unscaledTime - LastOrderCheckTime < 3f) return;
            LastOrderCheckTime = Time.unscaledTime;

            int idx = OrderCheckCounter++ % 20;
            SendCheck(10000 + idx);
            SendCheck(10100 + idx);
        }

        public static void OnHouseSold()
        {
            if (Time.timeSinceLevelLoad < 5f) return;
            SendCheck(10300 + (OrderCheckCounter % 15));
        }

        private static object GetLivePlayerProgress()
        {
            var asm = Assembly.Load("Assembly-CSharp");
            var pcType = asm.GetType("Assets.Code.Player.PlayerController");
            if (pcType == null) return null;
            var pcObj = FindObjectOfType(pcType);
            if (pcObj == null) return null;
            var progField = pcType.GetField("progress", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            return progField?.GetValue(pcObj);
        }

        private static object GetLiveSkillsObject()
        {
            var progObj = GetLivePlayerProgress();
            var skillsField = progObj?.GetType().GetField("skills", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            return skillsField?.GetValue(progObj);
        }

        private static void SyncUnlockedToolsToWheel()
        {
            var progObj = GetLivePlayerProgress();
            if (progObj == null) return;
            var atField = progObj.GetType().GetField("avaialbleTools", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            var atObj = atField?.GetValue(progObj);
            var listField = atObj?.GetType().GetField("tools", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            if (listField?.GetValue(atObj) is IList toolList)
            {
                var asm = Assembly.Load("Assembly-CSharp");
                var utType = asm.GetType("UnlockedTools");
                var enumType = utType?.GetMethod("IsToolUnlocked")?.GetParameters()[0]?.ParameterType;
                if (enumType != null)
                {
                    foreach (int tv in UnlockedToolEnums)
                    {
                        object enumVal = Enum.ToObject(enumType, tv);
                        if (!toolList.Contains(enumVal)) toolList.Add(enumVal);
                    }
                }
            }
            var tcType = Assembly.Load("Assembly-CSharp").GetType("Assets.Code.Player.Tools.ToolsChooser");
            var tcObj = tcType != null ? FindObjectOfType(tcType) : null;
            var mUpd = tcType?.GetMethod("UpdateAvailableTools", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            mUpd?.Invoke(tcObj, null);
        }

        private static long GetCurrentNetWorth()
        {
            var progObj = GetLivePlayerProgress();
            if (progObj == null) return 0;
            double cash = 0.0;
            var mpField = progObj.GetType().GetField("moneyProgress", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            var mpObj = mpField?.GetValue(progObj);
            if (mpObj != null)
            {
                var mField = mpObj.GetType().GetField("_money", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                if (mField != null) cash = Convert.ToDouble(mField.GetValue(mpObj));
            }
            return Math.Max(0L, (long)cash + (UnlockedDeedIndices.Count * 25000L));
        }

        private static void GrantCash(double amount)
        {
            var progObj = GetLivePlayerProgress();
            if (progObj == null) { _pendingCash += amount; return; }
            var mpField = progObj.GetType().GetField("moneyProgress", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            var mpObj = mpField?.GetValue(progObj);
            if (mpObj != null)
            {
                var mField = mpObj.GetType().GetField("_money", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                if (mField != null) mField.SetValue(mpObj, Convert.ToDouble(mField.GetValue(mpObj)) + amount);
            }
        }

        private static readonly (string catField, string perkField)[] PerkTargets = new[]
        {
            ("cleaning", "fastHands"), ("cleaning", "longDistance"), ("cleaning", "eyeOfTheMotherInLaw"),
            ("demolition", "tempo"), ("demolition", "muscle"), ("demolition", "biggerHammer"),
            ("painting", "paintingBase"), ("painting", "fastHands"), ("painting", "paintMore"),
            ("handyman", "fitter"), ("handyman", "plasterer"), ("handyman", "tiler"),
            ("building", "bricklayer"), ("building", "mason"), ("building", "fixer"),
            ("negotiation", "negotiatePrice"), ("negotiation", "fasterOrder"), ("negotiation", "higherPayment")
        };

        private static readonly string[] HouseSceneIds = new[]
        {
            "FirstOffice", "AbandonedHouse", "BurnedHouse", "HackerLoft", "SamartaMyersHouse",
            "FamilyHouse", "GardenAfterBuilding", "JustMarriedHouse", "PinkKingdom", "TrainCar",
            "ManCave", "UninhabitedHouse", "HouseOnTheMoon", "ConnoisseurHouse", "CacheInABunker",
            "13thFloor", "Castle", "CyberpunkLoft", "HucksterHouse", "LuxuryVilla"
        };

        private void Update()
        {
            if (Input.GetKeyDown(KeyCode.F1)) _showConnGui = !_showConnGui;
            if (Input.GetKeyDown(KeyCode.Tab)) GUI.FocusControl(null);

            _scanTimer += Time.unscaledDeltaTime;
            if (_scanTimer >= 0.4f)
            {
                _scanTimer = 0f;
                SyncSkillsAndPerks();
                EnforceHouseGates();
                CheckGoalCompletion();
                if (_pendingCash > 0.0) { double amt = _pendingCash; _pendingCash = 0.0; GrantCash(amt); }
            }

            while (PendingItems.TryDequeue(out long itemId))
                ApplyReceivedItem(itemId);
        }

        private void CheckGoalCompletion()
        {
            if (!Connected || GoalSent) return;
            bool won = (GoalMode == 0 && GetCurrentNetWorth() >= NetWorthTarget) ||
                       (GoalMode == 1 && OrderCheckCounter >= ContractsToWin) ||
                       (GoalMode == 2 && UnlockedDeedIndices.Count >= 20);
            if (won)
            {
                GoalSent = true;
                Outgoing.Enqueue("[{\"cmd\":\"StatusUpdate\",\"status\":30}]");
                _status = "GOAL COMPLETE! Victory Sent!";
            }
        }

        private void EnforceHouseGates()
        {
            if (!Connected) return;
            var progObj = GetLivePlayerProgress();
            if (progObj == null) return;
            var hpField = progObj.GetType().GetField("housesProgress", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            var hpObj = hpField?.GetValue(progObj);
            var mBuy = hpObj?.GetType().GetMethod("MarkAsBought", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            var boughtF = hpObj?.GetType().GetField("boughtHouseScenes", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            var boughtList = boughtF?.GetValue(hpObj) as IList;

            foreach (int dIdx in UnlockedDeedIndices)
            {
                if (dIdx >= 0 && dIdx < HouseSceneIds.Length)
                {
                    string sceneName = HouseSceneIds[dIdx];
                    if (boughtList != null && !boughtList.Contains(sceneName) && mBuy != null)
                        mBuy.Invoke(hpObj, new object[] { sceneName });
                }
            }

            var housesField = progObj.GetType().GetField("unlockedHousesToBuy", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            if (housesField?.GetValue(progObj) is HashSet<string> houseSet)
            {
                foreach (int dIdx in UnlockedDeedIndices)
                    if (dIdx >= 0 && dIdx < HouseSceneIds.Length)
                        houseSet.Add(HouseSceneIds[dIdx]);
                while (houseSet.Count > UnlockedDeedIndices.Count)
                    houseSet.Remove(houseSet.Last());
            }
        }

        private void SyncSkillsAndPerks()
        {
            var skillsObj = GetLiveSkillsObject();
            if (skillsObj == null) return;

            var skillsType = skillsObj.GetType();
            foreach (var t in PerkTargets)
            {
                var catF = skillsType.GetField(t.catField, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                var catObj = catF?.GetValue(skillsObj);
                if (catObj == null) continue;
                var perkF = catObj.GetType().GetField(t.perkField, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                if (perkF != null && perkF.FieldType == typeof(int))
                {
                    string key = t.catField + "." + t.perkField;
                    int allowed = GrantedPerks.TryGetValue(key, out int lvl) ? lvl : 0;
                    if ((int)perkF.GetValue(catObj) != allowed) perkF.SetValue(catObj, allowed);
                }
            }

            if (!Connected) return;
            var catsField = skillsType.GetField("skillCategories", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            if (catsField?.GetValue(skillsObj) is IEnumerable cats)
            {
                foreach (var cat in cats)
                {
                    if (cat == null) continue;
                    var availField = cat.GetType().GetField("numberOfPerksAvailable", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                    if (availField == null) continue;
                    if ((int)availField.GetValue(cat) > 0)
                    {
                        availField.SetValue(cat, 0);
                        if (_baselineCleared && Time.timeSinceLevelLoad >= 5f && Time.unscaledTime - LastPerkCheckTime >= 2.0f)
                        {
                            LastPerkCheckTime = Time.unscaledTime;
                            ScaleConfigFields(cat, 2.2f);
                            var cfgField = cat.GetType().GetField("skillProgressConfiguration", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                            var cfgObj = cfgField?.GetValue(cat);
                            if (cfgObj != null) ScaleConfigFields(cfgObj, 2.2f);
                            SendCheck(10200 + (PerkCheckCounter++ % 30));
                        }
                    }
                }
                _baselineCleared = true;
            }
        }

        private static void ScaleConfigFields(object targetObj, float mult)
        {
            foreach (var cf in targetObj.GetType().GetFields(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance))
            {
                if (cf.Name == "numberOfPerksAvailable" || cf.Name == "fastHands" || cf.Name == "longDistance" || cf.Name == "eyeOfTheMotherInLaw" ||
                    cf.Name == "tempo" || cf.Name == "muscle" || cf.Name == "biggerHammer" || cf.Name == "paintingBase" || cf.Name == "paintMore" ||
                    cf.Name == "fitter" || cf.Name == "plasterer" || cf.Name == "tiler" || cf.Name == "bricklayer" || cf.Name == "mason" ||
                    cf.Name == "fixer" || cf.Name == "negotiatePrice" || cf.Name == "fasterOrder" || cf.Name == "higherPayment")
                    continue;
                if (cf.FieldType == typeof(int))
                {
                    int val = (int)cf.GetValue(targetObj);
                    if (val > 0 && val < 500000) cf.SetValue(targetObj, (int)Math.Ceiling(val * mult));
                }
                else if (cf.FieldType == typeof(float))
                {
                    float val = (float)cf.GetValue(targetObj);
                    if (val > 0f && val < 500000f) cf.SetValue(targetObj, val * mult);
                }
            }
        }

        private void ApplyReceivedItem(long itemId)
        {
            TotalItemsReceived++;
            if (itemId >= 20001 && itemId <= 20004) { ContractPermits = Math.Max(ContractPermits, (int)(itemId - 20000)); return; }
            if (itemId == 20010) { UnlockedToolEnums.Add(10); SyncUnlockedToolsToWheel(); return; }
            if (itemId == 20011) { UnlockedToolEnums.Add(2); SyncUnlockedToolsToWheel(); return; }
            if (itemId == 20012) { UnlockedToolEnums.Add(7); UnlockedToolEnums.Add(8); UnlockedToolEnums.Add(9); SyncUnlockedToolsToWheel(); return; }
            if (itemId == 20013) { UnlockedToolEnums.Add(6); SyncUnlockedToolsToWheel(); return; }
            if (itemId == 20014) { UnlockedToolEnums.Add(4); UnlockedToolEnums.Add(5); SyncUnlockedToolsToWheel(); return; }
            if (itemId == 20060) { GrantCash(500.0); return; }
            if (itemId == 20061) { GrantCash(1500.0); return; }
            if (itemId == 20062) { GrantCash(5000.0); return; }
            if (itemId >= 20070 && itemId <= 20089) { UnlockedDeedIndices.Add((int)(itemId - 20070)); EnforceHouseGates(); return; }

            int pIdx = (int)(itemId - 20020);
            if (pIdx >= 0 && pIdx < PerkTargets.Length)
            {
                var t = PerkTargets[pIdx];
                string key = t.catField + "." + t.perkField;
                int cur = GrantedPerks.TryGetValue(key, out int lvl) ? lvl : 0;
                GrantedPerks[key] = Math.Min(3, cur + 1);
            }
            SyncSkillsAndPerks();
        }

        private string GetGoalProgressText()
        {
            if (GoalMode == 0)
            {
                long nw = GetCurrentNetWorth();
                int pct = (int)Math.Min(100, (nw * 100) / Math.Max(1, NetWorthTarget));
                return $"Net Worth: ${nw:N0} / ${NetWorthTarget:N0} ({pct}%)";
            }
            if (GoalMode == 1) return $"Contracts Completed: {OrderCheckCounter} / {ContractsToWin}";
            return $"Property Deeds: {UnlockedDeedIndices.Count} / 20";
        }

        private void OnGUI()
        {
            GUI.depth = -1000;
            float rx = Screen.width - 315f;
            GUI.Box(new Rect(rx, 15, 300, 102), "Archipelago Goal Progress");
            GUI.Label(new Rect(rx + 12, 38, 276, 22), GetGoalProgressText());
            GUI.Label(new Rect(rx + 12, 60, 276, 22), $"Deeds: {UnlockedDeedIndices.Count}/20 | Permits: Tier {ContractPermits}/4");
            GUI.Label(new Rect(rx + 12, 82, 276, 22), $"AP Items Received: {TotalItemsReceived}");

            if (!_showConnGui) return;
            GUI.Box(new Rect(15, 15, 300, 175), "House Flipper Connection (F1)");
            GUI.Label(new Rect(25, 38, 280, 22), _status);
            _url = GUI.TextField(new Rect(25, 62, 280, 24), _url);
            _slot = GUI.TextField(new Rect(25, 90, 280, 24), _slot);
            _pass = GUI.PasswordField(new Rect(25, 118, 280, 24), _pass, '*');
            if (GUI.Button(new Rect(25, 148, 280, 28), Connected ? "Connected (Reconnect)" : "Connect"))
            {
                _baselineCleared = false;
                GUI.FocusControl(null);
                _ = ConnectLoopAsync(_url, _slot, _pass);
            }
        }

        private async Task ConnectLoopAsync(string url, string slot, string pass)
        {
            try
            {
                _status = "Connecting...";
                if (!url.StartsWith("ws://") && !url.StartsWith("wss://")) url = "ws://" + url;
                var ws = new ClientWebSocket();
                await ws.ConnectAsync(new Uri(url), CancellationToken.None);
                string pkt = "[{\"cmd\":\"Connect\",\"password\":\"" + pass + "\",\"game\":\"House Flipper\",\"name\":\"" + slot + "\",\"uuid\":\"hf-ap-v23\",\"version\":{\"major\":0,\"minor\":5,\"build\":0,\"class\":\"Version\"},\"items_handling\":7,\"tags\":[\"AP\"]}]";
                await ws.SendAsync(new ArraySegment<byte>(Encoding.UTF8.GetBytes(pkt)), WebSocketMessageType.Text, true, CancellationToken.None);

                _ = Task.Run(async () =>
                {
                    while (ws.State == WebSocketState.Open)
                    {
                        while (Outgoing.TryDequeue(out var msg))
                            await ws.SendAsync(new ArraySegment<byte>(Encoding.UTF8.GetBytes(msg)), WebSocketMessageType.Text, true, CancellationToken.None);
                        await Task.Delay(100);
                    }
                });

                var buf = new byte[8192];
                while (ws.State == WebSocketState.Open)
                {
                    var sb = new StringBuilder();
                    WebSocketReceiveResult res;
                    do
                    {
                        res = await ws.ReceiveAsync(new ArraySegment<byte>(buf), CancellationToken.None);
                        sb.Append(Encoding.UTF8.GetString(buf, 0, res.Count));
                    } while (!res.EndOfMessage);
                    string raw = sb.ToString();
                    if (raw.Contains("\"Connected\""))
                    {
                        Connected = true;
                        _status = "Connected as " + slot + "!";
                        var mg = Regex.Match(raw, "\"goal\"\\s*:\\s*(\\d+)");
                        if (mg.Success) int.TryParse(mg.Groups[1].Value, out GoalMode);
                        var mn = Regex.Match(raw, "\"net_worth_target\"\\s*:\\s*(\\d+)");
                        if (mn.Success) long.TryParse(mn.Groups[1].Value, out NetWorthTarget);
                        var mc = Regex.Match(raw, "\"contracts_to_win\"\\s*:\\s*(\\d+)");
                        if (mc.Success) int.TryParse(mc.Groups[1].Value, out ContractsToWin);
                    }
                    if (raw.Contains("\"ReceivedItems\""))
                        foreach (Match m in Regex.Matches(raw, "\"item\"\\s*:\\s*(\\d+)"))
                            if (long.TryParse(m.Groups[1].Value, out long itemId))
                                PendingItems.Enqueue(itemId);
                }
            }
            catch (Exception ex) { Connected = false; _status = "Err: " + ex.Message; }
        }
    }
}
