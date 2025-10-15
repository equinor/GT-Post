#!/usr/bin/env python3
"""Extract simulation_id and run_id from a JSON payload file.

Usage: ./scripts/extract_ids.py /path/to/payload.json

Prints two whitespace-separated tokens: SIM_ID RUN_ID
If a key is missing, an empty string is printed in its place.
"""
import json
import sys
from pathlib import Path


def main(argv):
    if len(argv) < 2:
        print("", end=" ")
        print("")
        return 0
    p = Path(argv[1])
    if not p.is_file():
        print("", end=" ")
        print("")
        return 0
    try:
        with p.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        # On parse/read error, return empty ids
        print("", end=" ")
        print("")
        return 0

    sim = data.get("simulation_id") or data.get("simulationId") or ""
    run = data.get("run_id") or data.get("runId") or ""
    # Ensure no newlines in output
    sim = str(sim).replace("\n", " ")
    run = str(run).replace("\n", " ")
    print(f"{sim} {run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
