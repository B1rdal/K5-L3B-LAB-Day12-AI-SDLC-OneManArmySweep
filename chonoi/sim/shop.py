"""Shop phase for persistent upgrades."""


class ShopSim:
    mode = "day"
    phase = "shop"

    def __init__(self, tuning, stock, money, earned, reputation, upgrades):
        self.tuning = tuning
        self.stock = [dict(item) for item in stock]
        self.money, self.earned, self.reputation = money, earned, reputation
        self.upgrades = dict(upgrades)
        self.phase_tick = 0
        self.time_left_ticks = int(tuning["shop"]["max_ticks"])
        self.done, self.reason = False, None

    def snapshot(self):
        return {"stock": [dict(item) for item in self.stock], "upgrades": dict(self.upgrades)}

    def step(self, inp):
        events = []
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        if inp.buy is not None:
            self._buy(inp.buy, events)
        if inp.pressed("shop_done"):
            self._finish("done", events)
        elif self.time_left_ticks == 0:
            self._finish("time", events)
        return events

    def _buy(self, action, events):
        levels = self.tuning["shop"]["upgrades"].get(action)
        if levels is None:
            events.append(("buy_failed", {"action": action, "reason": "unknown"}))
            return
        current = self.upgrades.get(action, 0)
        if current >= len(levels):
            events.append(("buy_failed", {"action": action, "reason": "max_level"}))
            return
        target = levels[current]
        if self.money < target["price"]:
            events.append(("buy_failed", {"action": action, "reason": "funds"}))
            return
        self.money -= target["price"]
        self.upgrades[action] = target["level"]
        events.append(("bought", {"upgrade": action, "level": target["level"],
                                   "price": target["price"], "money": self.money}))

    def _finish(self, reason, events):
        self.done, self.reason = True, reason
        events.append(("shop_end", {"reason": reason}))
