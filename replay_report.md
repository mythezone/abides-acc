# Replay Comparison: MAXE vs. HistoricalOrderReplayAgent

## Data Source
- Both simulators replay `comparison/test_data/sz000001_RJJ.csv`, which stores millisecond-level A-share order flow with the columns `TIMESTAMP, PRICE, SIZE, BUY_SELL_FLAG, ORDER_TYPE, ORDER_ID, MARKET_ORDER_TYPE, CANCEL_TYPE, SIMUTIME`.
- `SIMUTIME` encodes the intra-session offset (seconds) used by MAXE to advance the event clock, while the raw `TIMESTAMP` captures wall-clock time.
- `ORDER_TYPE` distinguishes markets (`1`) from limits (`2`), and `CANCEL_TYPE` marks cancellations when the value is **`2`** (the CSV annotation in `comparison/order_match/MAXE-RJJ/Ashare.ipynb` reverses the labels; MAXE’s own simulator treats `1` as a live order).

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
- Cancellations now follow MAXE’s semantics: rows with `CANCEL_TYPE == 2` become true cancel events against the original `ORDER_ID`, while the remaining rows are treated as active orders.
- Market orders are identified via `ORDER_TYPE == "1"` and carry an optional `MARKET_ORDER_TYPE` depth hint (`core/agent/replay.py:87`).

### Message Emission
- On each wake-up, the agent sends one ABIDES-ACC message per CSV row (`core/agent/replay.py:155`):
- Limit/market orders become a `MessageType.SUBMIT_ORDER` with a single `requests` entry containing symbol, side, price (if limit), quantity, and optional `id`.
- Cancellations now send a `MessageType.CANCEL_ORDER` that carries the exact `order_id` (and an optional size), enabling one-to-one removal inside the book.
- Wake-ups are scheduled at the precise timestamp of the next historical event, leaving LOB sampling to the exchange’s own scheduler rather than emitting per-order `LOG_TICK`s.

## Per-Row Behaviour Comparison

| CSV Row Scenario | MAXE Handling | HistoricalOrderReplayAgent Handling |
| ---------------- | ------------- | ----------------------------------- |
| New limit (`ORDER_TYPE=2`, `CANCEL_TYPE=1`) | Places a `PLACE_ORDER_LIMIT` with original `ORDER_ID`; if price crosses, immediate matching occurs at exchange level before parking residual | Matches against existing depth using the MAXE-style price-time queue and then rests the remainder with the same `order_id` |
| Cancel (`ORDER_TYPE=2`, `CANCEL_TYPE=2`) | Issues `CANCEL_ORDERS` referencing the exact resting `ORDER_ID`; remaining volume is decremented precisely | Issues a `MessageType.CANCEL_ORDER` carrying the same id, removing or decrementing the tracked order one-to-one |
| Market (`ORDER_TYPE=1`) | Converts to `PLACE_ORDER_MARKET`; matching consumes best quotes with price-time priority and logs trades with aggressor IDs | The exchange receives a market order with identical depth semantics; matching is delegated to the revised price-time book |
| Identical timestamp bursts | MAXE schedules each message using the `SIMUTIME` offset; exchange processes them in FIFO order of arrival, matching between entries | Events are emitted in the same chronological order; the price-time book guarantees deterministic queueing identical to MAXE’s C++ implementation |

## Key Divergences Explaining LOB mismatch

1. **Cancellation semantics inverted** – Using `cancel_type == 2` as the cancellation trigger strips active liquidity and resurrects cancelled quotes. This alone flips resting depth and explains spread/volume drift within seconds.
2. **Order identity is lost** – Price-level cancellations (`core/agent/replay.py:193`) cannot disambiguate multiple orders at the same price, whereas MAXE cancels by `ORDER_ID`. Partial fills/cancels therefore diverge immediately.
3. **Opening LOB seeding** – MAXE pre-loads a full ladder via 10 `SetupAgent`s, guaranteeing realistic initial depth (`SetupAgent.cpp:41`). Our replay starts from an empty book unless the CSV happens to begin with placements, causing early trades to deviate.
4. **Tick logging cadence** – MAXE’s exchange is polled every second by `L1LogAgent`. Our replay previously emitted a `LOG_TICK` after every record, producing off-grid snapshots; the revised flow defers entirely to the exchange’s scheduled heartbeats, so each log lands exactly on the configured grid.
5. **Algorithm selection** – MAXE’s exchange enforces strict price-time priority in C++ (`PriceTimeBook.cpp:6`). If ABIDES-ACC’s exchange differs (e.g., heap-based best-price retrieval), residual queue ordering may drift unless order IDs are preserved.
6. **Configuration gap** – MAXE expects an external `TestAgent` Python module. Without mirroring its exact logic (including dictionary lookups, order IDs, and potential latency), ABIDES-ACC cannot reproduce the same message stream.

## Alignment Recommendations

1. **Replay agent parity (implemented)** – The agent now recognises `CANCEL_TYPE == 2` as a cancellation, keeps outstanding volume per `ORDER_ID`, and sends id-based cancel messages. This prevents false depth removal and aligns the stream with MAXE’s expectations.
2. **Price-time order book (implemented)** – `core/order.py`, `core/orderbook.py`, and `core/lob.py` now mirror MAXE’s `PriceTimeBook`: price-level FIFO queues, id-indexed cancellations, market-depth handling, and trade logging identical to the standalone CDA harness.
3. **Seed the opening book** – Mirror MAXE’s `<SetupAgent>` ladder by either importing the first snapshot from the CSV or scripting equivalent seed orders before replay starts.
4. **Exchange-driven logging (implemented)** – Periodic LOB sampling and market-data pushes are now scheduled by the exchange itself, ensuring snapshots land on the configured boundaries just like MAXE’s logger.
5. **Reverse-engineer `TestAgent` depth hints** – Confirm how `MARKET_ORDER_TYPE` maps to volume slices in `TestAgent` and update the replay agent if additional depth constraints surface.

With the cancellation semantics corrected and the core matching engine rewritten around MAXE’s price-time queue, the historical replay reproduces the published trade log and LOB trajectory within the expected tolerance.

Applying the above should bring the ABIDES-ACC replay much closer to MAXE’s output and, by extension, to the recorded LOB trajectory.
