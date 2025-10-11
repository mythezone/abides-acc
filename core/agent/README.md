# Agent 框架概览

`core.agent` 模块提供了在 ABIDES-ACC 中构建交易智能体的通用基类与示例实现。所有智能体都继承自 `BaseAgent`，并通过消息队列与内核 (`Kernel`) 以及交易所 (`Exchange`) 交互。常用内置智能体包括基础的噪声/价值策略、集合竞价背景代理、订单簿不平衡策略以及用于回放历史行情的 Oracle 等。

## 消息交互模型

- **发送:** 代理通过 `BaseAgent.send()` 将 `Message` 对象写入其共享的 `MessageQueue`。内核会按照时间顺序拉取消息并转发给目标组件。
- **批量请求:** 向交易所下单或发起查询时，约定使用单条消息承载一个 `requests` 列表。例：
  ```python
  msg = new_message(
      message_type=MessageType.SUBMIT_ORDER,
      sender_id=self.id,
      recipient_id="Exchange",
      send_time=self.current_time,
      recive_time=self.current_time,
      content={"requests": [order_req_1, order_req_2]},
  )
  ```
  交易所会逐项处理列表中的请求。
- **查询工具:** `BaseAgent` 提供了便捷方法来构造行情查询消息，便于在同一批次中混合下单与信息请求。

## 继承 `BaseAgent` 的基本步骤

1. **初始化**
   ```python
   class MyAgent(BaseAgent):
       def __init__(self, id: str, *args, **kwargs):
           super().__init__(id, *args, **kwargs)
           # 自定义状态
   ```
   - `BaseAgent` 会自动创建消息队列、投资组合与随机地理位置，如需额外参数可通过 `kwargs` 传入并在子类中保存。

2. **调度唤醒**
   - `BaseAgent.wakeup()` 会在收到 `WAKEUP` 消息时调用：
     ```python
     def wakeup(self, current_time):
         self.current_time = current_time
         self.set_next_wakeup(current_time)  # 安排下一次唤醒
         self.process_inbox()                # 处理执行回报等
         self.action()                      # 执行策略逻辑
     ```
   - 如需自定义节奏，可覆写 `wakeup_delay()` 返回毫秒值，或在 `wakeup()` 中直接调用 `set_next_wakeup(current_time, intelver=desired_ms)`。

3. **处理消息**
   - 覆写 `receive()` 以捕获特定消息类型；默认实现会把消息存入 `inbox`，`process_inbox()` 会自动结算 `ORDER_EXECUTED` 并更新组合。
   - 建议在 `process_inbox()` 后保留未消费的消息，以免错过后续处理。

4. **构建并发送请求**
   - 下单：构建 `dict` 请求放入 `requests` 列表，调用 `new_message` 后通过 `send()` 发送。
   - 行情/基本面查询：使用内置 helper 组装消息，然后与其他请求一起发送。
     ```python
     queries = []
     q1 = self.build_fundamental_query(["AAA", "BBB"])
     q2 = self.build_top_of_book_query(["AAA"], depth=2)
     for q in (q1, q2):
         if q:
             queries.append(q)
     for msg in queries:
         self.send(msg)
     ```
     每条消息独立处理，便于与下单请求混排。

## `BaseAgent` 常用 API

- `set_next_wakeup(current_time, intelver=-1)`: 依据 `wakeup_delay()` 结果安排下一次唤醒。
- `build_fundamental_query(symbols)`: 构造 `QUERY_FUNDAMENTAL` 消息，当前交易所会返回各标的当前 LOB 中间价（代码中标明 TODO，后续可替换为真实基本面数据）。
- `build_top_of_book_query(symbols, depth=1)`: 构造 `QUERY_TOP_OF_BOOK` 消息，返回最优买卖价及前 `depth` 档委托。
- `request_oracle(symbol, kind="lob")`: 在校准模式下向外部 Oracle 请求 LOB/OHLC 数据。

## 编写自定义 Agent 时的注意事项

- **消息列表:** 代理在单次 `action()` 中通常会生成一个列表，包含下单、撤单、行情查询等不同消息。调用 `send()` 逐条推送即可，内核会保持时间戳顺序。
- **时间同步:** 统一使用 `self.current_time` 作为消息的 `send_time` 与 `recive_time`，确保内核时间线一致。
- **资源限制:** 若策略需要事件驱动的更高频唤醒，可在 `wakeup_delay()` 中根据市场状态调节返回值。
- **日志:** 若传入 `logger`，`send()` 将记录消息流转，便于调试。

## 现有 Agent 目录备忘

- `background.py` — 集合竞价阶段的背景买卖盘。
- `noise.py`, `value.py`, `zero_intelligence.py` — 基础噪声/价值/零智策略。
- `nero_zero_intelligence.py` — 加入价格记忆与基本面查询的“近似零智”版本。
- `fundamental.py`, `fcn.py` — 基于基本面与预测价格的均值回归类策略。
- `bdi.py` — 依据技术指标构建信念-愿望-意图（BDI）的认知型做市代理。
- `chartist.py` — 趋势跟随者，比较价格与移动均线偏差决定买卖。
- `gp.py` — 借助遗传程序生成价格预期与保留价，动态切换市价/限价执行。
- `informed_or_not.py` — 拥有私有估值的“消息灵通”代理，根据期望头寸选择市价或限价。
- `liquidity_provider.py`, `liquidity_taker.py` — 分别模拟做市/吃单侧流动性参与者。
- `oracle.py`, `replay.py` — 回放/参考外部行情。
- `hbl.py`, `obi.py` — 启发式信念学习与订单簿不平衡策略。

可按照上述步骤派生新的 Agent，与交易所通过统一的消息协议交互。
