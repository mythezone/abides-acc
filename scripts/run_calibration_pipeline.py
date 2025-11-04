#!/usr/bin/env python3
"""
Run a two-phase simulation pipeline:
  1. Baseline simulation without calibration (records historical LOBs)
  2. Calibration simulation using baseline logs as oracle data

After both runs, compute normalized MSE metrics between baseline and calibrated
LOB logs (per symbol and aggregated).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.calibration import LOBMSEConfig, evaluate_directories, summarize_metrics


def _load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_temp_config(cfg: Dict) -> Path:
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(cfg, tmp, ensure_ascii=False, indent=2)
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


def _ensure_log_dir(cfg: Dict, fallback_name: str, override: Optional[Path], force: bool) -> Path:
    kernel_cfg = cfg.setdefault("kernel", {})
    log_dir_value = override or Path(kernel_cfg.get("log_dir") or f"log/{fallback_name}")
    log_dir = Path(log_dir_value)
    if not log_dir.is_absolute():
        log_dir = (PROJECT_ROOT / log_dir).resolve()
    kernel_cfg["log_dir"] = str(log_dir)
    if force and log_dir.exists():
        shutil.rmtree(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _prepare_baseline_config(cfg: Dict) -> Dict:
    calib_cfg = cfg.get("calibration")
    if calib_cfg:
        calib_cfg["enabled"] = False
    else:
        cfg["calibration"] = {"enabled": False}
    return cfg


def _prepare_calibration_config(cfg: Dict, source_log_dir: Path, output_dir: Path) -> Dict:
    calib_cfg = cfg.setdefault("calibration", {})
    calib_cfg["enabled"] = True
    calib_cfg["source_log_dir"] = str(source_log_dir)
    calib_cfg.setdefault("lob_levels", 10)
    out_path = output_dir if output_dir.is_absolute() else (PROJECT_ROOT / output_dir).resolve()
    calib_cfg["output_dir"] = str(out_path)
    kernel_cfg = cfg.setdefault("kernel", {})
    kernel_cfg["log_dir"] = str(out_path)
    return cfg


def _run_simulation(config_path: Path, max_steps: int, sim_seconds: Optional[int]) -> None:
    runner = PROJECT_ROOT / "scripts" / "run_kernel_once.py"
    cmd = [sys.executable, str(runner), "--config", str(config_path), "--max_steps", str(max_steps)]
    if sim_seconds is not None:
        cmd.extend(["--sim_seconds", str(sim_seconds)])
    subprocess.run(cmd, check=True)


def parse_args() -> argparse.Namespace:
    now_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    parser = argparse.ArgumentParser(description="Run baseline + calibration simulations and compute LOB MSE.")
    parser.add_argument("--baseline-config", required=True, help="JSON config for baseline run (calibration disabled automatically).")
    parser.add_argument("--calibration-config", required=True, help="JSON config for calibration run.")
    parser.add_argument("--max-steps", type=int, default=20000, help="Max steps for each simulation run.")
    parser.add_argument("--sim-seconds", type=int, default=None, help="Optional simulated seconds horizon.")
    parser.add_argument("--baseline-log-dir", type=Path, help="Override log dir for baseline run.")
    parser.add_argument("--calibrated-log-dir", type=Path, help="Override log dir for calibration run.")
    parser.add_argument("--force", action="store_true", help="Force removal of existing log directories.")
    parser.add_argument("--symbols", nargs="*", help="Explicit symbol list for evaluation.")
    parser.add_argument("--price-weight", type=float, default=0.5, help="Weight for price MSE in combined score.")
    parser.add_argument("--volume-weight", type=float, default=0.5, help="Weight for volume MSE in combined score.")
    parser.add_argument("--price-norm", default="max", choices=["max", "mean", "std", "none"], help="Normalization method for price columns.")
    parser.add_argument("--volume-norm", default="max", choices=["max", "mean", "std", "none"], help="Normalization method for volume columns.")
    parser.add_argument("--result-json", type=Path, help="Optional path to write metrics JSON.")
    parser.add_argument("--result-csv", type=Path, help="Optional path to write per-symbol metrics CSV.")
    parser.add_argument("--tag", default=now_tag, help="Run tag appended to default log dir if overrides not provided.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    baseline_cfg = _load_json(Path(args.baseline_config))
    baseline_name = baseline_cfg.get("kernel", {}).get("name", "Baseline")
    baseline_log = _ensure_log_dir(
        _prepare_baseline_config(baseline_cfg),
        f"{baseline_name}_{args.tag}",
        args.baseline_log_dir,
        args.force,
    )

    cal_cfg = _load_json(Path(args.calibration_config))
    cal_name = cal_cfg.get("kernel", {}).get("name", "Calibration")
    calibrated_log = _ensure_log_dir(
        _prepare_calibration_config(cal_cfg, baseline_log, args.calibrated_log_dir or Path(f"log/{cal_name}_{args.tag}")),
        f"{cal_name}_{args.tag}",
        args.calibrated_log_dir,
        args.force,
    )

    # Baseline run
    base_cfg_path = _write_temp_config(baseline_cfg)
    try:
        _run_simulation(base_cfg_path, args.max_steps, args.sim_seconds)
    finally:
        base_cfg_path.unlink(missing_ok=True)

    # Calibration run
    cal_cfg_path = _write_temp_config(cal_cfg)
    try:
        _run_simulation(cal_cfg_path, args.max_steps, args.sim_seconds)
    finally:
        cal_cfg_path.unlink(missing_ok=True)

    # Identify symbols to evaluate
    if args.symbols:
        symbols = args.symbols
    else:
        symbols = cal_cfg.get("symbols") or baseline_cfg.get("symbols") or []
        if symbols:
            normalized = []
            for s in symbols:
                if isinstance(s, str):
                    normalized.append(s)
                elif isinstance(s, dict):
                    sym_val = s.get("symbol")
                    if sym_val:
                        normalized.append(str(sym_val))
            symbols = normalized
        if not symbols:
            symbols = [
                p.name
                for p in baseline_log.iterdir()
                if p.is_dir() and (baseline_log / p / "lob.csv").exists()
            ]

    cfg = LOBMSEConfig(
        price_weight=args.price_weight,
        volume_weight=args.volume_weight,
        price_norm=args.price_norm,
        volume_norm=args.volume_norm,
    )
    metrics = evaluate_directories(str(baseline_log), str(calibrated_log), symbols, config=cfg)
    summary = summarize_metrics(metrics)

    print("=== Per-symbol metrics ===")
    for entry in metrics:
        print(
            f"{entry['symbol']}: price_mse={entry['price_mse']:.6f}, "
            f"volume_mse={entry['volume_mse']:.6f}, combined_mse={entry['combined_mse']:.6f}"
        )

    print("\n=== Aggregate statistics ===")
    for key, vals in summary.items():
        print(f"{key}: mean={vals['mean']:.6f}, variance={vals['variance']:.6f}")

    if args.result_json:
        args.result_json.parent.mkdir(parents=True, exist_ok=True)
        with args.result_json.open("w", encoding="utf-8") as fh:
            json.dump(
                {
                    "baseline_log_dir": str(baseline_log),
                    "calibrated_log_dir": str(calibrated_log),
                    "symbols": symbols,
                    "metrics": metrics,
                    "summary": summary,
                },
                fh,
                ensure_ascii=False,
                indent=2,
            )
        print(f"Saved metrics JSON to {args.result_json}")

    if args.result_csv:
        import pandas as pd

        args.result_csv.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(metrics).to_csv(args.result_csv, index=False)
        print(f"Saved metrics CSV to {args.result_csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
