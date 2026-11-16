(function () {
    var AP_STATE = {
        ws: null,
        connected: false,
        mySlot: 0,
        players: {},
        itemNamesByGame: {},
        scoutedLocations: {},
        checked: new Set(),
        pendingItems: [],
        engineCounter: 0,
        gameCounter: 0
    };

    function sendPacket(pkt) {
        if (AP_STATE.ws && AP_STATE.ws.readyState === 1) {
            AP_STATE.ws.send(JSON.stringify([pkt]));
        }
    }

    function sendCheck(id) {
        if (!AP_STATE.connected || AP_STATE.checked.has(id)) return;
        AP_STATE.checked.add(id);
        sendPacket({ cmd: "LocationChecks", locations: [id] });
        console.log("[GDT AP] Sent check:", id);
    }

    function resolveItemName(playerId, itemId) {
        var pInfo = AP_STATE.players[playerId];
        var game = pInfo ? pInfo.game : null;
        var map = game ? AP_STATE.itemNamesByGame[game] : null;
        return (map && map[itemId]) ? map[itemId] : ("Item #" + itemId);
    }

    function relabelTopics() {
        if (typeof Topics === "undefined" || !Topics.topics) return;
        for (var i = 0; i < Math.min(40, Topics.topics.length); i++) {
            var t = Topics.topics[i];
            if (!t) continue;
            if (!t._origName) t._origName = t.name;
            var info = AP_STATE.scoutedLocations[10000 + i];
            if (!info) continue;
            var itemName = resolveItemName(info.player, info.item);
            if (info.player !== AP_STATE.mySlot) {
                var pName = (AP_STATE.players[info.player] && AP_STATE.players[info.player].name) || ("Player " + info.player);
                t.name = "[AP: " + pName + " - " + itemName + "] (" + t._origName + ")";
            } else {
                t.name = "[AP: " + itemName + "] (" + t._origName + ")";
            }
        }
    }

    function applyItemToLiveCompany(itemId) {
        var comp = (typeof GameManager !== "undefined") ? GameManager.company : null;
        if (!comp) return false;

        if (itemId === 20010) {
            if (typeof comp.adjustCash === "function") comp.adjustCash(250000, "Archipelago Grant");
            else comp.cash += 250000;
        } else if (itemId === 20011) {
            comp.researchPoints = (comp.researchPoints || 0) + 50;
        } else if (itemId === 20012) {
            comp.fans = (comp.fans || 0) + 10000;
        } else if (itemId >= 20020 && itemId < 20060) {
            var allTopics = (typeof Topics !== "undefined" && Topics.topics) ? Topics.topics : [];
            var tObj = allTopics[(itemId - 20020) % Math.max(1, allTopics.length)];
            if (tObj && comp.topics && comp.topics.indexOf(tObj) === -1) {
                comp.topics.push(tObj);
            }
        }
        if (typeof UI !== "undefined" && typeof UI.updateStatusBar === "function") {
            try { UI.updateStatusBar(comp); } catch (e) {}
        }
        return true;
    }

    setInterval(function () {
        relabelTopics();
        if (AP_STATE.pendingItems.length > 0 && typeof GameManager !== "undefined" && GameManager.company) {
            var rem = [];
            for (var i = 0; i < AP_STATE.pendingItems.length; i++) {
                if (!applyItemToLiveCompany(AP_STATE.pendingItems[i])) {
                    rem.push(AP_STATE.pendingItems[i]);
                }
            }
            AP_STATE.pendingItems = rem;
        }
    }, 500);

    function hookGameMethods() {
        if (typeof GameManager === "undefined") return;

        if (!GameManager._apResearchHooked && typeof GameManager.researchCompleted === "function") {
            GameManager._apResearchHooked = true;
            var origResearch = GameManager.researchCompleted;
            GameManager.researchCompleted = function (research) {
                var res = origResearch.apply(this, arguments);
                try {
                    if (research) {
                        var isTopic = Boolean(research.topic) ||
                                      (research.id && String(research.id).toLowerCase().indexOf("topic") !== -1) ||
                                      (research.category && String(research.category).toLowerCase().indexOf("topic") !== -1);
                        if (isTopic) {
                            var idx = -1;
                            if (typeof Topics !== "undefined" && Topics.topics) {
                                var targetId = (research.topic && research.topic.id) || research.id;
                                for (var i = 0; i < Topics.topics.length; i++) {
                                    if (Topics.topics[i] === research.topic || Topics.topics[i].id === targetId || ("Topic_" + Topics.topics[i].id) === targetId) {
                                        idx = i;
                                        break;
                                    }
                                }
                            }
                            if (idx >= 0 && idx < 40) sendCheck(10000 + idx);
                        } else {
                            sendCheck(10100 + (AP_STATE.engineCounter++ % 35));
                        }
                    }
                } catch (e) { console.error("[GDT AP] Research hook err:", e); }
                return res;
            };
        }

        if (!GameManager._apReleaseHooked && typeof GameManager.finishRelease === "function") {
            GameManager._apReleaseHooked = true;
            var origRelease = GameManager.finishRelease;
            GameManager.finishRelease = function () {
                var res = origRelease.apply(this, arguments);
                sendCheck(10200 + (AP_STATE.gameCounter++ % 25));
                return res;
            };
        }
    }

    setInterval(hookGameMethods, 1000);

    function buildOverlay() {
        if (document.getElementById("gdt-ap-box")) return;
        var box = document.createElement("div");
        box.id = "gdt-ap-box";
        box.style.cssText = "position:fixed;top:10px;left:10px;z-index:99999;background:rgba(20,24,32,0.92);color:#fff;padding:10px;border-radius:6px;font-family:sans-serif;font-size:12px;width:250px;border:1px solid #4a90e2;";
        box.innerHTML = '<div style="font-weight:bold;margin-bottom:6px;">GDT Archipelago (F1 to hide)</div>' +
            '<div id="gdt-ap-status" style="margin-bottom:6px;color:#aad;">Disconnected</div>' +
            '<input id="gdt-ap-url" value="ws://localhost:38281" style="width:100%;margin-bottom:4px;box-sizing:border-box;"/>' +
            '<input id="gdt-ap-slot" value="GDT" style="width:100%;margin-bottom:4px;box-sizing:border-box;"/>' +
            '<input id="gdt-ap-pass" type="password" placeholder="Password" style="width:100%;margin-bottom:6px;box-sizing:border-box;"/>' +
            '<button id="gdt-ap-btn" style="width:100%;padding:4px;cursor:pointer;">Connect</button>';
        document.body.appendChild(box);

        window.addEventListener("keydown", function (e) {
            if (e.key === "F1") box.style.display = (box.style.display === "none") ? "block" : "none";
        });

        document.getElementById("gdt-ap-btn").onclick = function () {
            var url = document.getElementById("gdt-ap-url").value.trim();
            var slot = document.getElementById("gdt-ap-slot").value.trim();
            var pass = document.getElementById("gdt-ap-pass").value;
            var st = document.getElementById("gdt-ap-status");
            st.textContent = "Connecting...";
            try {
                var ws = new WebSocket(url);
                AP_STATE.ws = ws;
                ws.onopen = function () {
                    sendPacket({
                        cmd: "Connect", password: pass, game: "Game Dev Tycoon",
                        name: slot, uuid: "gdt-ap-live",
                        version: { major: 0, minor: 5, build: 0, class: "Version" },
                        items_handling: 7, tags: ["AP"]
                    });
                };
                ws.onmessage = function (ev) {
                    var pkts = JSON.parse(ev.data);
                    for (var i = 0; i < pkts.length; i++) {
                        var p = pkts[i];
                        if (p.cmd === "Connected") {
                            AP_STATE.connected = true;
                            AP_STATE.mySlot = p.slot;
                            AP_STATE.players = p.slot_info || {};
                            st.textContent = "Connected as " + slot + "!";
                            st.style.color = "#6f6";
                            if (p.checked_locations) p.checked_locations.forEach(function (id) { AP_STATE.checked.add(id); });

                            var scoutIds = [];
                            for (var k = 10000; k < 10040; k++) scoutIds.push(k);
                            sendPacket({ cmd: "LocationScouts", locations: scoutIds, create_as_hint: 0 });
                            sendPacket({ cmd: "GetDataPackage" });
                        } else if (p.cmd === "LocationInfo" && p.locations) {
                            for (var s = 0; s < p.locations.length; s++) {
                                var loc = p.locations[s];
                                AP_STATE.scoutedLocations[loc.location] = loc;
                            }
                            relabelTopics();
                        } else if (p.cmd === "DataPackage" && p.data && p.data.games) {
                            var games = p.data.games;
                            for (var gName in games) {
                                if (!games.hasOwnProperty(gName)) continue;
                                var idMap = {};
var nameToId = games[gName].item_name_to_id || {};
for (var iName in nameToId) {
if (nameToId.hasOwnProperty(iName)) idMap[nameToId[iName]] = iName;
}
AP_STATE.itemNamesByGame[gName] = idMap;
}
relabelTopics();
} else if (p.cmd === "ReceivedItems" && p.items) {
for (var j = 0; j < p.items.length; j++) {
var code = p.items[j].item;
if (!applyItemToLiveCompany(code)) {
AP_STATE.pendingItems.push(code);
}
}
}
}
};
ws.onerror = function () { st.textContent = "Connection Error"; st.style.color = "#f66"; };
ws.onclose = function () { AP_STATE.connected = false; st.textContent = "Disconnected"; st.style.color = "#aad"; };
} catch (err) { st.textContent = "Err: " + err.message; }
};
}
if (document.readyState === "complete") buildOverlay();
else window.addEventListener("load", buildOverlay);
})();
