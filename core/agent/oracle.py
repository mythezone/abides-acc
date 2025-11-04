import os
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

import pandas as pd

from core.agent.base import BaseAgent
from core.message import MessageType, new_message


class OracleAgent(BaseAgent):
    """
    Oracle agent reads previously generated logs (LOB/OHLC) and serves
    time-indexed queries to other agents during calibration runs.

    Supported directory layouts:
      1) root/<SYMBOL>/lob.csv (ABIDES-style hierarchy)
      2) root/<SYMBOL>.csv (flat directory, single file per symbol)
    """

    _DEFAULT_TIME_COLUMNS: Sequence[str] = (
        "kernel_time",
        "timestamp",
        "time",
        "datetime",
    )

    def __init__(
        self,
        id,
        *args,
        source_log_dir: str,
        lob_levels: int = 10,
        **kwargs,
    ):
        super().__init__(id, *args, **kwargs)
        self.source_log_dir = source_log_dir
        self._lob_levels = int(lob_levels)
        self.ohlc: Dict[str, pd.DataFrame] = {}
        self.lob: Dict[str, pd.DataFrame] = {}
        self._lob_time_col: Dict[str, str] = {}
        self._ohlc_time_col: Dict[str, str] = {}
        self._load_data()

    # ------------------------------------------------------------------ #
    # Data loading
    # ------------------------------------------------------------------ #
    def _load_data(self) -> None:
        base = Path(self.source_log_dir or "").expanduser()
        if not base.exists():
            return

        for entry in base.iterdir():
            if entry.is_dir():
                self._load_directory_symbol(entry)
            elif entry.is_file() and entry.suffix.lower() == ".csv":
                self._load_flat_symbol(entry)

    def _load_directory_symbol(self, dir_path: Path) -> None:
        symbol = dir_path.name
        lob_path = dir_path / "lob.csv"
        ohlc_path = dir_path / "ohlc.csv"
        if lob_path.exists():
            df, time_col = self._read_time_series_csv(lob_path)
            if df is not None:
                self.lob[symbol] = df
                self._lob_time_col[symbol] = time_col
        if ohlc_path.exists():
            df, time_col = self._read_time_series_csv(ohlc_path)
            if df is not None:
                self.ohlc[symbol] = df
                self._ohlc_time_col[symbol] = time_col

    def _load_flat_symbol(self, file_path: Path) -> None:
        symbol = file_path.stem
        df, time_col = self._read_time_series_csv(file_path)
        if df is not None:
            self.lob[symbol] = df
            self._lob_time_col[symbol] = time_col

    def _read_time_series_csv(
        self, csv_path: Path
    ) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        try:
            df = pd.read_csv(csv_path)
        except Exception:
            return None, None
        if df.empty:
            return None, None
        time_col = self._detect_time_column(df)
        if time_col is None:
            return None, None
        try:
            df[time_col] = pd.to_datetime(df[time_col]).astype("datetime64[ns]")
            df = df.sort_values(time_col).reset_index(drop=True)
        except Exception:
            return None, None
        return df, time_col

    def _detect_time_column(self, df: pd.DataFrame) -> Optional[str]:
        for candidate in self._DEFAULT_TIME_COLUMNS:
            if candidate in df.columns:
                return candidate
            # case-insensitive match
            lower_cols = {c.lower(): c for c in df.columns}
            if candidate in lower_cols:
                return lower_cols[candidate]
        return None

    # ------------------------------------------------------------------ #
    # Public helpers
    # ------------------------------------------------------------------ #
    def available_symbols(self) -> Sequence[str]:
        return list(self.lob.keys())

    def has_lob(self, symbol: str) -> bool:
        return symbol in self.lob

    def get_lob(
        self, symbol: str, current_time: pd.Timestamp
    ) -> Optional[Dict[str, object]]:
        df = self.lob.get(symbol)
        time_col = self._lob_time_col.get(symbol)
        if df is None or time_col is None or df.empty:
            return None
        t = pd.Timestamp(current_time)
        idx = df[time_col].searchsorted(t)
        if idx >= len(df):
            idx = len(df) - 1
        row = df.iloc[idx]
        asks = self._extract_levels(row, prefix="Ask")
        bids = self._extract_levels(row, prefix="Bid")
        return {
            "timestamp": row[time_col],
            "sell": asks,
            "buy": bids,
            "raw": row.to_dict(),
        }

    # ------------------------------------------------------------------ #
    # Internal utilities
    # ------------------------------------------------------------------ #
    def _extract_levels(
        self, row: pd.Series, prefix: str
    ) -> list[tuple[float, int]]:
        levels: list[tuple[float, int]] = []
        for level in range(self._lob_levels):
            price_col = f"{prefix}Price{level}"
            qty_col = f"{prefix}Volume{level}"
            if price_col not in row or qty_col not in row:
                break
            price = row[price_col]
            qty = row[qty_col]
            if pd.isna(price) or pd.isna(qty):
                continue
            try:
                price_val = float(price)
                qty_val = int(qty)
            except Exception:
                continue
            if qty_val <= 0:
                continue
            levels.append((price_val, qty_val))
        return levels

    def _find_next(
        self, df: pd.DataFrame, t: pd.Timestamp, *, time_col: Optional[str]
    ) -> Optional[dict]:
        if df is None or df.empty or time_col is None:
            return None
        idx = df[time_col].searchsorted(t)
        if idx >= len(df):
            idx = len(df) - 1
        row = df.iloc[idx]
        return row.to_dict()

    # ------------------------------------------------------------------ #
    # Message handling
    # ------------------------------------------------------------------ #
    def handle_inbox_message(self, message):
        # Answer queries immediately with response messages
        t = pd.to_datetime(message.content.get("time", message.recive_time))
        symbol = message.content.get("symbol")
        if message.message_type == MessageType.ORACLE_QUERY_OHLC:
            data = None
            time_col = self._ohlc_time_col.get(symbol)
            if symbol in self.ohlc:
                data = self._find_next(self.ohlc[symbol], t, time_col=time_col)
            rsp = new_message(
                message_type=MessageType.ORACLE_RESPONSE_OHLC,
                sender_id=self.id,
                recipient_id=message.sender_id,
                send_time=message.recive_time,
                recive_time=message.recive_time,
                content={"symbol": symbol, "ohlc": data},
            )
            self.send(rsp)
            return True
        if message.message_type == MessageType.ORACLE_QUERY_LOB:
            data = None
            time_col = self._lob_time_col.get(symbol)
            if symbol in self.lob:
                data = self._find_next(self.lob[symbol], t, time_col=time_col)
            rsp = new_message(
                message_type=MessageType.ORACLE_RESPONSE_LOB,
                sender_id=self.id,
                recipient_id=message.sender_id,
                send_time=message.recive_time,
                recive_time=message.recive_time,
                content={"symbol": symbol, "lob": data},
            )
            self.send(rsp)
            return True
        return super().handle_inbox_message(message)
