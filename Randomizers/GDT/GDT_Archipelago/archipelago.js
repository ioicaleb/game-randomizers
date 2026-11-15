;(function () {
    "use strict";
    var st = {
        ws: null, ok: false, slot: "GDTPlayer",
        url: "ws://localhost:38281", pass: "", done: {},
        genres: { "Action": 1, "Adventure": 1 },
        topics: { "Fantasy": 1, "Sci-Fi": 1 },
        plats: { "PC": 1, "G64": 1 }, office: 1
    };

    function toast(t, m) {
        if (typeof GameManager !== "undefined" && GameManager.company) {
            GameManager.company.notifications.push(
                new Notification(t, m, "OK", 1)
            );
        }
    }

    function sendLocs(ids) {
        var out = [];
        for (var i = 0; i < ids.length; i++) {
            if (!st.done[ids[i]]) {
                st.done[ids[i]] = true;
                out.push(ids[i]);
            }
        }
        if (out.length && st.ws && st.ok) {
            st.ws.send(JSON.stringify([
                { cmd: "LocationChecks", locations: out }
            ]));
        }
    }

    function giveItem(id) {
        var n = (typeof AP_DATA !== "undefined" && AP_DATA.items[id])
            ? AP_DATA.items[id] : ("Item #" + id);
        toast("Archipelago Item", n);
        if (n.indexOf("Genre: ") === 0) {
            st.genres[n.slice(7)] = 1;
        } else if (n.indexOf("Topic: ") === 0) {
            st.topics[n.slice(7)] = 1;
        } else if (n.indexOf("Platform: ") === 0) {
            st.plats[n.slice(10)] = 1;
        } else if (n.indexOf("Cash Grant") !== -1 && GameManager.company) {
            GameManager.company.adjustCash(250000, "AP Grant");
        } else if (n.indexOf("Research") !== -1 && GameManager.company) {
            GameManager.company.researchPoints += 25;
        }
    }

    function setStat(txt, col) {
        var el = document.getElementById("ap-stat");
        if (el) { el.textContent = txt; el.style.color = col; }
    }

    function connect(u, s, p) {
        if (st.ws) st.ws.close();
        st.url = u; st.slot = s; st.pass = p;
        var ws = new WebSocket(u);
        st.ws = ws;
        ws.onmessage = function (ev) {
            var pkts = JSON.parse(ev.data);
            for (var i = 0; i < pkts.length; i++) {
                var k = pkts[i];
                if (k.cmd === "RoomInfo") {
                    ws.send(JSON.stringify([{
                        cmd: "Connect", password: st.pass,
                        game: "Game Dev Tycoon", name: st.slot,
                        uuid: "gdt-" + Math.random().toString(36).slice(2),
                        version: { major: 0, minor: 5, build: 0,
                                   class: "Version" },
                        items_handling: 7, tags: ["AP"]
                    }]));
                } else if (k.cmd === "Connected") {
                    st.ok = true;
                    setStat("Connected: " + st.slot, "#4ade80");
                    toast("Archipelago", "Connected as " + st.slot);
                } else if (k.cmd === "ReceivedItems") {
                    for (var j = 0; j < k.items.length; j++) {
                        giveItem(k.items[j].item);
                    }
                }
            }
        };
        ws.onclose = function () {
            st.ok = false; setStat("Disconnected", "#f87171");
        };
    }

    function makeBox(val, ph, tp) {
        var inp = document.createElement("input");
        inp.value = val; inp.placeholder = ph; inp.type = tp || "text";
        inp.style.cssText = "width:140px;margin:2px 0;display:block;";
        return inp;
    }

    function buildUI() {
        if (document.getElementById("ap-box")) return;
        var box = document.createElement("div");
        box.id = "ap-box";
        box.style.cssText = "position:fixed;top:8px;right:8px;" +
            "z-index:99999;background:#0f172a;color:#fff;padding:8px;" +
            "border-radius:6px;font:12px sans-serif;";
        var lbl = document.createElement("div");
        lbl.id = "ap-stat"; lbl.textContent = "AP: Disconnected";
        var uIn = makeBox(st.url, "Server URL");
        var sIn = makeBox(st.slot, "Slot Name");
        var pIn = makeBox("", "Password", "password");
        var btn = document.createElement("button");
        btn.textContent = "Connect";
        btn.onclick = function () {
            connect(uIn.value.trim(), sIn.value.trim(), pIn.value);
        };
        box.appendChild(lbl); box.appendChild(uIn);
        box.appendChild(sIn); box.appendChild(pIn); box.appendChild(btn);
        document.body.appendChild(box);
    }

    function installGates() {
        if (typeof General !== "undefined" && General.getAvailableGenres) {
            var origG = General.getAvailableGenres;
            General.getAvailableGenres = function () {
                var list = origG.apply(this, arguments);
                if (!st.ok) return list;
                return list.filter(function (g) { return !!st.genres[g.name]; });
            };
        }
        if (typeof Platforms !== "undefined" && Platforms.getPlatformsOnMarket) {
            var origP = Platforms.getPlatformsOnMarket;
            Platforms.getPlatformsOnMarket = function () {
                var list = origP.apply(this, arguments);
                if (!st.ok) return list;
                return list.filter(function (pl) { return !!st.plats[pl.name]; });
            };
        }
    }

    function syncCompanyUnlocks(c) {
        if (!st.ok) return;
        if (typeof Topics !== "undefined" && c.topics) {
            c.topics = Topics.topics.filter(function (t) { return !!st.topics[t.name]; });
        }
        if (typeof Platforms !== "undefined" && c.licencedPlatforms) {
            for (var i = 0; i < Platforms.allPlatforms.length; i++) {
                var pl = Platforms.allPlatforms[i];
                if (st.plats[pl.name] && c.licencedPlatforms.indexOf(pl) === -1) {
                    c.licencedPlatforms.push(pl);
                }
            }
        }
        if (c.currentLevel === 1 && st.office >= 2 && GameManager.levelUp) {
            GameManager.levelUp();
        } else if (c.currentLevel === 2 && st.office >= 3 && GameManager.levelUp) {
            GameManager.levelUp();
        }
        if (c.cash >= 100000000 && c.fans >= 1000000 && !st.done) {
            st.done = true;
            st.ws.send(JSON.stringify([{ cmd: "StatusUpdate", status: 30 }]));
            toast("Archipelago Goal!", "Multiworld Victory achieved!");
        }
    }

    function poll() {
        if (typeof GameManager === "undefined" || !GameManager.company) {
            return;
        }
        var c = GameManager.company;
        syncCompanyUnlocks(c);
        if (st.ok && c.cash < -50000) {
            c.cash = 10000; toast("AP Bailout", "Bankruptcy prevented!");
        }
        if (typeof AP_DATA === "undefined") return;
        var hit = [];
        for (var i = 0; i < AP_DATA.cash.length; i++) {
            var r1 = AP_DATA.cash[i];
            if (c.cash >= r1.val) hit.push(r1.id);
        }
        for (var j = 0; j < AP_DATA.fans.length; j++) {
            var r2 = AP_DATA.fans[j];
            if (c.fans >= r2.val) hit.push(r2.id);
        }
        var rel = c.gameLog ? c.gameLog.length : 0;
        for (var k = 0; k < AP_DATA.releases.length; k++) {
            var r3 = AP_DATA.releases[k];
            if (rel >= r3.val) hit.push(r3.id);
        }
        if (c.achievements) {
            for (var a = 0; a < c.achievements.length; a++) {
                if (c.achievements[a].unlocked) hit.push(10300 + a);
            }
        }
        sendLocs(hit);
    }

    var boot = setInterval(function () {
        if (document.body && typeof GDT !== "undefined") {
            clearInterval(boot);
            GDT.loadJs(["mods/GDT_Archipelago/ap_data.js"], function () {
                buildUI();
                installGates();
                setInterval(poll, 1500);
            });
        }
    }, 1000);
})();
