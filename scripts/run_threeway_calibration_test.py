#!/usr/bin/env python3
"""
Run two baseline simulations with the same parameters (different seeds) and one calibration run
based on the first run. Then produce multi-run comparison visualizations and metrics.

This orchestrator spawns separate processes per run to avoid Singleton cross-run state.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from typing import Optional, Dict


def _ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)


def _write_config(base_cfg_path: str, out_cfg_path: str, *, kernel_name: Optional[str] = None, calibration: Optional[Dict] = None):
    with open(base_cfg_path, "r") as f:
        cfg = json.load(f)
    if kernel_name:
        cfg.setdefault("kernel", {}).setdefault("name", kernel_name)
        cfg["kernel"]["name"] = kernel_name
    if calibration is not None:
        cfg["calibration"] = calibration
    with open(out_cfg_path, "w") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def _python_exec() -> str:
    # Prefer python3, fallback to python
    for exe in ("python3", "python"):
        if shutil.which(exe):
            return exe
    return "python"


def run_kernel_once(config_path: str, max_steps: int):
    exe = _python_exec()
    cmd = [exe, os.path.join(os.path.dirname(__file__), "run_kernel_once.py"), "--config", config_path, "--max_steps", str(max_steps)]
    print("[run]", " ".join(cmd))
    subprocess.check_call(cmd)


def main():
    ap = argparse.ArgumentParser(description="Run two sims + one calibration, then compare")
    ap.add_argument("--config", default=os.path.join(os.path.dirname(__file__), "..", "config", "test.json"), help="Base kernel config JSON")
    ap.add_argument("--out_root", required=True, help="Output root directory for all runs and reports")
    ap.add_argument("--max_steps", type=int, default=20000, help="Max steps per run (used when --sim_seconds is not provided)")
    ap.add_argument("--sim_seconds", type=int, default=None, help="Simulated time horizon in seconds for all runs")
    ap.add_argument("--symbols", default="", help="Comma-separated symbols to plot; default=intersection")
    ap.add_argument("--tolerance", default="2s", help="Time tolerance for alignment in viz")
    ap.add_argument("--lob_levels", type=int, default=10, help="LOB levels for metrics")
    args = ap.parse_args()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_root = os.path.abspath(args.out_root)
    _ensure_dir(out_root)
    tmp_cfg_dir = os.path.join(out_root, "tmp_cfg")
    _ensure_dir(tmp_cfg_dir)

    # Paths per run
    runA_name = f"RunA_{ts}"
    runB_name = f"RunB_{ts}"
    calib_name = f"Calib_{ts}"
    runA_dir = os.path.join(out_root, runA_name)
    runB_dir = os.path.join(out_root, runB_name)
    calib_dir = os.path.join(out_root, calib_name)

    # Configs per run
    cfgA = os.path.join(tmp_cfg_dir, f"cfg_{runA_name}.json")
    cfgB = os.path.join(tmp_cfg_dir, f"cfg_{runB_name}.json")
    cfgC = os.path.join(tmp_cfg_dir, f"cfg_{calib_name}.json")

    # Write configs: set kernel name and force log_dir under out_root via calibration.output_dir override
    _write_config(args.config, cfgA, kernel_name=runA_name, calibration={
        "output_dir": runA_dir
    })
    _write_config(args.config, cfgB, kernel_name=runB_name, calibration={
        "output_dir": runB_dir
    })
    _write_config(args.config, cfgC, kernel_name=calib_name, calibration={
        "enabled": True,
        "source_log_dir": runA_dir,
        "output_dir": calib_dir
    })

    # Run A, B, C sequentially
    def _run(cfg):
        exe = _python_exec()
        cmd = [exe, os.path.join(os.path.dirname(__file__), "run_kernel_once.py"), "--config", cfg]
        if args.sim_seconds is not None:
            cmd += ["--sim_seconds", str(int(args.sim_seconds)), "--max_steps", str(max(1, args.max_steps))]
        else:
            cmd += ["--max_steps", str(int(args.max_steps))]
        print("[run]", " ".join(cmd))
        subprocess.check_call(cmd)

    _run(cfgA)
    _run(cfgB)
    _run(cfgC)

    # Visualization: Multi-run (truth=RunA, groups=RunB, Calib)
    exe = _python_exec()
    # Use the safer viz v2 (no fragile string interpolation in JS)
    viz = os.path.join(os.path.dirname(__file__), "multi_run_viz2.py")
    cmd = [exe, viz, "--truth_dir", runA_dir, "--group", f"RunB={runB_dir}", "--group", f"Calib={calib_dir}", "--out_dir", os.path.join(out_root, f"report_{ts}"), "--tolerance", args.tolerance, "--lob_levels", str(args.lob_levels)]
    if args.symbols.strip():
        cmd += ["--symbols", args.symbols]
    print("[viz]", " ".join(cmd))
    subprocess.check_call(cmd)


if __name__ == "__main__":
    sys.exit(main())
