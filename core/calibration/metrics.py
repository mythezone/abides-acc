from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


def _resolve_columns(level: int = 10) -> Dict[str, List[str]]:
    cols = {"price": [], "volume": []}
    for i in range(level):
        cols["price"].append(f"AskPrice{i}")
        cols["volume"].append(f"AskVolume{i}")
    for i in range(level):
        cols["price"].append(f"BidPrice{i}")
    for i in range(level):
        cols["volume"].append(f"BidVolume{i}")
    return cols


def load_lob_series(log_dir: str, stock: str) -> Optional[pd.DataFrame]:
    """Load the LOB CSV for a given stock if it exists."""
    path = Path(log_dir) / stock / "lob.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if df.empty or "kernel_time" not in df.columns:
        return None
    df["kernel_time"] = pd.to_datetime(df["kernel_time"])
    df = df.sort_values("kernel_time").reset_index(drop=True)
    return df


def align_lob_frames(
    base: pd.DataFrame, calibrated: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Align two LOB time series on kernel_time."""
    left = base.copy()
    right = calibrated.copy()
    left["kernel_time"] = pd.to_datetime(left["kernel_time"])
    right["kernel_time"] = pd.to_datetime(right["kernel_time"])
    # Inner join to focus on overlapping timestamps
    merged = pd.merge(
        left,
        right,
        on="kernel_time",
        suffixes=("_base", "_cal"),
    )
    if merged.empty:
        return pd.DataFrame(), pd.DataFrame()
    base_cols = [c for c in merged.columns if c.endswith("_base")]
    cal_cols = [c for c in merged.columns if c.endswith("_cal")]
    base_df = merged[["kernel_time"] + base_cols].copy()
    cal_df = merged[["kernel_time"] + cal_cols].copy()
    base_df.columns = ["kernel_time"] + [c[:-5] for c in base_cols]
    cal_df.columns = ["kernel_time"] + [c[:-4] for c in cal_cols]
    return base_df, cal_df


@dataclass
class LOBMSEConfig:
    price_weight: float = 0.5
    volume_weight: float = 0.5
    levels: int = 10
    normalization_mode: str = "col_wise"

    def normalized_weights(self) -> Tuple[float, float]:
        total = float(self.price_weight) + float(self.volume_weight)
        if total <= 0:
            return 0.5, 0.5
        return self.price_weight / total, self.volume_weight / total


def compute_lob_mse(
    base_df: pd.DataFrame,
    calibrated_df: pd.DataFrame,
    config: Optional[LOBMSEConfig] = None,
) -> Dict[str, float]:
    cfg = config or LOBMSEConfig()
    price_cols = [f"AskPrice{i}" for i in range(cfg.levels)] + [
        f"BidPrice{i}" for i in range(cfg.levels)
    ]
    volume_cols = [f"AskVolume{i}" for i in range(cfg.levels)] + [
        f"BidVolume{i}" for i in range(cfg.levels)
    ]
    missing_cols = [c for c in price_cols + volume_cols if c not in base_df.columns]
    if missing_cols:
        # Reduce levels if needed
        present = [c for c in price_cols if c in base_df.columns]
        price_cols = present
        present_v = [c for c in volume_cols if c in base_df.columns]
        volume_cols = present_v
    if not price_cols or not volume_cols:
        return {"price_mse": float("nan"), "volume_mse": float("nan"), "combined_mse": float("nan")}

    base_df, calibrated_df = align_lob_frames(base_df, calibrated_df)
    if base_df.empty or calibrated_df.empty:
        return {"price_mse": float("nan"), "volume_mse": float("nan"), "combined_mse": float("nan")}

    base_df = base_df.fillna(0.0)
    calibrated_df = calibrated_df.fillna(0.0)

    mode = (cfg.normalization_mode or "col_wise").lower()

    if mode == "none":
        base_price_norm = base_df[price_cols].to_numpy(dtype=float)
        cal_price_norm = calibrated_df[price_cols].to_numpy(dtype=float)
        base_volume_norm = base_df[volume_cols].to_numpy(dtype=float)
        cal_volume_norm = calibrated_df[volume_cols].to_numpy(dtype=float)
    else:
        base_price_norm, cal_price_norm = _apply_normalization(
            base_df[price_cols], calibrated_df[price_cols], mode
        )
        base_volume_norm, cal_volume_norm = _apply_normalization(
            base_df[volume_cols], calibrated_df[volume_cols], mode
        )
        base_price_norm = base_price_norm.values
        cal_price_norm = cal_price_norm.values
        base_volume_norm = base_volume_norm.values
        cal_volume_norm = cal_volume_norm.values

    price_diff = (cal_price_norm - base_price_norm) ** 2
    volume_diff = (cal_volume_norm - base_volume_norm) ** 2

    price_mse = float(np.nanmean(price_diff))
    volume_mse = float(np.nanmean(volume_diff))
    pw, vw = cfg.normalized_weights()
    combined = pw * price_mse + vw * volume_mse
    return {"price_mse": price_mse, "volume_mse": volume_mse, "combined_mse": combined}


def evaluate_directories(
    base_dir: str,
    calibrated_dir: str,
    stocks: Sequence[str],
    config: Optional[LOBMSEConfig] = None,
) -> List[Dict[str, float]]:
    results: List[Dict[str, float]] = []
    cfg = config or LOBMSEConfig()
    for stock in stocks:
        base_df = load_lob_series(base_dir, stock)
        cal_df = load_lob_series(calibrated_dir, stock)
        if base_df is None or cal_df is None:
            results.append(
                {
                    "stock": stock,
                    "price_mse": float("nan"),
                    "volume_mse": float("nan"),
                    "combined_mse": float("nan"),
                }
            )
            continue
        metrics = compute_lob_mse(base_df, cal_df, cfg)
        metrics["stock"] = stock
        results.append(metrics)
    return results


def summarize_metrics(metrics: Iterable[Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    df = pd.DataFrame(metrics)
    stats = {}
    for key in ["price_mse", "volume_mse", "combined_mse"]:
        series = df[key].replace([np.inf, -np.inf], np.nan).dropna()
        if series.empty:
            stats[key] = {"mean": float("nan"), "variance": float("nan")}
        else:
            stats[key] = {
                "mean": float(series.mean()),
                "variance": float(series.var(ddof=0)),
            }
    return stats


def _apply_normalization(
    base: pd.DataFrame, calibrated: pd.DataFrame, mode: str
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    mode = mode.lower()
    if mode == "none":
        return base.copy(), calibrated.copy()
    if mode == "col_wise":
        means = base.mean(axis=0)
        stds = base.std(axis=0, ddof=0).replace(0.0, np.nan).fillna(1.0)
        base_norm = (base - means) / stds
        cal_norm = (calibrated - means) / stds
        return base_norm, cal_norm
    if mode == "pv":
        values = base.values.astype(float)
        mean = float(values.mean())
        std = float(values.std())
        if std == 0.0:
            std = 1.0
        base_norm = (base - mean) / std
        cal_norm = (calibrated - mean) / std
        return base_norm, cal_norm
    raise ValueError(f"Unknown normalization_mode: {mode}")
