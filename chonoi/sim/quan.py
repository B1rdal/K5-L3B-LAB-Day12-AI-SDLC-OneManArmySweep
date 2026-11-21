"""Buổi tối: kho cá thể, giữ món, nấu, phục vụ và thanh toán."""

import math

from ..errors import BadInput
from ..ids import id_key, sort_by_id
from ..inventory import decay_items, validate_items
from .ramp import ramp_velocity

TICK = 60.0


class QuanSim:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None, menu_filter=None,
                 money=0, earned=0, reputation=None):
        self.all_tuning, self.t = tuning, tuning["quan"]
        self.menu = {key: value for key, value in tuning["menu"].items()
                     if menu_filter is None or key in menu_filter}
        self.freshness = tuning["freshness"]
        self.rng, self.ids = streams, ids
        self.phase_tick = 0
        player = scenario.get("player", {})
        self.pos = [float(v) for v in player.get("pos", self.t["start_pos"])]
        self.vel = [float(v) for v in player.get("vel", [0, 0])]
        self._tgt, self._ramp_left = None, 0
        source_stock = inventory if inventory is not None else scenario.get("stock", [])
        self.stock = [dict(item) for item in validate_items(source_stock)]
        for item in self.stock:
            ids.reserve(item["id"])
        self.hand = None
        self.time_left_ticks = int(scenario.get("time_left_ticks", round(self.t["duration_s"] * TICK)))
        self.random_customers = scenario.get("random_customers", True)
        self.reputation = float(scenario.get("reputation", self.t["reputation_initial"])
                                if reputation is None else reputation)
        self.stoves = [dict(stove, state=stove.get("state", "idle"), dish=stove.get("dish"),
                            customer_id=stove.get("customer_id"), base_price=stove.get("base_price"),
                            cook_ticks_left=int(stove.get("cook_ticks_left", 0)),
                            ready_ticks=int(stove.get("ready_ticks", 0)))
                       for stove in self._merge(self.t["stoves"], scenario.get("stoves", []))]
        self.tables = self._merge(self.t["tables"], scenario.get("tables", []))
        self.customers = [self._normalise_customer(customer) for customer in scenario.get("customers", [])]
        for customer in self.customers:
            ids.reserve(customer["id"])
        self._initial_reservations()
        initial_hand = scenario.get("hand")
        if initial_hand is not None:
            if isinstance(initial_hand, str):
                owner = next((c for c in sort_by_id(self.customers) if c["dish_id"] == initial_hand), None)
                if owner is None:
                    raise BadInput("món đang cầm không có khách")
                self.hand = {"dish_id": initial_hand, "customer_id": owner["id"],
                             "base_price": owner.get("base_price")}
            else:
                self.hand = dict(initial_hand)
        self.money, self.earned, self.shift_earned = int(money), int(earned), 0
        self.served_count = self.left_count = self.tips = 0
        self.done, self.reason = False, None

    @staticmethod
    def _merge(defaults, updates):
        by_id = {value["id"]: dict(value) for value in defaults}
        for update in updates:
            if update["id"] not in by_id:
                raise BadInput(f"id bếp/bàn không tồn tại: {update['id']}")
            by_id[update["id"]].update(update)
        return sort_by_id(list(by_id.values()))

    def _normalise_customer(self, source):
        dish_id = source["dish_id"]
        return {"id": source["id"], "order_id": source.get("order_id", source["id"]),
                "table_id": source["table_id"], "dish_id": dish_id,
                "state": source.get("state", "waiting"),
                "patience_ticks_left": int(source.get("patience_ticks_left", self.t["patience_s"] * TICK)),
                "eat_ticks_left": int(source.get("eat_ticks_left", 0)),
                "reserved": list(source.get("reserved", [])),
                "order_tick": int(source.get("order_tick", 0)),
                "order_started": bool(source.get("order_started", False)),
                "base_price": source.get("base_price"),
                "patience_ratio_at_service": float(source.get("patience_ratio_at_service", 0))}

    def _initial_reservations(self):
        claimed = set()
        for customer in sorted(self.customers, key=self._order_key):
            if customer["reserved"]:
                ids = set(customer["reserved"])
                by_id = {item["id"]: item for item in self.stock}
                if ids & claimed or not ids <= set(by_id) or any(by_id[i]["fresh"] < self.freshness["spoiled_below"] for i in ids):
                    raise BadInput("reserved trùng, thiếu hoặc đã ươn")
                if self._reserved_counts(customer["reserved"]) != self.menu[customer["dish_id"]]["recipe"]:
                    raise BadInput("reserved không khớp công thức")
                claimed.update(ids)
            elif customer["state"] in ("waiting", "cooking"):
                selected = self._select_items(customer["dish_id"], claimed)
                if not selected:
                    raise BadInput(f"không đủ kho cho khách {customer['id']}")
                customer["reserved"] = selected
                claimed.update(selected)

    def _reserved_counts(self, item_ids):
        by_id, counts = {item["id"]: item for item in self.stock}, {}
        for ident in item_ids:
            if ident in by_id:
                kind = by_id[ident]["kind"]
                counts[kind] = counts.get(kind, 0) + 1
        return counts

    def snapshot(self):
        occupied = {customer["table_id"]: customer for customer in self.customers}
        return {
            "player": {"pos": self.pos, "vel": self.vel},
            "stock": [dict(item) for item in sorted(self.stock, key=lambda value: id_key(value["id"]))],
            "hand": dict(self.hand) if self.hand else None,
            "stoves": [{key: stove.get(key) for key in ("id", "pos", "state", "dish", "customer_id",
                                                                  "base_price", "cook_ticks_left", "ready_ticks")}
                       for stove in self.stoves],
            "tables": [{"id": table["id"], "pos": table["pos"],
                        "customer_id": occupied.get(table["id"], {}).get("id"), "reservation_id": None}
                       for table in self.tables],
            "customers": [dict(customer) for customer in sort_by_id(self.customers)],
        }

    def step(self, inp):
        events = []
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self._tick_customer_timers()
        events.extend(decay_items(self.stock, self.freshness["quan_decay_per_s"] / TICK,
                                  self.freshness["spoiled_below"], "stock"))
        self._repair_reservations()
        self._advance_stoves(events)
        self._move(inp)
        if inp.pressed("interact"):
            self._interact(events)
        self._settle_customers(events, closing=self.time_left_ticks == 0)
        if self.time_left_ticks > 0:
            self._schedule_customer(events)
        else:
            self._close(events)
        return events

    def _repair_reservations(self):
        by_id = {item["id"]: item for item in self.stock}
        claimed = set()
        affected = []
        for customer in sorted(self.customers, key=self._order_key):
            if customer["state"] == "waiting" and any(
                    ident not in by_id or by_id[ident]["fresh"] < self.freshness["spoiled_below"]
                    for ident in customer["reserved"]):
                affected.append(customer)
            else:
                claimed.update(customer["reserved"])
        for customer in affected:
            customer["reserved"] = []
            selected = self._select_items(customer["dish_id"], claimed)
            if selected:
                customer["reserved"] = selected
                claimed.update(selected)
            else:
                customer["state"] = "unfulfillable"

    def _select_items(self, dish_id, extra_claimed=None):
        claimed = set(extra_claimed or ()) | {ident for customer in self.customers for ident in customer["reserved"]}
        selected = []
        for kind, amount in sorted(self.menu[dish_id]["recipe"].items()):
            candidates = [item for item in self.stock if item["kind"] == kind and item["id"] not in claimed
                          and item["fresh"] >= self.freshness["spoiled_below"]]
            candidates.sort(key=lambda item: (-item["fresh"], id_key(item["id"])))
            if len(candidates) < amount:
                return None
            chosen = candidates[:amount]
            selected.extend(item["id"] for item in chosen)
            claimed.update(item["id"] for item in chosen)
        return selected

    def _available_dishes(self):
        return [dish_id for dish_id in sorted(self.menu) if self._select_items(dish_id)]

    def _schedule_customer(self, events):
        first, interval = self.t["first_customer_tick"], int(round(self.t["customer_interval_s"] * TICK))
        if not self.random_customers or self.phase_tick < first or (self.phase_tick - first) % interval:
            return
        occupied = {customer["table_id"] for customer in self.customers}
        table = next((value for value in sort_by_id(self.tables) if value["id"] not in occupied), None)
        if table is None:
            return
        dishes = self._available_dishes()
        if not dishes:
            events.append(("no_dish", {"table_id": table["id"]}))
            return
        dish_id = self.rng.get("customer_dish").choice(dishes)
        customer = self._normalise_customer({"id": self.ids.new("C"), "table_id": table["id"],
                                               "dish_id": dish_id, "order_tick": self.phase_tick})
        customer["reserved"] = self._select_items(dish_id) or []
        self.customers.append(customer)
        events.append(("customer_arrived", {"customer_id": customer["id"], "order_id": customer["order_id"],
                                             "table_id": table["id"], "dish_id": dish_id}))

    def _advance_stoves(self, events):
        for stove in sort_by_id(self.stoves):
            if stove["state"] == "cooking":
                stove["cook_ticks_left"] = max(0, stove["cook_ticks_left"] - 1)
                if stove["cook_ticks_left"] == 0:
                    stove["state"], stove["ready_ticks"] = "ready", 0
                    events.append(("dish_ready", {"stove_id": stove["id"], "dish_id": stove["dish"],
                                                   "customer_id": stove["customer_id"]}))
            elif stove["state"] == "ready":
                stove["ready_ticks"] += 1

    def _tick_customer_timers(self):
        for customer in self.customers:
            if customer["state"] == "eating":
                customer["eat_ticks_left"] = max(0, customer["eat_ticks_left"] - 1)
            elif customer["state"] in ("waiting", "cooking", "unfulfillable"):
                customer["patience_ticks_left"] = max(0, customer["patience_ticks_left"] - 1)

    def _settle_customers(self, events, closing=False):
        to_remove = []
        for customer in sort_by_id(self.customers):
            if customer["state"] == "eating":
                if closing:
                    customer["eat_ticks_left"] = 0
                if customer["eat_ticks_left"] == 0:
                    self._pay(customer, events)
                    to_remove.append(customer)
            elif customer["state"] in ("waiting", "cooking", "unfulfillable"):
                if closing:
                    to_remove.append(customer)
                    continue
                if customer["patience_ticks_left"] == 0:
                    self.reputation = self._clamp(self.reputation + self.t["left_reputation_delta"])
                    self.left_count += 1
                    events.append(("customer_left", {"customer_id": customer["id"],
                                                      "reputation": self.reputation}))
                    to_remove.append(customer)
        for customer in to_remove:
            self._remove_customer(customer)

    def _pay(self, customer, events):
        base = int(customer["base_price"])
        tip = math.floor(base * self.t["tip_rate"]) if customer["patience_ratio_at_service"] >= self.t["tip_min_patience_ratio"] else 0
        total = base + tip
        self.money += total
        self.earned += total
        self.shift_earned += total
        self.tips += tip
        self.served_count += 1
        if tip > 0:
            self.reputation = self._clamp(self.reputation + self.t["tip_reputation"])
        events.append(("paid", {"customer_id": customer["id"], "base_price": base, "tip": tip,
                                 "total": total, "reputation": self.reputation}))

    def _remove_customer(self, customer):
        if customer in self.customers:
            self.customers.remove(customer)
        if self.hand and self.hand.get("customer_id") == customer["id"]:
            self.hand = None
        for stove in self.stoves:
            if stove.get("customer_id") == customer["id"]:
                stove.update(state="idle", dish=None, customer_id=None, base_price=None,
                             cook_ticks_left=0, ready_ticks=0)

    def _close(self, events):
        if self.done:
            return
        self.customers.clear()
        self.hand = None
        for stove in self.stoves:
            stove.update(state="idle", dish=None, customer_id=None, base_price=None,
                         cook_ticks_left=0, ready_ticks=0)
        self.done, self.reason = True, "time"
        events.append(("quan_end", {"reason": "time", "money": self.money, "earned": self.earned,
                                     "shift_earned": self.shift_earned, "tips": self.tips,
                                     "served": self.served_count, "left": self.left_count,
                                     "reputation": self.reputation}))

    def _interact(self, events):
        choices = [(math.dist(self.pos, stove["pos"]), 0, id_key(stove["id"]), "stove", stove)
                   for stove in self.stoves]
        choices += [(math.dist(self.pos, table["pos"]), 1, id_key(table["id"]), "table", table)
                    for table in self.tables]
        choices = [choice for choice in choices if choice[0] <= self.t["interact_radius"]]
        if not choices:
            return
        *_, kind, target = min(choices, key=lambda choice: choice[:3])
        self._use_stove(target, events) if kind == "stove" else self._use_table(target, events)

    def _use_stove(self, stove, events):
        if stove["state"] == "idle":
            customer = next((value for value in sorted(self.customers, key=self._order_key)
                             if value["state"] == "waiting" and value["reserved"] and not value["order_started"]), None)
            if customer is None:
                return
            by_id = {item["id"]: item for item in self.stock}
            items = [by_id[ident] for ident in customer["reserved"]]
            for item in items:
                self.stock.remove(item)
            average = sum(item["fresh"] for item in items) / len(items)
            base_price = math.floor(self.menu[customer["dish_id"]]["price"] * average / 100)
            customer.update(state="cooking", order_started=True, base_price=base_price, reserved=[])
            stove.update(state="cooking", dish=customer["dish_id"], customer_id=customer["id"],
                         base_price=base_price,
                         cook_ticks_left=int(round(self.menu[customer["dish_id"]]["cook_s"] * TICK)),
                         ready_ticks=0)
            ordered = sorted((dict(item) for item in items), key=lambda item: (item["kind"], id_key(item["id"])))
            events.append(("cook_started", {"stove_id": stove["id"], "order_id": customer["order_id"],
                                             "dish_id": customer["dish_id"], "items": ordered,
                                             "base_price": base_price}))
        elif stove["state"] == "ready" and self.hand is None:
            self.hand = {"dish_id": stove["dish"], "customer_id": stove["customer_id"],
                         "base_price": stove["base_price"]}
            events.append(("dish_picked", {"stove_id": stove["id"], **self.hand}))
            stove.update(state="idle", dish=None, customer_id=None, base_price=None,
                         cook_ticks_left=0, ready_ticks=0)

    def _use_table(self, table, events):
        if not self.hand:
            return
        customer = next((value for value in self.customers if value["table_id"] == table["id"]), None)
        if customer is None or customer["id"] != self.hand["customer_id"] or customer["state"] != "cooking":
            return
        customer["state"] = "eating"
        customer["eat_ticks_left"] = int(round(self.t["eat_s"] * TICK))
        customer["patience_ratio_at_service"] = customer["patience_ticks_left"] / (self.t["patience_s"] * TICK)
        events.append(("served", {"customer_id": customer["id"], "order_id": customer["order_id"],
                                   "table_id": table["id"], "dish_id": customer["dish_id"],
                                   "base_price": customer["base_price"]}))
        self.hand = None

    def _move(self, inp):
        mx, mz = inp.move
        self.vel = ramp_velocity(self, (mx * self.t["walk_speed"], mz * self.t["walk_speed"]),
                                 int(self.t["ramp_max_ticks"]))
        for index, axis in enumerate(("x", "z")):
            self.pos[index] += self.vel[index] / TICK
            low, high = self.t["bounds"][axis]
            if self.pos[index] <= low:
                self.pos[index], self.vel[index] = low, max(0.0, self.vel[index])
            elif self.pos[index] >= high:
                self.pos[index], self.vel[index] = high, min(0.0, self.vel[index])

    @staticmethod
    def _order_key(customer):
        return customer["order_tick"], id_key(customer["table_id"])

    def _clamp(self, value):
        return max(self.t["reputation_min"], min(self.t["reputation_max"], value))
