#!/usr/bin/env python3
"""Sample ABIDES LOB snapshots at a fixed interval.

Loads a `lob.csv` file produced by the replay script and selects the first
snapshot observed on or after every interval boundary (default 3 seconds).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Down-sample ABIDES LOB snapshots")
    parser.add_argument("input", type=Path, help="Path to lob.csv")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Destination CSV (defaults to <input>_sampled.csv)",
    )
    parser.add_argument(
        "--freq",
        type=str,
        default="3S",
        help="Sampling interval in pandas offset alias format (default: 3S)",
    )
    return parser.parse_args()


def load_lob(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "timestamp" not in df.columns:
        raise ValueError("CSV missing required 'timestamp' column")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
    if df.empty:
        raise ValueError("No valid timestamp rows found in input")
    return df.reset_index(drop=True)


def sample_first_after_boundaries(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    first_ts = df["timestamp"].iloc[0]
    start = first_ts.floor(freq)
    end = df["timestamp"].iloc[-1]
    boundaries = pd.DataFrame({"boundary": pd.date_range(start=start, end=end, freq=freq)})

    sampled = pd.merge_asof(
        boundaries,
        df,
        left_on="boundary",
        right_on="timestamp",
        direction="forward",
        allow_exact_matches=True,
    )

    sampled = sampled.dropna(subset=["timestamp"]).copy()

    if sampled.empty or sampled.iloc[0]["timestamp"] != first_ts:
        sampled = pd.concat([df.iloc[[0]], sampled[df.columns]], ignore_index=True)

    sampled = sampled[df.columns].drop_duplicates(subset=["timestamp"], keep="first")
    sampled.reset_index(drop=True, inplace=True)
    return sampled


def main() -> None:
    args = parse_args()
    input_path = args.input
    output_path = args.output or input_path.with_name(f"{input_path.stem}_sampled.csv")

    df = load_lob(input_path)
    sampled = sample_first_after_boundaries(df, args.freq)
    sampled.to_csv(output_path, index=False)
    print(f"Wrote sampled LOB to {output_path}")


if __name__ == "__main__":
    main()
