#!/usr/bin/env python3
"""
Analyze baseline vs. calibration log directories and report LOB MSE statistics.

This script is intended for post-processing when the baseline and calibration
runs have already completed (e.g., via run_kernel_once.py / run_calibration.py).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.calibration import (
    LOBMSEConfig,
    evaluate_directories,
    summarize_metrics,
)


def load_config(path: Optional[Path]) -> dict:
    if path is None:
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def normalize_stocks(stocks: Optional[Sequence]) -> List[str]:
    if not stocks:
        return []
    normalized: List[str] = []
    for entry in stocks:
        if isinstance(entry, str):
            normalized.append(entry)
        elif isinstance(entry, dict):
            sym = entry.get("stock")
            if sym:
                normalized.append(str(sym))
    return normalized


def infer_stocks(
    baseline_dir: Path, calibrated_dir: Path, explicit: Optional[Sequence[str]]
) -> List[str]:
    if explicit:
        return list(explicit)
    candidates = []
    for root in (baseline_dir, calibrated_dir):
        if not root.exists():
            continue
        for item in root.iterdir():
            lob_path = item / "lob.csv"
            if item.is_dir() and lob_path.exists():
                candidates.append(item.name)
    # retain stocks present in both runs
    stocks = sorted({sym for sym in candidates})
    return stocks


def write_outputs(
    metrics: List[dict],
    summary: dict,
    json_path: Optional[Path],
    csv_path: Optional[Path],
) -> None:
    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with json_path.open("w", encoding="utf-8") as fh:
            json.dump(
                {"metrics": metrics, "summary": summary},
                fh,
                ensure_ascii=False,
                indent=2,
            )
        print(f"Saved JSON metrics to {json_path}")
    if csv_path:
        import pandas as pd

        csv_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(metrics).to_csv(csv_path, index=False)
        print(f"Saved CSV metrics to {csv_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare baseline vs calibration LOB logs and report MSE metrics."
    )
    parser.add_argument(
        "--baseline",
        required=True,
        help="Path to baseline log directory (contains per-stock folders).",
    )
    parser.add_argument(
        "--calibrated",
        required=True,
        help="Path to calibrated log directory.",
    )
    parser.add_argument(
        "--config",
        help="Optional JSON config (e.g., config/calibration_results_config.json).",
    )
    parser.add_argument(
        "--stocks",
        nargs="*",
        help="Optional list of stocks to evaluate; otherwise inferred from directories.",
    )
    parser.add_argument(
        "--result-json",
        help="Optional path to write summary JSON (overrides config output).",
    )
    parser.add_argument(
        "--result-csv",
        help="Optional path to write per-stock CSV (overrides config output).",
    )
    parser.add_argument(
        "--price-weight",
        type=float,
        help="Weight for price MSE in combined score (overrides config).",
    )
    parser.add_argument(
        "--volume-weight",
        type=float,
        help="Weight for volume MSE in combined score (overrides config).",
    )
    parser.add_argument(
        "--normalization-mode",
        choices=["none", "col_wise", "pv"],
        help="Normalization mode applied before MSE (z-score).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    baseline_dir = Path(args.baseline).expanduser().resolve()
    calibrated_dir = Path(args.calibrated).expanduser().resolve()
    if not baseline_dir.exists():
        raise FileNotFoundError(f"Baseline directory not found: {baseline_dir}")
    if not calibrated_dir.exists():
        raise FileNotFoundError(f"Calibrated directory not found: {calibrated_dir}")

    config_data = load_config(Path(args.config).resolve()) if args.config else {}
    mse_cfg = config_data.get("mse", {})
    output_cfg = config_data.get("output", {})

    price_weight = (
        args.price_weight if args.price_weight is not None else mse_cfg.get("price_weight", 0.5)
    )
    volume_weight = (
        args.volume_weight if args.volume_weight is not None else mse_cfg.get("volume_weight", 0.5)
    )
    normalization_mode = args.normalization_mode or mse_cfg.get("normalization_mode", "col_wise")

    cfg = LOBMSEConfig(
        price_weight=price_weight,
        volume_weight=volume_weight,
        normalization_mode=normalization_mode,
    )

    explicit_stocks = normalize_stocks(args.stocks) if args.stocks else normalize_stocks(
        config_data.get("stocks")
    )
    stocks = infer_stocks(baseline_dir, calibrated_dir, explicit_stocks)
    if not stocks:
        raise RuntimeError("No stocks found. Specify --stocks or provide directories with lob.csv files.")

    metrics = evaluate_directories(str(baseline_dir), str(calibrated_dir), stocks, config=cfg)
    summary = summarize_metrics(metrics)

    print("=== Per-stock metrics ===")
    for entry in metrics:
        print(
            f"{entry['stock']}: price_mse={entry['price_mse']:.6f}, "
            f"volume_mse={entry['volume_mse']:.6f}, combined_mse={entry['combined_mse']:.6f}"
        )

    print("\n=== Aggregate statistics ===")
    for key, vals in summary.items():
        print(f"{key}: mean={vals['mean']:.6f}, variance={vals['variance']:.6f}")

    json_path = Path(args.result_json).expanduser() if args.result_json else None
    csv_path = Path(args.result_csv).expanduser() if args.result_csv else None
    if json_path is None and isinstance(output_cfg, dict):
        rj = output_cfg.get("result_json")
        if rj:
            json_path = (PROJECT_ROOT / rj).resolve()
        rc = output_cfg.get("result_csv")
        if rc:
            csv_path = (PROJECT_ROOT / rc).resolve()

    write_outputs(metrics, summary, json_path, csv_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
