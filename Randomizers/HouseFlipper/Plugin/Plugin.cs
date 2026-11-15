using System;
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
    [BepInPlugin("com.sotrando.houseflipper.ap", "House Flipper Archipelago", "1.0.0")]
    public class Plugin : BaseUnityPlugin
    {
        public static bool Connected = false;
        public static HashSet<long> UnlockedIds = new HashSet<long>();
        public static HashSet<long> CheckedLocations = new HashSet<long>();
        public static ConcurrentQueue<string> Outgoing = new ConcurrentQueue<string>();
        public static ConcurrentQueue<int> PendingCash = new ConcurrentQueue<int>();
        public static int OrderCounter = 0;
        public static int PerkCounter = 0;

        private void Awake()
        {
            var go = new GameObject("HouseFlipperApOverlay");
            go.hideFlags = HideFlags.HideAndDontSave;
            DontDestroyOnLoad(go);
            go.AddComponent<ApOverlay>();

            var harmony = new Harmony("com.sotrando.houseflipper.ap");
            foreach (var t in Assembly.Load("Assembly-CSharp").GetTypes())
            {
                var mOrder = t.GetMethod("CompleteOrder", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly);
                if (mOrder != null)
                    harmony.Patch(mOrder, postfix: new HarmonyMethod(typeof(Plugin), nameof(OnOrderCompleted)));

                var mPerk = t.GetMethod("SetNumberOfAvailablePerks", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly);
                if (mPerk != null)
                    harmony.Patch(mPerk, postfix: new HarmonyMethod(typeof(Plugin), nameof(OnPerkUpdated)));
            }
            Logger.LogInfo("House Flipper Archipelago plugin loaded!");
        }

        public static void OnOrderCompleted()
        {
            if (!Connected) return;
            long id = 10000 + (OrderCounter++ % 20);
            if (CheckedLocations.Add(id))
                Outgoing.Enqueue($"[{{\"cmd\":\"LocationChecks\",\"locations\":[{id}]}}]");
        }

        public static void OnPerkUpdated()
        {
            if (!Connected) return;
            long id = 10200 + (PerkCounter++ % 20);
            if (CheckedLocations.Add(id))
                Outgoing.Enqueue($"[{{\"cmd\":\"LocationChecks\",\"locations\":[{id}]}}]");
        }
    }

    public class ApOverlay : MonoBehaviour
    {
        private bool _showGui = true;
        private string _url = "ws://localhost:38281";
        private string _slot = "Flipper";
        private string _pass = "";
        private string _status = "Disconnected (F1 to toggle)";

        private void Update()
        {
            if (Input.GetKeyDown(KeyCode.F1)) _showGui = !_showGui;
        }

        private void OnGUI()
        {
            if (!_showGui) return;
            GUI.depth = -1000;
            GUI.Box(new Rect(15, 15, 290, 175), "House Flipper Archipelago (F1)");
            GUI.Label(new Rect(25, 38, 270, 22), _status);
            _url = GUI.TextField(new Rect(25, 62, 270, 24), _url);
            _slot = GUI.TextField(new Rect(25, 90, 270, 24), _slot);
            _pass = GUI.PasswordField(new Rect(25, 118, 270, 24), _pass, '*');
            if (GUI.Button(new Rect(25, 148, 270, 28), Plugin.Connected ? "Reconnect" : "Connect"))
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
                string connectPkt = $"[{{\"cmd\":\"Connect\",\"password\":\"{pass}\",\"game\":\"House Flipper\",\"name\":\"{slot}\",\"uuid\":\"hf-ap\",\"version\":{{\"major\":0,\"minor\":5,\"build\":0,\"class\":\"Version\"}},\"items_handling\":7,\"tags\":[\"AP\"]}}]";
                await ws.SendAsync(new ArraySegment<byte>(Encoding.UTF8.GetBytes(connectPkt)), WebSocketMessageType.Text, true, CancellationToken.None);

                _ = Task.Run(async () =>
                {
                    while (ws.State == WebSocketState.Open)
                    {
                        while (Plugin.Outgoing.TryDequeue(out var msg))
                            await ws.SendAsync(new ArraySegment<byte>(Encoding.UTF8.GetBytes(msg)), WebSocketMessageType.Text, true, CancellationToken.None);
                        await Task.Delay(100);
                    }
                });

                var buf = new byte[4096];
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
                    if (raw.Contains("\"Connected\"")) { Plugin.Connected = true; _status = $"Connected as {slot}!"; }
                    if (raw.Contains("\"ReceivedItems\""))
                        foreach (Match m in Regex.Matches(raw, "\"item\"\\s*:\\s*(\\d+)"))
                            if (long.TryParse(m.Groups[1].Value, out long itemId))
                                Plugin.UnlockedIds.Add(itemId);
                }
            }
            catch (Exception ex) { Plugin.Connected = false; _status = "Err: " + ex.Message; }
        }
    }
}
