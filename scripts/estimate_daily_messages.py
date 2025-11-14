#!/usr/bin/env python3
"""
Estimate the number of messages generated in a full trading day.

Two sampling modes:
- sim-time: run the simulator for N simulated seconds and extrapolate to 6.5h
- wall-time: run the simulator for N real seconds and extrapolate capacity

Optionally enable a heavy profile to increase agent/message volume during sampling.

Outputs a JSON summary to stdout.
"""

from __future__ import annotations

import argparse
import json

import pandas as pd

from core.kernel import Kernel
from core.message import MessageType, new_message


FULL_DAY_SECONDS = 6.5 * 3600  # 23,400 seconds


def main():
    parser = argparse.ArgumentParser(description="Estimate daily message volume")
    parser.add_argument("--config", type=str, default="config/test_agents.json", help="Config path")
    parser.add_argument("--mode", type=str, choices=["sim-time", "wall-time"], default="sim-time", help="Sampling mode")
    parser.add_argument("--sample-seconds", type=int, default=60, help="Sampling duration (seconds)")
    parser.add_argument("--heavy", action="store_true", help="Use a heavy agent profile to increase load")
    parser.add_argument("--disable-main-log", action="store_true", help="Disable main CSV message log during sampling")
    args = parser.parse_args()

    kernel = Kernel.from_config(args.config)
    if args.disable_main_log and hasattr(kernel, "logger") and kernel.logger:
        kernel.logger.disable_main_log = True

    # Optionally augment with a heavy profile to increase message volume
    if args.heavy:
        stocks = []
        try:
            stocks = list(kernel.exchange.lob_dict.keys())
            if not stocks:
                stocks = ["AAA", "BBB", "CCC", "DDD", "EEE"]
                from core.orderbook import LimitOrderBook

                for s in stocks:
                    kernel.exchange.lob_dict[s] = LimitOrderBook(s)
        except Exception:
            stocks = ["AAA", "BBB", "CCC"]
        extra_agents = [
            {"type": "zero_intelligence", "num": 50, "params": {"initial_stocks": stocks, "wakeup_ms_range": [5, 15]}},
            {"type": "noise", "num": 100, "params": {"initial_stocks": stocks, "max_batch": 5}},
            {"type": "order_book_imbalance", "num": 50, "params": {"initial_stocks": stocks, "depth": 1}},
            {"type": "hbl", "num": 50, "params": {"initial_stocks": stocks}},
            {"type": "value", "num": 50, "params": {"initial_stocks": stocks}},
            {"type": "fundamental_tracking", "num": 50, "params": {"initial_stocks": stocks}},
        ]
        kernel.init_agent(extra_agents)

    if args.mode == "sim-time":
        start = kernel.clock.now()
        res = kernel.run(max_steps=10_000_000, max_sim_seconds=int(args.sample_seconds))
        end = res.get("end_time") or kernel.clock.now()
        processed = int(res.get("processed", 0))
        sim_seconds = max(1e-9, (pd.Timestamp(end) - pd.Timestamp(start)).total_seconds())
        rate = processed / sim_seconds
        estimate = int(rate * FULL_DAY_SECONDS)
        out = {
            "config": args.config,
            "mode": args.mode,
            "heavy": bool(args.heavy),
            "sample_seconds": int(args.sample_seconds),
            "processed": processed,
            "sim_seconds": sim_seconds,
            "msg_per_simsec": rate,
            "full_day_seconds": FULL_DAY_SECONDS,
            "estimated_daily_messages": estimate,
            "kernel_now": str(kernel.clock.now()),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        kernel.shutdown()
        return

    # wall-time: run process loop by real wall-clock time
    start_time = kernel.clock.now()
    # Seed first wakeups for all agents
    for agent_id in kernel.agents.keys():
        wake = new_message(
            message_type=MessageType.WAKEUP,
            sender_id=agent_id,
            recipient_id=agent_id,
            send_time=start_time,
            recive_time=start_time,
            content={},
        )
        if hasattr(kernel, "logger") and kernel.logger:
            kernel.logger.kernel_message_log(wake, stage="SEND")
        kernel.message_queue.put(wake)
        kernel.in_box.put(wake)

    import time as _time

    t0 = _time.perf_counter()
    t_end = t0 + int(args.sample_seconds)
    total_processed = 0
    while _time.perf_counter() < t_end:
        res = kernel.process_messages(max_steps=200_000)
        total_processed += int(res.get("processed", 0))

    elapsed = max(1e-9, _time.perf_counter() - t0)
    rate = total_processed / elapsed
    estimate = int(rate * FULL_DAY_SECONDS)
    out = {
        "config": args.config,
        "mode": args.mode,
        "heavy": bool(args.heavy),
        "sample_seconds": int(args.sample_seconds),
        "processed": total_processed,
        "wall_seconds": elapsed,
        "msg_per_wallsec": rate,
        "full_day_seconds": FULL_DAY_SECONDS,
        "estimated_daily_messages": estimate,
        "kernel_now": str(kernel.clock.now()),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    kernel.shutdown()


if __name__ == "__main__":
    main()
