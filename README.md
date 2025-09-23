# ABIDES‑ACC — An Accelerated, ABIDES‑Compatible Market Simulator

[![License](https://img.shields.io/github/license/mythezone/abides-acc.svg)](./LICENSE.txt)

ABIDES‑ACC 提供一个现代、可扩展的多资产市场仿真内核，兼容 ABIDES 风格的消息与代理，同时在工程结构、日志体系与易用性方面做了强化。项目包含独立的撮合与日志模块、面向消息的 Agent 框架、以及与 ABIDES 的轻量级兼容层，便于团队协同研发与扩展。

## 特色特性

- 明确的分层结构：`core/kernel`（调度）、`core/exchange`（交易所）、`core/lob`（订单簿）、`core/agent`（代理）、`core/logger`（日志）、`core/clock`（交易时钟）。
- 统一消息协议：支持批量多标的下单、改/撤、数据查询、行情订阅；预开盘集合竞价（SZSE 风格）可选。
- 日志与可回放：每个标的输出 `ohlc.csv`/`lob.csv`/`preopen.csv`，核心消息流写入 `log.csv`，便于回放与标注。
- 兼容 ABIDES：提供若干 ABIDES 风格 Agent 适配器与迁移指南；保留 ABIDES 原仓库到 `abides/` 目录以供参考与对照。
- 工程化与测试：PEP 8/Typing 友好；提供单元测试与一键仿真脚本；更低的上手门槛与二次开发成本。

## 架构总览

- `core/kernel.py`：基于优先队列的事件驱动内核。统一调度消息、推进时间，支持心跳 `LOG_TICK` 驱动的 OHLC/LOB 定时写盘。
- `core/exchange.py`：交易所，维护每个标的的 LOB。支持限价/市价、改/撤、集合竞价、T+1 与涨跌幅限制（可配置）、行情订阅推送。T+1 规则通过为每个代理记录“可售上限”实现：基于日初持仓计算单日可卖数量，所有卖单提交时都会占用额度，无法重复出售同一份库存，买入侧不受限制。若需要复现真实开盘深度，可在配置中为每个标的提供 CSV 形式的初始挂单快照，交易所会在启动时以 `InitAgent` 身份注入，且不会被撤销。
- `core/lob.py`：价格层级堆 + FIFO 队列实现的 LOB，保证价优时优撮合，提供快照与 CSV 序列化能力。
- `core/agent/`：代理基类与适配器。基类统一处理收/发、资金/持仓更新；适配器提供 ABIDES 风格策略。
- `core/logger.py`：统一的日志与 CSV 落盘，便于后处理/标注。
- `core/clock.py`：交易时段定义、跨日推进、午休跳时段。

### T+1 卖出限制实现

针对 A 股 T+1 规则，交易所会在日初读取 `initial_positions` 并为每个代理、标的生成一份“可卖额度”。每日提交的卖单会立即占用该额度（无论是否成交），超过额度的卖单将被拒绝，从而避免同一日重复出售相同库存；买单不受限制，会在次日计入新的可卖额度。若未提供初始持仓信息，则默认放宽限制以兼容不受约束的场景。

## 消息协议（摘要）

- 订单类：
  - `SUBMIT_ORDER`（支持单条消息中批量多标的）；`MODIFY_ORDER`；`CANCEL_ORDER`。
  - 回执：`ORDER_ACCEPTED`（受理）/`ORDER_EXECUTED`（成交明细含 `trades`/`fees`）。
- 查询类：
  - `QUERY_LAST_TRADE`、`QUERY_SPERAD`（按历史兼容保留拼写）、`QUERY_ORDER_STREAM`、`QUERY_TRANSACTED_VOLUME`。
- 行情订阅：
  - `MKT_DATA_SUBSCRIPTION_REQUEST/CANCELLATION`；推送 `MKT_DATA`（`{symbol, depth, bids, asks, ts}`）。
  - 预开盘推送使用集合竞价盘，连续竞价推送使用 LOB。
- 会话控制：`MKT_OPEN/MKT_CLOSE`；`LOG_TICK` 用于空闲时驱动定时日志。

详见项目书的相关章节。

## 快速开始

```bash
git clone https://github.com/mythezone/abides-acc.git
cd abides-acc
pip install -r requirements.txt

# 运行包含所有示例代理的演示（短时仿真）
python scripts/run_all_agents.py
```

输出日志将写入 `log/<run>/` 目录：

- `log/<run>/<symbol>/ohlc.csv`、`lob.csv`、`preopen.csv`
- `log/<run>/log.csv`（核心消息流）

## 配置说明

- 示例配置：`config/test_agents.json`
  - `simulation`: 仿真起止时间、交易所类型（`SZSE`/`NYSE`）。
  - `kernel.exchange_params`: OHLC/LOB 日志频率/档位、workers、撮合规则（T+1/涨跌幅/手续费/是否启用集合竞价）。
  - `kernel.agent_positions`: 代理初始仓位随机化区间。
  - `agents`: 代理类型与参数（详见下节 ABIDES 兼容）。
  - `symbols`: 挂牌标的列表。

## Agent 框架与示例策略

内置若干 ABIDES 风格策略适配器（位于 `core/agent`），全部使用当前消息协议：

- `zero_intelligence.py`：零智代理（示例）。
- `noise.py`（NoiseAgent）：随机小额限价/市价批量下单；不放回抽样标的；卖出时若库存不足退化为买入。
- `value.py`（ValueAgent）：若启用 Oracle，围绕参考收盘价在上下侧各布小额限价单；否则围绕随机参考价。
- `obi.py`（OrderBookImbalanceAgent）：查询盘口后按买/卖盘量能不平衡决定方向；若卖出无库存则改买入；价格锚定最优档，缺失回退到另一侧最优档。
- `hbl.py`（HeuristicBeliefLearningAgent）：近似 HBL；先查询盘口，随后在买/卖之间交替下单；卖出无库存时改买入。
- `fundamental.py`（FundamentalTrackingAgent）：与 ValueAgent 类似，但更强调均值回归（买价略低、卖价略高于参考）。

所有代理都通过 `BaseAgent` 统一处理成交反馈（`ORDER_EXECUTED`），自动更新资金/持仓。若某个代理在构造时启用 `track_performance=True`，则每次被唤醒时都会记录一条包含现金、总资产与收益的快照到 `log/agents/<agent>.csv`（默认不开启）。基础类还提供：

- `current_total_value(price_map=None)`：按最新成交价或自定义价格字典计算资产净值。
- `get_profit(price_map=None)`：返回相对初始净值的收益。
- `performance_snapshot(price_map=None)`：生成包含现金、净值、收益与持仓的 JSON 结构，供后处理或自定义日志使用。
- `log_performance(timestamp=None, price_map=None)`：显式写入一条代理日志（内部调用 `logger.agent_log`）。

## 与 ABIDES 的兼容与迁移

- 保留 ABIDES 原仓库到 `abides/` 目录，便于查阅原始实现与接口风格。
- 消息风格兼容：支持 ABIDES 风格的文本语义（限价/市价/改/撤/查询/订阅等）映射为当前枚举协议。
- 代理适配：已提供 Noise/Value/OBI/HBL/Fundamental 等适配器，可作为迁移模板。
- 迁移建议：
  1. 生命周期：`FinancialAgent/TradingAgent` → `BaseAgent`；方法改 `kernelInitializing/receiveMessage` 为 `wakeup/receive`。
  2. 消息：将 ABIDES 文本消息改为 `MessageType.*`（尤其 `SUBMIT_ORDER` 的批量 `requests`）。
  3. 订单/仓位：使用当前订单字典结构；成交回报统一由 `BaseAgent` 应用到 `Portfolio`。
  4. 日志：打印改为 `Logger`；行情快照由交易所模块按配置落盘。

更多详情见论文 `paper/doc/sections/module_design.tex` 中“ABIDES 代理适配与动作逻辑/迁移指南”。

## 测试与验证

- 单元测试（建议安装 pytest）：

```bash
pytest -q tests/core/agents/test_noise_agent.py
pytest -q tests/core/agents/test_value_agent.py
pytest -q tests/core/agents/test_obi_agent.py
pytest -q tests/core/agents/test_hbl_agent.py
pytest -q tests/core/agents/test_fundamental_agent.py
pytest -q tests/core/test_exchange_compat.py
```

- 一键仿真（覆盖所有示例代理）：

```bash
python scripts/run_all_agents.py
# 或使用自定义配置
python scripts/run_all_agents.py config/test_agents.json
```

## 贡献与开发

- 代码风格：PEP 8；类型提示完备；Black/Isort 友好。
- 日志与性能注意：在大规模实验中可通过 `exchange_params` 调低日志频率以减少 IO。
- 欢迎通过 Issue/PR 讨论新策略、性能优化或更广泛的 ABIDES 兼容。

## 致谢

- 本项目参考并兼容 [ABIDES](https://github.com/abides-sim/abides) 的若干理念与风格，感谢原作者与社区贡献。
