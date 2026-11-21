"""Public regression coverage for the v1.1–v1.3 core."""

import json
import os
import subprocess
import unittest

from chonoi.contract import load_contract
from chonoi.inputs import InputState
from chonoi.runner import Session
from chonoi.soak import soak

from helpers import Workdir, run_headless, write_json


def state(edges=(), buy=None):
    return InputState((0.0, 0.0), {name: True for name in edges}, set(edges), buy)


def item(number, kind, fresh=100):
    return {"id": f"I{number}", "kind": kind, "fresh": fresh}


class Freshness(unittest.TestCase):
    def setUp(self):
        self.tuning = load_contract()["tuning"]

    def test_crossing_30_emits_spoiled_at_tick_one(self):
        session = Session("gather", self.tuning,
                          {"hold": [item(1, "ca_linh", 30)], "random_fish": False,
                           "monsters": []}, 1)
        rows = session.step(state())
        self.assertEqual([(row["tick"], row["name"], row["data"]["item_id"]) for row in rows],
                         [(1, "spoiled", "I1")])
        self.assertLess(session.sim.hold[0]["fresh"], 30)
        self.assertEqual([row["name"] for row in session.step(state())], [])

    def test_v12_rejects_counted_inventory(self):
        with Workdir() as work:
            inventory = write_json(work.path("inventory.json"), {"items": {"ca_loc": 1}})
            code, _ = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0",
                                   "--inventory", inventory, "--out", work.path("out.jsonl"))
            self.assertEqual(code, 2)


class GatherV11(unittest.TestCase):
    def setUp(self):
        self.tuning = load_contract()["tuning"]

    def test_fish_move_turn_and_spawn(self):
        moving = Session("gather", self.tuning, {"monsters": []}, 2)
        before = list(moving.sim.fish[0]["pos"])
        moving.step(state())
        self.assertNotEqual(moving.sim.fish[0]["pos"], before)
        spawning = Session("gather", self.tuning, {"fish": [], "monsters": []}, 2)
        names = []
        for _ in range(360):
            names.extend(row["name"] for row in spawning.step(state()))
        self.assertIn("fish_spawned", names)
        self.assertEqual(len(spawning.sim.fish), 1)

    def test_monster_hit_drops_lifo_and_recoils(self):
        hold = [item(i, "ca_loc") for i in range(1, 5)]
        monster = {"id": "M1", "kind": "ca_sau", "pos": [60, 24],
                   "waypoints": [[60, 24], [64, 24]]}
        session = Session("gather", self.tuning,
                          {"player": {"pos": [60, 24]}, "hold": hold,
                           "random_fish": False, "monsters": [monster]}, 1)
        hit = next(row for row in session.step(state()) if row["name"] == "monster_hit")
        self.assertEqual([value["id"] for value in hit["data"]["lost"]], ["I4", "I3"])
        self.assertEqual(session.sim.monsters[0]["state"], "recoil")
        self.assertEqual(session.sim.invuln_ticks, 90)


class DayAndShop(unittest.TestCase):
    def setUp(self):
        self.tuning = load_contract()["tuning"]

    def test_pause_stops_simulation_and_resume_runs_step(self):
        session = Session("gather", self.tuning, {"random_fish": False, "monsters": []}, 1)
        self.assertEqual([row["name"] for row in session.step(state(("pause",)))], ["paused"])
        self.assertEqual(session.sim_tick, 0)
        session.step(state())
        self.assertEqual(session.sim_tick, 0)
        names = [row["name"] for row in session.step(state(("pause",)))]
        self.assertEqual(names[0], "resumed")
        self.assertEqual(session.sim_tick, 1)

    def test_day_transitions_and_upgrade_activates_next_day(self):
        scenario = {"day": {"money": 500, "earned": 500},
                    "gather": {"random_fish": False, "monsters": []},
                    "quan": {"random_customers": False, "time_left_ticks": 1}}
        session = Session("day", self.tuning, scenario, 1, days=2)
        rows = session.step(state(("interact",)))
        self.assertEqual([(row["phase"], row["name"]) for row in rows[-2:]],
                         [("gather", "gather_end"), ("quan", "phase_start")])
        session.step(state())
        self.assertEqual(session.sim.phase, "shop")
        rows = session.step(state(("shop_done",), buy="oxygen"))
        self.assertEqual([row["name"] for row in rows[:2]], ["bought", "shop_end"])
        self.assertEqual(session.sim.day, 2)
        self.assertEqual(session.sim.active_upgrades["oxygen"], 1)
        self.assertEqual(session.sim.current.oxygen_max, 2700)

    def test_soak_completes_repeated_days(self):
        result = soak(7, 2)
        self.assertEqual(result["crashes"], 0)
        self.assertEqual(result["days_completed"], 2)
        self.assertEqual([entry["day"] for entry in result["results"]], [1, 2])


class ManifestV13(unittest.TestCase):
    def test_commands_and_contract_version(self):
        contract = load_contract()
        self.assertEqual(contract["contract_version"], "1.3")
        self.assertIn("chonoi.bench", contract["bench_cmd"])
        self.assertIn("chonoi.soak", contract["soak_cmd"])
        self.assertEqual(len(contract["tuning"]["menu"]), 6)
        self.assertEqual(len(contract["tuning"]["quan"]["tables"]), 4)


if __name__ == "__main__":
    unittest.main()
