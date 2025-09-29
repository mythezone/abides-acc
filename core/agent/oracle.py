import os
import pandas as pd
from typing import Dict, Optional

from core.agent.base import BaseAgent
from core.message import MessageType, new_message


class OracleAgent(BaseAgent):
    """
    Oracle agent reads previously generated logs (LOB/OHLC) and serves
    time-indexed queries to other agents during calibration runs.
    Expected directory layout:
      root/
        <SYMBOL>/ohlc.csv
        <SYMBOL>/lob.csv
    """

    def __init__(self, id, *args, source_log_dir: str, **kwargs):
        super().__init__(id, *args, **kwargs)
        self.source_log_dir = source_log_dir
        self.ohlc: Dict[str, pd.DataFrame] = {}
        self.lob: Dict[str, pd.DataFrame] = {}
        self._load_data()

    def _load_data(self):
        if not os.path.isdir(self.source_log_dir):
            return
        # load all symbols under directory
        for sym in os.listdir(self.source_log_dir):
            spath = os.path.join(self.source_log_dir, sym)
            if not os.path.isdir(spath):
                continue
            ohlc_path = os.path.join(spath, "ohlc.csv")
            lob_path = os.path.join(spath, "lob.csv")
            if os.path.exists(ohlc_path):
                try:
                    df = pd.read_csv(ohlc_path)
                    if "kernel_time" in df.columns:
                        df["kernel_time"] = pd.to_datetime(df["kernel_time"]).astype('datetime64[ns]')
                        df = df.sort_values("kernel_time").reset_index(drop=True)
                        self.ohlc[sym] = df
                except Exception:
                    pass
            if os.path.exists(lob_path):
                try:
                    df = pd.read_csv(lob_path)
                    if "kernel_time" in df.columns:
                        df["kernel_time"] = pd.to_datetime(df["kernel_time"]).astype('datetime64[ns]')
                        df = df.sort_values("kernel_time").reset_index(drop=True)
                        self.lob[sym] = df
                except Exception:
                    pass

    def _find_next(self, df: pd.DataFrame, t: pd.Timestamp) -> Optional[dict]:
        if df is None or df.empty:
            return None
        # next row with kernel_time >= t
        idx = df["kernel_time"].searchsorted(t)
        if idx >= len(df):
            idx = len(df) - 1
        row = df.iloc[idx]
        return row.to_dict()

    def handle_inbox_message(self, message):
        # Answer queries immediately with response messages
        t = pd.to_datetime(message.content.get("time", message.recive_time))
        symbol = message.content.get("symbol")
        if message.message_type == MessageType.ORACLE_QUERY_OHLC:
            data = None
            if symbol in self.ohlc:
                data = self._find_next(self.ohlc[symbol], t)
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
            if symbol in self.lob:
                data = self._find_next(self.lob[symbol], t)
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
