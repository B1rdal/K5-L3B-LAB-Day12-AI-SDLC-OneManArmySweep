"""Kiểm tra các vòng chơi bắt buộc của gather và quan."""

import unittest

from chonoi.contract import load_contract
from chonoi.inputs import InputState
from chonoi.runner import Session


def idle():
    return InputState((0.0, 0.0), {}, set())


def press(button):
    return InputState((0.0, 0.0), {button: True}, {button})


class GatherRules(unittest.TestCase):
    def setUp(self):
        self.tuning = load_contract()["tuning"]

    def test_harvest_and_catch_update_hold(self):
        harvest = Session("gather", self.tuning,
                          {"player": {"pos": [12, 0]}, "fish": [], "nodes": [
                              {"id": "N1", "kind": "bong_dien_dien", "pos": [12, 0]}]}, 1)
        rows = harvest.step(press("interact"))
        self.assertEqual([row["name"] for row in rows], ["gather"])
        self.assertEqual([item["kind"] for item in harvest.sim.hold], ["bong_dien_dien"])
        self.assertGreater(harvest.sim.nodes[0]["regrow_ticks"], 0)

        fishing = Session("gather", self.tuning,
                          {"player": {"pos": [15, 5]}, "nodes": [], "fish": [
                              {"id": "F1", "kind": "ca_linh", "pos": [15, 5]}]}, 1)
        rows = fishing.step(press("catch"))
        self.assertEqual([row["name"] for row in rows], ["fish_caught"])
        self.assertEqual([item["kind"] for item in fishing.sim.hold], ["ca_linh"] * 3)
        self.assertEqual(fishing.sim.fish, [])

    def test_oxygen_choke_faint_clears_inventory(self):
        session = Session("gather", self.tuning,
                          {"player": {"pos": [20, 5], "oxygen_ticks": 1, "hp": 1},
                           "hold": [{"id": "I1", "kind": "ca_loc", "fresh": 100}],
                           "nodes": [], "fish": [], "monsters": []}, 1)
        names = []
        while not session.done:
            names.extend(row["name"] for row in session.step(idle()))
        self.assertEqual(names, ["oxygen_empty", "choke", "faint", "gather_end"])
        self.assertEqual(session.sim.reason, "fainted")
        self.assertEqual(session.sim.hold, [])


class QuanRules(unittest.TestCase):
    def setUp(self):
        self.tuning = load_contract()["tuning"]

    def test_customer_cook_serve_and_pay(self):
        scenario = {"player": {"pos": [2, 8]},
                    "stock": [{"id": "I1", "kind": "ca_loc", "fresh": 100}], "customers": [
            {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}]}
        session = Session("quan", self.tuning, scenario, 1)
        self.assertEqual([row["name"] for row in session.step(press("interact"))], ["cook_started"])
        rows = []
        for _ in range(360):
            rows.extend(session.step(idle()))
        self.assertIn("dish_ready", [row["name"] for row in rows])
        self.assertEqual([row["name"] for row in session.step(press("interact"))], ["dish_picked"])
        session.sim.pos = [9, 2]
        self.assertEqual([row["name"] for row in session.step(press("interact"))], ["served"])
        rows = []
        for _ in range(600):
            rows.extend(session.step(idle()))
        paid = next(row for row in rows if row["name"] == "paid")
        self.assertEqual(paid["data"]["base_price"], 59)
        self.assertEqual(paid["data"]["tip"], 11)
        self.assertEqual(session.sim.money, 70)
        self.assertEqual(session.sim.customers, [])

    def test_scheduled_customer_reserves_stock(self):
        session = Session("quan", self.tuning,
                          {"stock": [{"id": "I1", "kind": "ca_loc", "fresh": 100}]}, 7)
        names = []
        for _ in range(self.tuning["quan"]["first_customer_tick"]):
            names.extend(row["name"] for row in session.step(idle()))
        self.assertEqual(names, ["customer_arrived"])
        self.assertEqual(len(session.sim.customers), 1)
        self.assertEqual(session.sim.customers[0]["reserved"], ["I1"])
        self.assertEqual(len(session.sim.stock), 1)

    def test_random_customers_can_be_disabled(self):
        stock = [{"id": "I1", "kind": "ca_loc", "fresh": 100}]
        session = Session("quan", self.tuning, {"stock": stock, "random_customers": False}, 7)
        for _ in range(self.tuning["quan"]["first_customer_tick"] + 1):
            session.step(idle())
        self.assertEqual(session.sim.customers, [])
        self.assertEqual(session.sim.stock[0]["id"], "I1")


if __name__ == "__main__":
    unittest.main()
