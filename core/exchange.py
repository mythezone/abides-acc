from core.lob import LimitOrderBook
from core.message import MessageType, new_message, Message
from core.ohlc import OHLCAggregator
from core.order import Order, LimitOrder, MarketOrder
import pandas as pd
import numpy as np


import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor


class Exchange:
    def __init__(self, symbols: dict, logger=None, ohlc_freq: str = "3s", lob_log_level: int = 5, lob_log_freq: str = "3s", workers: int = 0, out_queue=None):
        self.symbols = symbols
        self.lob_dict = {
            symbol_name: LimitOrderBook(symbol_name) for symbol_name in symbols
        }
        self.logger = logger
        self.ohlc_freq = ohlc_freq
        self.ohlc_by_symbol: dict[str, OHLCAggregator] = {}
        self.lob_log_level = lob_log_level
        # support special tick mode
        self._lob_tick_mode = (str(lob_log_freq).lower() == "tick")
        self.lob_log_delta = None if self._lob_tick_mode else pd.Timedelta(lob_log_freq)
        self._last_lob_log: dict[str, pd.Timestamp] = {}
        self.out_queue = out_queue

        # Parallel workers sharded by symbol hash (if requested)
        self.workers = int(workers) if workers and int(workers) > 0 else 0
        self._worker_queues: list[Queue] = []
        self._executor: Optional[ThreadPoolExecutor] = None
        if self.workers > 0:
            self._executor = ThreadPoolExecutor(max_workers=self.workers, thread_name_prefix="exch")
            self._worker_queues = [Queue() for _ in range(self.workers)]
            for idx in range(self.workers):
                self._executor.submit(self._worker_loop, idx)

    def handle_message(self, message: Message):
        response_messages = []
        now = message.send_time
        # PROC log for incoming message at Exchange
        if self.logger is not None:
            self.logger.kernel_message_log(message, stage="PROC")

        if message.message_type in (MessageType.LMT_ORDER, MessageType.MKT_ORDER, MessageType.SUBMIT_ORDER):
            # Accept generic SUBMIT_ORDER and type-specific LMT/MKT
            for req in message.content.get("requests", []):
                symbol = req.get("symbol", "SYM")
                # Ensure a LOB exists even if symbols were not pre-registered
                if symbol not in self.lob_dict:
                    self.lob_dict[symbol] = LimitOrderBook(symbol)

                # Decide order class
                otype = req.get("type")
                if otype == "limit_order":
                    order = LimitOrder.from_dict(req)
                elif otype == "market_order":
                    order = MarketOrder.from_dict(req)
                else:
                    order = Order.from_dict(req)

                # attach symbol reference to order for worker processing
                try:
                    setattr(order, "_symbol", symbol)
                except Exception:
                    pass
                if self.workers > 0:
                    # Enqueue to worker based on symbol shard
                    shard = hash(symbol) % self.workers
                    self._worker_queues[shard].put((now, order))
                else:
                    # Synchronous processing
                    self._process_order(now, order)
        elif message.message_type == MessageType.CANCEL_ORDER:
            for req in message.content.get("requests", []):
                symbol = req.get("symbol")
                order_id = req.get("order_id")
                self.lob_dict[symbol].cancel_order(order_id)
                response_messages.append(
                    new_message(
                        message_type=MessageType.ORDER_CANCELLED,
                        sender_id="Exchange",
                        recipient_id=message.sender_id,
                        send_time=now,
                        recive_time=now,
                        content={"order_id": order_id, "symbol": symbol},
                    )
                )
        elif message.message_type == MessageType.MKT_DATA:
            content = message.content or {}
            if content.get("type") == "query_symbols":
                n = int(content.get("n", 3))
                # Provide dummy symbol list
                universe = list(self.lob_dict.keys()) or ["SYM1", "SYM2", "SYM3", "SYM4"]
                if len(universe) < n:
                    # Pad with synthetic symbols
                    universe += [f"SYM{i}" for i in range(len(universe) + 1, n + 1)]
                selected = universe[:n]
                response_messages.append(
                    new_message(
                        message_type=MessageType.MKT_DATA,
                        sender_id="Exchange",
                        recipient_id=message.sender_id,
                        send_time=now,
                        recive_time=now,
                        content={"symbols": selected},
                    )
                )
            else:
                for req in content.get("requests", []):
                    symbol = req.get("symbol", "SYM1")
                    # Return a dummy snapshot
                    best_bid = round(np.random.uniform(10, 100), 2)
                    best_ask = round(best_bid + np.random.uniform(0.01, 0.5), 2)
                    snapshot = {
                        "symbol": symbol,
                        "best_bid": best_bid,
                        "best_ask": best_ask,
                        "mid": round((best_bid + best_ask) / 2, 2),
                        "ts": str(now),
                    }
                    response_messages.append(
                        new_message(
                            message_type=MessageType.MKT_DATA,
                            sender_id="Exchange",
                            recipient_id=message.sender_id,
                            send_time=now,
                            recive_time=now,
                            content=snapshot,
                        )
                    )
        return response_messages

    def _worker_loop(self, idx: int):
        q = self._worker_queues[idx]
        while True:
            now, order = q.get()
            try:
                self._process_order(now, order)
            except Exception:
                pass
            finally:
                q.task_done()

    def _emit(self, msg: Message):
        if self.out_queue is not None:
            self.out_queue.put(msg)

    def _process_order(self, now: pd.Timestamp, order: Order):
        symbol = getattr(order, "_symbol", None) or getattr(order, "symbol", None) or None
        if symbol is None:
            # fallback from request dict stored in order
            if hasattr(order, "__dict__") and "symbol" in order.__dict__:
                symbol = order.__dict__["symbol"]
        if symbol not in self.lob_dict:
            self.lob_dict[symbol] = LimitOrderBook(symbol)

        trades = self.lob_dict[symbol].add_order(order)
        # Acknowledge
        ack = new_message(
            message_type=MessageType.ORDER_ACCEPTED,
            sender_id="Exchange",
            recipient_id=order.agent_id,
            send_time=now,
            recive_time=now,
            content={"order_id": order.id, "symbol": symbol},
        )
        self._emit(ack)

        if trades:
            execmsg = new_message(
                message_type=MessageType.ORDER_EXECUTED,
                sender_id="Exchange",
                recipient_id=order.agent_id,
                send_time=now,
                recive_time=now,
                content={"trades": trades, "symbol": symbol},
            )
            self._emit(execmsg)

        # OHLC update
        price = None
        if trades:
            price = float(trades[-1]["price"])
        else:
            snap = self.lob_dict[symbol].snapshot_top_n(1)
            if snap["buy"] and snap["sell"]:
                bid = float(snap["buy"][0][0])
                ask = float(snap["sell"][0][0])
                price = round((bid + ask) / 2.0, 2)
        if price is not None and self.logger is not None:
            if symbol not in self.ohlc_by_symbol:
                self.ohlc_by_symbol[symbol] = OHLCAggregator(symbol, self.ohlc_freq, self.logger)
            self.ohlc_by_symbol[symbol].update(now, price, volume=float(order.quantity))
        # LOB periodic log
        if self.logger is not None:
            last = self._last_lob_log.get(symbol)
            should_log = False
            if self._lob_tick_mode:
                should_log = True
            else:
                if (last is None) or (now - last >= self.lob_log_delta):
                    should_log = True
            if should_log:
                lob_csv = self.lob_dict[symbol].format_snapshot_csv(self.lob_log_level)
                self.logger.lob_log(symbol_name=symbol, kernel_time=now, level=self.lob_log_level, lob=lob_csv)
                self._last_lob_log[symbol] = now
