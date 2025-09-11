#!/usr/bin/env python3
"""
Run a single Kernel simulation from a JSON config path and exit.

This small wrapper exists to isolate Singletons (Logger, ConfigManager) per process.
"""
import argparse
import sys
from core.kernel import Kernel
import os, shutil


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
        "--no_clean",
        action="store_false",
        help="If set, clean up log files from previous runs",
    )
    args = ap.parse_args()

    if args.no_clean:
        log_dir = os.path.join(
            os.path.dirname(__file__), "..", "log", "Testing Simulation"
        )
        if os.path.isdir(log_dir):
            shutil.rmtree(log_dir)
            print(f"Removed old log directory {log_dir}")

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
