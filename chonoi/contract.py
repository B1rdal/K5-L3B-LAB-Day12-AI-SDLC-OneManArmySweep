"""Đọc và kiểm tra manifest Test Contract v1.3."""

import json
import math
import os

from .errors import BadInput
from .inventory import KINDS

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game.contract.json")


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _range(name, value, lower, upper):
    if not _number(value) or not lower <= value <= upper:
        raise BadInput(f"tuning.{name} phải trong [{lower}, {upper}]")


def _positive_int(name, value):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise BadInput(f"tuning.{name} phải là số nguyên dương")


def _bounds(name, value, axes):
    if not isinstance(value, dict) or set(value) != set(axes):
        raise BadInput(f"tuning.{name}.bounds phải có đúng {list(axes)}")
    for axis in axes:
        span = value[axis]
        if not isinstance(span, list) or len(span) != 2 or not all(_number(v) for v in span) or span[0] >= span[1]:
            raise BadInput(f"tuning.{name}.bounds.{axis} không hợp lệ")


def _position(name, value, bounds, axes):
    if not isinstance(value, list) or len(value) != 2 or not all(_number(v) for v in value):
        raise BadInput(f"tuning.{name} phải là vị trí hai chiều")
    if any(not bounds[axis][0] <= coordinate <= bounds[axis][1]
           for axis, coordinate in zip(axes, value)):
        raise BadInput(f"tuning.{name} nằm ngoài biên")


def load_contract(path=DEFAULT_PATH):
    try:
        with open(path, encoding="utf-8") as stream:
            contract = json.load(stream)
    except (OSError, ValueError) as exc:
        raise BadInput(f"không đọc được {path}: {exc}")
    if contract.get("contract_version") != "1.3":
        raise BadInput("contract_version phải là '1.3'")
    for command in ("build_cmd", "run_cmd", "headless_cmd", "bench_cmd", "soak_cmd"):
        if not isinstance(contract.get(command), str) or not contract[command].strip():
            raise BadInput(f"thiếu lệnh {command}")
    validate_tuning(contract.get("tuning"))
    return contract


def validate_tuning(tuning):
    if not isinstance(tuning, dict):
        raise BadInput("thiếu tuning")
    required = {"gather", "quan", "menu", "freshness", "day_plan", "shop", "score"}
    if not required <= set(tuning):
        raise BadInput(f"tuning thiếu khóa: {sorted(required - set(tuning))}")
    fresh = tuning["freshness"]
    expected = {"initial": 100, "gather_decay_per_s": 0.5, "quan_decay_per_s": 0.25, "spoiled_below": 30}
    if fresh != expected:
        raise BadInput("tuning.freshness không khớp số chuẩn v1.2")
    g = tuning["gather"]
    _bounds("gather", g.get("bounds"), ("x", "d"))
    for key in ("dock_pos", "start_pos"):
        _position(f"gather.{key}", g.get(key), g["bounds"], ("x", "d"))
    for name, lower, upper in (("duration_s", 60, 600), ("swim_speed", 1, 10),
                               ("oxygen_max_s", 10, 120), ("hold_capacity", 4, 30),
                               ("fish_speed", 0.1, 10)):
        _range(f"gather.{name}", g.get(name), lower, upper)
    if len(g.get("nodes", [])) != 6 or len(g.get("fish_initial", [])) != 8:
        raise BadInput("gather cần đúng 6 nút hái và 8 đàn cá đầu ca")
    ids = set()
    for entity in [*g["nodes"], *g["fish_initial"]]:
        if not isinstance(entity.get("id"), str) or entity["id"] in ids:
            raise BadInput("id gather phải duy nhất")
        ids.add(entity["id"])
    if set(g.get("fish_yield", {})) != {"ca_linh", "ca_loc", "ca_keo"}:
        raise BadInput("fish_yield phải có đủ ba loài cá")
    q = tuning["quan"]
    _bounds("quan", q.get("bounds"), ("x", "z"))
    _position("quan.start_pos", q.get("start_pos"), q["bounds"], ("x", "z"))
    if len(q.get("stoves", [])) != 2 or len(q.get("tables", [])) != 4:
        raise BadInput("quan cần đúng 2 bếp và 4 bàn")
    menu = tuning["menu"]
    if not isinstance(menu, dict) or len(menu) != 6:
        raise BadInput("menu cần đúng 6 món")
    for dish_id, dish in menu.items():
        recipe = dish.get("recipe")
        if not isinstance(recipe, dict) or not recipe or not set(recipe) <= set(KINDS):
            raise BadInput(f"menu.{dish_id}.recipe không hợp lệ")
        if any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in recipe.values()):
            raise BadInput(f"menu.{dish_id}.recipe cần số nguyên dương")
        _range(f"menu.{dish_id}.cook_s", dish.get("cook_s"), 0.1, 600)
        _positive_int(f"menu.{dish_id}.price", dish.get("price"))
    plans = tuning["day_plan"]
    if not isinstance(plans, list) or [plan.get("day") for plan in plans] != [1, 2, 3, 4, 5]:
        raise BadInput("day_plan phải có D1-D5")
    for plan in plans:
        calculated = {}
        for dish_id, servings in plan.get("dishes", {}).items():
            if dish_id not in menu or isinstance(servings, bool) or not isinstance(servings, int) or servings <= 0:
                raise BadInput("day_plan.dishes không hợp lệ")
            for kind, amount in menu[dish_id]["recipe"].items():
                calculated[kind] = calculated.get(kind, 0) + amount * servings
        if calculated != plan.get("ingredients"):
            raise BadInput(f"day_plan D{plan['day']} có ingredients sai")
    shop = tuning["shop"]
    _positive_int("shop.max_ticks", shop.get("max_ticks"))
    for upgrade in ("oxygen", "hp"):
        levels = shop.get("upgrades", {}).get(upgrade)
        if not isinstance(levels, list) or [level.get("level") for level in levels] != [1, 2]:
            raise BadInput(f"shop.upgrades.{upgrade} cần hai cấp")
