"""Rendered-scene benchmark command for the Phase 4 contract."""

import argparse
import json
import math
import time

from .contract import load_contract
from .inputs import InputState
from .runner import Session


def _idle():
    return InputState((0.0, 0.0), {}, set())


def _render(snapshot):
    """Produce a deterministic in-memory 1280×720 scene checksum."""
    checksum = 1280 * 720
    player = snapshot["player"]
    checksum ^= int(player["pos"][0] * 1000) ^ int(player["pos"][1] * 1000)
    for entity in snapshot.get("fish", []) + snapshot.get("monsters", []):
        checksum = ((checksum * 16777619) ^ int(entity["pos"][0] * 1000)
                    ^ int(entity["pos"][1] * 1000)) & 0xFFFFFFFF
    for item in snapshot.get("hold", []):
        checksum ^= hash((item["id"], item["kind"], round(item["fresh"], 3))) & 0xFFFFFFFF
    return checksum


def benchmark(seed, duration):
    started = time.perf_counter()
    tuning = load_contract()["tuning"]
    session = Session("gather", tuning, {}, seed)
    _render(session.snapshot())
    load_ms = (time.perf_counter() - started) * 1000
    warm_until = time.perf_counter() + 3.0
    while time.perf_counter() < warm_until:
        session.step(_idle())
        _render(session.snapshot())
    frame_times = []
    measured_start = time.perf_counter()
    previous = measured_start
    target = previous
    while time.perf_counter() - measured_start < duration:
        target += 1 / 61
        session.step(_idle())
        _render(session.snapshot())
        delay = target - time.perf_counter()
        if delay > 0:
            time.sleep(delay)
        now = time.perf_counter()
        frame_times.append(now - previous)
        previous = now
    measured = previous - measured_start if frame_times else 0.0
    frames = len(frame_times)
    slow_count = max(1, math.ceil(0.01 * frames)) if frames else 1
    slowest = sorted(frame_times, reverse=True)[:slow_count]
    return {"avg_fps": frames / measured if measured else 0,
            "p1_low_fps": 1 / (sum(slowest) / len(slowest)) if slowest else 0,
            "frames": frames, "measured_s": measured, "load_ms": load_ms}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="chonoi.bench")
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--duration", required=True, type=float)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.duration <= 0:
        parser.error("--duration phải > 0")
    result = benchmark(args.seed, args.duration)
    with open(args.out, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, separators=(",", ":"))
        stream.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
