local BridgeDir = "C:\\users\\steamuser\\AppData\\Local\\RetroRewind\\Saved\\SaveGames\\AP_Bridge\\"
os.execute('mkdir "' .. BridgeDir .. '" 2>NUL')

local AutoChangeEnabled = true
local AutoSortReturnsEnabled = true
local ArmCarryLimit = 20
local AllowedMovieGenres = {}
local AllowedGameGenres = {}
local AllowedSystems = {}
local UnlockedCatalogKeys = {}
local UnlockNewReleases = false
local UnlockCheckIdx = 0
local HooksInstalled = false
local StartGenresLoaded = false

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
        local al = content:match("arm_carry_limit=(%d+)")        local sg = content:match("starting_genres=(%d+,%d+)")
        if ac then AutoChangeEnabled = (tonumber(ac) == 1) end
        if as then AutoSortReturnsEnabled = (tonumber(as) == 1) end
        if al then ArmCarryLimit = tonumber(al) end        if sg and not StartGenresLoaded then
            StartGenresLoaded = true
            AllowedMovieGenres = {}
            AllowedGameGenres = {}
            for num in sg:gmatch("%d+") do
                local g = tonumber(num)
                if g then
                    AllowedMovieGenres[g] = true
                    AllowedGameGenres[g] = true
                end
            end
        end
    end
end


local function GateSingleCatalogCard(card)
    if not card or not card:IsValid() then return end
    local cname = ""
    local ok1, c1 = pcall(function() return card["Spawn Class Actor"] end)
    if ok1 and c1 and c1:IsValid() then cname = cname .. " " .. c1:GetFullName():lower() end
    local ok2, c2 = pcall(function() return card["Product Class"] end)
    if ok2 and c2 and c2:IsValid() then cname = cname .. " " .. c2:GetFullName():lower() end
    if cname:find("shelf_movie_4row_01") or cname:find("movingbox") then return end
    local key = tostring((#cname + 7) % 35)
    local allowed = (UnlockedCatalogKeys[key] == true)
    pcall(function()
        if card["div_unlock"] and card["div_unlock"]:IsValid() then card["div_unlock"]:SetVisibility(1) end
        if card["txt_Unlock"] and card["txt_Unlock"]:IsValid() then card["txt_Unlock"]:SetVisibility(1) end
        local buyBtn = card["UI_Catalogue_ButtonBuy"]
        if buyBtn and buyBtn:IsValid() then
            buyBtn:SetIsEnabled(allowed)
            buyBtn:SetVisibility(allowed and 0 or 2)
        end
    end)
end

local function EnforceLocksAndQoL()
    local mkt = FindFirstOf("Market_C")
    if not mkt or not mkt:IsValid() then return end
    if not StartGenresLoaded then
        AllowedMovieGenres = true
        AllowedMovieGenres = true
    end

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

        -- Gate Stations & Gameplay Systems behind AP items (prevents vanilla level-up unlocks!)
        pcall(function()
            local gs = sys["Unlock Gameplay System"]
            if gs and gs.ForEach then
                gs:ForEach(function(k, v)
                    local key = k:get()
                    v:set(AllowedSystems[key] == true)
                end)
            end
        end)

        -- Enforce 2 shuffled starting genres + AP unlocked genres
        pcall(function()
            local list = {}
            for gId, ok in pairs(AllowedMovieGenres) do
                if ok then table.insert(list, gId) end
            end
            table.sort(list)
            local mg = sys["Movie Genres Unlock"]
            if mg and #list > 0 and mg.ForEach then
                local n = mg:GetArrayNum()
                mg:ForEach(function(i, elem)
                    if list[i] ~= nil then elem:set(list[i]) end
                end)
                for i = n + 1, #list do
                    pcall(function() sys["Force Unlock Genre"](sys, list[i]) end)
                end
            end
        end)
    end

    local cards = FindAllOf("UI_Catalogue_Product_C")
    if cards then
        for _, card in ipairs(cards) do
            GateSingleCatalogCard(card)
        end
    end

    local staffBtns = FindAllOf("UI_Catalogue_ButtonHireStaff_C")
    if staffBtns then
        for idx, btn in ipairs(staffBtns) do
            if btn:IsValid() then
                local unlocked = UnlockedCatalogKeys["staff_" .. tostring(idx)] == true
                pcall(function() btn:SetIsEnabled(unlocked) end)
            end
        end
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
    elseif itemId >= 20060 and itemId <= 20065 then
        local staffSlot = (itemId - 20060) + 1
        UnlockedCatalogKeys["staff_" .. tostring(staffSlot)] = true
    else
        local key = tostring(itemId % 35)
        UnlockedCatalogKeys[key] = true
        local sysSlot = (itemId % 16)
        AllowedSystems[sysSlot] = true
        if sys and sys:IsValid() then
            pcall(function() sys["Force Unlock Gameplay System"](sys, sysSlot) end)
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
        for line in content:gmatch("%d+") do
            local itemId = tonumber(line)
            if itemId then ApplyApUnlock(itemId) end
        end
        EnforceLocksAndQoL()
    end
end

local function InstallHooks()
    if HooksInstalled then return end
    local coCls = StaticFindObject("/Game/VideoStore/asset/prop/CheckOut/CheckOut.CheckOut_C")
    local usCls = StaticFindObject("/Game/VideoStore/core/blueprint/research/Unlockable_System.Unlockable_System_C")    local prodCls = StaticFindObject("/Game/VideoStore/asset/prop/catalogue/UI_Catalogue_Product.UI_Catalogue_Product_C")
    local qmCls = StaticFindObject("/Game/VideoStore/core/blueprint/quest/Quest_Manager.Quest_Manager_C")
    if not coCls or not usCls then return end
    HooksInstalled = true
    if qmCls then
        pcall(function()
            RegisterHook("/Game/VideoStore/core/blueprint/quest/Quest_Manager.Quest_Manager_C:Load", function(Context)
                local qm = Context:get()
                if qm and qm:IsValid() then
                    pcall(function()
                        local qd = qm["Quest Done"]
                        if qd and qd.Empty then qd:Empty() end
                    end)
                end
            end)
        end)
    end

    if prodCls then
        pcall(function()
            RegisterHook("/Game/VideoStore/asset/prop/catalogue/UI_Catalogue_Product.UI_Catalogue_Product_C:Construct", function(Context)
                local card = Context:get()
                ExecuteWithDelay(50, function() GateSingleCatalogCard(card) end)
            end)
        end)
    end

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
                        co["Checkout Close Drawer Trigger - Pickup Event"](co)
                    end)
                end)
            end
        end)
    end)

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
end

RegisterKeyBind(Key.F6, function() AutoChangeEnabled = not AutoChangeEnabled end)
RegisterKeyBind(Key.F7, function() AutoSortReturnsEnabled = not AutoSortReturnsEnabled end)
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



local MarketRefreshed = false
local function RefreshMarketForShuffledGenres()
    if MarketRefreshed or not StartGenresLoaded then return end
    local mkt = FindFirstOf("Market_C")
    if mkt and mkt:IsValid() then
        MarketRefreshed = true
        pcall(function()
            mkt["Clear Market"](mkt)
            mkt["Generate Movie For The Day"](mkt)
            mkt["Generate Movie Bundles ForThe Day"](mkt)
        end)
    end
end


LoopAsync(2500, function()
    RefreshMarketForShuffledGenres()
    return MarketRefreshed
end)
