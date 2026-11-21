"""Scenario validation for Test Contract v1.3."""

import json
import math

from .errors import BadInput
from .inventory import validate_items

GATHER_KEYS = {"player", "hold", "nodes", "fish", "monsters", "random_fish", "time_left_ticks"}
QUAN_KEYS = {"player", "stock", "hand", "stoves", "tables", "customers", "random_customers",
             "reputation", "time_left_ticks"}
DAY_KEYS = {"money", "earned", "reputation", "upgrades", "day_plan"}


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _position(name, value, bounds, axes):
    if not isinstance(value, list) or len(value) != 2 or not all(_number(v) for v in value):
        raise BadInput(f"{name} phải là [{axes[0]}, {axes[1]}]")
    for coordinate, axis in zip(value, axes):
        if not bounds[axis][0] <= coordinate <= bounds[axis][1]:
            raise BadInput(f"{name} nằm ngoài biên {axis}")


def _unique_entities(name, values):
    if not isinstance(values, list):
        raise BadInput(f"{name} phải là mảng")
    seen = set()
    for value in values:
        ident = value.get("id") if isinstance(value, dict) else None
        if not isinstance(ident, str) or not ident or ident in seen:
            raise BadInput(f"{name} có id trống hoặc trùng")
        seen.add(ident)


def load_scenario(path, mode, tuning):
    if path is None:
        return {}
    try:
        with open(path, encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, ValueError) as exc:
        raise BadInput(f"không đọc được scenario {path}: {exc}")
    if not isinstance(data, dict) or not set(data) <= {"gather", "quan", "day"}:
        raise BadInput("scenario chỉ nhận gather, quan và day")
    allowed_blocks = {mode} if mode != "day" else {"day", "gather", "quan"}
    if not set(data) <= allowed_blocks:
        raise BadInput(f"scenario có khối sai mode {mode}")
    gather = data.get("gather", {})
    quan = data.get("quan", {})
    day = data.get("day", {})
    _validate_gather(gather, tuning)
    _validate_quan(quan, tuning, in_day=mode == "day")
    if mode == "day":
        _validate_day(day, tuning)
        return {"day": day, "gather": gather, "quan": quan}
    return gather if mode == "gather" else quan


def _validate_time(block, duration):
    if "time_left_ticks" in block:
        value = block["time_left_ticks"]
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= duration:
            raise BadInput(f"time_left_ticks phải trong [1,{duration}]")


def _validate_gather(block, tuning):
    if not isinstance(block, dict) or not set(block) <= GATHER_KEYS:
        raise BadInput("gather có trường lạ")
    g = tuning["gather"]
    _validate_time(block, int(g["duration_s"] * 60))
    if "hold" in block:
        hold = validate_items(block["hold"])
        if len(hold) > g["hold_capacity"]:
            raise BadInput("hold vượt sức chứa")
    player = block.get("player", {})
    allowed_player = {"pos", "vel", "heading_deg", "hp", "oxygen_ticks", "zero_oxy_ticks",
                      "invuln_ticks", "catch_cd_ticks"}
    if not isinstance(player, dict) or not set(player) <= allowed_player:
        raise BadInput("gather.player có trường lạ")
    if "pos" in player:
        _position("gather.player.pos", player["pos"], g["bounds"], ("x", "d"))
    if "vel" in player and (not isinstance(player["vel"], list) or len(player["vel"]) != 2
                             or not all(_number(v) for v in player["vel"])):
        raise BadInput("gather.player.vel không hợp lệ")
    for flag in ("random_fish",):
        if flag in block and not isinstance(block[flag], bool):
            raise BadInput(f"{flag} phải là boolean")
    if "nodes" in block:
        _unique_entities("gather.nodes", block["nodes"])
        for node in block["nodes"]:
            if node.get("kind") not in {"bong_dien_dien", "bong_sung", "keo_neo"}:
                raise BadInput("node.kind không hợp lệ")
            _position(f"node {node['id']}", node.get("pos"), g["bounds"], ("x", "d"))
            if node["pos"][1] != 0:
                raise BadInput("nút hái phải ở mặt nước")
    if "fish" in block:
        _unique_entities("gather.fish", block["fish"])
        for fish in block["fish"]:
            if fish.get("kind") not in g["fish_yield"]:
                raise BadInput("fish.kind không hợp lệ")
            _position(f"fish {fish['id']}", fish.get("pos"), g["bounds"], ("x", "d"))
    if "monsters" in block:
        _unique_entities("gather.monsters", block["monsters"])


def _validate_quan(block, tuning, in_day=False):
    if not isinstance(block, dict) or not set(block) <= QUAN_KEYS:
        raise BadInput("quan có trường lạ")
    q = tuning["quan"]
    _validate_time(block, int(q["duration_s"] * 60))
    if in_day and ("stock" in block or "reputation" in block):
        raise BadInput("day cấm quan.stock và quan.reputation")
    if "stock" in block:
        validate_items(block["stock"])
    if "random_customers" in block and not isinstance(block["random_customers"], bool):
        raise BadInput("random_customers phải là boolean")
    player = block.get("player", {})
    if not isinstance(player, dict) or not set(player) <= {"pos", "vel"}:
        raise BadInput("quan.player có trường lạ")
    if "pos" in player:
        _position("quan.player.pos", player["pos"], q["bounds"], ("x", "z"))
    for collection in ("stoves", "tables", "customers"):
        if collection in block:
            _unique_entities(f"quan.{collection}", block[collection])
    table_ids = {table["id"] for table in q["tables"]}
    menu = tuning["menu"]
    reserved = set()
    stock_ids = {item["id"] for item in validate_items(block.get("stock", []))}
    for customer in block.get("customers", []):
        if customer.get("table_id") not in table_ids or customer.get("dish_id") not in menu:
            raise BadInput(f"customer {customer['id']} tham chiếu bàn hoặc món sai")
        ids = customer.get("reserved", [])
        if not isinstance(ids, list) or any(not isinstance(ident, str) for ident in ids):
            raise BadInput("customers.reserved phải là mảng id")
        if set(ids) & reserved or (stock_ids and not set(ids) <= stock_ids):
            raise BadInput("reserved trùng hoặc không có trong kho")
        reserved.update(ids)


def _validate_day(block, tuning):
    if not isinstance(block, dict) or not set(block) <= DAY_KEYS:
        raise BadInput("day có trường lạ")
    money, earned = block.get("money", 0), block.get("earned", 0)
    if not _number(money) or not _number(earned) or not 0 <= money <= earned:
        raise BadInput("day cần 0 ≤ money ≤ earned")
    if money and "earned" not in block:
        raise BadInput("khai earned khi có money đầu kỳ")
    upgrades = block.get("upgrades", {})
    if not isinstance(upgrades, dict) or not set(upgrades) <= {"oxygen", "hp"}:
        raise BadInput("day.upgrades không hợp lệ")
    if any(isinstance(level, bool) or not isinstance(level, int) or not 0 <= level <= 2
           for level in upgrades.values()):
        raise BadInput("cấp nâng cấp phải trong [0,2]")
