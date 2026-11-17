local BridgeDir = "C:\\users\\steamuser\\AppData\\Local\\RetroRewind\\Saved\\SaveGames\\AP_Bridge\\"
os.execute('mkdir "' .. BridgeDir .. '" 2>NUL')

local AutoChangeEnabled = true
local AutoSortReturnsEnabled = true
local ArmCarryLimit = 20
local AllowedMovieGenres = { [4] = true, [5] = true }
local AllowedGameGenres = {}
local AllowedSystems = {}
local UnlockNewReleases = false
local UnlockCheckIdx = 0
local QuestCheckIdx = 0
local HooksInstalled = false

local function SendCheck(locId)
    local f = io.open(BridgeDir .. "outbox.txt", "a")
    if f then
        f:write(tostring(locId) .. "\n")
        f:close()
    end
end

local function ReadConfig()
    local f = io.open(BridgeDir .. "config.txt", "r")
    if not f then return end
    local content = f:read("*a")
    f:close()
    if content then
        local ac = content:match("auto_change=(%d+)")
        local as = content:match("auto_sort_returns=(%d+)")
        local al = content:match("arm_carry_limit=(%d+)")
        if ac then AutoChangeEnabled = (tonumber(ac) == 1) end
        if as then AutoSortReturnsEnabled = (tonumber(as) == 1) end
        if al then ArmCarryLimit = tonumber(al) end
    end
end

local function EnforceLocksAndQoL()
    local pc = FindFirstOf("PlayerController")
    if pc and pc:IsValid() and pc.Pawn and pc.Pawn:IsValid() then
        local pawn = pc.Pawn
        pcall(function() pawn["Inventory Max Movies Object Hold size"] = ArmCarryLimit end)
        pcall(function() pawn["Inventory Max Misc Object Hold size"] = ArmCarryLimit end)
        pcall(function() pawn["Inventory Max Electronics Object Hold size"] = ArmCarryLimit end)
    end

    local sys = FindFirstOf("Unlockable_System_C")
    if sys and sys:IsValid() then
        pcall(function() sys["Player Personnal Inventory Size"] = ArmCarryLimit end)
        pcall(function() sys["New Released Unlock"] = UnlockNewReleases end)
        pcall(function() sys["Video Game New Released Unlock"] = UnlockNewReleases end)

        -- Sync allowed Movie Genres into Movie Genres Unlock array
        pcall(function()
            local mg = sys["Movie Genres Unlock"]
            if mg and mg.Empty and mg.Add then
                mg:Empty()
                for gId, ok in pairs(AllowedMovieGenres) do
                    if ok then mg:Add(gId) end
                end
            end
        end)

        -- Sync allowed Video Game Genres into Video Game Genres Unlock array
        pcall(function()
            local vg = sys["Video Game Genres Unlock"]
            if vg and vg.Empty and vg.Add then
                vg:Empty()
                for gId, ok in pairs(AllowedGameGenres) do
                    if ok then vg:Add(gId) end
                end
            end
        end)

        -- Sync allowed Systems / Furniture / Staff / Upgrades in Unlock Gameplay System map
        pcall(function()
            local gs = sys["Unlock Gameplay System"]
            if gs and gs.ForEach then
                gs:ForEach(function(k, v)
                    local key = k:get()
                    v:set(AllowedSystems[key] == true)
                end)
            end
        end)
    end
end

local function ApplyApUnlock(itemId)
    local sys = FindFirstOf("Unlockable_System_C")
    if itemId == 20019 then
        UnlockNewReleases = true
    elseif itemId >= 20010 and itemId <= 20018 then
        local gIdx = itemId - 20010
        AllowedMovieGenres[gIdx] = true
        AllowedGameGenres[gIdx] = true
        if sys and sys:IsValid() then
            pcall(function() sys["Force Unlock Genre"](sys, gIdx) end)
        end
    else
        local sIdx = (itemId % 100) + 1
        AllowedSystems[sIdx] = true
        if sys and sys:IsValid() then
            pcall(function() sys["Force Unlock Gameplay System"](sys, sIdx) end)
        end
    end
end

local function PollInbox()
    local f = io.open(BridgeDir .. "inbox.txt", "r")
    if not f then return end
    local content = f:read("*a")
    f:close()
    if content and #content > 0 then
        local clear = io.open(BridgeDir .. "inbox.txt", "w")
        if clear then clear:close() end
        for line in content:gmatch("[^\r\n]+") do
            local itemId = tonumber(line)
            if itemId then ApplyApUnlock(itemId) end
        end
        EnforceLocksAndQoL()
    end
end

local function InstallHooks()
    if HooksInstalled then return end
    local coCls = StaticFindObject("/Game/VideoStore/asset/prop/CheckOut/CheckOut.CheckOut_C")
    local usCls = StaticFindObject("/Game/VideoStore/core/blueprint/research/Unlockable_System.Unlockable_System_C")
    local dbCls = StaticFindObject("/Game/VideoStore/asset/prop/DropBox/DropBox.DropBox_C")
    local qmCls = StaticFindObject("/Game/VideoStore/core/blueprint/quest/Quest_Manager.Quest_Manager_C")
    if not coCls or not usCls then return end
    HooksInstalled = true

    pcall(function()
        RegisterHook("/Game/VideoStore/asset/prop/CheckOut/CheckOut.CheckOut_C:Receive Client Money", function(Context)
            if not AutoChangeEnabled then return end
            local co = Context:get()
            if co and co:IsValid() then
                ExecuteWithDelay(250, function()
                    if not co:IsValid() then return end
                    pcall(function()
                        co["Actual Payback"] = co["Money to Payback"] or 0
                        co["User can close the Cash Drawer"] = true
                        co["Refresh Display"](co)
                        co["Check if Payback Money is correct and set final transaction interaction"](co)
                        co["Close Cash Drawer"](co)
                    end)
                end)
            end
        end)
    end)

    if dbCls then
        pcall(function()
            RegisterHook("/Game/VideoStore/asset/prop/DropBox/DropBox.DropBox_C:Event Move Animation Completed for Storage in DropBox", function(Context)
                if not AutoSortReturnsEnabled then return end
                local db = Context:get()
                if db and db:IsValid() then
                    ExecuteWithDelay(300, function()
                        if not db:IsValid() then return end
                        pcall(function()
                            db["Check if any Shelve can store Product"](db)
                            db["Move Product to Shelve Animation"](db)
                        end)
                    end)
                end
            end)
        end)
    end

    pcall(function()
        RegisterHook("/Game/VideoStore/core/blueprint/research/Unlockable_System.Unlockable_System_C:TryUnlock", function(Context)
            SendCheck(10200 + (UnlockCheckIdx % 20))
            UnlockCheckIdx = UnlockCheckIdx + 1
            ExecuteWithDelay(100, EnforceLocksAndQoL)
        end)
    end)

    pcall(function()
        RegisterHook("/Game/VideoStore/core/blueprint/research/Unlockable_System.Unlockable_System_C:Check Load Unlock With Level When Savegame Loaded", function(Context)
            ExecuteWithDelay(200, EnforceLocksAndQoL)
        end)
    end)

    if qmCls then
        pcall(function()
            RegisterHook("/Game/VideoStore/core/blueprint/quest/Quest_Manager.Quest_Manager_C:Save", function(Context)
                SendCheck(10100 + (QuestCheckIdx % 25))
                QuestCheckIdx = QuestCheckIdx + 1
            end)
        end)
    end
end

RegisterKeyBind(Key.F6, function()
    AutoChangeEnabled = not AutoChangeEnabled
end)
RegisterKeyBind(Key.F7, function()
    AutoSortReturnsEnabled = not AutoSortReturnsEnabled
end)
RegisterKeyBind(Key.F8, function()
    ArmCarryLimit = (ArmCarryLimit == 5) and 20 or 5
    EnforceLocksAndQoL()
end)

LoopAsync(1500, function()
    ReadConfig()
    InstallHooks()
    PollInbox()
    EnforceLocksAndQoL()
    return false
end)
