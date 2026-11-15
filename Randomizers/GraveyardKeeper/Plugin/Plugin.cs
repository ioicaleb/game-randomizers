using System;
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

namespace GraveyardKeeperArchipelago
{
    [BepInPlugin("com.sotrando.graveyardkeeper.ap", "Graveyard Keeper Archipelago", "1.0.0")]
    public class Plugin : BaseUnityPlugin
    {
        public static bool Connected = false;
        public static HashSet<long> UnlockedIds = new HashSet<long>();
        public static HashSet<long> CheckedLocations = new HashSet<long>();
        public static ConcurrentQueue<string> Outgoing = new ConcurrentQueue<string>();
        public static ConcurrentQueue<float> PendingMoney = new ConcurrentQueue<float>();
        public static MethodInfo AddMoneyMethod = null;
        public static int TechCounter = 0;
        public static int QuestCounter = 0;

        private void Awake()
        {
            var go = new GameObject("GkApOverlay");
            go.hideFlags = HideFlags.HideAndDontSave;
            DontDestroyOnLoad(go);
            go.AddComponent<ApOverlay>();

            var harmony = new Harmony("com.sotrando.graveyardkeeper.ap");
            var asm = Assembly.Load("Assembly-CSharp");
            foreach (var t in asm.GetTypes())
            {
                var mTech = t.GetMethod("Flow_UnlockTech", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly);
                if (mTech != null) harmony.Patch(mTech, postfix: new HarmonyMethod(typeof(Plugin), nameof(OnTechUnlocked)));

                var mQuest = t.GetMethod("CheckQuestProgress", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly);
                if (mQuest != null) harmony.Patch(mQuest, postfix: new HarmonyMethod(typeof(Plugin), nameof(OnQuestChecked)));

                var mMoney = t.GetMethod("Flow_AddMoney", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.DeclaredOnly);
                if (mMoney != null && mMoney.GetParameters().Length >= 1) AddMoneyMethod = mMoney;
            }
            Logger.LogInfo("Graveyard Keeper Archipelago loaded!");
        }

        public static void OnTechUnlocked()
        {
            if (!Connected) return;
            long id = 10000 + (TechCounter++ % 60);
            if (CheckedLocations.Add(id))
                Outgoing.Enqueue("[{\"cmd\":\"LocationChecks\",\"locations\":[" + id + "]}]");
        }

        public static void OnQuestChecked()
        {
            if (!Connected) return;
            long id = 10100 + (QuestCounter++ % 45);
            if (CheckedLocations.Add(id))
                Outgoing.Enqueue("[{\"cmd\":\"LocationChecks\",\"locations\":[" + id + "]}]");
        }
    }

    public class ApOverlay : MonoBehaviour
    {
        private bool _showGui = true;
        private string _url = "ws://localhost:38281";
        private string _slot = "Keeper";
        private string _pass = "";
        private string _status = "Disconnected (F1 to toggle)";

        private void Update()
        {
            if (Input.GetKeyDown(KeyCode.F1)) _showGui = !_showGui;
            if (Plugin.AddMoneyMethod != null && Plugin.PendingMoney.TryDequeue(out float coins))
            {
                try
                {
                    var ps = Plugin.AddMoneyMethod.GetParameters();
                    var args = new object[ps.Length];
                    args[0] = coins;
                    Plugin.AddMoneyMethod.Invoke(null, args);
                }
                catch { }
            }
        }

        private void OnGUI()
        {
            if (!_showGui) return;
            GUI.depth = -1000;
            GUI.Box(new Rect(15, 15, 300, 175), "Graveyard Keeper Archipelago (F1)");
            GUI.Label(new Rect(25, 38, 280, 22), _status);
            _url = GUI.TextField(new Rect(25, 62, 280, 24), _url);
            _slot = GUI.TextField(new Rect(25, 90, 280, 24), _slot);
            _pass = GUI.PasswordField(new Rect(25, 118, 280, 24), _pass, '*');
            if (GUI.Button(new Rect(25, 148, 280, 28), Plugin.Connected ? "Reconnect" : "Connect"))
                _ = ConnectLoopAsync(_url, _slot, _pass);
        }

        private async Task ConnectLoopAsync(string url, string slot, string pass)
        {
            try
            {
                _status = "Connecting...";
                if (!url.StartsWith("ws://") && !url.StartsWith("wss://")) url = "ws://" + url;
                var ws = new ClientWebSocket();
                await ws.ConnectAsync(new Uri(url), CancellationToken.None);
                string pkt = "[{\"cmd\":\"Connect\",\"password\":\"" + pass + "\",\"game\":\"Graveyard Keeper\",\"name\":\"" + slot + "\",\"uuid\":\"gk-ap\",\"version\":{\"major\":0,\"minor\":5,\"build\":0,\"class\":\"Version\"},\"items_handling\":7,\"tags\":[\"AP\"]}]";
                await ws.SendAsync(new ArraySegment<byte>(Encoding.UTF8.GetBytes(pkt)), WebSocketMessageType.Text, true, CancellationToken.None);

                _ = Task.Run(async () =>
                {
                    while (ws.State == WebSocketState.Open)
                    {
                        while (Plugin.Outgoing.TryDequeue(out var msg))
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
                    if (raw.Contains("\"Connected\"")) { Plugin.Connected = true; _status = "Connected as " + slot + "!"; }
                    if (raw.Contains("\"ReceivedItems\""))
                        foreach (Match m in Regex.Matches(raw, "\"item\"\\s*:\\s*(\\d+)"))
                            if (long.TryParse(m.Groups[1].Value, out long itemId))
                            {
                                Plugin.UnlockedIds.Add(itemId);
                                if (itemId == 20030) Plugin.PendingMoney.Enqueue(1500f);
                                else if (itemId == 20032) Plugin.PendingMoney.Enqueue(10000f);
                            }
                }
            }
            catch (Exception ex) { Plugin.Connected = false; _status = "Err: " + ex.Message; }
        }
    }
}
