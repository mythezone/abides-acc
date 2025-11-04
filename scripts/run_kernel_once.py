#!/usr/bin/env python3
"""
Run a single Kernel simulation from a JSON config path and exit.

This small wrapper exists to isolate Singletons (Logger, ConfigManager) per process.
"""
# Get the project root and add it at the begining of the path.
import sys
import json
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


import argparse
import json
import os
import shutil
from typing import Optional

from core.kernel import Kernel


def _resolve_log_dir(config_path: Path) -> Optional[Path]:
    try:
        with config_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return None
    kernel_cfg = data.get("kernel", {}) if isinstance(data, dict) else {}
    log_dir = kernel_cfg.get("log_dir")
    if not log_dir:
        name = kernel_cfg.get("name", "Simulation")
        log_dir = f"log/{name}"
    log_path = Path(log_dir)
    if not log_path.is_absolute():
        log_path = (project_root / log_path).resolve()
    return log_path


def main():
    ap = argparse.ArgumentParser(description="Run one simulation and exit")
    ap.add_argument("--config", required=True, help="Path to JSON config file")
    ap.add_argument(
        "--max_steps",
        type=int,
        default=10000,
        help="Max steps for kernel.run() (ignored if --sim_seconds is set)",
    )
    ap.add_argument(
        "--sim_seconds",
        type=int,
        default=None,
        help="Simulated time horizon in seconds; if set, overrides --max_steps",
    )
    ap.add_argument(
        "--clean",
        action="store_true",
        help="Remove the configured log directory before running.",
    )
    args = ap.parse_args()

    if args.clean:
        log_dir = _resolve_log_dir(Path(args.config))
        if log_dir and log_dir.exists():
            shutil.rmtree(log_dir)
            print(f"[run_kernel_once] Removed existing log directory {log_dir}")

    kernel = Kernel.from_config(args.config)
    if args.sim_seconds is not None:
        kernel.run(
            max_steps=max(1, args.max_steps), max_sim_seconds=int(args.sim_seconds)
        )
    else:
        kernel.run(max_steps=args.max_steps)
    kernel.shutdown()


if __name__ == "__main__":
    sys.exit(main())
