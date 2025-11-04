from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


LOB_COL_TEMPLATE = {
    "price": [f"AskPrice{i}" for i in range(10)] + [f"BidPrice{i}" for i in range(10)],
    "volume": [f"AskVolume{i}" for i in range(10)] + [f"BidVolume{i}" for i in range(10)],
}


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


def load_lob_series(log_dir: str, symbol: str) -> Optional[pd.DataFrame]:
    """Load the LOB CSV for a given symbol if it exists."""
    path = Path(log_dir) / symbol / "lob.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if df.empty or "kernel_time" not in df.columns:
        return None
    df["kernel_time"] = pd.to_datetime(df["kernel_time"])
    df = df.sort_values("kernel_time").reset_index(drop=True)
    return df


def _normalization_scale(values: pd.DataFrame, method: str) -> pd.Series:
    method = (method or "max").lower()
    if method == "none":
        return pd.Series(1.0, index=values.columns)
    if method == "mean":
        scale = values.abs().mean()
    elif method == "std":
        scale = values.std().replace(0, np.nan)
    else:
        scale = values.abs().max()
    scale = scale.replace(0, np.nan).fillna(1.0)
    return scale


def _normalize(values: pd.DataFrame, scale: pd.Series) -> pd.DataFrame:
    shared = scale.reindex(values.columns).fillna(1.0)
    return values.divide(shared, axis=1)


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
    price_norm: str = "max"
    volume_norm: str = "max"
    levels: int = 10

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

    price_scale = _normalization_scale(base_df[price_cols], cfg.price_norm)
    volume_scale = _normalization_scale(base_df[volume_cols], cfg.volume_norm)

    base_price_norm = _normalize(base_df[price_cols], price_scale)
    cal_price_norm = _normalize(calibrated_df[price_cols], price_scale)
    base_volume_norm = _normalize(base_df[volume_cols], volume_scale)
    cal_volume_norm = _normalize(calibrated_df[volume_cols], volume_scale)

    price_diff = (cal_price_norm.values - base_price_norm.values) ** 2
    volume_diff = (cal_volume_norm.values - base_volume_norm.values) ** 2

    price_mse = float(np.nanmean(price_diff))
    volume_mse = float(np.nanmean(volume_diff))
    pw, vw = cfg.normalized_weights()
    combined = pw * price_mse + vw * volume_mse
    return {"price_mse": price_mse, "volume_mse": volume_mse, "combined_mse": combined}


def evaluate_directories(
    base_dir: str,
    calibrated_dir: str,
    symbols: Sequence[str],
    config: Optional[LOBMSEConfig] = None,
) -> List[Dict[str, float]]:
    results: List[Dict[str, float]] = []
    cfg = config or LOBMSEConfig()
    for symbol in symbols:
        base_df = load_lob_series(base_dir, symbol)
        cal_df = load_lob_series(calibrated_dir, symbol)
        if base_df is None or cal_df is None:
            results.append(
                {
                    "symbol": symbol,
                    "price_mse": float("nan"),
                    "volume_mse": float("nan"),
                    "combined_mse": float("nan"),
                }
            )
            continue
        metrics = compute_lob_mse(base_df, cal_df, cfg)
        metrics["symbol"] = symbol
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
