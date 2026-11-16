;(function () {
    "use strict";
    var TOPIC_ID_MAP = {
        20010: "zombies", 20011: "cyberpunk", 20012: "space", 20013: "medieval",
        20014: "time travel", 20015: "dungeon", 20016: "pirates", 20017: "ninjas",
        20018: "aliens", 20019: "post apocalyptic", 20020: "superheroes", 20021: "vampires",
        20022: "werewolves", 20023: "sports", 20024: "racing", 20025: "military",
        20026: "hacking", 20027: "game dev", 20028: "history", 20029: "mystery",
        20030: "horror", 20031: "music", 20032: "detective", 20033: "martial arts",
        20034: "transport", 20035: "evolution"
    };

    var AP = {
        ws: null,
        connected: false,
        connecting: false,
        mySlot: 0,
        players: {},
        itemNamesByGame: {},
        scoutedLocations: {},
        checked: {},
        pendingItems: [],
        unlockedGenres: { "action": true, "adventure": true },
        unlockedTopics: { "fantasy": true, "sci-fi": true },
        researchedTopics: {},
        inResearchModal: false,
        unlockedPlats: { "pc": true, "g64": true },
        officeLevel: 1
    };

    function toast(title, msg) {
        if (typeof GameManager !== "undefined" && GameManager.company && GameManager.company.notifications) {
            try { GameManager.company.notifications.push(new Notification(title, msg, "OK", 1)); } catch (e) {}
        }
    }

    function sendPacket(pkt) {
        if (AP.ws && AP.ws.readyState === 1) {
            AP.ws.send(JSON.stringify([pkt]));
        }
    }

    function sendLocs(ids) {
        if (!AP.connected) return;
        var out = [];
        for (var i = 0; i < ids.length; i++) {
            if (!AP.checked[ids[i]]) {
                AP.checked[ids[i]] = true;
                out.push(ids[i]);
            }
        }
        if (out.length > 0) sendPacket({ cmd: "LocationChecks", locations: out });
    }

    function resolveItemName(playerId, itemId) {
        var pInfo = AP.players[playerId];
        var game = pInfo ? pInfo.game : null;
        var map = game ? AP.itemNamesByGame[game] : null;
        return (map && map[itemId]) ? map[itemId] : ("Item #" + itemId);
    }

        function getResearchableCheckIndex(topicObj) {
        if (!topicObj || typeof Topics === "undefined" || !Topics.topics) return -1;
        var k1 = String(topicObj.name || "").toLowerCase();
        var k2 = String(topicObj.id || "").toLowerCase();
        if (k1 === "fantasy" || k2 === "fantasy" || k1 === "sci-fi" || k2 === "sci-fi") return -1;
        var resIdx = 0;
        for (var i = 0; i < Topics.topics.length; i++) {
            var t = Topics.topics[i];
            if (!t) continue;
            var tk1 = String(t.name || "").toLowerCase();
            var tk2 = String(t.id || "").toLowerCase();
            if (tk1 === "fantasy" || tk2 === "fantasy" || tk1 === "sci-fi" || tk2 === "sci-fi") continue;
            if (t === topicObj || tk1 === k1 || tk2 === k2) return resIdx % 35;
            resIdx++;
        }
        return -1;
    }

    function getResearchLabel(idx, origName) {
        var info = AP.scoutedLocations[10300 + idx];
        if (!info) return origName;
        var itemName = resolveItemName(info.player, info.item);
        if (info.player !== AP.mySlot) {
            var pName = (AP.players[info.player] && AP.players[info.player].name) || ("Player " + info.player);
            return "[AP: " + pName + " - " + itemName + "]";
        }
        return "[AP: " + itemName + "]";
    }

    function updateResearchBadges() {
        if (typeof Topics === "undefined" || !Topics.topics || typeof $ === "undefined") return;
        var isResearchModal = Boolean(AP.inResearchModal);
        $(".topicButtonText:visible").each(function () {
            var txtEl = $(this);
            var card = txtEl.parent();
            var orig = txtEl.attr("data-ap-orig");
            if (!orig) {
                orig = txtEl.text().trim();
                txtEl.attr("data-ap-orig", orig);
            }
            var badge = card.find(".ap-scout-tag");
            // Never spoil locked "?" cards!
            if (!isResearchModal || !orig || orig === "?") {
                if (badge.length > 0) badge.remove();
                return;
            }
            var idx = -1;
            for (var i = 0; i < Topics.topics.length; i++) {
                if (Topics.topics[i] && (Topics.topics[i].name === orig || Topics.topics[i].id === orig)) {
                    idx = i;
                    break;
                }
            }
            var chkIdx = (idx >= 0) ? getResearchableCheckIndex(Topics.topics[idx]) : -1;
            if (chkIdx >= 0) {
                var desired = getResearchLabel(chkIdx, orig);
                if (badge.length === 0) {
                    if (card.css("position") === "static") card.css("position", "relative");
                    badge = $('<div class="ap-scout-tag" style="position:absolute;top:2px;left:2px;right:2px;background:rgba(15,23,42,0.92);color:#38bdf8;font-size:9.5px;line-height:1.1;padding:2px 3px;border-radius:3px;pointer-events:none;z-index:5;overflow:hidden;text-overflow:ellipsis;"></div>');
                    card.append(badge);
                }
                if (badge.text() !== desired) badge.text(desired);
            } else if (badge.length > 0) {
                badge.remove();
            }
        });
    }

    function hookGdtUIAndEvents() {
        if (typeof UI !== "undefined" && typeof UI.pickTopicClick === "function" && !UI._apModeTrackHooked) {
            UI._apModeTrackHooked = true;
            var origPick = UI.pickTopicClick;
            UI.pickTopicClick = function (a) {
                if (a === "research") AP.inResearchModal = true;
                else if (arguments.length === 0 || a === undefined || a === null) AP.inResearchModal = false;
                return origPick.apply(this, arguments);
            };
        }
        if (typeof General !== "undefined" && typeof General.getTopicOrder === "function" && !General._apTopicOrderHooked) {
            General._apTopicOrderHooked = true;
            var origOrder = General.getTopicOrder;
            General.getTopicOrder = function (company) {
                var list = origOrder.apply(this, arguments) || [];
                if (AP.inResearchModal) {
                    return list.filter(function (t) {
                        return t && !AP.researchedTopics[String(t.name || "").toLowerCase()] && !AP.researchedTopics[String(t.id || "").toLowerCase()];
                    });
                }
                return list.filter(function (t) {
                    return t && (AP.unlockedTopics[String(t.name || "").toLowerCase()] || AP.unlockedTopics[String(t.id || "").toLowerCase()]);
                });
            };
        }
        if (typeof General !== "undefined" && typeof General.getTopicsAvailableForResearch === "function" && !General._apResAvailHooked) {
            General._apResAvailHooked = true;
            var origAvail = General.getTopicsAvailableForResearch;
            General.getTopicsAvailableForResearch = function (company) {
                var list = origAvail.apply(this, arguments) || [];
                return list.filter(function (t) {
                    return t && !AP.researchedTopics[String(t.name || "").toLowerCase()] && !AP.researchedTopics[String(t.id || "").toLowerCase()];
                });
            };
        }
        if (typeof UI !== "undefined" && typeof UI.showModMismatchDialog === "function" && !UI._apMismatchHooked) {
            UI._apMismatchHooked = true;
            UI.showModMismatchDialog = function (cb) { if (typeof cb === "function") cb(); };
        }
        // 1. Separate Game Dev Pick-Topic (a !== "research") from Research New Topic (a === "research")


        // 2. Official GDT researchCompleted event -> sends exact 10300 + idx check
        if (typeof GDT !== "undefined" && GDT.on && GDT.eventKeys && !GDT._apResearchEventHooked) {
            GDT._apResearchEventHooked = true;
            if (typeof GameManager !== "undefined" && typeof GameManager.researchTopic === "function" && !GameManager._apResTopicHooked) {
            GameManager._apResTopicHooked = true;
            var origResTopic = GameManager.researchTopic;
            GameManager.researchTopic = function (topic) {
                if (topic && typeof Topics !== "undefined" && Topics.topics) {
                    var idx = Topics.topics.indexOf(topic);
                    if (idx >= 0 && idx < 35) {
                        AP._lastStartedTopicIdx = idx;
                        AP._lastStartedTopic = topic;
                    }
                }
                return origResTopic.apply(this, arguments);
            };
        }
        GDT.on(GDT.eventKeys.gameplay.researchCompleted, function (e) {
                try {
                    var r = e && e.researchItem;
                    if (r && r.id === "New Topic" && r.topicId && typeof Topics !== "undefined" && Topics.topics) {
                        for (var i = 0; i < Topics.topics.length; i++) {
                            if (Topics.topics[i] && Topics.topics[i].id === r.topicId) {
                                AP.researchedTopics[String(Topics.topics[i].name || '').toLowerCase()] = true;
                                AP.researchedTopics[String(Topics.topics[i].id || '').toLowerCase()] = true;
                                if (GameManager.company && GameManager.company.topics && GameManager.company.topics.indexOf(Topics.topics[i]) === -1) GameManager.company.topics.push(Topics.topics[i]);
                                var cIdx = getResearchableCheckIndex(Topics.topics[i]);
                                if (cIdx >= 0) sendLocs([10300 + cIdx]);
                                break;
                            }
                        }
                    }
                } catch (err) { console.error("[GDT AP] researchCompleted err:", err); }
            });
        }

        // 3. Genre & Platform gating
        if (typeof General !== "undefined" && General.getAvailableGenres && !General._apGenreHooked) {
            General._apGenreHooked = true;
            var origGenres = General.getAvailableGenres;
            General.getAvailableGenres = function () {
                var list = origGenres.apply(this, arguments) || [];
                var filtered = list.filter(function (g) {
                    return AP.unlockedGenres[String(g.name || "").toLowerCase()] || AP.unlockedGenres[String(g.id || "").toLowerCase()];
                });
                return filtered.length > 0 ? filtered : list;
            };
        }

        if (typeof Platforms !== "undefined" && Platforms.getPlatforms && !Platforms._apPlatHooked) {
            Platforms._apPlatHooked = true;
            var origPlats = Platforms.getPlatforms;
            Platforms.getPlatforms = function () {
                var list = origPlats.apply(this, arguments) || [];
                var filtered = list.filter(function (p) {
                    return AP.unlockedPlats[String(p.name || "").toLowerCase()] || AP.unlockedPlats[String(p.id || "").toLowerCase()];
                });
                return filtered.length > 0 ? filtered : list;
            };
        }
    }

    function checkCompanyMilestones() {
        if (!AP.connected || typeof GameManager === "undefined" || !GameManager.company || typeof AP_DATA === "undefined") return;
        var comp = GameManager.company;
        var found = [];
        for (var i = 0; i < AP_DATA.cash.length; i++) {
            if (comp.cash >= AP_DATA.cash[i].val) found.push(AP_DATA.cash[i].id);
        }
        for (var j = 0; j < AP_DATA.fans.length; j++) {
            if (comp.fans >= AP_DATA.fans[j].val) found.push(AP_DATA.fans[j].id);
        }
        var relCount = (comp.gameLog && comp.gameLog.length) || 0;
        for (var k = 0; k < AP_DATA.releases.length; k++) {
            if (relCount >= AP_DATA.releases[k].val) found.push(AP_DATA.releases[k].id);
        }
        if (found.length > 0) sendLocs(found);
    }

    function registerPersistentUnlock(itemId) {
        if (TOPIC_ID_MAP[itemId]) {
            AP.unlockedTopics[TOPIC_ID_MAP[itemId]] = true;
        }
        var label = (typeof AP_DATA !== "undefined" && AP_DATA.items && AP_DATA.items[itemId]) ? AP_DATA.items[itemId] : "";
        if (label.indexOf("Genre: ") === 0) AP.unlockedGenres[label.replace("Genre: ", "").toLowerCase()] = true;
        else if (label.indexOf("Topic: ") === 0) AP.unlockedTopics[label.replace("Topic: ", "").toLowerCase()] = true;
        else if (label.indexOf("Platform: ") === 0) AP.unlockedPlats[label.replace("Platform: ", "").toLowerCase()] = true;
    }

    function applyItemLive(itemId) {
        registerPersistentUnlock(itemId);
        var comp = (typeof GameManager !== "undefined") ? GameManager.company : null;
        if (!comp) return false;

        var label = (typeof AP_DATA !== "undefined" && AP_DATA.items && AP_DATA.items[itemId]) ? AP_DATA.items[itemId] : ("Item #" + itemId);

        if (label.indexOf("Genre: ") === 0 || label.indexOf("Topic: ") === 0 || label.indexOf("Platform: ") === 0) {
            toast("Archipelago", "Unlocked " + label + "!");
        } else if (label.indexOf("Office Upgrade") !== -1) {
            AP.officeLevel += 1;
            toast("Archipelago", "Unlocked Progressive Office Upgrade (Tier " + AP.officeLevel + ")!");
} else if (label.indexOf("Cash Grant") !== -1) {
if (typeof comp.adjustCash === "function") comp.adjustCash(250000, "Archipelago Grant");
else comp.cash += 250000;
toast("Archipelago", "Received Investor Cash Grant (+$250K)!");
} else if (label.indexOf("Research Bundle") !== -1) {
comp.researchPoints = (comp.researchPoints || 0) + 25;
toast("Archipelago", "Received Research Bundle (+25 RP)!");
} else if (label.indexOf("Hype Campaign") !== -1) {
if (comp.currentGame) comp.currentGame.hypePoints = (comp.currentGame.hypePoints || 0) + 50;
else comp.fans = (comp.fans || 0) + 2500;
toast("Archipelago", "Received Hype Campaign (+50 Hype)!");
}
if (typeof UI !== "undefined" && typeof UI.updateStatusBar === "function") {
try { UI.updateStatusBar(comp); } catch (e) {}
}
return true;
}
setInterval(function () {
hookGdtUIAndEvents();
updateResearchBadges();
checkCompanyMilestones();
        if (typeof GameManager !== "undefined" && GameManager.company && GameManager.company.topics && typeof Topics !== "undefined" && Topics.topics) {
            for (var ti = 0; ti < Topics.topics.length; ti++) {
                var tObj = Topics.topics[ti];
                if (!tObj) continue;
                var k1 = String(tObj.name || "").toLowerCase();
                var k2 = String(tObj.id || "").toLowerCase();
                if ((AP.unlockedTopics[k1] || AP.unlockedTopics[k2]) && GameManager.company.topics.indexOf(tObj) === -1) {
                    GameManager.company.topics.push(tObj);
                }
            }
        }
if (AP.pendingItems.length > 0 && typeof GameManager !== "undefined" && GameManager.company) {
var rem = [];
for (var i = 0; i < AP.pendingItems.length; i++) {
if (!applyItemLive(AP.pendingItems[i])) rem.push(AP.pendingItems[i]);
}
AP.pendingItems = rem;
}
}, 250);
function buildOverlay() {
if (!document.body || document.getElementById("gdt-ap-box")) return;
var box = document.createElement("div");
box.id = "gdt-ap-box";
box.style.cssText = "position:fixed;top:10px;left:10px;z-index:99999;background:rgba(20,24,32,0.92);color:#fff;padding:10px;border-radius:6px;font-family:sans-serif;font-size:12px;width:250px;border:1px solid #4a90e2;";
var title = document.createElement("div");
title.style.cssText = "font-weight:bold;margin-bottom:6px;cursor:pointer;";
title.textContent = "GDT Archipelago (Click or F1 to hide)";
var st = document.createElement("div");
st.style.cssText = "margin-bottom:6px;color:#aad;";
st.textContent = "Disconnected";
var inUrl = document.createElement("input");
inUrl.value = "ws://localhost:38281";
inUrl.style.cssText = "width:100%;margin-bottom:4px;box-sizing:border-box;";
var inSlot = document.createElement("input");
inSlot.value = "GDT";
inSlot.style.cssText = "width:100%;margin-bottom:4px;box-sizing:border-box;";
var inPass = document.createElement("input");
inPass.type = "password";
inPass.placeholder = "Password";
inPass.style.cssText = "width:100%;margin-bottom:6px;box-sizing:border-box;";
var btn = document.createElement("button");
btn.textContent = "Connect";
btn.style.cssText = "width:100%;padding:4px;cursor:pointer;";
box.appendChild(title);
box.appendChild(st);
box.appendChild(inUrl);
box.appendChild(inSlot);
box.appendChild(inPass);
box.appendChild(btn);
document.body.appendChild(box);
var miniBtn = document.createElement("button");
miniBtn.textContent = "AP";
miniBtn.style.cssText = "display:none;position:fixed;top:10px;left:10px;z-index:99999;background:#1e293b;color:#fff;border:1px solid #4a90e2;border-radius:4px;padding:4px 8px;cursor:pointer;font-size:11px;";
document.body.appendChild(miniBtn);
function toggleBox() {
var hide = (box.style.display !== "none");
box.style.display = hide ? "none" : "block";
miniBtn.style.display = hide ? "block" : "none";
}
title.onclick = toggleBox;
miniBtn.onclick = toggleBox;
document.addEventListener("keydown", function (e) {
if (e.key === "F1" || e.keyCode === 112) {
e.preventDefault();
toggleBox();
}
}, true);
btn.onclick = function () {
if (AP.connected || AP.connecting) {
if (AP.ws) { try { AP.ws.close(); } catch (e) {} }
AP.connected = false;
AP.connecting = false;
btn.textContent = "Connect";
st.textContent = "Disconnected";
st.style.color = "#aad";
return;
}
var url = inUrl.value.trim();
var slot = inSlot.value.trim();
var pass = inPass.value;
AP.connecting = true;
btn.textContent = "Connecting...";
st.textContent = "Connecting...";
try {
var ws = new WebSocket(url);
AP.ws = ws;
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
AP.connecting = false;
AP.connected = true;
AP.mySlot = p.slot;
AP.players = p.slot_info || {};
btn.textContent = "Disconnect";
st.textContent = "Connected as " + slot + "!";
st.style.color = "#6f6";
toast("Archipelago", "Connected to Multiworld as " + slot + "!");
if (p.checked_locations) p.checked_locations.forEach(function (id) { AP.checked[id] = true; });
var scoutIds = [];
for (var k = 10300; k < 10335; k++) scoutIds.push(k);
sendPacket({ cmd: "LocationScouts", locations: scoutIds, create_as_hint: 0 });
var gameList = [];
                            for (var pid in AP.players) {
                                if (AP.players.hasOwnProperty(pid) && AP.players[pid].game && gameList.indexOf(AP.players[pid].game) === -1) {
                                    gameList.push(AP.players[pid].game);
                                }
                            }
                            sendPacket({ cmd: "GetDataPackage", games: gameList });
} else if (p.cmd === "LocationInfo" && p.locations) {
for (var s = 0; s < p.locations.length; s++) {
var loc = p.locations[s];
AP.scoutedLocations[loc.location] = loc;
}
} else if (p.cmd === "DataPackage" && p.data && p.data.games) {
var games = p.data.games;
for (var gName in games) {
if (!games.hasOwnProperty(gName)) continue;
var idMap = {};
var nameToId = games[gName].item_name_to_id || {};
for (var iName in nameToId) {
if (nameToId.hasOwnProperty(iName)) idMap[nameToId[iName]] = iName;
}
AP.itemNamesByGame[gName] = idMap;
}
} else if (p.cmd === "ReceivedItems" && p.items) {
for (var j = 0; j < p.items.length; j++) {
var code = p.items[j].item;
if (!applyItemLive(code)) AP.pendingItems.push(code);
}
}
}
};
ws.onerror = function () {
AP.connecting = false;
btn.textContent = "Connect";
st.textContent = "Connection Error";
st.style.color = "#f66";
};
ws.onclose = function () {
AP.connecting = false;
AP.connected = false;
btn.textContent = "Connect";
st.textContent = "Disconnected";
st.style.color = "#aad";
};
} catch (err) {
AP.connecting = false;
btn.textContent = "Connect";
st.textContent = "Err: " + err.message;
}
};
}
var uiTimer = setInterval(function () {
if (document.body) {
clearInterval(uiTimer);
buildOverlay();
}
}, 250);
})();
