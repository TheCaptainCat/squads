"""Measure the CLI shim's overhead: the wall time of a command run against a live daemon, minus the
time the daemon reports for its own handler.

Usage:
    uv run python scripts/bench_remote_client.py --squad DIR --sq PATH_TO_SQ --task N \
        [--type task] [--runs 31]

The squad directory is copied to a temporary directory and a daemon is started on the copy by the
first command. Three commands run interleaved, the one that goes first rotating from round to
round: `<type> <n> show`, `list --json` and a bash completion of `<type> <n> `. The output is the
median and p25-p75 of the shim's overhead for each, in milliseconds, against the budget of 100 ms
on the reference host, with the load average at the start and the end. A run that fell back to
local mode fails the script. The daemon is stopped at the end.
"""

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

from bench_local_mode import quartiles, run_once

#: Milliseconds of shim overhead a release allows, measured on the CI job's Linux runner.
BUDGET_MS = 100.0


def handler_ms(stderr: str) -> float:
    for line in stderr.splitlines():
        if line.startswith("SQUADS_SPAN handler "):
            return float(line.split()[2])
    sys.exit(f"no daemon handler time in stderr (did the command fall back?): {stderr[-300:]}")


def commands(kind: str, task: int) -> dict[str, tuple[list[str], dict[str, str]]]:
    """Each measured command: its arguments and the environment it adds."""
    return {
        "show": ([kind, str(task), "show"], {}),
        "list --json": (["list", "--json"], {}),
        "bash completion": (
            [],
            {
                "_SQ_COMPLETE": "complete_bash",
                "COMP_WORDS": f"sq {kind} {task} ",
                "COMP_CWORD": "3",
            },
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--squad", required=True, help="a directory holding the squad copy")
    parser.add_argument("--sq", required=True, help="the sq executable to measure")
    parser.add_argument("--task", type=int, required=True, help="the item number `show` runs on")
    parser.add_argument("--type", default="task", help="the item type `show` is addressed by")
    parser.add_argument("--runs", type=int, default=31)
    args = parser.parse_args()
    os.environ["SQUADS_DAEMON"] = "on"
    load_before = os.getloadavg()
    with tempfile.TemporaryDirectory(prefix="sq-bench-") as tmp:
        squad = Path(tmp) / "squad"
        shutil.copytree(args.squad, squad)
        forms = commands(args.type, args.task)
        try:
            for argv, extra in forms.values():  # the first starts the daemon; all warm the caches
                run_once(args.sq, argv, squad, spans=True, extra_env=extra)
                run_once(args.sq, argv, squad, spans=True, extra_env=extra)
            overhead: dict[str, list[float]] = {name: [] for name in forms}
            for round_ in range(args.runs):
                names = list(forms)
                turn = round_ % len(names)
                for name in names[turn:] + names[:turn]:
                    argv, extra = forms[name]
                    wall, err = run_once(args.sq, argv, squad, spans=True, extra_env=extra)
                    overhead[name].append(wall - handler_ms(err))
        finally:
            run_once(args.sq, ["daemon", "stop"], squad)
    load_after = os.getloadavg()
    print(f"{'form':<18}{'median':>9}{'p25':>9}{'p75':>9}{'budget':>9}   (ms, {args.runs} runs)")
    for name, values in overhead.items():
        p25, med, p75 = quartiles(values)
        verdict = "ok" if med <= BUDGET_MS else "OVER"
        print(f"{name:<18}{med:>9.0f}{p25:>9.0f}{p75:>9.0f}{BUDGET_MS:>9.0f}   {verdict}")
    print(f"load average  before: {load_before}  after: {load_after}")


if __name__ == "__main__":
    main()
