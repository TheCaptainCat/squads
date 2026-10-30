"""Measure the remote client's overhead: the wall time of `sq <type> <n> show` against a running
daemon, minus the time the daemon reports for its own handler.

Usage:
    uv run python scripts/bench_remote_client.py --squad DIR --sq PATH_TO_SQ --task N \
        [--type task] [--runs 31]

The squad directory is copied to a temporary directory and a daemon is started on the copy by the
first command. The human and the `--json` form of the command run interleaved, the form that goes
first alternating from round to round; the output is the median and p25-p75 of the client overhead
for each, in milliseconds, against the budget (275 ms human, 235 ms `--json`). A run that fell back
to local mode fails the script. The daemon is stopped at the end.
"""

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

from bench_local_mode import quartiles, run_once

BUDGET_MS = {"human": 275.0, "json": 235.0}


def handler_ms(stderr: str) -> float:
    for line in stderr.splitlines():
        if line.startswith("SQUADS_SPAN handler "):
            return float(line.split()[2])
    sys.exit(f"no daemon handler time in stderr (did the command fall back?): {stderr[-300:]}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--squad", required=True, help="a directory holding the squad copy")
    parser.add_argument("--sq", required=True, help="the sq executable to measure")
    parser.add_argument("--task", type=int, required=True, help="the item number `show` runs on")
    parser.add_argument("--type", default="task", help="the item type `show` is addressed by")
    parser.add_argument("--runs", type=int, default=31)
    args = parser.parse_args()
    os.environ["SQUADS_DAEMON"] = "on"
    with tempfile.TemporaryDirectory(prefix="sq-bench-") as tmp:
        squad = Path(tmp) / "squad"
        shutil.copytree(args.squad, squad)
        forms = {
            "human": [args.type, str(args.task), "show"],
            "json": [args.type, str(args.task), "show", "--json"],
        }
        try:
            for argv in forms.values():  # the first starts the daemon; both warm the caches
                run_once(args.sq, argv, squad, spans=True)
                run_once(args.sq, argv, squad, spans=True)
            overhead: dict[str, list[float]] = {name: [] for name in forms}
            for round_ in range(args.runs):
                for name in list(forms)[:: -1 if round_ % 2 else 1]:
                    wall, err = run_once(args.sq, forms[name], squad, spans=True)
                    overhead[name].append(wall - handler_ms(err))
        finally:
            run_once(args.sq, ["daemon", "stop"], squad)
    print(f"{'form':<8}{'median':>9}{'p25':>9}{'p75':>9}{'budget':>9}   (ms, {args.runs} runs)")
    for name, values in overhead.items():
        p25, med, p75 = quartiles(values)
        verdict = "ok" if med <= BUDGET_MS[name] else "OVER"
        print(f"{name:<8}{med:>9.0f}{p25:>9.0f}{p75:>9.0f}{BUDGET_MS[name]:>9.0f}   {verdict}")


if __name__ == "__main__":
    main()
