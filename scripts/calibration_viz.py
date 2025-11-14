#!/usr/bin/env python3
"""
Compare a Calibration run against reference (ground-truth) logs and visualize differences.

Inputs are two log directories with the structure produced by core.logger.Logger:

<LOG_DIR>/
  <SYMBOL>/ohlc.csv     (columns: kernel_time, open, high, low, close, volume)
  <SYMBOL>/lob.csv      (columns: kernel_time, AskPrice0.., AskVolume0.., BidPrice0.., BidVolume0..)

Outputs:
- metrics.csv: per-stock MSE/MAE for OHLC (per field and averaged) and LOB top-N
- overview.txt: quick summary with overall averages
- plots/*.png: per-stock plots for OHLC (candles) and top-of-book (best bid/ask)
- index.html: simple HTML report linking the above
"""

import argparse
import os
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.dates import date2num
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle


def _ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)


def _list_stocks(log_dir: str) -> List[str]:
    if not log_dir or not os.path.isdir(log_dir):
        return []
    return [d for d in os.listdir(log_dir) if os.path.isdir(os.path.join(log_dir, d))]


def _load_ohlc(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path)
    if "kernel_time" not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df["kernel_time"] = pd.to_datetime(df["kernel_time"]).astype("datetime64[ns]")
    df = df.sort_values("kernel_time").drop_duplicates(subset=["kernel_time"]).reset_index(drop=True)
    # Forward-fill close to avoid line breaks in overlays; keep OHLC as-is for candles
    if "close" in df.columns:
        df["close"] = pd.to_numeric(df["close"], errors="coerce").ffill()
    return df


def _load_lob(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_csv(path)
    if "kernel_time" not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df["kernel_time"] = pd.to_datetime(df["kernel_time"]).astype("datetime64[ns]")
    # coerce numeric for price/volume-like columns
    for c in df.columns:
        if c == "kernel_time":
            continue
        df[c] = pd.to_numeric(df[c], errors="coerce")
    # Forward-fill price levels to reduce mid-price discontinuities
    price_cols = [c for c in df.columns if c.startswith("BidPrice") or c.startswith("AskPrice")]
    if price_cols:
        df[price_cols] = df[price_cols].ffill()
    df = df.sort_values("kernel_time").drop_duplicates(subset=["kernel_time"]).reset_index(drop=True)
    return df


def _merge_nearest(a: pd.DataFrame, b: pd.DataFrame, on: str, tol: pd.Timedelta) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if a.empty or b.empty:
        return a.iloc[0:0], b.iloc[0:0]
    a2 = a[[on]].copy()
    b2 = b[[on]].copy()
    a2["__idx_a"] = np.arange(len(a2))
    b2["__idx_b"] = np.arange(len(b2))
    j = pd.merge_asof(a2, b2, on=on, direction="nearest", tolerance=tol)
    j = j.dropna(subset=["__idx_b"]).astype({"__idx_a": int, "__idx_b": int})
    return a.take(j["__idx_a"].values), b.take(j["__idx_b"].values)


def _mse(a: np.ndarray, b: np.ndarray) -> float:
    m = np.isfinite(a) & np.isfinite(b)
    if not m.any():
        return np.nan
    diff = a[m] - b[m]
    return float(np.mean(diff * diff))


def _mae(a: np.ndarray, b: np.ndarray) -> float:
    m = np.isfinite(a) & np.isfinite(b)
    if not m.any():
        return np.nan
    return float(np.mean(np.abs(a[m] - b[m])))


def compute_ohlc_metrics(df_t: pd.DataFrame, df_c: pd.DataFrame, tol: pd.Timedelta) -> Dict[str, float]:
    A, B = _merge_nearest(df_t, df_c, on="kernel_time", tol=tol)
    metrics: Dict[str, float] = {}
    for col in ["open", "high", "low", "close", "volume"]:
        if col in A.columns and col in B.columns:
            metrics[f"mse_{col}"] = _mse(A[col].values, B[col].values)
            metrics[f"mae_{col}"] = _mae(A[col].values, B[col].values)
        else:
            metrics[f"mse_{col}"] = np.nan
            metrics[f"mae_{col}"] = np.nan
    # aggregated across OHLC only (exclude volume)
    mses = [metrics[f"mse_{c}"] for c in ["open", "high", "low", "close"] if not np.isnan(metrics[f"mse_{c}"])]
    maes = [metrics[f"mae_{c}"] for c in ["open", "high", "low", "close"] if not np.isnan(metrics[f"mae_{c}"])]
    metrics["mse_ohlc_avg"] = float(np.mean(mses)) if mses else np.nan
    metrics["mae_ohlc_avg"] = float(np.mean(maes)) if maes else np.nan
    return metrics


def compute_lob_metrics(df_t: pd.DataFrame, df_c: pd.DataFrame, tol: pd.Timedelta, levels: int) -> Dict[str, float]:
    A, B = _merge_nearest(df_t, df_c, on="kernel_time", tol=tol)
    metrics: Dict[str, float] = {}
    mse_list = []
    mae_list = []
    for side in ("Ask", "Bid"):
        for field in ("Price", "Volume"):
            for lvl in range(levels):
                col = f"{side}{field}{lvl}"
                if col in A.columns and col in B.columns:
                    mse = _mse(A[col].values, B[col].values)
                    mae = _mae(A[col].values, B[col].values)
                    metrics[f"mse_{col}"] = mse
                    metrics[f"mae_{col}"] = mae
                    mse_list.append(mse)
                    mae_list.append(mae)
                else:
                    metrics[f"mse_{col}"] = np.nan
                    metrics[f"mae_{col}"] = np.nan
    metrics["mse_lob_avg"] = float(np.mean([x for x in mse_list if not np.isnan(x)])) if mse_list else np.nan
    metrics["mae_lob_avg"] = float(np.mean([x for x in mae_list if not np.isnan(x)])) if mae_list else np.nan
    return metrics


def _plot_candles(ax, df: pd.DataFrame, color_up="#26a69a", color_down="#ef5350", width_minutes=3.0, alpha=0.9, label_prefix=""):
    if df.empty:
        return
    # Expect columns: kernel_time, open, high, low, close
    t = pd.to_datetime(df["kernel_time"]).dt.to_pydatetime()
    tnum = date2num(t)
    opens = df["open"].values.astype(float)
    highs = df["high"].values.astype(float)
    lows = df["low"].values.astype(float)
    closes = df["close"].values.astype(float)
    up = closes >= opens
    # wicks via LineCollection
    segs = [((tnum[i], lows[i]), (tnum[i], highs[i])) for i in range(len(tnum))]
    lc = LineCollection(segs, colors="#666666", linewidths=0.8, alpha=alpha)
    ax.add_collection(lc)
    # candle bodies via Rectangle
    w = (width_minutes / (24.0 * 60.0))
    for i in range(len(tnum)):
        c = color_up if up[i] else color_down
        o = opens[i]
        cl = closes[i]
        lower = min(o, cl)
        height = max(abs(cl - o), 1e-12)
        rect = Rectangle((tnum[i] - w/2.0, lower), w, height, facecolor=c, edgecolor=c, alpha=alpha)
        ax.add_patch(rect)
    ax.grid(True, linestyle=":", alpha=0.25)
    ax.autoscale_view()


def _plot_bestpx(ax, df: pd.DataFrame, color_bid="#42a5f5", color_ask="#ab47bc", label_prefix=""):
    if df.empty:
        return
    t = pd.to_datetime(df["kernel_time"]).astype("datetime64[ns]")
    if "BidPrice0" in df.columns:
        ax.plot(t, df["BidPrice0"].astype(float).values, color=color_bid, linewidth=1.2, alpha=0.9, label=f"{label_prefix} Bid0")
    if "AskPrice0" in df.columns:
        ax.plot(t, df["AskPrice0"].astype(float).values, color=color_ask, linewidth=1.2, alpha=0.9, label=f"{label_prefix} Ask0")
    ax.grid(True, linestyle=":", alpha=0.25)


def visualize_stock(stock: str,
                     truth_dir: str,
                     calib_dir: str,
                     out_dir: str,
                     tol: pd.Timedelta,
                     lob_levels: int) -> Dict[str, float]:
    sym_dir = os.path.join(out_dir, "plots")
    _ensure_dir(sym_dir)
    ohlc_t = _load_ohlc(os.path.join(truth_dir, stock, "ohlc.csv"))
    ohlc_c = _load_ohlc(os.path.join(calib_dir, stock, "ohlc.csv"))
    lob_t = _load_lob(os.path.join(truth_dir, stock, "lob.csv"))
    lob_c = _load_lob(os.path.join(calib_dir, stock, "lob.csv"))

    m_ohlc = compute_ohlc_metrics(ohlc_t, ohlc_c, tol=tol)
    m_lob = compute_lob_metrics(lob_t, lob_c, tol=tol, levels=lob_levels)
    metrics = {**{f"ohlc_{k}": v for k, v in m_ohlc.items()}, **{f"lob_{k}": v for k, v in m_lob.items()}}

    # Plots
    # OHLC overlay
    fig, ax = plt.subplots(1, 1, figsize=(10, 5))
    _plot_candles(ax, ohlc_t, color_up="#4caf50", color_down="#c62828", label_prefix="Truth")
    _plot_candles(ax, ohlc_c, color_up="#81d4fa", color_down="#1565c0", alpha=0.5, label_prefix="Calib")
    ax.set_title(f"{stock} OHLC (avg MSE={m_ohlc.get('mse_ohlc_avg', np.nan):.4g})")
    ax.legend(loc="best")
    fig.tight_layout()
    f1 = os.path.join(sym_dir, f"{stock}_ohlc.png")
    fig.savefig(f1, dpi=150)
    plt.close(fig)

    # Best px overlay
    fig, ax = plt.subplots(1, 1, figsize=(10, 4))
    _plot_bestpx(ax, lob_t, color_bid="#2e7d32", color_ask="#c62828", label_prefix="Truth")
    _plot_bestpx(ax, lob_c, color_bid="#0277bd", color_ask="#6a1b9a", label_prefix="Calib")
    ax.set_title(f"{stock} BestPx (LOB avg MSE={m_lob.get('mse_lob_avg', np.nan):.4g})")
    ax.legend(loc="best")
    fig.tight_layout()
    f2 = os.path.join(sym_dir, f"{stock}_bestpx.png")
    fig.savefig(f2, dpi=150)
    plt.close(fig)

    return metrics


def main():
    ap = argparse.ArgumentParser(description="Visualize and score calibration run against reference logs")
    ap.add_argument("--truth_dir", required=True, help="Ground-truth log directory (contains <SYMBOL>/ohlc.csv, lob.csv)")
    ap.add_argument("--calib_dir", required=True, help="Calibration run log directory to evaluate")
    ap.add_argument("--out_dir", required=True, help="Output directory for report/plots")
    ap.add_argument("--stocks", default="", help="Comma-separated stocks to evaluate; default is intersection of both dirs")
    ap.add_argument("--tolerance", default="2s", help="Time alignment tolerance for nearest match, e.g. '2s'")
    ap.add_argument("--lob_levels", type=int, default=1, help="LOB levels to include for metrics (default=1, top-of-book)")
    args = ap.parse_args()

    truth_dir = os.path.abspath(args.truth_dir)
    calib_dir = os.path.abspath(args.calib_dir)
    out_dir = os.path.abspath(args.out_dir)
    _ensure_dir(out_dir)
    _ensure_dir(os.path.join(out_dir, "plots"))

    if args.stocks.strip():
        stocks = [s.strip() for s in args.stocks.split(",") if s.strip()]
    else:
        s_truth = set(_list_stocks(truth_dir))
        s_calib = set(_list_stocks(calib_dir))
        stocks = sorted(list(s_truth & s_calib))

    tol = pd.Timedelta(args.tolerance)

    rows = []
    for sym in stocks:
        metrics = visualize_stock(sym, truth_dir, calib_dir, out_dir, tol, args.lob_levels)
        row = {"stock": sym}
        row.update(metrics)
        rows.append(row)

    df = pd.DataFrame(rows)
    csv_path = os.path.join(out_dir, "metrics.csv")
    df.to_csv(csv_path, index=False)

    # Overall summary
    overall = {
        "stocks": len(stocks),
        "mse_ohlc_avg": float(df[[c for c in df.columns if c.endswith("mse_ohlc_avg") or c == "ohlc_mse_ohlc_avg"]].mean(axis=1).mean()) if not df.empty else np.nan,
        "mae_ohlc_avg": float(df[[c for c in df.columns if c.endswith("mae_ohlc_avg") or c == "ohlc_mae_ohlc_avg"]].mean(axis=1).mean()) if not df.empty else np.nan,
        "mse_lob_avg": float(df[[c for c in df.columns if c.endswith("mse_lob_avg") or c == "lob_mse_lob_avg"]].mean(axis=1).mean()) if not df.empty else np.nan,
        "mae_lob_avg": float(df[[c for c in df.columns if c.endswith("mae_lob_avg") or c == "lob_mae_lob_avg"]].mean(axis=1).mean()) if not df.empty else np.nan,
    }
    with open(os.path.join(out_dir, "overview.txt"), "w") as f:
        f.write("Calibration vs Truth Summary\n")
        f.write(f"Symbols: {overall['stocks']}\n")
        f.write(f"OHLC avg MSE: {overall['mse_ohlc_avg']:.6g}\n")
        f.write(f"OHLC avg MAE: {overall['mae_ohlc_avg']:.6g}\n")
        f.write(f"LOB  avg MSE: {overall['mse_lob_avg']:.6g}\n")
        f.write(f"LOB  avg MAE: {overall['mae_lob_avg']:.6g}\n")

    # Simple HTML
    try:
        html = ["<html><head><meta charset='utf-8'><title>Calibration Report</title></head><body>"]
        html.append("<h2>Calibration vs Truth Summary</h2>")
        html.append(f"<p>Symbols: {overall['stocks']}<br>"
                    f"OHLC avg MSE: {overall['mse_ohlc_avg']:.6g}, MAE: {overall['mae_ohlc_avg']:.6g}<br>"
                    f"LOB avg MSE: {overall['mse_lob_avg']:.6g}, MAE: {overall['mae_lob_avg']:.6g}</p>")
        html.append("<h3>Per-Symbol Plots</h3>")
        for sym in stocks:
            html.append(f"<h4>{sym}</h4>")
            html.append(f"<img src='plots/{sym}_ohlc.png' style='max-width: 1000px;'><br>")
            html.append(f"<img src='plots/{sym}_bestpx.png' style='max-width: 1000px;'><br>")
        html.append("</body></html>")
        with open(os.path.join(out_dir, "index.html"), "w") as f:
            f.write("\n".join(html))
    except Exception:
        pass


if __name__ == "__main__":
    main()
