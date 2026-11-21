"""Deterministic multi-day soak command."""

import argparse
import json
import time

from .contract import load_contract
from .inputs import InputState
from .runner import Session


def _input(edges=()):
    return InputState((0.0, 0.0), {name: True for name in edges}, set(edges))


def soak(seed, days):
    started = time.perf_counter()
    crashes = 0
    tuning = load_contract()["tuning"]
    session = Session("day", tuning, {}, seed, days=days)
    try:
        limit = days * 22200 + 100
        while not session.done and session.sim_tick < limit:
            phase = session.sim.phase
            if phase == "gather" and session.sim.phase_tick == 0:
                state = _input(("interact",))
            elif phase == "shop":
                state = _input(("shop_done",))
            else:
                state = _input()
            session.step(state)
    except Exception:
        crashes = 1
    return {"days": days, "days_completed": session.sim.days_completed,
            "crashes": crashes, "results": list(session.sim.results),
            "duration_s": time.perf_counter() - started}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="chonoi.soak")
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--days", required=True, type=int)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.days <= 0:
        parser.error("--days phải > 0")
    result = soak(args.seed, args.days)
    with open(args.out, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, separators=(",", ":"))
        stream.write("\n")
    return 0 if result["crashes"] == 0 and result["days_completed"] == args.days else 1


if __name__ == "__main__":
    raise SystemExit(main())
