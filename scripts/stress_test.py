import os
import sys
import json
import time
import math
import random
import tracemalloc
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pandas as pd

from core.kernel import Kernel
from core.message import new_message, MessageType


def sizeof_dir(path: str) -> int:
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def get_rss_bytes() -> int:
    try:
        import psutil

        p = psutil.Process()
        return int(p.memory_info().rss)
    except Exception:
        try:
            import resource

            rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # macOS returns bytes, Linux returns kilobytes; try to detect
            return int(rss_kb if rss_kb > 1e9 else rss_kb * 1024)
        except Exception:
            return 0


def inject_orders(
    kernel: Kernel,
    symbols,
    start_time: pd.Timestamp,
    orders: int,
    rate_per_sec: int,
    price_min=10.0,
    price_max=100.0,
    virtual_agents: int = 0,
):
    # Spread orders uniformly across simulation window determined by orders/rate
    for i in range(orders):
        ts = start_time + pd.Timedelta(seconds=(i / max(1, rate_per_sec)))
        sym = symbols[i % len(symbols)] if symbols else f"SYM{i%10:02d}"
        side = random.choice(["buy", "sell"])  # introduce both sides
        qty = random.randint(1, 100)
        price = round(random.uniform(price_min, price_max), 2)
        agent_id = "STRESS" if virtual_agents <= 0 else f"A{(i % virtual_agents):06d}"
        order = {
            "type": "limit_order",
            "symbol": sym,
            "agent_id": agent_id,
            "timestamp": str(ts),
            "side": side,
            "quantity": qty,
            "price": price,
        }
        msg = new_message(
            message_type=MessageType.SUBMIT_ORDER,
            sender_id="STRESS",
            recipient_id="Exchange",
            send_time=ts,
            recive_time=ts,
            content={"requests": [order]},
        )
        # Directly put to queue; kernel.run drains it.
        kernel.message_queue.put(msg)


def main():
    # Read config
    cfg_path = os.environ.get(
        "STRESS_CONFIG",
        os.path.join(os.path.dirname(__file__), "..", "config", "stress.json"),
    )
    with open(cfg_path, "r") as f:
        stress_cfg: Dict[str, Any] = json.load(f)

    orders_per_sec = int(stress_cfg.get("orders_per_sim_sec", 300000))
    sim_duration_sec = int(stress_cfg.get("sim_duration_sec", 60))
    sample_orders = int(stress_cfg.get("sample_orders", min(orders_per_sec, 20000)))

    kernel_cfg_path = stress_cfg.get("kernel_config_path") or os.path.join(
        os.path.dirname(__file__), "..", "config", "test.json"
    )

    # Build kernel from config
    kernel = Kernel.from_config(kernel_cfg_path)
    # Disable main log if requested
    if stress_cfg.get("disable_main_log", False):
        kernel.logger.disable_main_log = True

    # Reduce agent noise for stress: if any agents exist, we let them be; this script injects main load
    start_time = kernel.clock.now()

    # Prepare symbols: use those initialized in exchange or from config
    symbols = list(kernel.exchange.lob_dict.keys())
    if not symbols:
        symbols = stress_cfg.get("symbols", [f"S{i:04d}" for i in range(10)])
        # Initialize LOBs so that snapshots work
        from core.lob import LimitOrderBook

        for s in symbols:
            kernel.exchange.lob_dict[s] = LimitOrderBook(s)

    # Optional: configure logging frequencies
    ex_params = kernel.config.get("exchange_params", {})
    ohlc_freq = stress_cfg.get("ohlc_freq", ex_params.get("ohlc_freq", "3s"))
    lob_freq = stress_cfg.get("lob_log_freq", ex_params.get("lob_log_freq", "3s"))
    workers = int(stress_cfg.get("exchange_workers", ex_params.get("workers", 0)))
    kernel.exchange.ohlc_freq = ohlc_freq
    kernel.exchange._lob_tick_mode = str(lob_freq).lower() == "tick"
    kernel.exchange.lob_log_delta = (
        None if kernel.exchange._lob_tick_mode else pd.Timedelta(lob_freq)
    )
    if workers and workers > 0 and kernel.exchange.workers == 0:
        # Reinitialize workers if originally disabled (simple approach: no dynamic restart; warn)
        print(
            f"[warn] exchange workers were {kernel.exchange.workers}, requested {workers}. Restart recommended."
        )

    # Baseline memory
    rss_before = get_rss_bytes()
    tracemalloc.start()
    t0 = time.perf_counter()

    # Inject sample orders
    inject_orders(
        kernel,
        symbols,
        start_time=start_time,
        orders=sample_orders,
        rate_per_sec=orders_per_sec,
        virtual_agents=int(stress_cfg.get("virtual_agents", 0)),
    )

    # Run kernel until queues drain
    res = kernel.run(max_steps=sample_orders * 5)
    t1 = time.perf_counter()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rss_after = get_rss_bytes()

    # Compute metrics
    wall_elapsed = t1 - t0
    orders_processed = sample_orders
    per_order_time = wall_elapsed / max(1, orders_processed)
    rss_delta = max(0, rss_after - rss_before)
    per_order_rss = rss_delta / max(1, orders_processed)
    # use tracemalloc peak if RSS seems unrealistic (e.g., >50MB per order)
    use_tracemalloc = per_order_rss > 1 * 1024 * 1024 or rss_delta == 0
    mem_delta_bytes = peak if use_tracemalloc else rss_delta
    per_order_mem_bytes = mem_delta_bytes / max(1, orders_processed)

    # Log sizes
    log_dir = kernel.config.get("log_dir")
    total_log_size = sizeof_dir(log_dir) if log_dir else 0
    per_order_log_bytes = total_log_size / max(1, orders_processed)

    # Extrapolate to target 300k/s for 60s (18,000,000 orders)
    target_orders = orders_per_sec * sim_duration_sec
    est_time_sec = per_order_time * target_orders
    est_mem_bytes = per_order_mem_bytes * target_orders
    est_logs_bytes = per_order_log_bytes * target_orders

    def fmt_bytes(n):
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if n < 1024:
                return f"{n:.2f} {unit}"
            n /= 1024
        return f"{n:.2f} PB"

    print("--- Stress Sample Results ---")
    print(f"Orders processed: {orders_processed}")
    print(f"Wall time: {wall_elapsed:.3f} s (avg {per_order_time*1e6:.2f} us/order)")
    print(
        f"Memory delta ({'tracemalloc' if use_tracemalloc else 'RSS'}): {fmt_bytes(mem_delta_bytes)} "
        f"(avg {fmt_bytes(per_order_mem_bytes)}/order)"
    )
    print(
        f"Logs total: {fmt_bytes(total_log_size)} (avg {fmt_bytes(per_order_log_bytes)}/order)"
    )
    print("--- Extrapolated to target ---")
    print(f"Target orders: {target_orders:,}")
    print(f"Estimated wall-clock: {est_time_sec/60:.2f} minutes")
    print(f"Estimated peak/additional RSS: {fmt_bytes(est_mem_bytes)}")
    print(f"Estimated log size: {fmt_bytes(est_logs_bytes)}")

    # Ensure clean shutdown so the process can exit automatically
    try:
        kernel.shutdown()
    except Exception:
        pass


if __name__ == "__main__":
    main()
