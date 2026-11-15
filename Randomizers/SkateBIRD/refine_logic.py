import re

p = "/mnt/E8A2D79FA2D77114/Source/repos/GameRandomizers/Randomizers/SkateBIRD/build_apworld.py"
txt = open(p).read()

old_rules = '''            if "Gold Score" in loc_name:
                loc.access_rule = lambda state: state.has("Grinds", self.player) and state.has("Manuals", self.player)
            elif "Mission #08" in loc_name or "Mission #09" in loc_name or "Mission #10" in loc_name:
                loc.access_rule = lambda state: state.has("Wing Flap (Air Ollie)", self.player)'''

new_rules = '''            if "Gold Score" in loc_name:
                loc.access_rule = lambda state: state.has("Grinds", self.player) and state.has("Manuals", self.player)
            elif "Silver Score" in loc_name:
                loc.access_rule = lambda state: state.has("Grinds", self.player) or state.has("Manuals", self.player)
            elif any(m in loc_name for m in ("Mission #04", "Mission #05")):
                loc.access_rule = lambda state: state.has("Grinds", self.player)
            elif any(m in loc_name for m in ("Mission #06", "Mission #07")):
                loc.access_rule = lambda state: state.has("Manuals", self.player)
            elif any(m in loc_name for m in ("Mission #08", "Mission #09", "Mission #10")):
                loc.access_rule = lambda state: state.has("Wing Flap (Air Ollie)", self.player)'''

assert old_rules in txt, "Rule block not found"
txt = txt.replace(old_rules, new_rules)
open(p, "w").write(txt)
