import os
import sys
import argparse
import pandas as pd
import matplotlib.pyplot as plt


def load_series(log_dir: str, stock: str, kind: str = "ohlc"):
    f = os.path.join(log_dir, stock, f"{kind}.csv")
    if not os.path.exists(f):
        return None
    df = pd.read_csv(f)
    if "kernel_time" not in df.columns:
        return None
    df["kernel_time"] = pd.to_datetime(df["kernel_time"]) 
    df = df.sort_values("kernel_time")
    return df


def compare_stock(src_dir: str, cal_dir: str, stock: str, out_dir: str, kind: str = "ohlc"):
    a = load_series(src_dir, stock, kind)
    b = load_series(cal_dir, stock, kind)
    if a is None or b is None:
        print(f"[skip] missing data for {stock} kind={kind}")
        return
    # align on time
    key = "close" if kind == "ohlc" else None
    if kind == "ohlc" and key in a.columns and key in b.columns:
        merged = pd.merge_asof(a[["kernel_time", key]].sort_values("kernel_time"), b[["kernel_time", key]].sort_values("kernel_time"), on="kernel_time", direction="nearest", suffixes=("_src", "_cal"))
        merged.dropna(inplace=True)
        merged["abs_err"] = (merged[f"{key}_src"] - merged[f"{key}_cal"]).abs()
        mae = merged["abs_err"].mean()
        os.makedirs(out_dir, exist_ok=True)
        plt.figure(figsize=(10,4))
        plt.plot(merged["kernel_time"], merged[f"{key}_src"], label="src")
        plt.plot(merged["kernel_time"], merged[f"{key}_cal"], label="cal")
        plt.legend(); plt.title(f"{stock} {kind} compare (MAE={mae:.4f})")
        plt.tight_layout()
        outp = os.path.join(out_dir, f"{stock}_{kind}.png")
        plt.savefig(outp)
        plt.close()
        print(f"[ok] {stock} {kind} MAE={mae:.4f} -> {outp}")
    else:
        print(f"[skip] unsupported kind or columns for {stock}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True, help="source log dir (first run)")
    parser.add_argument("--cal", required=True, help="calibration log dir (second run)")
    parser.add_argument("--stocks", nargs="*", default=[])
    parser.add_argument("--out", default="calibration_plots")
    args = parser.parse_args()

    stocks = args.stocks
    if not stocks:
        # infer from directories
        stocks = [d for d in os.listdir(args.src) if os.path.isdir(os.path.join(args.src, d))]

    for s in stocks:
        compare_stock(args.src, args.cal, s, args.out, kind="ohlc")


if __name__ == "__main__":
    main()

