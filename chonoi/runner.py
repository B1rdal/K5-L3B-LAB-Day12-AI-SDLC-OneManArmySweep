"""Deterministic tick runner shared by headless and live modes."""

import math

from .ids import IdAllocator
from .inputs import InputPlayer
from .inventory import write_inventory
from .jsonl import JsonlWriter
from .rng import Streams
from .sim.day import DaySim
from .sim.gather import GatherSim
from .sim.quan import QuanSim


def build_sim(mode, tuning, scenario, seed, inventory=None, days=1):
    streams, ids = Streams(seed), IdAllocator()
    if mode == "gather":
        return GatherSim(tuning, scenario, streams, ids)
    if mode == "quan":
        return QuanSim(tuning, scenario, streams, ids, inventory=inventory)
    return DaySim(tuning, scenario, streams, ids, days=days)


def _common(sim, tick, sim_tick, state, tuning):
    score = sim.earned + tuning["score"]["reputation_multiplier"] * math.floor(sim.reputation)
    return {"type": "snapshot", "tick": tick, "sim_tick": sim_tick, "mode": sim.mode,
            "phase": sim.phase, "phase_tick": sim.phase_tick, "state": state,
            "time_left_ticks": sim.time_left_ticks, "money": sim.money, "earned": sim.earned,
            "reputation": sim.reputation, "score": score}


class Session:
    def __init__(self, mode, tuning, scenario, seed, inventory=None, days=1):
        self.mode, self.tuning = mode, tuning
        self.sim = build_sim(mode, tuning, scenario, seed, inventory, days)
        self.tick = self.sim_tick = 0
        self.paused = False

    @property
    def done(self):
        return self.sim.done

    def snapshot(self):
        state = "finished" if self.done else "paused" if self.paused else "playing"
        snapshot = _common(self.sim, self.tick, self.sim_tick, state, self.tuning)
        snapshot.update(self.sim.snapshot())
        return snapshot

    def initial_rows(self):
        return [self._event(name, data, tick=0) for name, data in getattr(self.sim, "initial_events", [])]

    def _event(self, name, data, tick=None, phase=None):
        row = {"type": "event", "tick": self.tick if tick is None else tick,
               "phase": phase or self.sim.phase, "name": name, "data": data}
        if self.mode == "day":
            row["day"] = self.sim.day
        return row

    def step(self, inp):
        events = []
        if inp.pressed("pause"):
            if not self.paused:
                self.paused = True
                self.tick += 1
                return [self._event("paused", {})]
            self.paused = False
            events.append(("resumed", {}))
        elif self.paused:
            self.tick += 1
            return []
        events.extend(self.sim.step(inp))
        self.tick += 1
        self.sim_tick += 1
        rows = []
        for event in events:
            if len(event) == 3:
                phase, name, data = event
                rows.append(self._event(name, data, phase=phase))
            else:
                name, data = event
                rows.append(self._event(name, data))
        return rows

    def end_row(self):
        score = self.sim.earned + self.tuning["score"]["reputation_multiplier"] * math.floor(self.sim.reputation)
        row = {"type": "end", "ticks": self.tick, "sim_tick": self.sim_tick, "mode": self.sim.mode,
               "state": "finished" if self.done else "paused" if self.paused else "playing",
               "reason": self.sim.reason if self.done else "tick_limit", "money": self.sim.money,
               "earned": self.sim.earned, "reputation": self.sim.reputation, "score": score}
        if self.mode == "day":
            row["days_completed"] = self.sim.days_completed
        return row

    def write_inventory_if_done(self, inventory_out):
        if self.mode == "gather" and self.sim.done and inventory_out:
            write_inventory(inventory_out, self.sim.inventory_items())


def run(mode, tuning, scenario, seed, frames, ticks, out_path, snapshot_every,
        inventory=None, inventory_out=None, days=1):
    session = Session(mode, tuning, scenario, seed, inventory, days)
    player, writer = InputPlayer(frames), JsonlWriter(out_path)
    try:
        for row in session.initial_rows():
            writer.write(row)
        writer.write(session.snapshot())
        last_snapshot = 0
        while session.tick < ticks and not session.done:
            for row in session.step(player.advance(session.tick)):
                writer.write(row)
            if session.tick % snapshot_every == 0 or session.done:
                writer.write(session.snapshot())
                last_snapshot = session.tick
        if last_snapshot != session.tick:
            writer.write(session.snapshot())
        writer.write(session.end_row())
    finally:
        writer.close()
    session.write_inventory_if_done(inventory_out)
    return session.sim
