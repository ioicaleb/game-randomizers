using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Net.WebSockets;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using BepInEx;
using HarmonyLib;
using Skatebirb;
using Skatebirb.Managers;
using Skatebirb.Menus;
using Skatebirb.SkateControl;
using UnityEngine;

namespace SkateBirdArchipelago
{
    [BepInPlugin("com.sotrando.skatebird.ap", "SkateBIRD Archipelago", "1.0.0")]
    public class Plugin : BaseUnityPlugin
    {
        public static ClientWebSocket Ws;
        public static bool Connected = false;
        public static HashSet<long> UnlockedIds = new HashSet<long>();
        public static HashSet<long> CheckedLocations = new HashSet<long>();
        public static ConcurrentQueue<string> Outgoing = new ConcurrentQueue<string>();
        public static int MissionCheckCounter = 0;

        private void Awake()
        {
            var go = new GameObject("SkateBirdApOverlay");
            go.hideFlags = HideFlags.HideAndDontSave;
            DontDestroyOnLoad(go);
            go.AddComponent<ApOverlay>();

            var harmony = new Harmony("com.sotrando.skatebird.ap");
            harmony.PatchAll();
            Logger.LogInfo("SkateBIRD Archipelago plugin ready!");
        }

        public static bool HasItem(long id) => !Connected || UnlockedIds.Contains(id);

        public static void CompleteNextLocation(long baseId)
        {
            if (!Connected) return;
            long id = baseId + MissionCheckCounter++;
            if (CheckedLocations.Add(id))
                Outgoing.Enqueue($"[{{\"cmd\":\"LocationChecks\",\"locations\":[{id}]}}]");
        }
    }

    public class ApOverlay : MonoBehaviour
    {
        private bool _showGui = true;
        private string _url = "ws://localhost:38281";
        private string _slot = "SkateBirb";
        private string _pass = "";
        private string _status = "Disconnected (F1 / F2 to toggle)";

        private void Update()
        {
            if (Input.GetKeyDown(KeyCode.F1) || Input.GetKeyDown(KeyCode.F2))
                _showGui = !_showGui;
        }

        private void OnGUI()
        {
            if (!_showGui) return;
            GUI.depth = -1000;
            GUI.Box(new Rect(15, 15, 290, 175), "SkateBIRD Archipelago (F1 / F2)");
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
                Plugin.Ws = ws;

                string connectPkt = $"[{{\"cmd\":\"Connect\",\"password\":\"{pass}\",\"game\":\"SkateBIRD\",\"name\":\"{slot}\",\"uuid\":\"sb-ap\",\"version\":{{\"major\":0,\"minor\":5,\"build\":0,\"class\":\"Version\"}},\"items_handling\":7,\"tags\":[\"AP\"]}}]";
                var sendBytes = Encoding.UTF8.GetBytes(connectPkt);
                await ws.SendAsync(new ArraySegment<byte>(sendBytes), WebSocketMessageType.Text, true, CancellationToken.None);

                _ = Task.Run(async () =>
                {
                    while (ws.State == WebSocketState.Open)
                    {
                        while (Plugin.Outgoing.TryDequeue(out var msg))
                        {
                            var b = Encoding.UTF8.GetBytes(msg);
                            await ws.SendAsync(new ArraySegment<byte>(b), WebSocketMessageType.Text, true, CancellationToken.None);
                        }
                        await Task.Delay(100);
                    }
                });

                var buf = new byte[65536];
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
                        Plugin.Connected = true;
                        _status = $"Connected as {slot}!";
                    }
                    else if (raw.Contains("\"ConnectionRefused\""))
                    {
                        _status = "Refused (check slot/game name)";
                    }
                    if (raw.Contains("\"ReceivedItems\""))
                    {
                        foreach (Match m in Regex.Matches(raw, "\"item\"\\s*:\\s*(\\d+)"))
                            if (long.TryParse(m.Groups[1].Value, out long itemId))
                                Plugin.UnlockedIds.Add(itemId);
                    }
                }
            }
            catch (Exception ex)
            {
                Plugin.Connected = false;
                _status = "Err: " + ex.Message;
            }
        }
    }

    [HarmonyPatch(typeof(CelebrationWindow), nameof(CelebrationWindow.CelebrateMission))]
    public static class Patch_MissionComplete
    {
        static void Postfix(string missionName) => Plugin.CompleteNextLocation(10000);
    }

    [HarmonyPatch(typeof(SkateboardGateway), nameof(SkateboardGateway.AttemptToFliptrick))]
    public static class Patch_Fliptrick
    {
        static bool Prefix() => true;
    }

    [HarmonyPatch(typeof(SkateboardGateway), nameof(SkateboardGateway.AttemptToGrind))]
    public static class Patch_Grind
    {
        static bool Prefix() => Plugin.HasItem(20011);
    }

    [HarmonyPatch(typeof(PlayTrick), "PlayManual")]
    public static class Patch_Manual
    {
        static bool Prefix() => Plugin.HasItem(20012);
    }

    [HarmonyPatch(typeof(UnlocksManager), nameof(UnlocksManager.HasReachedLevel))]
    public static class Patch_LevelUnlock
    {
        static void Postfix(object __0, ref bool __result)
        {
            if (!Plugin.Connected) return;
            string lvlName = __0.ToString();
            if (lvlName.Contains("Office")) __result = Plugin.HasItem(20001);
            else if (lvlName.Contains("Roof")) __result = Plugin.HasItem(20002);
            else if (lvlName.Contains("Skate")) __result = Plugin.HasItem(20003);
            else if (lvlName.Contains("Ware")) __result = Plugin.HasItem(20004);
        }
    }
}
