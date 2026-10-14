#!/usr/bin/env python3
"""Create real TSDB blocks from explicitly simulated OpenMetrics history."""
import argparse
import subprocess
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab.engine import Simulator
from lab.metrics import render


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--promtool", required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--instance", default="127.0.0.1:8090")
    args = parser.parse_args()
    if Path(args.data_dir).exists() and any(Path(args.data_dir).iterdir()):
        raise SystemExit("Seed requires an empty TSDB directory; use a fresh runtime or omit --seed.")
    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    end = int(time.time()) - 60
    start = end - 45 * 60
    simulation = Simulator(start)
    blocks = [(0, "normal"), (6, "ib_gray_failure"), (12, "normal"), (18, "roce_congestion"), (23, "normal"), (29, "thermal"), (33, "normal"), (38, "inference_overload"), (42, "normal")]
    # OpenMetrics requires each series to be contiguous in the import file.
    series = {}
    for stamp in range(start, end + 1, 15):
        minute = (stamp - start) / 60
        scenario = next(name for begin, name in reversed(blocks) if minute >= begin)
        simulation.set_scenario(scenario)
        for group in simulation.update(stamp).values():
            for sample in group:
                sample.labels.update({"job": sample.labels["source"], "instance": args.instance})
                key = (sample.name, tuple(sorted(sample.labels.items())))
                series.setdefault(key, []).append((sample, stamp))
    path = work / "history.openmetrics"
    with path.open("w") as output:
        for samples in series.values():
            for sample, stamp in samples:
                text = render([sample], timestamp=stamp)
                output.write("\n".join(line for line in text.splitlines() if not line.startswith("#")) + "\n")
        output.write("# EOF\n")
    Path(args.data_dir).mkdir(parents=True, exist_ok=True)
    subprocess.run([args.promtool, "tsdb", "create-blocks-from", "openmetrics", str(path), args.data_dir], check=True)
    print("Seeded 45 minutes of synthetic history; all sample origins are simulated.")


if __name__ == "__main__":
    main()
