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

namespace ShadowsOverLoathingArchipelago
{
    [BepInPlugin("com.sotrando.shadowsoverloathing.ap", "Shadows Over Loathing Archipelago", "1.0.0")]
    public class Plugin : BaseUnityPlugin
    {
        public static bool Connected = false;
        public static HashSet<long> UnlockedIds = new HashSet<long>();
        public static HashSet<long> CheckedLocations = new HashSet<long>();
        public static ConcurrentQueue<string> Outgoing = new ConcurrentQueue<string>();
        public static ConcurrentQueue<int> PendingMeat = new ConcurrentQueue<int>();
        public static object PlayerSessionInstance = null;
        public static MethodInfo AddMeatMethod = null;
        public static int FlagCheckCounter = 0;
        public static int ItemCheckCounter = 0;

        private void Awake()
        {
            var go = new GameObject("SolApOverlay");
            go.hideFlags = HideFlags.HideAndDontSave;
            DontDestroyOnLoad(go);
            go.AddComponent<ApOverlay>();

            var harmony = new Harmony("com.sotrando.shadowsoverloathing.ap");
            var gameAsm = Assembly.Load("Assembly-CSharp");
            foreach (var t in gameAsm.GetTypes())
            {
                var mFlag = t.GetMethod("AddFlags", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly);
                if (mFlag != null)
                    harmony.Patch(mFlag, postfix: new HarmonyMethod(typeof(Plugin), nameof(OnFlagAdded)));

                var mItem = t.GetMethod("AddItemInternal", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly);
                if (mItem != null)
                    harmony.Patch(mItem, postfix: new HarmonyMethod(typeof(Plugin), nameof(OnItemAdded)));

                var mMeat = t.GetMethod("AddMeat", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.DeclaredOnly);
                if (mMeat != null && mMeat.GetParameters().Length == 1)
                {
                    AddMeatMethod = mMeat;
                    harmony.Patch(mMeat, postfix: new HarmonyMethod(typeof(Plugin), nameof(CaptureSession)));
                }
            }
            Logger.LogInfo("Shadows Over Loathing Archipelago plugin loaded!");
        }

        public static void CaptureSession(object __instance) => PlayerSessionInstance = __instance;

        public static void OnFlagAdded(object __instance)
        {
            PlayerSessionInstance = __instance;
            if (!Connected) return;
            long id = 10000 + (FlagCheckCounter++ % 70);
            if (CheckedLocations.Add(id))
                Outgoing.Enqueue("[{\"cmd\":\"LocationChecks\",\"locations\":[" + id + "]}]");
        }

        public static void OnItemAdded(object __instance)
        {
            PlayerSessionInstance = __instance;
            if (!Connected) return;
            long id = 10200 + (ItemCheckCounter++ % 35);
            if (CheckedLocations.Add(id))
                Outgoing.Enqueue("[{\"cmd\":\"LocationChecks\",\"locations\":[" + id + "]}]");
        }
    }

    public class ApOverlay : MonoBehaviour
    {
        private bool _showGui = true;
        private string _url = "ws://localhost:38281";
        private string _slot = "Loathing";
        private string _pass = "";
        private string _status = "Disconnected (F1 to toggle)";

        private void Update()
        {
            if (Input.GetKeyDown(KeyCode.F1)) _showGui = !_showGui;
            if (Plugin.PlayerSessionInstance != null && Plugin.AddMeatMethod != null && Plugin.PendingMeat.TryDequeue(out int meat))
            {
                try { Plugin.AddMeatMethod.Invoke(Plugin.PlayerSessionInstance, new object[] { meat }); }
                catch { }
            }
        }

        private void OnGUI()
        {
            if (!_showGui) return;
            GUI.depth = -1000;
            GUI.Box(new Rect(15, 15, 300, 175), "Shadows Over Loathing Archipelago (F1)");
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
                string connectPkt = "[{\"cmd\":\"Connect\",\"password\":\"" + pass + "\",\"game\":\"Shadows Over Loathing\",\"name\":\"" + slot + "\",\"uuid\":\"sol-ap\",\"version\":{\"major\":0,\"minor\":5,\"build\":0,\"class\":\"Version\"},\"items_handling\":7,\"tags\":[\"AP\"]}]";
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
                                if (itemId == 20030) Plugin.PendingMeat.Enqueue(250);
                                else if (itemId == 20031) Plugin.PendingMeat.Enqueue(1000);
                            }
                }
            }
            catch (Exception ex) { Plugin.Connected = false; _status = "Err: " + ex.Message; }
        }
    }
}
