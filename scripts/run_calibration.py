import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.kernel import Kernel


def _resolve_log_dir(config_path: Path) -> Path:
    with config_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    kernel_cfg = data.get("kernel", {})
    log_dir = kernel_cfg.get("log_dir")
    if not log_dir:
        name = kernel_cfg.get("name", "CalibrationRun")
        log_dir = f"log/{name}"
    return (config_path.parent / log_dir).resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a calibration-enabled simulation from a config file.")
    parser.add_argument(
        "--config",
        default=os.environ.get("CALIB_CONFIG", os.path.join(os.path.dirname(__file__), "..", "config", "calibration.json")),
        help="Path to calibration JSON config.",
    )
    parser.add_argument("--max-steps", type=int, default=20000, help="Maximum kernel steps.")
    parser.add_argument("--sim-seconds", type=int, default=None, help="Optional simulated time horizon (seconds).")
    parser.add_argument("--clean", action="store_true", help="Remove the configured log directory before running.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg_path = Path(args.config).resolve()
    if args.clean:
        log_dir = _resolve_log_dir(cfg_path)
        if log_dir.exists():
            import shutil

            shutil.rmtree(log_dir)
            print(f"[run_calibration] Removed log directory {log_dir}")

    kernel = Kernel.from_config(str(cfg_path))
    start = time.perf_counter()
    if args.sim_seconds is not None:
        res = kernel.run(max_steps=max(1, args.max_steps), max_sim_seconds=int(args.sim_seconds))
    else:
        res = kernel.run(max_steps=args.max_steps)
    elapsed = time.perf_counter() - start
    kernel.shutdown()
    processed = res.get("processed")
    end_time = res.get("end_time")
    steps = res.get("steps")
    print(
        f"[run_calibration] Finished in {elapsed:.2f}s | processed={processed} steps={steps} end_time={end_time} | "
        f"kernel.total_processed={kernel.total_processed_messages}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
