
from __future__ import annotations
from typing import Dict, Any, List, Optional
import yaml, re, json

class EngineError(Exception): ...

class World:
    def __init__(self, data: Dict[str,Any]):
        self.meta = data.get("meta", {})
        self.locations = { l["id"]: l for l in data.get("locations",[]) }
        self.objects = { o["id"]: o for o in data.get("objects",[]) }
        self.npcs = { n["id"]: n for n in data.get("npcs",[]) }
        self.verbs = data.get("verbs",{})
        self.situations = data.get("situations",[])

class State:
    def __init__(self, world: World):
        start = world.meta.get("start_location")
        self.loc = start
        self.turn = 0
        self.energy = world.meta.get("start_energy", 5)
        self.money = world.meta.get("start_money", 0)
        self.capacity = world.meta.get("capacity", 6)
        self.inventory: List[str] = world.meta.get("start_items",[]).copy()
        self.flags: set[str] = set()
        self.npc_idx = { nid:0 for nid in world.npcs }
    def to_public(self)->Dict[str,Any]:
        return {
            "loc": self.loc,
            "turn": self.turn,
            "energy": self.energy,
            "money": self.money,
            "capacity": self.capacity,
            "inventory": self.inventory,
            "flags": sorted(list(self.flags)),
        }

class Parser:
    def __init__(self, verbs: Dict[str,List[str]]):
        self.map = {}
        for canon, syns in verbs.items():
            for s in syns:
                self.map[s.lower()] = canon
        self.default = "examinar"
    def parse(self, text: str):
        t = text.strip().lower()
        tokens = re.findall(r"[a-záàâãéêíóôõúç0-9]+", t)
        if not tokens: return (self.default, [])
        if t in ("n","s","e","o","norte","sul","este","oeste"):
            return ("mover",[t])
        for i, tok in enumerate(tokens):
            if tok in self.map:
                return (self.map[tok], tokens[i+1:])
        return (self.default, tokens)

class Engine:
    def __init__(self, world_data: Dict[str,Any]):
        self.world = World(world_data)
        self.state = State(self.world)
        self.loc_by_xy = {(l["x"],l["y"]): lid for lid,l in self.world.locations.items()}
        self.obj_index = self.world.objects
        self.obj_by_name = {}
        for o in self.world.objects.values():
            name = o["name"].lower()
            for token in re.findall(r"[a-záàâãéêíóôõúç0-9]+", name):
                self.obj_by_name.setdefault(token, o["id"])
        self.parser = Parser(self.world.verbs)

    def neighbors(self, loc_id: str)->Dict[str,Optional[str]]:
        L = self.world.locations[loc_id]; x,y = L["x"], L["y"]
        def at(xx,yy): return self.loc_by_xy.get((xx,yy))
        return {"norte":at(x,y-1), "sul":at(x,y+1), "este":at(x+1,y), "oeste":at(x-1,y)}

    def move(self, dir_token: str)->str:
        mapping={"n":"norte","s":"sul","e":"este","o":"oeste",
                 "norte":"norte","sul":"sul","este":"este","oeste":"oeste"}
        d = mapping.get(dir_token)
        if not d: return "Direcção inválida."
        nxt = self.neighbors(self.state.loc).get(d)
        if not nxt: return "Não podes ir por aí."
        self.state.loc = nxt
        self.advance_turn()
        name = self.world.locations[nxt]["name"]
        return f"Vais para {name} ({nxt})."

    def items_at(self, loc_id: str)->List[str]:
        return [o["id"] for o in self.world.objects.values() if o.get("location")==loc_id]

    def advance_turn(self):
        self.state.turn += 1
        self.state.energy = max(0, self.state.energy-1)
        for nid, npc in self.world.npcs.items():
            route = npc.get("route",[])
            if route:
                self.state.npc_idx[nid] = (self.state.npc_idx[nid]+1) % len(route)

    def npc_here(self, nid:str)->bool:
        npc = self.world.npcs[nid]
        idx = self.state.npc_idx[nid]
        return npc["route"][idx] == self.state.loc

    def pre_ok(self, pre: Dict[str,Any])->bool:
        s = self.state
        if not pre: return True
        if "has_item" in pre and pre["has_item"] not in s.inventory: return False
        if "has_item2" in pre and pre["has_item2"] not in s.inventory: return False
        if "not_has_item" in pre and pre["not_has_item"] in s.inventory: return False
        if "min_money" in pre and s.money < pre["min_money"]: return False
        if "flag" in pre and pre["flag"] not in s.flags: return False
        if "not_flag" in pre and pre["not_flag"] in s.flags: return False
        if "npc" in pre and not self.npc_here(pre["npc"]): return False
        return True

    def apply(self, eff: Dict[str,Any]):
        s = self.state
        if not eff: return
        s.money += eff.get("money_delta",0)
        for f in eff.get("set_flags",[]): s.flags.add(f)
        for f in eff.get("clear_flags",[]): s.flags.discard(f)
        for oid in eff.get("give_items",[]):
            if oid not in s.inventory: s.inventory.append(oid)
        if "transform_item" in eff:
            frm=eff["transform_item"]["from"]; to=eff["transform_item"]["to"]
            if frm in s.inventory: s.inventory.remove(frm)
            if to not in s.inventory: s.inventory.append(to)

    def try_situations(self, verb: str, words: List[str])->Optional[str]:
        here = self.state.loc
        for sit in self.world.situations:
            if sit.get("location") != here: continue
            trig = sit.get("trigger",{})
            if trig.get("verb") != verb: continue
            target = trig.get("args",{}).get("target")
            if target and target not in " ".join(words): continue
            if not self.pre_ok(sit.get("pre")): continue
            self.apply(sit.get("effects"))
            self.advance_turn()
            return sit.get("text","")
        return None

    def describe(self)->str:
        L = self.world.locations[self.state.loc]
        items = self.items_at(self.state.loc)
        items_str = ", ".join(self.world.objects[i]["name"] for i in items) if items else "nada relevante"
        dirs = [d for d,v in self.neighbors(self.state.loc).items() if v]
        return f"{L['name']}. Vês {items_str}. Saídas: {', '.join(dirs)}."

    def run(self, text: str)->Dict[str,Any]:
        verb, words = self.parser.parse(text)
        if verb=="mover":
            out = self.move(words[0] if words else "")
        elif verb in ("examinar","inventario","mapa"):
            if verb=="inventario":
                out = f"Inventário: {', '.join(self.world.objects[i]['name'] for i in self.state.inventory) or 'vazio'}. Dinheiro: €{self.state.money}."
            elif verb=="mapa":
                neigh = self.neighbors(self.state.loc); out = ' | '.join([f"{k}:{v}" for k,v in neigh.items() if v])
            else:
                tried = self.try_situations("examinar", words)
                out = tried if tried else self.describe()
        else:
            tried = self.try_situations(verb, words)
            out = tried if tried else "Nada acontece."
        return {"output": out, "state": self.state.to_public()}

def load_world(path: str)->Dict[str,Any]:
    import yaml
    with open(path,"r",encoding="utf-8") as f:
        return yaml.safe_load(f)
