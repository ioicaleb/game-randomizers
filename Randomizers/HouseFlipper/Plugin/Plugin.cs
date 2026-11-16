using System;
using System.Collections;
using System.Collections.Concurrent;
using System.Collections.Generic;
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
    [BepInPlugin("com.sotrando.houseflipper.ap", "House Flipper Archipelago", "1.9.0")]
    public class Plugin : BaseUnityPlugin
    {
        public static bool Connected = false;
        public static HashSet<long> CheckedLocations = new HashSet<long>();
        public static ConcurrentQueue<string> Outgoing = new ConcurrentQueue<string>();
        public static ConcurrentQueue<long> PendingItems = new ConcurrentQueue<long>();
        public static Dictionary<string, int> GrantedPerks = new Dictionary<string, int>();
        public static Dictionary<int, int> VirtualXpRanksByCatHash = new Dictionary<int, int>();
        public static HashSet<int> UnlockedToolEnums = new HashSet<int> { 0, 1, 2 };
        public static int PerkCheckCounter = 0;
        public static int OrderCheckCounter = 0;
        public static int HouseCheckCounter = 0;
        public static float LastOrderCheckTime = -10f;
        public static float LastPerkCheckTime = -10f;
        private static bool _baselineCleared = false;

        private bool _showGui = true;
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
            var mTool = utType?.GetMethod("IsToolUnlocked", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static);
            if (mTool != null)
                harmony.Patch(mTool, postfix: new HarmonyMethod(typeof(Plugin), nameof(OnIsToolUnlocked)));

            foreach (var t in asm.GetTypes())
            {
                var mClip = t.GetMethod("PlayCompleteOrderClip", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.DeclaredOnly);
                if (mClip != null) harmony.Patch(mClip, postfix: new HarmonyMethod(typeof(Plugin), nameof(OnOrderCompleted)));

                var mSell = t.GetMethod("HandleSellHouse", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.DeclaredOnly);
                if (mSell != null) harmony.Patch(mSell, postfix: new HarmonyMethod(typeof(Plugin), nameof(OnHouseSold)));
            }
            Logger.LogInfo("House Flipper Archipelago 1.9.0 loaded!");
        }

        public static void OnIsToolUnlocked(object[] __args, ref bool __result)
        {
            if (!Connected || __args == null || __args.Length == 0 || __args == null) return;
            int toolVal = Convert.ToInt32(__args[0]);
            if (toolVal > 2)
                __result = UnlockedToolEnums.Contains(toolVal);
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
            SendCheck(10100 + (OrderCheckCounter++ % 30));
        }

        public static void OnHouseSold()
        {
            if (Time.timeSinceLevelLoad < 5f) return;
            SendCheck(10200 + (HouseCheckCounter++ % 20));
        }

        private static object GetLiveSkillsObject()
        {
            var asm = Assembly.Load("Assembly-CSharp");
            var pcType = asm.GetType("Assets.Code.Player.PlayerController");
            if (pcType == null) return null;
            var pcObj = FindObjectOfType(pcType);
            if (pcObj == null) return null;

            var progField = pcType.GetField("progress", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            var progObj = progField?.GetValue(pcObj);
            if (progObj == null) return null;

            var skillsField = progObj.GetType().GetField("skills", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            return skillsField?.GetValue(progObj);
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

        private static readonly HashSet<int> ScaledConfigs = new HashSet<int>();

        private void Update()
        {
            if (Input.GetKeyDown(KeyCode.F1)) _showGui = !_showGui;

            _scanTimer += Time.unscaledDeltaTime;
            if (_scanTimer >= 0.4f)
            {
                _scanTimer = 0f;
                SyncSkillsAndPerks();
            }

            while (PendingItems.TryDequeue(out long itemId))
            {
                ApplyReceivedItem(itemId);
            }
        }

        private void SyncSkillsAndPerks()
        {
            var skillsObj = GetLiveSkillsObject();
            if (skillsObj == null) return;

            var skillsType0 = skillsObj.GetType();
            foreach (var t in PerkTargets)
            {
                var catF = skillsType0.GetField(t.catField, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
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

            var catsField = skillsObj.GetType().GetField("skillCategories", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            var cats = catsField?.GetValue(skillsObj) as IEnumerable;
            if (cats != null)
            {
                foreach (var cat in cats)
                {
                    if (cat == null) continue;
                    int catHash = cat.GetHashCode();
                    var availField = cat.GetType().GetField("numberOfPerksAvailable", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                    if (availField == null) continue;
                    int avail = (int)availField.GetValue(cat);
                    if (avail > 0)
                    {
                        availField.SetValue(cat, 0);
                        if (_baselineCleared && Time.timeSinceLevelLoad >= 5f && Time.unscaledTime - LastPerkCheckTime >= 1.5f)
                        {
                            LastPerkCheckTime = Time.unscaledTime;
                            int curRank = VirtualXpRanksByCatHash.TryGetValue(catHash, out int r) ? r : 0;
                            VirtualXpRanksByCatHash[catHash] = curRank + 1;

                            // Escalate the XP requirement config on this category so each subsequent perk check requires more XP!
                            var cfgField = cat.GetType().GetField("skillProgressConfiguration", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                            var cfgObj = cfgField?.GetValue(cat);
                            if (cfgObj != null)
                            {
                                foreach (var cf in cfgObj.GetType().GetFields(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance))
                                {
                                    if (cf.FieldType == typeof(int))
                                    {
                                        int val = (int)cf.GetValue(cfgObj);
                                        if (val > 0 && val < 50000) cf.SetValue(cfgObj, (int)(val * 1.6f));
                                    }
                                    else if (cf.FieldType == typeof(float))
                                    {
                                        float val = (float)cf.GetValue(cfgObj);
                                        if (val > 0f && val < 50000f) cf.SetValue(cfgObj, val * 1.6f);
                                    }
                                }
                            }

                            SendCheck(10000 + (PerkCheckCounter++ % 40));
                        }
                    }
                }
                _baselineCleared = true;
            }

            // Enforce that ALL active perk bonuses strictly match GrantedPerks (0 unless received from Archipelago!)
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
        }

        private void ApplyReceivedItem(long itemId)
        {
            if (itemId >= 20001 && itemId <= 20009)
            {
                int toolEnum = (int)(itemId - 20001) + 2;
                UnlockedToolEnums.Add(toolEnum);
                return;
            }

            int idx = (int)(Math.Abs(itemId) % PerkTargets.Length);
            var target = PerkTargets[idx];
            string key = target.catField + "." + target.perkField;
            int cur = GrantedPerks.TryGetValue(key, out int lvl) ? lvl : 0;
            GrantedPerks[key] = Math.Min(3, cur + 1);
            SyncSkillsAndPerks();
        }

        private void OnGUI()
        {
            if (!_showGui) return;
            GUI.depth = -1000;
            GUI.Box(new Rect(15, 15, 300, 175), "House Flipper Archipelago (F1)");
            GUI.Label(new Rect(25, 38, 280, 22), _status);
            _url = GUI.TextField(new Rect(25, 62, 280, 24), _url);
            _slot = GUI.TextField(new Rect(25, 90, 280, 24), _slot);
            _pass = GUI.PasswordField(new Rect(25, 118, 280, 24), _pass, '*');
            if (GUI.Button(new Rect(25, 148, 280, 28), Connected ? "Connected (Reconnect)" : "Connect"))
            {
                _baselineCleared = false;
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
                string pkt = "[{\"cmd\":\"Connect\",\"password\":\"" + pass + "\",\"game\":\"House Flipper\",\"name\":\"" + slot + "\",\"uuid\":\"hf-ap-v10\",\"version\":{\"major\":0,\"minor\":5,\"build\":0,\"class\":\"Version\"},\"items_handling\":7,\"tags\":[\"AP\"]}]";
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
                    if (raw.Contains("\"Connected\"")) { Connected = true; _status = "Connected as " + slot + "!"; }
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
