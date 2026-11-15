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

namespace DateEverythingArchipelago
{
    [BepInPlugin("com.sotrando.dateeverything.ap", "Date Everything Archipelago", "1.0.0")]
    public class Plugin : BaseUnityPlugin
    {
        public static bool Connected = false;
        public static HashSet<long> UnlockedIds = new HashSet<long>();
        public static HashSet<long> CheckedLocations = new HashSet<long>();
        public static ConcurrentQueue<string> Outgoing = new ConcurrentQueue<string>();
        public static int EndingCounter = 0;

        private void Awake()
        {
            var go = new GameObject("DeApOverlay");
            go.hideFlags = HideFlags.HideAndDontSave;
            DontDestroyOnLoad(go);
            go.AddComponent<ApOverlay>();

            var harmony = new Harmony("com.sotrando.dateeverything.ap");
            var asm = Assembly.Load("Assembly-CSharp");
            foreach (var t in asm.GetTypes())
            {
                var mEnd = t.GetMethod("CalculateSpecsOnEnding", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly);
                if (mEnd != null) harmony.Patch(mEnd, postfix: new HarmonyMethod(typeof(Plugin), nameof(OnEndingReached)));
            }
            Logger.LogInfo("Date Everything Archipelago loaded!");
        }

        public static void OnEndingReached()
        {
            if (!Connected) return;
            long id = 10000 + (EndingCounter++ % 100);
            if (CheckedLocations.Add(id))
                Outgoing.Enqueue("[{\"cmd\":\"LocationChecks\",\"locations\":[" + id + "]}]");
        }
    }

    public class ApOverlay : MonoBehaviour
    {
        private bool _showGui = true;
        private string _url = "ws://localhost:38281";
        private string _slot = "DateEverything";
        private string _pass = "";
        private string _status = "Disconnected (F1 to toggle)";

        private void Update() { if (Input.GetKeyDown(KeyCode.F1)) _showGui = !_showGui; }

        private void OnGUI()
        {
            if (!_showGui) return;
            GUI.depth = -1000;
            GUI.Box(new Rect(15, 15, 300, 175), "Date Everything Archipelago (F1)");
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
                string pkt = "[{\"cmd\":\"Connect\",\"password\":\"" + pass + "\",\"game\":\"Date Everything\",\"name\":\"" + slot + "\",\"uuid\":\"de-ap\",\"version\":{\"major\":0,\"minor\":5,\"build\":0,\"class\":\"Version\"},\"items_handling\":7,\"tags\":[\"AP\"]}]";
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
                                Plugin.UnlockedIds.Add(itemId);
                }
            }
            catch (Exception ex) { Plugin.Connected = false; _status = "Err: " + ex.Message; }
        }
    }
}
