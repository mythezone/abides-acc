from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from tests.trys.test_cda import replay_orders


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run standalone CDA replay using MAXE-like order book.")
    parser.add_argument("--orders", required=True, help="Path to the orders CSV.")
    parser.add_argument(
        "--snapshot",
        default=None,
        help="Optional path to an initial LOB snapshot CSV (bid_price,bid_volume,ask_price,ask_volume).",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where trade and LOB snapshot CSV files will be written.",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=5,
        help="Depth (number of levels) to include in LOB snapshots (default: 5).",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=3.0,
        help="Snapshot interval in seconds (default: 3.0).",
    )
    parser.add_argument(
        "--cancel-flag",
        type=int,
        default=2,
        help="Value in CANCEL_TYPE column that indicates a cancellation event (default: 2).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    trades_df, snapshot_df = replay_orders(
        Path(args.orders),
        snapshot_csv=Path(args.snapshot).expanduser() if args.snapshot else None,
        depth=int(args.depth),
        snapshot_interval=pd.Timedelta(seconds=float(args.interval)),
        cancel_flag=int(args.cancel_flag),
    )

    trades_path = output_dir / "trades.csv"
    lob_path = output_dir / "lob_snapshots.csv"
    trades_df.to_csv(trades_path, index=False)
    snapshot_df.to_csv(lob_path, index=False)
    print(f"Trades written to {trades_path}")
    print(f"LOB snapshots written to {lob_path}")


if __name__ == "__main__":
    main()
