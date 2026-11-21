"""Kho cá thể v1.2+: ``{"items":[{"id","kind","fresh"}]}``."""

import json
import math
import os
import tempfile

from .errors import BadInput
from .ids import id_key

KINDS = ("ca_loc", "ca_linh", "ca_keo", "bong_dien_dien", "bong_sung", "keo_neo")
KINDS_P1 = KINDS


def validate_items(items, kinds=KINDS):
    if not isinstance(items, list):
        raise BadInput("items phải là mảng cá thể ở contract v1.2+")
    out, seen = [], set()
    for index, raw in enumerate(items):
        if not isinstance(raw, dict) or set(raw) != {"id", "kind", "fresh"}:
            raise BadInput(f"items[{index}] phải có đúng id, kind, fresh")
        ident, kind, fresh = raw["id"], raw["kind"], raw["fresh"]
        if not isinstance(ident, str) or not ident or ident in seen:
            raise BadInput(f"id cá thể trống hoặc trùng: {ident!r}")
        if kind not in kinds:
            raise BadInput(f"nguyên liệu lạ: {kind}")
        if isinstance(fresh, bool) or not isinstance(fresh, (int, float)) or not math.isfinite(fresh):
            raise BadInput(f"độ tươi không hợp lệ cho {ident}")
        if not 0 <= fresh <= 100:
            raise BadInput(f"độ tươi ngoài [0,100] cho {ident}")
        seen.add(ident)
        out.append({"id": ident, "kind": kind, "fresh": float(fresh)})
    return out


def read_inventory(path: str) -> list:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        raise BadInput(f"không đọc được file kho {path}: {exc}")
    if not isinstance(data, dict) or set(data) != {"items"}:
        raise BadInput("file kho chỉ được có khóa gốc 'items'")
    return validate_items(data["items"])


def inventory_payload(items: list) -> dict:
    ordered = sorted((dict(item) for item in items), key=lambda item: id_key(item["id"]))
    return {"items": ordered}


def write_inventory(path: str, items: list):
    payload = inventory_payload(validate_items(items))
    directory = os.path.dirname(os.path.abspath(path))
    fd, temporary = tempfile.mkstemp(prefix=".inv-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"))
            stream.write("\n")
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def new_item(ids, kind: str, fresh: float = 100.0) -> dict:
    return {"id": ids.new("I"), "kind": kind, "fresh": float(fresh)}


def item_counts(items: list) -> dict:
    counts = {}
    for item in items:
        counts[item["kind"]] = counts.get(item["kind"], 0) + 1
    return {kind: counts[kind] for kind in sorted(counts)}


def hold_to_items(hold: list) -> dict:
    """Compatibility name retained for callers; returns the v1.2 inventory envelope."""
    return inventory_payload(hold)


def decay_items(items: list, amount: float, spoiled_below: float, location: str):
    events = []
    for item in sorted(items, key=lambda value: id_key(value["id"])):
        before = item["fresh"]
        item["fresh"] = max(0.0, before - amount)
        if before >= spoiled_below and item["fresh"] < spoiled_below:
            events.append(("spoiled", {"item_id": item["id"], "kind": item["kind"],
                                        "location": location}))
    return events
