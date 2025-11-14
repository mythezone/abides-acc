#!/usr/bin/env python3
"""
Benchmark Exchange order-processing throughput.

Generates random orders and feeds them to a single Exchange instance,
measuring wall-clock time and computing orders-per-second.

Two modes:
- direct: call Exchange._process_order() directly (single-threaded path)
- submit: send SUBMIT_ORDER messages via handle_message (can use workers)

Results are printed as JSON to stdout.
"""

from __future__ import annotations

import argparse
import json
import time
from typing import List

import numpy as np
import pandas as pd

from core.exchange import new_exchange
from core.message import MessageType, new_message
from core.order import generate_random_order, Order


def _make_exchange(
    stocks: List[str], workers: int, exchange_type: str = "SZSE"
):
    params = {
        # Minimize logging overhead during benchmark
        "ohlc_freq": "999999s",
        "lob_log_freq": "999999s",
        "lob_log_level": 0,
        "workers": int(workers or 0),
        # Relax trading rules for speed
        "fee_rate": 0.0,
        "t_plus_one": False,
        "price_limit_pct": 0.0,
        "opening_call": False,
    }
    exch = new_exchange(
        exchange_type,
        stocks=stocks,
        logger=None,  # completely disable logging inside exchange for this benchmark
        exchange_params=params,
        out_queue=None,
    )
    return exch


def _direct_mode(exch, stocks: List[str], total_orders: int) -> int:
    now = pd.Timestamp.now()
    count = 0
    # Round-robin stocks
    for i in range(total_orders):
        sym = stocks[i % len(stocks)]
        order: Order = generate_random_order(sym)
        # Ensure stock attribute is present (Exchange/LOB rely on it)
        setattr(order, "_stock", sym)
        setattr(order, "stock", sym)
        exch._process_order(now, order)  # noqa: SLF001 (intentional direct call for benchmark)
        count += 1
    return count


def _submit_mode(exch, stocks: List[str], total_orders: int, batch_size: int) -> int:
    now = pd.Timestamp.now()
    count = 0
    i = 0
    while i < total_orders:
        n = min(batch_size, total_orders - i)
        reqs = []
        for j in range(n):
            sym = stocks[(i + j) % len(stocks)]
            o = generate_random_order(sym)
            d = {
                "type": "limit_order" if hasattr(o, "price") else "market_order",
                "stock": sym,
                "agent_id": getattr(o, "agent_id", "bench"),
                "timestamp": getattr(o, "timestamp", str(now)),
                "side": getattr(o, "side", "buy"),
                "quantity": int(getattr(o, "quantity", 1)),
            }
            if hasattr(o, "price"):
                d["price"] = float(getattr(o, "price"))
            reqs.append(d)
        msg = new_message(
            message_type=MessageType.SUBMIT_ORDER,
            sender_id="bench",
            recipient_id="Exchange",
            send_time=now,
            recive_time=now,
            content={"requests": reqs},
        )
        exch.handle_message(msg)
        count += n
        i += n
    # If workers were used, ensure background tasks finish cleanly
    try:
        exch.shutdown(wait=True)
    except Exception:
        pass
    return count


def main():
    parser = argparse.ArgumentParser(description="Benchmark Exchange throughput")
    parser.add_argument("--orders", type=int, default=100_000, help="Total orders to process")
    parser.add_argument("--stocks", type=int, default=1, help="Number of stocks")
    parser.add_argument(
        "--stock-list",
        type=str,
        default="",
        help="Comma-separated stock list (overrides --stocks)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="direct",
        choices=["direct", "submit"],
        help="direct: call _process_order; submit: send SUBMIT_ORDER",
    )
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size in submit mode")
    parser.add_argument("--workers", type=int, default=0, help="Exchange worker threads (submit mode)")
    parser.add_argument(
        "--exchange",
        type=str,
        default="SZSE",
        choices=["SZSE", "NYSE"],
        help="Exchange rule-set",
    )
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    args = parser.parse_args()

    np.random.seed(args.seed)
    if args.stock_list:
        syms = [s.strip() for s in args.stock_list.split(",") if s.strip()]
    else:
        syms = [f"SYM{i+1:02d}" for i in range(max(1, int(args.stocks)))]

    exch = _make_exchange(syms, workers=args.workers if args.mode == "submit" else 0, exchange_type=args.exchange)

    t0 = time.perf_counter()
    if args.mode == "direct":
        processed = _direct_mode(exch, syms, int(args.orders))
    else:
        processed = _submit_mode(exch, syms, int(args.orders), int(args.batch_size))
    t1 = time.perf_counter()

    duration = max(1e-9, t1 - t0)
    result = {
        "mode": args.mode,
        "exchange": args.exchange,
        "workers": int(args.workers if args.mode == "submit" else 0),
        "orders": int(args.orders),
        "processed": int(processed),
        "stocks": syms,
        "duration_seconds": duration,
        "throughput_ops": float(processed / duration),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

