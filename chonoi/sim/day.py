"""Multi-day orchestration for gather → quan → shop."""

import math

from ..inventory import validate_items
from .gather import GatherSim
from .quan import QuanSim
from .shop import ShopSim


class DaySim:
    mode = "day"

    def __init__(self, tuning, scenario, streams, ids, days=1):
        self.tuning, self.scenario = tuning, scenario
        self.rng, self.ids, self.days_target = streams, ids, days
        state = scenario.get("day", {})
        self.day = 1
        self.days_completed = 0
        self.money = int(state.get("money", 0))
        self.earned = int(state.get("earned", 0))
        self.reputation = float(state.get("reputation", tuning["quan"]["reputation_initial"]))
        self.upgrades = dict(state.get("upgrades", {}))
        self.active_upgrades = dict(self.upgrades)
        self.results = []
        self.done, self.reason = False, None
        self.initial_events = [("day_start", {}), ("day_plan", self._plan_payload()),
                               ("phase_start", {})]
        self._start_gather()

    @property
    def phase(self):
        return self.current.phase

    @property
    def phase_tick(self):
        return self.current.phase_tick

    @property
    def time_left_ticks(self):
        return self.current.time_left_ticks

    def _plan(self):
        plans = self.scenario.get("day", {}).get("day_plan") or self.tuning["day_plan"]
        return plans[(self.day - 1) % len(plans)]

    def _plan_payload(self):
        plan = self._plan()
        return {"dishes": dict(plan["dishes"]), "ingredients": dict(plan.get("ingredients", {}))}

    def _start_gather(self):
        gather = dict(self.scenario.get("gather", {}))
        if self.day > 1 and "hold" in gather:
            gather["hold"] = [{"id": self.ids.new("I"), "kind": item["kind"], "fresh": item["fresh"]}
                              for item in validate_items(gather["hold"])]
        self.current = GatherSim(self.tuning, gather, self.rng, self.ids, self.day, self.active_upgrades)

    def _start_quan(self, stock):
        self.current = QuanSim(self.tuning, self.scenario.get("quan", {}), self.rng, self.ids,
                               inventory=stock, menu_filter=set(self._plan()["dishes"]),
                               money=self.money, earned=self.earned, reputation=self.reputation)

    def _start_shop(self, stock):
        self.current = ShopSim(self.tuning, stock, self.money, self.earned,
                               self.reputation, self.upgrades)

    def snapshot(self):
        snapshot = self.current.snapshot()
        snapshot.update({"day": self.day, "day_plan": self._plan_payload(),
                         "upgrades": dict(self.upgrades), "active_upgrades": dict(self.active_upgrades),
                         "days_completed": self.days_completed})
        return snapshot

    def step(self, inp):
        old_phase = self.current.phase
        events = [(old_phase, name, data) for name, data in self.current.step(inp)]
        if old_phase in ("quan", "shop"):
            self.money, self.earned = self.current.money, self.current.earned
            self.reputation = self.current.reputation
            if old_phase == "shop":
                self.upgrades = dict(self.current.upgrades)
        if not self.current.done:
            return events
        if self.current.phase == "gather":
            stock = self.current.inventory_items()
            self._start_quan(stock)
            events.append((self.current.phase, "phase_start", {}))
        elif self.current.phase == "quan":
            self.money, self.earned = self.current.money, self.current.earned
            self.reputation = self.current.reputation
            stock = [dict(item) for item in self.current.stock]
            self._start_shop(stock)
            events.append((self.current.phase, "phase_start", {}))
        else:
            self.money, self.earned = self.current.money, self.current.earned
            self.reputation, self.upgrades = self.current.reputation, dict(self.current.upgrades)
            self.days_completed += 1
            score = self.earned + self.tuning["score"]["reputation_multiplier"] * math.floor(self.reputation)
            self.results.append({"day": self.day, "earned": self.earned,
                                 "reputation": self.reputation, "score": score})
            if self.days_completed >= self.days_target:
                self.done, self.reason = True, "days_complete"
            else:
                self.day += 1
                self.active_upgrades = dict(self.upgrades)
                self._start_gather()
                events.extend([(self.current.phase, "day_start", {}),
                               (self.current.phase, "day_plan", self._plan_payload()),
                               (self.current.phase, "phase_start", {})])
        return events
