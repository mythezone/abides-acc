# Ours 撮合重放实验

本实验用于对比 ABIDES-ACC 仿真撮合结果与真实 LOB 之间的差异。我们基于 `MAXE-RJJ` 提供的深度订单流数据，按照历史时间顺序重放订单，并记录交易所撮合后生成的十档订单簿快照，从而与真实市场中间价走势进行对比。

## 数据与设置

- 历史订单：`comparison/order_match/MAXE-RJJ/sz000001_RJJ.csv`
- 真实 LOB：`comparison/order_match/MAXE-RJJ/data.csv`（包含真实十档信息，可用于绘制基准中间价）
- 仿真配置：`comparison/order_match/Ours/config.json`
- 复现代理：`HistoricalOrderReplayAgent`（`core/agent/replay.py`），会将历史订单逐条转换为交易所可识别的消息，并在每次撮合后触发 LOB 快照记录。由于原始数据的 `CANCEL_TYPE` 字段缺乏明确释义，当前实现会忽略该列，将所有记录按市价/限价单重放。

仿真仅包含一个标的 `SZ000001`，且只有一个代理负责按历史时间发送订单。交易所禁用手续费、涨跌幅与 T+1 约束，以贴合历史成交逻辑。

## 运行步骤

1. 创建虚拟环境并安装依赖（如未完成）：
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   ```
2. 在项目根目录执行实验脚本（数据量较大，完整重放约需 15 分钟）：
   ```bash
   python comparison/order_match/Ours/run_experiment.py --config comparison/order_match/Ours/config.json
   ```

运行完成后会生成：

- `comparison/order_match/Ours/log/<symbol>/lob.csv`：仿真得到的十档订单簿时间序列。
- `comparison/order_match/Ours/log/mid_price.csv`：提取的仿真中间价，便于与真实数据绘图对比。

## 可视化与对比

- 使用 `comparison/order_match/MAXE-RJJ/data.csv` 中的 `AskPrice1`/`BidPrice1` 可计算真实中间价，与 `log/mid_price.csv` 中的仿真中间价折线图对比。
- 如需进一步分析，可在 `Ashare.ipynb` 中读取上述 CSV 文件绘制对比图或进行误差统计。

## 配置项说明

`config.json` 中的关键字段：

- `orders_csv`：历史订单文件路径。
- `start_time`：仿真开始时间（用于将 `SIMUTIME` 偏移转化为绝对时间）。
- `log_tick_after`：是否在每笔订单后请求一次 `LOG_TICK`，以确保记录最新的十档 LOB。
- `lob_log_level`：设置为 `10`，使日志输出十档深度。

如需复用本实验框架替换其他数据，只需调整 `orders_csv`、`symbol` 及仿真起止时间即可。
