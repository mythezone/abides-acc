# Replay Comparison: MAXE vs. HistoricalOrderReplayAgent

## Data Source
- Both simulators replay `comparison/test_data/sz000001_RJJ.csv`, which stores millisecond-level A-share order flow with the columns `TIMESTAMP, PRICE, SIZE, BUY_SELL_FLAG, ORDER_TYPE, ORDER_ID, MARKET_ORDER_TYPE, CANCEL_TYPE, SIMUTIME`.
- `SIMUTIME` encodes the intra-session offset (seconds) used by MAXE to advance the event clock, while the raw `TIMESTAMP` captures wall-clock time.
- `ORDER_TYPE` distinguishes markets (`1`) from limits (`2`), and `CANCEL_TYPE` marks whether a row is an active order (`2`) or a cancellation (`1`). This semantic is documented in `comparison/order_match/MAXE-RJJ/Ashare.ipynb`.

## MAXE Replay Pipeline

### Initial Book State
- Each `<SetupAgent>` defined in `comparison/order_match/MAXE-RJJ/Ashare.xml` plants paired bid/ask ladders at simulation start.
- `SetupAgent::receiveMessage` listens for `EVENT_SIMULATION_START` and immediately sends `PLACE_ORDER_LIMIT` messages to `EXCHANGE` for both sides using the preconfigured price/volume (`comparison/methods/Simulator/TheSimulator/TheSimulator/SetupAgent.cpp:41`).
- The exchange therefore begins with a 10-level ladder that mirrors the actual opening LOB.

### Order Ingestion (TestAgent)
- `Simulation::setupChildConfiguration` falls back to `PythonAgent` for unrecognised nodes and expects a `TestAgent` Python class (`comparison/methods/Simulator/TheSimulator/TheSimulator/Simulation.cpp:283`).
- The relevant Python source is not versioned in this tree, but the compiled simulator (`build/TheSimulator/.../TheSimulator`) succeeds in loading it, implying that MAXE’s `TestAgent` reads the CSV, interprets `SIMUTIME` as seconds, and schedules dispatches via `simulation()->dispatchMessage`.
- Given MAXE’s output logs, `TestAgent` appears to:
  - Map `BUY_SELL_FLAG` into `OrderDirection`.
  - Treat `ORDER_TYPE == 1` as market orders and `2` as limit orders.
  - Honour `CANCEL_TYPE == 1` as an order cancellation request carrying the original `ORDER_ID`.
  - Forward volume and price verbatim, so the exchange always sees full depth.

### Matching & Book Maintenance
- `ExchangeAgent::receiveMessage` routes `PLACE_ORDER_LIMIT`/`PLACE_ORDER_MARKET` into the live `Book` instance (`comparison/methods/Simulator/TheSimulator/TheSimulator/ExchangeAgent.cpp:22`).
- Limit orders are inserted or matched by `Book::placeOrder` with price-time priority; partial fills loop until the residual either matches or gets parked in the correct deque (`comparison/methods/Simulator/TheSimulator/TheSimulator/Book.cpp:9`).
- `PriceTimeBook::processAgainstTheSellQueue`/`processAgainstTheBuyQueue` consume resting liquidity tick-by-tick, emitting trades for every partial execution with explicit aggressor/resting order IDs (`comparison/methods/Simulator/TheSimulator/TheSimulator/PriceTimeBook.cpp:6`).
- `CANCEL_ORDERS` operates strictly on order IDs and uses `Book::cancelOrder` to zero out the remaining volume; the order remains in the ID map until fully cancelled (`Book.cpp:111`).
- The 1-second L1 sampling in `L1LogAgent` pulls the best quote with `RETRIEVE_L1` every simulation second, mirroring the `SIMUTIME` grid (`comparison/methods/Simulator/TheSimulator/TheSimulator/L1LogAgent.cpp:36`).

## HistoricalOrderReplayAgent Flow

### Parsing & Event Construction
- The agent loads the CSV at instantiation, generating `_HistoricalOrder` or `_HistoricalCancel` events sorted by timestamp (`core/agent/replay.py:61`).
- Price/volume fields are coerced to floats/ints; orders missing a price are skipped.
- **Bug**: cancellations are recognised when `cancel_type == 2` instead of `1`, which inverts the meaning documented in MAXE’s notebook (`core/agent/replay.py:97`). As a result:
  - Genuine cancellation rows (`CANCEL_TYPE == 1`) are replayed as fresh limit orders.
  - Active orders with `CANCEL_TYPE == 2` are instead turned into price-level cancellation requests.
- Market orders are identified via `ORDER_TYPE == "1"` and carry an optional `MARKET_ORDER_TYPE` depth hint (`core/agent/replay.py:87`).

### Message Emission
- On each wake-up, the agent sends one ABIDES-ACC message per CSV row (`core/agent/replay.py:155`):
  - Limit/market orders become a `MessageType.SUBMIT_ORDER` with a single `requests` entry containing symbol, side, price (if limit), quantity, and optional `id` (`core/agent/replay.py:166`).
  - Cancellations issue `MessageType.CANCEL_ORDER`, but only identify the target by side/price/quantity – the original `ORDER_ID` is discarded (`core/agent/replay.py:193`).
  - After every submit or cancel, the agent voluntarily triggers a `LOG_TICK` request, so the exchange emits an L1 snapshot even if no other agent requested it (`core/agent/replay.py:212`).
- Timing is controlled by re-queuing the next wake-up at the next event time (converted to milliseconds) with a 100μs epsilon for grouping (`core/agent/replay.py:141`).

## Per-Row Behaviour Comparison

| CSV Row Scenario | MAXE Handling | HistoricalOrderReplayAgent Handling |
| ---------------- | ------------- | ----------------------------------- |
| New limit (`ORDER_TYPE=2`, `CANCEL_TYPE=2`) | Places a `PLACE_ORDER_LIMIT` with original `ORDER_ID`; if price crosses, immediate matching occurs at exchange level before parking residual | Misidentified as a cancellation: sends `CANCEL_ORDER` targeted by price/side/size, removing book depth that should have been added |
| Cancel (`ORDER_TYPE=2`, `CANCEL_TYPE=1`) | Issues `CANCEL_ORDERS` referencing the exact resting `ORDER_ID`; remaining volume is decremented precisely | Treated as a fresh limit order, duplicating resting interest and never reducing volume |
| Market (`ORDER_TYPE=1`) | Converts to `PLACE_ORDER_MARKET`; matching consumes best quotes with price-time priority and logs trades with aggressor IDs | Sends a `market_order` request with optional `market_depth` hint; exchange must infer the intended depth and matching ends once stated depth is consumed |
| Identical timestamp bursts | MAXE schedules each message using the `SIMUTIME` offset; exchange processes them in FIFO order of arrival, matching between entries | Agent emits all entries at the same `event_time` and enqueues them sequentially; however `LOG_TICK` is interleaved after every row, producing additional idle callbacks |

## Key Divergences Explaining LOB mismatch

1. **Cancellation semantics inverted** – Using `cancel_type == 2` as the cancellation trigger strips active liquidity and resurrects cancelled quotes. This alone flips resting depth and explains spread/volume drift within seconds.
2. **Order identity is lost** – Price-level cancellations (`core/agent/replay.py:193`) cannot disambiguate multiple orders at the same price, whereas MAXE cancels by `ORDER_ID`. Partial fills/cancels therefore diverge immediately.
3. **Opening LOB seeding** – MAXE pre-loads a full ladder via 10 `SetupAgent`s, guaranteeing realistic initial depth (`SetupAgent.cpp:41`). Our replay starts from an empty book unless the CSV happens to begin with placements, causing early trades to deviate.
4. **Tick logging cadence** – MAXE’s exchange is polled every second by `L1LogAgent`, while HistoricalOrderReplayAgent generates a `LOG_TICK` after each row. The additional ticks can pull snapshots before all same-timestamp events finish, skewing 3 s aggregates.
5. **Algorithm selection** – MAXE’s exchange enforces strict price-time priority in C++ (`PriceTimeBook.cpp:6`). If ABIDES-ACC’s exchange differs (e.g., heap-based best-price retrieval), residual queue ordering may drift unless order IDs are preserved.
6. **Configuration gap** – MAXE expects an external `TestAgent` Python module. Without mirroring its exact logic (including dictionary lookups, order IDs, and potential latency), ABIDES-ACC cannot reproduce the same message stream.

## Alignment Recommendations

1. **Fix cancellation parsing** – Switch the replay agent to recognise `CANCEL_TYPE == 1` as a cancellation and treat `2` as a live order. Additionally, carry `ORDER_ID` through to cancellation requests so the exchange can cancel the precise resting order.
2. **Seed the opening book** – Mirror MAXE’s `<SetupAgent>` ladder by either importing the first snapshot from the CSV or scripting equivalent seed orders before replay starts.
3. **Batch events per timestamp** – Emit all submissions/cancels for a timestamp first, then trigger a single `LOG_TICK`, matching MAXE’s 1 s sampling cadence.
4. **Reproduce MAXE’s market order depth semantics** – Confirm how `MARKET_ORDER_TYPE` maps to volume slices in `TestAgent` and update the replay agent to follow the same rule.
5. **Reverse-engineer `TestAgent` behaviour** – Extract the deployed Python source (or replicate from logs) to ensure parity in: timestamp offsets, ID management, cancel handling, and any throttling/back-pressure logic.

Applying the above should bring the ABIDES-ACC replay much closer to MAXE’s output and, by extension, to the recorded LOB trajectory.
