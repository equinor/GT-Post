#!/usr/bin/env python3
"""Handle scheduler payload JSON: create per-run input/output folders and write input.ini

This script prints two shell assignments to stdout that can be eval'd by the
entrypoint to set MODEL_DIR and JOB_OUTPUT, for example:

MODEL_DIR='./<simid>/<runid>/input'
JOB_OUTPUT='./<simid>/<runid>/output'
"""
from __future__ import annotations

import json
import os
import sys
from configparser import ConfigParser
from pathlib import Path


def write_ini_files(save_dir: str, ini_params: dict) -> None:
    """Write input.ini under save_dir from ini_params.

    The ini_params is expected to be a dict of sections -> {value: ...} or similar.
    """
    save_dir = Path(save_dir)
    cfg = ConfigParser()
    for section, content in ini_params.items():
        if not cfg.has_section(section):
            cfg.add_section(section)
        if isinstance(content, dict) and "value" in content:
            cfg.set(section, "value", str(content["value"]))
        else:
            cfg.set(section, "value", str(content))

    with open(Path(save_dir) / "input.ini", "w") as fh:
        cfg.write(fh)

    


def main(payload_path: str, save_dir: str) -> int:
    p = Path(payload_path)
    if not p.exists():
        print(f"# payload file not found: {payload_path}", file=sys.stderr)
        return 1

    with p.open() as fh:
        data = json.load(fh)

    ini = data.get("ini_parameters") or data.get("iniParameters")

    sp = Path(save_dir)
    if not sp.exists():
        try:
            sp.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"# failed creating save_dir {save_dir}: {e}", file=sys.stderr)
            return 2
    
    if ini:
        try:
            write_ini_files(save_dir, ini)
        except Exception as e:
            print(f"# failed writing ini: {e}", file=sys.stderr)
            return 3

    # Dump ini to print later
    try:
        ini_json = json.dumps(ini, separators=(",", ":"))
    except Exception:
        ini_json = json.dumps(ini)

    # Shell-escape single quotes by replacing ' with '"'"'
    ini_json_safe = ini_json.replace("'", "'\"'\"'")

    print(f"export INPUT='{ini_json_safe}'")
    return 0


if __name__ == "__main__":

    # payload_handler.py <payload.json> <save_dir>
    if len(sys.argv) < 2:
        print("Usage: payload_handler.py <payload.json> [save_dir]", file=sys.stderr)
        sys.exit(1)
    payload_arg = sys.argv[1]
    save_arg = sys.argv[2]
   
    rc = main(payload_arg, save_arg)
    sys.exit(rc)
