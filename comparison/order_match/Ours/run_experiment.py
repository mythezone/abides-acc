from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.kernel import Kernel


def run_replay(config_path: Optional[str] = None, max_steps: int = 500000) -> Path:
    """Run the historical order replay experiment using the provided config."""

    base_dir = Path(__file__).resolve().parent
    cfg_path = Path(config_path) if config_path else base_dir / "config.json"
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {cfg_path}")
    with cfg_path.open("r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    symbols = cfg.get("symbols") or []
    symbol = str(symbols[0]) if symbols else "SZ000001"
    calibration_cfg = cfg.get("calibration") or {}
    raw_dir_cfg = calibration_cfg.get("output_dir")
    if raw_dir_cfg:
        raw_path = Path(raw_dir_cfg)
        raw_log_dir = (
            raw_path if raw_path.is_absolute() else (base_dir / raw_path)
        ).resolve()
    else:
        raw_log_dir = base_dir / "raw_log"
    final_log_dir = base_dir / "log"

    # Clean previous outputs
    if raw_log_dir.exists():
        shutil.rmtree(raw_log_dir)
    if final_log_dir.exists():
        shutil.rmtree(final_log_dir)

    kernel = Kernel.from_config(str(cfg_path))
    try:
        result = kernel.run(max_steps=max_steps)
        # Drain any remaining messages until queues are empty.
        while True:
            extra = kernel.process_messages(max_steps=max_steps)
            if extra.get("processed", 0) == 0:
                break
            result["processed"] = result.get("processed", 0) + extra["processed"]
            result["steps"] = result.get("steps", 0) + extra["processed"]
            if extra.get("last_time") is not None:
                result["end_time"] = extra["last_time"]
    finally:
        kernel.shutdown()

    if raw_log_dir.exists():
        shutil.copytree(raw_log_dir, final_log_dir, dirs_exist_ok=True)
    else:
        final_log_dir.mkdir(parents=True, exist_ok=True)

    lob_path = final_log_dir / symbol / "lob.csv"
    if lob_path.exists():
        _write_mid_price_series(lob_path, final_log_dir)
    run_stats_path = final_log_dir / "run_stats.json"
    with run_stats_path.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, default=str, indent=2)
    return lob_path, final_log_dir


def _write_mid_price_series(lob_path: Path, final_log_dir: Path) -> None:
    df = pd.read_csv(lob_path)
    if {"AskPrice0", "BidPrice0"}.issubset(df.columns):
        mid = (df["AskPrice0"].astype(float) + df["BidPrice0"].astype(float)) / 2.0
        out = pd.DataFrame({"kernel_time": df["kernel_time"], "mid_price": mid})
        out.to_csv(final_log_dir / "mid_price.csv", index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the historical order replay experiment.")
    parser.add_argument(
        "--config",
        dest="config",
        default=None,
        help="Path to the experiment configuration JSON file.",
    )
    parser.add_argument(
        "--max-steps",
        dest="max_steps",
        type=int,
        default=500000,
        help="Maximum number of kernel steps to execute.",
    )
    args = parser.parse_args()
    lob_csv, log_dir = run_replay(args.config, max_steps=args.max_steps)
    print(f"Kernel run stats written to: {log_dir / 'run_stats.json'}")
    print(f"LOB snapshot log written to: {lob_csv}")
