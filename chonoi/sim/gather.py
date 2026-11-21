"""Buổi sáng: bơi, độ tươi, cá, thu hoạch và Cá Sấu Năm Chèo."""

import math

from ..ids import id_key, sort_by_id
from ..inventory import decay_items, inventory_payload, new_item, validate_items
from .ramp import ramp_velocity

TICK = 60.0


class GatherSim:
    mode = "gather"
    phase = "gather"

    def __init__(self, tuning, scenario, streams, ids, day=1, active_upgrades=None):
        self.all_tuning = tuning
        self.t = tuning["gather"]
        self.freshness = tuning["freshness"]
        self.rng, self.ids = streams, ids
        self.day = day
        self.phase_tick = 0
        active_upgrades = active_upgrades or {}
        player = scenario.get("player", {})
        self.pos = [float(v) for v in player.get("pos", self.t["start_pos"])]
        self.vel = [float(v) for v in player.get("vel", [0, 0])]
        self._tgt, self._ramp_left = None, 0
        self.heading = float(player.get("heading_deg", self.t["start_heading_deg"]))
        oxygen_s = self.t["oxygen_max_s"]
        hp_max = self.t["hp_max"]
        if active_upgrades.get("oxygen"):
            oxygen_s = tuning["shop"]["upgrades"]["oxygen"][active_upgrades["oxygen"] - 1]["oxygen_max_s"]
        if active_upgrades.get("hp"):
            hp_max = tuning["shop"]["upgrades"]["hp"][active_upgrades["hp"] - 1]["hp_max"]
        self.oxygen_max = int(round(oxygen_s * TICK))
        self.hp_max = hp_max
        self.oxygen_ticks = int(player.get("oxygen_ticks", self.oxygen_max))
        self.hp = int(player.get("hp", hp_max))
        self.zero_oxy_ticks = int(player.get("zero_oxy_ticks", 0))
        self.invuln_ticks = int(player.get("invuln_ticks", 0))
        self.catch_cd_ticks = int(player.get("catch_cd_ticks", 0))
        self.hold = [dict(item) for item in validate_items(scenario.get("hold", []))]
        for item in self.hold:
            ids.reserve(item["id"])
        self.time_left_ticks = int(scenario.get("time_left_ticks", round(self.t["duration_s"] * TICK)))
        source_nodes = scenario.get("nodes", self.t["nodes"])
        self.nodes = [{"id": n["id"], "kind": n["kind"], "pos": [float(v) for v in n["pos"]],
                       "regrow_ticks": int(n.get("regrow_ticks", 0))} for n in source_nodes]
        self.random_fish = scenario.get("random_fish", True)
        source_fish = scenario.get("fish", self.t["fish_initial"] if self.random_fish else [])
        self.fish = [{"id": f["id"], "kind": f["kind"], "pos": [float(v) for v in f["pos"]],
                      "heading_deg": float(f.get("heading_deg", 0)), "age_ticks": int(f.get("age_ticks", 0))}
                     for f in source_fish]
        source_monsters = scenario.get("monsters")
        if source_monsters is None:
            source_monsters = [m for m in self.t["monsters"]["spawns"] if m["from_day"] <= day]
        self.monsters = [self._make_monster(m) for m in source_monsters]
        for collection in (self.nodes, self.fish, self.monsters):
            for entity in collection:
                ids.reserve(entity["id"])
        self.money = self.earned = 0
        self.reputation = tuning["quan"]["reputation_initial"]
        self.done, self.reason = False, None

    def _make_monster(self, source):
        return {"id": source["id"], "kind": source.get("kind", "ca_sau"),
                "pos": [float(v) for v in source["pos"]],
                "waypoints": [[float(v) for v in p] for p in source["waypoints"]],
                "target_idx": int(source.get("target_idx", 1)), "state": source.get("state", "patrol"),
                "state_ticks_left": int(source.get("state_ticks_left", 0)),
                "recoil_dir": source.get("recoil_dir")}

    def inventory_items(self):
        return [dict(item) for item in self.hold]

    def snapshot(self):
        return {
            "player": {"pos": self.pos, "vel": self.vel, "heading_deg": self.heading,
                       "oxygen_ticks": self.oxygen_ticks, "oxygen_max_ticks": self.oxygen_max,
                       "hp": self.hp, "hp_max": self.hp_max, "zero_oxy_ticks": self.zero_oxy_ticks,
                       "invuln_ticks": self.invuln_ticks, "catch_cd_ticks": self.catch_cd_ticks,
                       "at_surface": self._at_surface()},
            "hold": [dict(item) for item in self.hold], "hold_count": len(self.hold),
            "hold_capacity": self.t["hold_capacity"],
            "nodes": [{**n, "ready": n["regrow_ticks"] == 0} for n in sort_by_id(self.nodes)],
            "fish": [dict(f) for f in sort_by_id(self.fish)],
            "monsters": [dict(m) for m in sort_by_id(self.monsters)],
        }

    def step(self, inp):
        events = []
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self.invuln_ticks = max(0, self.invuln_ticks - 1)
        self.catch_cd_ticks = max(0, self.catch_cd_ticks - 1)
        for node in sort_by_id(self.nodes):
            if node["regrow_ticks"] > 0:
                node["regrow_ticks"] -= 1
                if node["regrow_ticks"] == 0:
                    events.append(("node_regrown", {"node_id": node["id"]}))
        events.extend(decay_items(self.hold, self.freshness["gather_decay_per_s"] / TICK,
                                  self.freshness["spoiled_below"], "hold"))

        was_surface = self._at_surface()
        self._move_player(inp)
        at_surface = self._at_surface()
        if at_surface != was_surface:
            events.append(("surface" if at_surface else "dive", {"pos": list(self.pos)}))
        if at_surface:
            self.oxygen_ticks = min(self.oxygen_max,
                                    self.oxygen_ticks + int(self.t["oxygen_refill_per_tick"]))
            self.zero_oxy_ticks = 0
        else:
            before = self.oxygen_ticks
            self.oxygen_ticks = max(0, before - 1)
            if before > 0 and self.oxygen_ticks == 0:
                events.append(("oxygen_empty", {"pos": list(self.pos)}))
            if self.oxygen_ticks == 0:
                self.zero_oxy_ticks += 1
                if self.zero_oxy_ticks >= self.t["choke_interval_ticks"]:
                    self.zero_oxy_ticks = 0
                    self.hp = max(0, self.hp - 1)
                    events.append(("choke", {"hp": self.hp}))
                    if self.hp == 0:
                        self._faint(events, None)
                        return events

        self._update_monsters(events)
        if self.done:
            return events
        if inp.pressed("interact"):
            if self._in_dock():
                self._finish("docked", events)
                return events
            if at_surface:
                node = self._nearest(self.nodes, self.t["interact_radius"],
                                     lambda value: value["regrow_ticks"] == 0)
                if node is not None:
                    if len(self.hold) >= self.t["hold_capacity"]:
                        events.append(("hold_full", {"source_id": node["id"], "kind": node["kind"]}))
                    else:
                        item = new_item(self.ids, node["kind"], self.freshness["initial"])
                        self.hold.append(item)
                        node["regrow_ticks"] = int(round(self.t["regrow_s"] * TICK))
                        events.append(("gather", {"node_id": node["id"], "item": dict(item)}))
        if inp.pressed("catch") and self.catch_cd_ticks == 0 and not at_surface:
            fish = self._nearest(self.fish, self.t["catch_radius"])
            if fish is not None:
                amount = self.t["fish_yield"][fish["kind"]]
                if len(self.hold) + amount > self.t["hold_capacity"]:
                    events.append(("hold_full", {"source_id": fish["id"], "kind": fish["kind"]}))
                else:
                    items = [new_item(self.ids, fish["kind"], self.freshness["initial"]) for _ in range(amount)]
                    self.hold.extend(items)
                    self.fish.remove(fish)
                    self.catch_cd_ticks = int(round(self.t["catch_cooldown_s"] * TICK))
                    events.append(("fish_caught", {"fish_id": fish["id"], "kind": fish["kind"],
                                                    "items": [dict(item) for item in items]}))
        if self.time_left_ticks == 0:
            self._finish("time", events)
            return events
        if self.random_fish:
            self._move_fish()
            self._spawn_fish(events)
        return events

    def _move_player(self, inp):
        mx, md = inp.move
        speed = self.t["swim_speed"]
        self.vel = ramp_velocity(self, (mx * speed, md * speed), int(self.t["ramp_max_ticks"]))
        if (mx, md) != (0.0, 0.0):
            self.heading = math.degrees(math.atan2(md, mx)) % 360
        for index, axis in enumerate(("x", "d")):
            self.pos[index] += self.vel[index] / TICK
            low, high = self.t["bounds"][axis]
            if self.pos[index] <= low:
                self.pos[index], self.vel[index] = low, max(0.0, self.vel[index])
            elif self.pos[index] >= high:
                self.pos[index], self.vel[index] = high, min(0.0, self.vel[index])

    def _move_fish(self):
        speed = self.t["fish_speed"] / TICK
        for fish in sort_by_id(self.fish):
            fish["age_ticks"] += 1
            if fish["age_ticks"] % self.t["fish_turn_ticks"] == 0:
                fish["heading_deg"] = self.rng.get("fish_turn").uniform(0, 360)
            angle = math.radians(fish["heading_deg"])
            velocity = [math.cos(angle) * speed, math.sin(angle) * speed]
            x_bounds = self.t["fish_x"]
            d_bounds = self.t["fish_depths"][fish["kind"]]
            fish["pos"][0], velocity[0] = self._reflect(fish["pos"][0] + velocity[0], velocity[0], x_bounds)
            fish["pos"][1], velocity[1] = self._reflect(fish["pos"][1] + velocity[1], velocity[1], d_bounds)
            fish["heading_deg"] = math.degrees(math.atan2(velocity[1], velocity[0])) % 360

    @staticmethod
    def _reflect(value, velocity, bounds):
        low, high = bounds
        while value < low or value > high:
            if value < low:
                value, velocity = low + (low - value), -velocity
            elif value > high:
                value, velocity = high - (value - high), -velocity
        return value, velocity

    def _spawn_fish(self, events):
        if self.phase_tick % self.t["fish_spawn_ticks"] or len(self.fish) >= self.t["fish_max"]:
            return
        valid = {}
        for kind, depths in self.t["fish_spawn_depths"].items():
            points = [[x, depth] for x in self.t["fish_spawn_x"] for depth in depths]
            points = [point for point in points if all(math.dist(point, fish["pos"]) > self.t["fish_spawn_clearance"]
                                                       for fish in self.fish)]
            if points:
                valid[kind] = points
        if not valid:
            return
        kinds = sorted(valid)
        weights = [self.t["fish_weights"][kind] for kind in kinds]
        kind = self.rng.get("fish_spawn_kind").choices(kinds, weights=weights, k=1)[0]
        point = list(self.rng.get("fish_spawn_pos").choice(valid[kind]))
        fish = {"id": self.ids.new("F"), "kind": kind, "pos": point,
                "heading_deg": self.rng.get("fish_spawn_heading").uniform(0, 360), "age_ticks": 0}
        self.fish.append(fish)
        events.append(("fish_spawned", {"id": fish["id"], "kind": kind, "pos": point}))

    def _update_monsters(self, events):
        for monster in sort_by_id(self.monsters):
            species = self.t["monsters"]["species"][monster["kind"]]
            if monster["state"] == "recoil":
                step = species["recoil_dist"] / species["recoil_ticks"]
                self._move_monster(monster, [v * step for v in monster["recoil_dir"]], species)
                monster["state_ticks_left"] -= 1
                if monster["state_ticks_left"] == 0:
                    monster["state"], monster["recoil_dir"] = "patrol", None
                continue
            distance = math.dist(monster["pos"], self.pos)
            min_depth = species["depths"][0]
            if monster["state"] == "chase" and (distance > species["exit_radius"] or self.pos[1] < min_depth):
                monster["state"] = "patrol"
            elif monster["state"] == "patrol" and distance <= species["detect_radius"] and self.pos[1] >= min_depth:
                monster["state"] = "chase"
            if monster["state"] == "chase":
                direction = self._unit(monster["pos"], self.pos)
                self._move_monster(monster, [v * species["chase_speed"] / TICK for v in direction], species)
            else:
                target = monster["waypoints"][monster["target_idx"]]
                direction = self._unit(monster["pos"], target)
                remaining = math.dist(monster["pos"], target)
                amount = min(remaining, species["patrol_speed"] / TICK)
                self._move_monster(monster, [v * amount for v in direction], species)
                if math.dist(monster["pos"], target) < 1e-9:
                    monster["target_idx"] = 1 - monster["target_idx"]
        if self.invuln_ticks or self.pos[1] < 10:
            return
        candidates = [(math.dist(monster["pos"], self.pos), monster) for monster in self.monsters
                      if monster["state"] != "recoil"]
        candidates = [(distance, monster) for distance, monster in candidates
                      if distance <= self.t["monsters"]["species"][monster["kind"]]["hit_radius"]]
        if not candidates:
            return
        _, monster = min(candidates, key=lambda value: (value[0], id_key(value[1]["id"])))
        lost = [self.hold.pop() for _ in range(math.floor(len(self.hold) * self.t["loss_ratio"]))]
        self.hp = max(0, self.hp - 1)
        self.invuln_ticks = self.t["invuln_ticks"]
        direction = self._unit(self.pos, monster["pos"])
        monster.update(state="recoil", state_ticks_left=self.t["monsters"]["species"][monster["kind"]]["recoil_ticks"],
                       recoil_dir=direction)
        events.append(("monster_hit", {"monster_id": monster["id"], "hp": self.hp,
                                        "lost": [dict(item) for item in lost], "pos": list(self.pos)}))
        if self.hp == 0:
            self._faint(events, "monster")

    def _move_monster(self, monster, delta, species):
        monster["pos"][0] = min(self.t["bounds"]["x"][1], max(self.t["bounds"]["x"][0], monster["pos"][0] + delta[0]))
        monster["pos"][1] = min(species["depths"][1], max(species["depths"][0], monster["pos"][1] + delta[1]))

    @staticmethod
    def _unit(origin, target):
        dx, dy = target[0] - origin[0], target[1] - origin[1]
        length = math.hypot(dx, dy)
        return [1.0, 0.0] if length == 0 else [dx / length, dy / length]

    def _faint(self, events, cause):
        lost = [self.hold.pop() for _ in range(len(self.hold))]
        data = {"hp": 0, "lost": [dict(item) for item in lost]}
        if cause:
            data["cause"] = cause
        events.append(("faint", data))
        self._finish("fainted", events)

    def _finish(self, reason, events):
        self.done, self.reason = True, reason
        events.append(("gather_end", {"reason": reason, "inventory": inventory_payload(self.hold)}))

    def _at_surface(self):
        return self.pos[1] <= self.t["surface_depth"]

    def _in_dock(self):
        return math.dist(self.pos, self.t["dock_pos"]) <= self.t["dock_radius"]

    def _nearest(self, entities, radius, predicate=lambda _: True):
        candidates = [(math.dist(self.pos, entity["pos"]), entity) for entity in entities if predicate(entity)]
        candidates = [entry for entry in candidates if entry[0] <= radius]
        return min(candidates, key=lambda entry: (entry[0], id_key(entry[1]["id"])))[1] if candidates else None
