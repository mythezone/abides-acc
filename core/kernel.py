import numpy as np
import pandas as pd

import time
from pathlib import Path
from typing import List, Dict, Optional
from rich.progress import Progress
from types import SimpleNamespace

from core.message import MessageBox, MessageType, Message, MessageQueue, new_message
from core.agent import AGENTS
from core.clock import KernelClock
from core.exchange import new_exchange
from core.logger import Logger
from core.lob import LimitOrderBook
from core.config import ConfigManager

from gui.component.agent_panel import AgentPanel


class Kernel:
    def __init__(self, config: Dict = {}):
        self.config = config
        self.agents = {}

    def initialize(self):
        self.name = self.config["name"]
        self.message_queue = MessageQueue()
        self.in_box = MessageBox()

        self.clock = KernelClock(
            initial_time=self.config.get("start_date", "now"),
            trading_days=self.config.get("trading_days", []),
            exchange=self.config.get("exchange_type", "SZSE"),
        )
        # Init logger early
        ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        log_dir = self.config.get("log_dir", f"log/run_{ts}")
        self.logger = Logger(log_dir)

        # Optionally disable main message log to reduce IO
        if self.config.get("disable_main_log", False):
            self.logger.disable_main_log = True

        # Minimal exchange with empty symbol universe, will grow on demand
        ex_params = self.config.get("exchange_params", {})
        symbols = self.config.get("symbols", [])
        self.exchange = new_exchange(
            self.config.get("exchange_type", "SZSE"),
            symbols=symbols,
            logger=self.logger,
            exchange_params=ex_params,
            out_queue=self.message_queue,
        )
        self.simulation_end_time = None
        self._end_event_scheduled = False
        # Oracle agent in calibration mode
        calib = self.config.get("calibration", {})
        self.oracle = None
        self.calibration_context = None
        if calib.get("enabled", False):
            try:
                from core.agent.oracle import OracleAgent
                from core.calibration import CalibrationContext

                src_dir = (
                    calib.get("source_log_dir")
                    or calib.get("lob_data_dir")
                    or calib.get("data_dir")
                )
                if not src_dir:
                    raise ValueError("Calibration source_log_dir/lob_data_dir is required.")
                self.oracle = OracleAgent(
                    id="Oracle",
                    message_queue=self.message_queue,
                    logger=self.logger,
                    source_log_dir=src_dir,
                    lob_levels=int(calib.get("lob_levels", 10)),
                )
                specs = calib.get("agent_specs") or []
                symbol_filter = calib.get("symbols")
                if isinstance(symbol_filter, list):
                    symbol_filter = [str(s) for s in symbol_filter]
                trigger_offset = (
                    calib.get("trigger_offset")
                    or calib.get("trigger_offset_ms")
                    or "10ms"
                )
                max_levels = int(calib.get("max_levels", 10))
                self.calibration_context = CalibrationContext(
                    exchange=self.exchange,
                    oracle=self.oracle,
                    agent_specs=specs,
                    symbols=symbol_filter,
                    max_levels=max_levels,
                    trigger_offset=trigger_offset,
                )
                if hasattr(self.exchange, "enable_calibration"):
                    self.exchange.enable_calibration(self.calibration_context)
            except Exception:
                self.oracle = None
                self.calibration_context = None
        self.enforce_step_limit = bool(self.config.get("enforce_step_limit", False))
        self.simulation_end_time = self._compute_simulation_end_time()

    def init_agent(
        self,
        agent_config: List,
        agent_panel: Optional[AgentPanel] = None,
        progress: Optional[Progress] = None,
        task=None,
    ):
        agent_log_freq = self.config.get("agent_log_freq", "tick")
        positions_default = self.config.get("agent_positions") or {}
        # Symbols universe (for random positions)
        try:
            universe_symbols = list(self.exchange.lob_dict.keys())
        except Exception:
            universe_symbols = []
        for config in agent_config:
            # accept either 'type' or legacy 'name'
            agent_type = config.get("type") or config.get("name")
            agent_class = AGENTS[agent_type]
            agent_num = config.get("num", 1)
            # accept either 'params' or legacy 'args'
            args: Dict = config.get("params") or config.get("args") or {}
            args.setdefault("agent_log_freq", agent_log_freq)
            if self.oracle is not None:
                args.setdefault("calibration_mode", True)
                args.setdefault("oracle_id", "Oracle")
            for id in range(agent_num):
                if progress and task:
                    progress.update(task, advance=1)
                # Here we would create an agent instance, e.g.:
                # Agent(id=id, type=agent_type, **args)
                agent_id = f"{agent_type}_{id}"
                agent_instance = agent_class(
                    id=agent_id,
                    message_queue=self.message_queue,
                    logger=self.logger,
                    **args,
                )
                agent_instance.exchange_location = getattr(self.exchange, "location", None)
                self.agents[agent_id] = agent_instance
                try:
                    self.exchange.register_agent_location(
                        agent_id, getattr(agent_instance, "location", None)
                    )
                except Exception:
                    pass
                # Initialize positions per configuration
                try:
                    # Per-agent override
                    pos_spec = args.get("positions") or args.get("initial_positions")
                    rnd_spec = args.get("random_positions")
                    if pos_spec and isinstance(pos_spec, dict):
                        # fixed positions
                        self.agents[agent_id].portfolio.holdings = {
                            k: int(v) for k, v in pos_spec.items()
                        }
                    else:
                        # random positions via per-agent or kernel default
                        spec = (
                            rnd_spec
                            if isinstance(rnd_spec, dict)
                            else positions_default
                        )
                        if spec and (spec.get("mode", "random") == "random"):
                            min_sh = int(spec.get("min_shares", 0))
                            max_sh = int(spec.get("max_shares", 0))
                            min_cash = float(spec.get("min_cash", 100000.0))
                            max_cash = float(spec.get("max_cash", 1000000.0))
                            syms = spec.get("symbols") or universe_symbols
                            if syms:
                                agent_instance.portfolio.initialize_random_portfolio(
                                    syms,
                                    min_shares=min_sh,
                                    max_shares=max_sh,
                                    min_cash=min_cash,
                                    max_cash=max_cash,
                                )
                except Exception:
                    pass
                if agent_panel:
                    agent_panel.update_agent(
                        {"agent_id": agent_instance.id, "status": "sleep"}
                    )
                    agent_panel.render()
                    time.sleep(0.01)

        self._sync_agent_locations()

        # After all agents are initialized, feed initial positions to exchange for T+1 rules
        try:
            init_pos_map: Dict[str, Dict[str, int]] = {}
            for aid, ag in self.agents.items():
                if getattr(ag, "portfolio", None) is not None and getattr(
                    ag.portfolio, "holdings", None
                ):
                    init_pos_map[aid] = {
                        sym: int(qty) for sym, qty in ag.portfolio.holdings.items()
                    }
            if hasattr(self.exchange, "initial_positions"):
                self.exchange.initial_positions = init_pos_map
        except Exception:
            pass

    # Kernel now receives messages via self.message_queue from agents.

    def process_messages(self, max_steps: int = 100000):
        """Drain incoming queue and process messages in priority order.

        This mirrors the per-message routing used by run(), without seeding agent wakeups
        or managing the main simulation loop. Intended for incremental processing in
        interactive or service contexts.

        Returns a dict with counters for processed messages and last processed time.
        """
        processed = 0
        steps = 0
        last_time = None
        self._schedule_simulation_end()

        # Drain cross-process queue to local inbox (non-blocking)
        while True:
            try:
                self.in_box.put(self.message_queue.get_nowait_raw())
            except Exception:
                break

        # Process messages from inbox in receive_time order
        while (not self.in_box.empty()) and steps < max_steps:
            msg = self.in_box.get()
            if msg is None:
                # Nothing to process
                break
            # Advance simulation time & skip market breaks if necessary
            self.clock.simulate_time = msg.recive_time
            if self.clock.is_market_closed() or self.clock.is_break_time():
                self.clock.skip_break()
                msg.recive_time = self.clock.now()
                # Skip PROC log to reduce duplication

            # Log receive (PROC omitted to save volume)
            self.logger.kernel_message_log(msg, stage="RECV")
            last_time = msg.recive_time

            # Route to recipient
            rid = msg.recipient_id
            if rid in self.agents:
                agent = self.agents[rid]
                # Skip PROC log to reduce duplication
                if msg.message_type == MessageType.WAKEUP:
                    agent.wakeup(last_time)
                else:
                    agent.receive(msg)
                # Drain any messages the agent just enqueued
                while True:
                    try:
                        self.in_box.put(self.message_queue.get_nowait_raw())
                    except Exception:
                        break
            elif rid == "Exchange":
                # Skip PROC log to reduce duplication
                responses = self.exchange.handle_message(msg)
                for rsp in responses:
                    self.logger.kernel_message_log(rsp, stage="SEND")
                    self.message_queue.put(rsp)
                # also drain any async responses emitted by exchange workers
                while True:
                    try:
                        self.in_box.put(self.message_queue.get_nowait_raw())
                    except Exception:
                        break
            else:
                if self.oracle and rid == "Oracle":
                    self.logger.kernel_message_log(msg, stage="PROC")
                    self.oracle.receive(msg)
                elif rid == "Kernel" and msg.message_type == MessageType.SIMULATION_END:
                    self.logger.kernel_message_log(msg, stage="PROC")
                    last_time = msg.recive_time
                    self._handle_simulation_end(msg)
                    break
                else:
                    # Unknown recipient; ignore or log
                    pass

            processed += 1
            steps += 1

        # Flush batched logs
        self.logger.save_log_to_file()
        return {"processed": processed, "last_time": last_time}

    def _compute_simulation_end_time(self) -> Optional[pd.Timestamp]:
        end_spec = self.config.get("end_date")
        if not end_spec:
            return None
        try:
            has_time = isinstance(end_spec, str) and (":" in end_spec)
            end_ts = pd.to_datetime(end_spec)
        except Exception:
            return None
        start_spec = self.config.get("start_date") or self.clock.now()
        try:
            start_ts = pd.to_datetime(start_spec)
        except Exception:
            start_ts = self.clock.now()
        if not has_time:
            # Default to the last trading session end on the final trading day
            target_date = end_ts.date()
            try:
                if self.clock.trading_days:
                    target_date = self.clock.trading_days[-1]
            except Exception:
                pass
            sessions = getattr(self.clock, "sessions", [])
            if sessions:
                last_end = sessions[-1][1]
                end_ts = pd.Timestamp.combine(target_date, last_end)
        if end_ts <= start_ts:
            return None
        return end_ts

    def _schedule_simulation_end(self):
        if self.simulation_end_time is None or self._end_event_scheduled:
            return
        stop_msg = new_message(
            message_type=MessageType.SIMULATION_END,
            sender_id="Kernel",
            recipient_id="Kernel",
            send_time=self.simulation_end_time,
            recive_time=self.simulation_end_time,
            content={},
        )
        self.message_queue.put(stop_msg)
        self._end_event_scheduled = True

    def _handle_simulation_end(self, msg: Message):
        end_time = msg.recive_time
        # Notify agents
        for agent in self.agents.values():
            try:
                agent.receive(
                    new_message(
                        message_type=MessageType.SIMULATION_END,
                        sender_id="Kernel",
                        recipient_id=agent.id,
                        send_time=end_time,
                        recive_time=end_time,
                        content={},
                    )
                )
            except Exception:
                pass
        # Notify exchange (best-effort)
        try:
            end_msg = new_message(
                message_type=MessageType.SIMULATION_END,
                sender_id="Kernel",
                recipient_id="Exchange",
                send_time=end_time,
                recive_time=end_time,
                content={},
            )
            self.exchange.handle_message(end_msg)
        except Exception:
            pass

    def run(self, max_steps: int = 10000, max_sim_seconds: Optional[int] = None):
        # Seed first wakeups for all agents
        start_time = self.clock.now()
        self._end_event_scheduled = False
        self._schedule_simulation_end()
        for agent_id in self.agents.keys():
            wake = new_message(
                message_type=MessageType.WAKEUP,
                sender_id=agent_id,
                recipient_id=agent_id,
                send_time=start_time,
                recive_time=start_time,
                content={},
            )
            # Log send
            self.logger.kernel_message_log(wake, stage="SEND")
            self.message_queue.put(wake)
            # Also seed directly into local inbox to avoid Queue semantics issues in tests
            self.in_box.put(wake)

        steps = 0
        processed = 0
        current_time = start_time

        # Optional time-based stop
        stop_at = None
        if max_sim_seconds is not None and isinstance(max_sim_seconds, int):
            stop_at = start_time + pd.Timedelta(seconds=int(max_sim_seconds))

        while True:
            # If no time horizon, enforce step cap unless disabled by configuration
            if stop_at is None and max_steps is not None and steps >= max_steps:
                if self.simulation_end_time is not None and not self.enforce_step_limit:
                    pass
                else:
                    break
            # Drain inter-process queue into local box (non-blocking)
            while True:
                try:
                    self.in_box.put(self.message_queue.get_nowait_raw())
                except Exception:
                    break

            # Pop next event by time
            msg = self.in_box.get()
            if msg is None:
                break
            # Apply trading session skip if needed
            self.clock.simulate_time = msg.recive_time
            if self.clock.is_market_closed() or (
                self.clock.is_break_time()
                and not getattr(self.exchange, "is_preopen_time", lambda t: False)(
                    msg.recive_time
                )
            ):
                before = self.clock.now()
                self.clock.skip_break()
                # shift message receive time forward to next valid time
                msg.recive_time = self.clock.now()
                # Log time skip as PROC stage
                self.logger.kernel_message_log(msg, stage="PROC")
            # Log receive
            self.logger.kernel_message_log(msg, stage="RECV")
            current_time = msg.recive_time
            # stop by simulated time horizon if configured
            if stop_at is not None and current_time >= stop_at:
                break

            # Route to recipient
            rid = msg.recipient_id
            if rid in self.agents:
                agent = self.agents[rid]
                # Skip PROC log to reduce duplication
                if msg.message_type == MessageType.WAKEUP:
                    agent.wakeup(current_time)
                else:
                    agent.receive(msg)
            elif rid == "Exchange":
                # Skip PROC log to reduce duplication; exchange may log internally
                responses = self.exchange.handle_message(msg)
                for rsp in responses:
                    # Log send
                    self.logger.kernel_message_log(rsp, stage="SEND")
                    self.message_queue.put(rsp)
                # Drain any additional messages emitted synchronously by Exchange
                while True:
                    try:
                        self.in_box.put(self.message_queue.get_nowait_raw())
                    except Exception:
                        break
            else:
                if self.oracle and rid == "Oracle":
                    # Let oracle handle
                    self.logger.kernel_message_log(msg, stage="PROC")
                    self.oracle.receive(msg)
                elif rid == "Kernel" and msg.message_type == MessageType.SIMULATION_END:
                    self.logger.kernel_message_log(msg, stage="PROC")
                    current_time = msg.recive_time
                    self._handle_simulation_end(msg)
                    break
                else:
                    # Unknown recipient; drop or log
                    pass

            processed += 1
            steps += 1

        # Flush logs and shutdown background components
        try:
            self.logger.save_log_to_file()
        finally:
            # Ensure exchange workers are stopped so process can exit cleanly
            try:
                self.exchange.shutdown(wait=True)
            except Exception:
                pass
        return {"processed": processed, "steps": steps, "end_time": current_time}

    @classmethod
    def from_config(cls, config_path: str):
        cm = ConfigManager(config_path)
        # Derive minimal kernel config
        sim = getattr(cm, "simulation", SimpleNamespace())
        start_date = getattr(sim, "start_date", "now")
        end_date = getattr(sim, "end_date", start_date)
        exchange_type = getattr(sim, "exchange_type", "SZSE")
        kcfg = getattr(cm, "kernel", SimpleNamespace())
        kname = getattr(kcfg, "name", "sim")
        # Build trading days range
        try:
            start_dt = pd.to_datetime(start_date).date()
            end_dt = pd.to_datetime(end_date).date()
            days = pd.date_range(start=start_dt, end=end_dt, freq="D").date.tolist()
        except Exception:
            days = [start_date]
        # Extract exchange params from config if available
        ex_params_conf = {}
        try:
            ex_params_conf = getattr(kcfg, "exchange_params")
            # Normalize SimpleNamespace to dict
            if isinstance(ex_params_conf, SimpleNamespace):
                ex_params_conf = vars(ex_params_conf)
        except Exception:
            pass
        if not ex_params_conf:
            try:
                # try first exchange in list
                ex0 = cm.exchanges[0]
                p = ex0.get("params", {})
                # support both names
                ex_params_conf = {
                    "ohlc_freq": p.get("log_ohlc_freq", p.get("ohlc_freq")),
                    "lob_log_freq": p.get("log_lob_freq", p.get("lob_log_freq")),
                    "lob_log_level": p.get("log_lob_level", p.get("lob_level", 5)),
                }
            except Exception:
                ex_params_conf = {}

        # If start_date already includes time, use as-is; else default to 09:30
        def _normalize_start(s):
            try:
                if isinstance(s, str) and (":" in s):
                    pd.to_datetime(s)
                    return s
            except Exception:
                pass
            return f"{s} 09:30:00"

        # Merge exchange params: carry through all provided keys and ensure defaults
        ep = {}
        try:
            if isinstance(ex_params_conf, dict):
                ep.update(ex_params_conf)
        except Exception:
            pass
        ep.setdefault("ohlc_freq", "3s")
        ep.setdefault("lob_log_level", 5)
        ep.setdefault("lob_log_freq", "3s")
        ep.setdefault("workers", 0)

        snapshots = ep.get("initial_snapshots")
        if isinstance(snapshots, dict):
            cfg_dir = Path(config_path).resolve().parent
            resolved = {}
            for sym, path in snapshots.items():
                if not path:
                    continue
                try:
                    p = Path(path)
                    resolved_path = p if p.is_absolute() else (cfg_dir / p)
                    resolved[sym] = str(resolved_path.resolve())
                except Exception:
                    resolved[sym] = path
            ep["initial_snapshots"] = resolved

        symbols_raw = getattr(cm, "symbols", [])
        log_dir_override = getattr(kcfg, "log_dir", None)
        cfg = {
            "name": kname,
            "start_date": _normalize_start(start_date),
            "trading_days": days,
            "exchange_type": exchange_type,
            "log_dir": str(log_dir_override) if log_dir_override else f"log/{kname}",
            "exchange_params": ep,
            "calibration": {},
            "symbols": symbols_raw,
            "end_date": str(end_date) if end_date is not None else None,
            "enforce_step_limit": bool(getattr(kcfg, "enforce_step_limit", False)),
        }
        # Optional calibration settings embedded in config
        try:
            calib = getattr(cm, "calibration")
            if isinstance(calib, SimpleNamespace):
                calib = vars(calib)
            if isinstance(calib, dict):
                cfg["calibration"] = calib
                # allow override of log_dir for calibration output
                out_dir = calib.get("output_dir")
                if out_dir:
                    cfg["log_dir"] = out_dir
        except Exception:
            pass
        kernel = cls(config=cfg)
        kernel.initialize()
        # Initialize exchange symbol universe if provided
        try:
            symbols = getattr(cm, "symbols", [])
            for sym in symbols:
                if isinstance(sym, dict):
                    sym_name = sym.get("symbol")
                else:
                    sym_name = sym
                if not sym_name:
                    continue
                sym_name = str(sym_name)
                try:
                    kernel.exchange._ensure_lob(sym_name)
                except Exception:
                    pass
        except Exception:
            pass
        # Build agents from config
        agent_cfgs = []
        try:
            agent_defs = getattr(cm, "agents", [])
            all_symbols = getattr(cm, "symbols", [])
            for a in agent_defs:
                atype = a.get("type") or a.get("name") or "zero_intelligence"
                # Validate against registered agents registry
                if atype not in AGENTS:
                    atype = "zero_intelligence"
                params = a.get("params") or a.get("args") or {}
                if atype == "zero_intelligence" and "initial_symbols" not in params:
                    params["initial_symbols"] = list(all_symbols)
                agent_cfgs.append(
                    {
                        "type": atype,
                        "num": a.get("num", 1),
                        "params": params,
                    }
                )
        except Exception:
            # Fallback: one zero intelligence agent
            agent_cfgs = [{"type": "zero_intelligence", "num": 1, "params": {}}]
        kernel.init_agent(agent_cfgs)
        return kernel

    def shutdown(self):
        """Explicit shutdown hook to terminate any background workers and flush logs."""
        try:
            if hasattr(self, "exchange") and self.exchange is not None:
                self.exchange.shutdown(wait=True)
        finally:
            try:
                if hasattr(self, "logger") and self.logger is not None:
                    self.logger.save_log_to_file()
            except Exception:
                pass

    def _sync_agent_locations(self) -> None:
        try:
            exchange_loc = getattr(self.exchange, "location", None)
        except Exception:
            exchange_loc = None
        location_map = {
            aid: getattr(agent, "location", None) for aid, agent in self.agents.items()
        }
        for aid, agent in self.agents.items():
            agent.exchange_location = exchange_loc
            peer_map = {
                other_id: loc
                for other_id, loc in location_map.items()
                if other_id != aid and loc is not None
            }
            agent._peer_locations = peer_map
