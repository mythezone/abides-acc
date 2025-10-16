from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd



CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[3]
EXPERIMENT_DIR = PROJECT_ROOT / "log" 
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.kernel import Kernel


def load_config(config_path: str) -> Tuple[Dict, Path]:
    cfg_path = Path(config_path).expanduser().resolve()
    if not cfg_path.is_file():
        raise FileNotFoundError(f"Config file not found: {cfg_path}")

    with cfg_path.open("r", encoding="utf-8") as fh:
        cfg = json.load(fh)

    symbols = cfg.get("symbols")
    if not symbols:
        raise ValueError("Config must define a non-empty 'symbols' list.")

    calibration = cfg.get("calibration")
    if not isinstance(calibration, dict) or not calibration.get("output_dir"):
        raise ValueError("Config must define 'calibration.output_dir'.")

    return cfg, cfg_path


def run_replay(config_path: str, max_steps: int = 500_000) -> Tuple[Path, Path]:
    cfg, cfg_path = load_config(config_path)

    output_dir = Path(cfg["calibration"]["output_dir"]).expanduser().resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    kernel = Kernel.from_config(str(cfg_path))
    try:
        result = kernel.run(max_steps=max_steps)
        while True:
            extra = kernel.process_messages(max_steps=max_steps)
            if extra.get("processed", 0) == 0:
                break
            result["processed"] = result.get("processed", 0) + extra["processed"]
            result["steps"] = result.get("steps", 0) + extra["processed"]
            if extra.get("last_time") is not None:
                result["end_time"] = extra["last_time"]
        print(f"Kernel run complete. Steps processed: {result.get('steps', 0)}")
    finally:
        kernel.shutdown()

    symbol = str(cfg["symbols"][0])
    lob_path = EXPERIMENT_DIR / symbol / "lob.csv"
    if not lob_path.exists():
        raise FileNotFoundError(f"LOB file not found at expected location: {lob_path}")

    mid_price_path = output_dir / "mid_price.csv"
    _write_mid_price_series(lob_path, mid_price_path)

    run_stats_path = output_dir / "run_stats.json"
    with run_stats_path.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, default=str, indent=2)

    return lob_path, output_dir


def _write_mid_price_series(lob_path: Path, output_path: Path) -> None:
    df = pd.read_csv(lob_path)
    required_cols = {"AskPrice0", "BidPrice0"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"LOB file {lob_path} is missing columns {required_cols}.")

    mid = (df["AskPrice0"].astype(float) + df["BidPrice0"].astype(float)) / 2.0
    out = pd.DataFrame({"kernel_time": df["kernel_time"], "mid_price": mid})
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the historical order replay experiment."
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to the experiment configuration JSON file.",
    )
    parser.add_argument(
        "--max-steps",
        dest="max_steps",
        type=int,
        default=500_000,
        help="Maximum number of kernel steps to execute.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    lob_csv, output_dir = run_replay(args.config, max_steps=args.max_steps)
    print(f"Run statistics written to: {output_dir / 'run_stats.json'}")
    print(f"Mid-price series written to: {output_dir / 'mid_price.csv'}")
    print(f"LOB snapshot log located at: {lob_csv}")
