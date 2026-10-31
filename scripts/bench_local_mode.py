"""Compare local-mode run time of two `sq` builds on one squad, and break a build's run into spans.

Usage:
    uv run python scripts/bench_local_mode.py --squad DIR --old PATH_TO_RELEASED_SQ \
        --new PATH_TO_DEV_SQ --task N [--runs 31] [--spans]

The squad directory is copied to a temporary directory first. Each command runs interleaved
against that copy, the build that goes first alternating from round to round. The default output
is the median and p25-p75 wall time in milliseconds per command and build; `--spans` prints the
median of each span the dev build reports instead.
"""

import argparse
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path


def commands(task: int) -> dict[str, list[str]]:
    return {"show": ["task", str(task), "show"], "list": ["list"], "tree": ["tree"]}


def run_once(
    sq: str,
    args: list[str],
    squad: Path,
    *,
    spans: bool = False,
    extra_env: dict[str, str] | None = None,
) -> tuple[float, str]:
    env = {**os.environ, "NO_COLOR": "1", **(extra_env or {})}
    env.pop("FORCE_COLOR", None)
    env.pop("SQUADS_SPANS", None)
    if spans:
        env["SQUADS_SPANS"] = f"t={time.perf_counter()!r}"
    start = time.perf_counter()
    done = subprocess.run(
        [sq, *args], cwd=squad, env=env, capture_output=True, text=True, check=False
    )
    elapsed = (time.perf_counter() - start) * 1000
    if done.returncode != 0:
        sys.exit(f"{sq} {' '.join(args)} exited {done.returncode}: {done.stderr[-400:]}")
    return elapsed, done.stderr


def quartiles(values: list[float]) -> tuple[float, float, float]:
    q = statistics.quantiles(values, n=4, method="inclusive")
    return q[0], statistics.median(values), q[2]


def compare(args: argparse.Namespace) -> None:
    squad = args.squad_copy
    builds = {"old": args.old, "new": args.new}
    print(f"{'command':<8}{'build':<6}{'median':>9}{'p25':>9}{'p75':>9}   (ms, {args.runs} runs)")
    for name, argv in commands(args.task).items():
        for sq in builds.values():  # one warm-up each, so file caches are equal
            run_once(sq, argv, squad)
        times: dict[str, list[float]] = defaultdict(list)
        for round_ in range(args.runs):
            order = list(builds.items())[:: -1 if round_ % 2 else 1]
            for label, sq in order:
                times[label].append(run_once(sq, argv, squad)[0])
        for label in builds:
            p25, med, p75 = quartiles(times[label])
            print(f"{name:<8}{label:<6}{med:>9.0f}{p25:>9.0f}{p75:>9.0f}")
        ratio = statistics.median(times["new"]) / statistics.median(times["old"])
        print(f"{name:<8}new/old median = {ratio:.3f}")


def span_breakdown(args: argparse.Namespace) -> None:
    squad = args.squad_copy
    for name, argv in commands(args.task).items():
        run_once(args.new, argv, squad, spans=True)
        seen: dict[str, list[float]] = defaultdict(list)
        totals: list[float] = []
        for _ in range(args.runs):
            total, err = run_once(args.new, argv, squad, spans=True)
            totals.append(total)
            for line in err.splitlines():
                if line.startswith("SQUADS_SPAN "):
                    _, span, value = line.split()
                    seen[span].append(float(value))
        print(f"\n{name}: median wall {statistics.median(totals):.0f} ms")
        for span, values in seen.items():
            print(f"  {span:<16}{statistics.median(values):>9.1f} ms")
        if seen["end"]:
            tail = statistics.median(totals) - statistics.median(seen["end"])
            print(f"  {'exit (after end)':<16}{tail:>9.1f} ms")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--squad", required=True, help="a directory holding the squad copy")
    parser.add_argument("--old", required=True, help="the released sq executable")
    parser.add_argument("--new", required=True, help="the dev tree's sq executable")
    parser.add_argument("--runs", type=int, default=31)
    parser.add_argument("--task", type=int, required=True, help="the item number `show` runs on")
    parser.add_argument("--spans", action="store_true", help="print the dev build's span medians")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="sq-bench-") as tmp:
        args.squad_copy = Path(tmp) / "squad"
        shutil.copytree(args.squad, args.squad_copy)
        (span_breakdown if args.spans else compare)(args)


if __name__ == "__main__":
    main()
