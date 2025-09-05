#!/usr/bin/env python3
"""
Multi-run visualization and metrics: compare multiple simulation runs against a baseline (truth)
and optionally compute pairwise metrics. Produces per-symbol plots and metrics tables.

Usage example:
  python scripts/multi_run_viz.py \
    --truth_dir log/real \
    --group A=log/run_A --group B=log/run_B --group Calib=log/run_C \
    --out_dir insight/result/multi_compare --tolerance 2s --lob_levels 1
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

from calibration_viz import (
    _ensure_dir,
    _list_symbols,
    _load_ohlc,
    _load_lob,
    _merge_nearest,
    compute_ohlc_metrics,
    compute_lob_metrics,
)


def _draw_candles(ax, df: pd.DataFrame, width_minutes: float = 3.0,
                  color_up: str = "#26a69a", color_down: str = "#ef5350", alpha: float = 0.9):
    if df.empty:
        return
    t = pd.to_datetime(df["kernel_time"]).dt.to_pydatetime()
    tnum = date2num(t)
    opens = df["open"].astype(float).values
    highs = df["high"].astype(float).values
    lows = df["low"].astype(float).values
    closes = df["close"].astype(float).values
    up = closes >= opens
    down = ~up
    # width in days for date axis
    w = (width_minutes / (24.0 * 60.0))
    # Wicks
    segs = [((tnum[i], lows[i]), (tnum[i], highs[i])) for i in range(len(tnum))]
    lc = LineCollection(segs, colors="#666666", linewidths=0.8, alpha=alpha)
    ax.add_collection(lc)
    # Bodies
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


def overlay_symbol(symbol: str,
                   truth_dir: str,
                   groups: Dict[str, str],
                   out_dir: str,
                   tol: pd.Timedelta,
                   lob_levels: int) -> Dict[str, Dict[str, float]]:
    sym_dir = os.path.join(out_dir, "plots")
    _ensure_dir(sym_dir)
    ohlc_t = _load_ohlc(os.path.join(truth_dir, symbol, "ohlc.csv"))
    lob_t = _load_lob(os.path.join(truth_dir, symbol, "lob.csv"))

    # Metrics per group
    metrics: Dict[str, Dict[str, float]] = {}

    # ---------- OHLC panel: [Truth candles] + [each group close overlay vs truth] ----------
    n_groups = len(groups)
    cols = min(3, n_groups + 1)
    rows = int(np.ceil((n_groups + 1) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(6 * cols, 3.6 * rows), squeeze=False)

    # First subplot: truth candlestick
    ax0 = axes[0, 0]
    _draw_candles(ax0, ohlc_t)
    ax0.set_title(f"{symbol} Truth OHLC")
    if not ohlc_t.empty:
        ax0.set_xlim(date2num(pd.to_datetime(ohlc_t["kernel_time"]).dt.to_pydatetime()).min(),
                     date2num(pd.to_datetime(ohlc_t["kernel_time"]).dt.to_pydatetime()).max())

    palette = ["#1976d2", "#6a1b9a", "#00838f", "#ef6c00", "#ad1457", "#2e7d32", "#8e24aa"]
    # Remaining subplots: overlay truth close + group close
    gi = 0
    for gname, gdir in groups.items():
        r = (gi + 1) // cols
        c = (gi + 1) % cols
        ax = axes[r, c]
        ohlc_g = _load_ohlc(os.path.join(gdir, symbol, "ohlc.csv"))
        if not ohlc_g.empty:
            A, B = _merge_nearest(ohlc_t, ohlc_g, on="kernel_time", tol=tol) if not ohlc_t.empty else (ohlc_g, ohlc_g)
            m_ohlc = compute_ohlc_metrics(A, B, tol=tol)
            metrics[gname] = metrics.get(gname, {})
            for k, v in m_ohlc.items():
                metrics[gname][f"ohlc_{k}"] = v
        # Plot truth close
        if not ohlc_t.empty:
            ax.plot(pd.to_datetime(ohlc_t["kernel_time"]).astype("datetime64[ns]"), ohlc_t["close"].astype(float).values, color="#455a64", linewidth=1.0, alpha=0.8, label="Truth close")
        # Plot group close
        if not ohlc_g.empty:
            ax.plot(pd.to_datetime(ohlc_g["kernel_time"]).astype("datetime64[ns]"), ohlc_g["close"].astype(float).values, color=palette[gi % len(palette)], linewidth=1.0, alpha=0.95, label=f"{gname} close")
        ax.set_title(f"{gname} vs Truth (OHLC)")
        ax.grid(True, linestyle=":", alpha=0.25)
        ax.legend(loc="best")
        gi += 1

    # Hide any unused axes
    for i in range(n_groups + 1, rows * cols):
        r = i // cols
        c = i % cols
        axes[r, c].axis('off')

    fig.tight_layout()
    fig.savefig(os.path.join(sym_dir, f"{symbol}_ohlc_panel.png"), dpi=150)
    plt.close(fig)

    # ---------- LOB: generate one image per level (mid price line + volumes as bars) ----------
    for lvl in range(lob_levels):
        fig, axes = plt.subplots(rows, cols, figsize=(6 * cols, 3.4 * rows), squeeze=False)
        # Truth mid
        ax0 = axes[0, 0]
        bid = f"BidPrice{lvl}"
        ask = f"AskPrice{lvl}"
        bvol = f"BidVolume{lvl}"
        avol = f"AskVolume{lvl}"
        if not lob_t.empty and bid in lob_t.columns and ask in lob_t.columns:
            t = pd.to_datetime(lob_t["kernel_time"]).astype("datetime64[ns]")
            mid = (lob_t[bid].astype(float) + lob_t[ask].astype(float)) / 2.0
            ax0.plot(t, mid.values, color="#1b5e20", linewidth=1.2, label="Truth mid")
            # volume bars on twin y
            if bvol in lob_t.columns and avol in lob_t.columns:
                vol = lob_t[bvol].fillna(0).astype(float) + lob_t[avol].fillna(0).astype(float)
                ax2 = ax0.twinx()
                # width in days for bar
                wd = 0.0004
                ax2.bar(t, vol.values, width=wd, color="#90caf9", alpha=0.4, label="Truth vol")
                ax2.set_ylabel("Vol")
        ax0.set_title(f"{symbol} L{lvl} Truth mid/vol")
        ax0.grid(True, linestyle=":", alpha=0.25)

        gi = 0
        for gname, gdir in groups.items():
            r = (gi + 1) // cols
            c = (gi + 1) % cols
            ax = axes[r, c]
            lob_g = _load_lob(os.path.join(gdir, symbol, "lob.csv"))
            if not lob_g.empty:
                A, B = _merge_nearest(lob_t, lob_g, on="kernel_time", tol=tol) if not lob_t.empty else (lob_g, lob_g)
                m_lob = compute_lob_metrics(A, B, tol=tol, levels=lob_levels)
                metrics[gname] = metrics.get(gname, {})
                for k, v in m_lob.items():
                    metrics[gname][f"lob_{k}"] = v
            # plot overlay mid
            if not lob_t.empty and bid in lob_t.columns and ask in lob_t.columns:
                t = pd.to_datetime(lob_t["kernel_time"]).astype("datetime64[ns]")
                mid_t = (lob_t[bid].astype(float) + lob_t[ask].astype(float)) / 2.0
                ax.plot(t, mid_t.values, color="#455a64", linewidth=1.0, alpha=0.8, label="Truth mid")
            if not lob_g.empty and bid in lob_g.columns and ask in lob_g.columns:
                tg = pd.to_datetime(lob_g["kernel_time"]).astype("datetime64[ns]")
                mid_g = (lob_g[bid].astype(float) + lob_g[ask].astype(float)) / 2.0
                ax.plot(tg, mid_g.values, color=palette[gi % len(palette)], linewidth=1.0, alpha=0.95, label=f"{gname} mid")
                # volumes twin bars (group)
                if bvol in lob_g.columns and avol in lob_g.columns:
                    vol = lob_g[bvol].fillna(0).astype(float) + lob_g[avol].fillna(0).astype(float)
                    ax2 = ax.twinx()
                    wd = 0.0004
                    ax2.bar(tg, vol.values, width=wd, color="#ffcc80", alpha=0.35, label=f"{gname} vol")
                    ax2.set_ylabel("Vol")
            ax.set_title(f"{gname} vs Truth (LOB L{lvl})")
            ax.grid(True, linestyle=":", alpha=0.25)
            ax.legend(loc="best")
            gi += 1

        for i in range(n_groups + 1, rows * cols):
            r = i // cols
            c = i % cols
            axes[r, c].axis('off')

        fig.tight_layout()
        fig.savefig(os.path.join(sym_dir, f"{symbol}_lob_level{lvl}.png"), dpi=150)
        plt.close(fig)

    return metrics


def main():
    ap = argparse.ArgumentParser(description="Multi-run comparison and visualization against baseline")
    ap.add_argument("--truth_dir", required=True, help="Baseline (truth) log dir")
    ap.add_argument("--group", action="append", default=[], help="Group spec as NAME=DIR; can be provided multiple times")
    ap.add_argument("--out_dir", required=True, help="Output report directory")
    ap.add_argument("--symbols", default="", help="Comma-separated symbols to evaluate; default is intersection")
    ap.add_argument("--tolerance", default="2s", help="Time tolerance for alignment")
    ap.add_argument("--lob_levels", type=int, default=1, help="LOB levels to include for metrics")
    args = ap.parse_args()

    truth_dir = os.path.abspath(args.truth_dir)
    groups: Dict[str, str] = {}
    for g in args.group:
        if "=" not in g:
            raise SystemExit(f"Invalid --group '{g}', expected NAME=DIR")
        name, p = g.split("=", 1)
        groups[name.strip()] = os.path.abspath(p.strip())

    out_dir = os.path.abspath(args.out_dir)
    _ensure_dir(out_dir)
    _ensure_dir(os.path.join(out_dir, "plots"))

    if args.symbols.strip():
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    else:
        s_truth = set(_list_symbols(truth_dir))
        inter = s_truth
        for _, d in groups.items():
            inter = inter & set(_list_symbols(d))
        symbols = sorted(list(inter))

    tol = pd.Timedelta(args.tolerance)

    # Collect per symbol metrics per group
    rows = []
    for sym in symbols:
        m = overlay_symbol(sym, truth_dir, groups, out_dir, tol, args.lob_levels)
        for gname, gm in m.items():
            row = {"symbol": sym, "group": gname}
            row.update(gm)
            rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(out_dir, "metrics_by_group.csv"), index=False)

    # Summaries per group
    if not df.empty:
        gsum = df.groupby("group").agg({
            "ohlc_mse_ohlc_avg": "mean",
            "ohlc_mae_ohlc_avg": "mean",
            "lob_mse_lob_avg": "mean",
            "lob_mae_lob_avg": "mean",
        }).reset_index()
        gsum.to_csv(os.path.join(out_dir, "summary_by_group.csv"), index=False)

    # HTML index with LOB level dropdown
    try:
        html = ["<html><head><meta charset='utf-8'><title>Multi-run Report</title>",
                "<style>body{font-family:Arial,Helvetica,sans-serif} .sym{margin-bottom:28px}</style>",
                "<script>function sel(sym){var lvl=document.getElementById('lvl_'+sym).value; var max=""+""" + str(args.lob_levels) + """ +""; for(var i=0;i<max;i++){var d=document.getElementById('lob_'+sym+'_'+i); if(d) d.style.display=(i==lvl? 'block':'none');}}</script>",
                "</head><body>"]
        html.append("<h2>Multi-run Summary</h2>")
        if not df.empty:
            html.append("<table border='1' cellspacing='0' cellpadding='4'><tr><th>Group</th><th>OHLC MSE(avg)</th><th>OHLC MAE(avg)</th><th>LOB MSE(avg)</th><th>LOB MAE(avg)</th></tr>")
            for _, r in gsum.iterrows():
                html.append(f"<tr><td>{r['group']}</td><td>{r['ohlc_mse_ohlc_avg']:.6g}</td><td>{r['ohlc_mae_ohlc_avg']:.6g}</td><td>{r['lob_mse_lob_avg']:.6g}</td><td>{r['lob_mae_lob_avg']:.6g}</td></tr>")
            html.append("</table>")
        html.append("<h3>Per-Symbol Panels</h3>")
        for sym in symbols:
            html.append(f"<div class='sym'><h4>{sym}</h4>")
            html.append(f"<div><img src='plots/{sym}_ohlc_panel.png' style='max-width: 1100px;'></div>")
            # dropdown for LOB levels
            html.append(f"<div>LOB Level: <select id='lvl_{sym}' onchange=\"sel('{sym}')\">")
            for i in range(args.lob_levels):
                html.append(f"<option value='{i}'>{i}</option>")
            html.append("</select></div>")
            # containers per level
            for i in range(args.lob_levels):
                display = 'block' if i == 0 else 'none'
                html.append(f"<div id='lob_{sym}_{i}' style='display:{display};'><img src='plots/{sym}_lob_level{i}.png' style='max-width: 1100px;'></div>")
            html.append("</div>")
        html.append("</body></html>")
        with open(os.path.join(out_dir, "index.html"), "w") as f:
            f.write("\n".join(html))
    except Exception:
        pass


if __name__ == "__main__":
    main()
