# gui/main.py
import gradio as gr
import subprocess
import threading
import sys
import os

def run_simulation(config, ticker, historical_date, start_time, end_time,
                   log_dir, seed, verbose, execution_agents, execution_pov,
                   mm_pov, mm_window_size, mm_min_order_size, mm_num_ticks,
                   mm_wake_up_freq, mm_skew_beta, mm_level_spacing,
                   mm_spread_alpha, mm_backstop_quantity, fund_vol):

    cmd = [
        sys.executable, "./config/rmsc03.py",
        '-c', config,
        '-t', ticker,
        '-d', historical_date,
        '--start-time', start_time,
        '--end-time', end_time,
        '-p', str(execution_pov),
        '--mm-pov', str(mm_pov),
        '--mm-window-size', mm_window_size,
        '--mm-min-order-size', str(mm_min_order_size),
        '--mm-num-ticks', str(mm_num_ticks),
        '--mm-wake-up-freq', mm_wake_up_freq,
        '--mm-skew-beta', str(mm_skew_beta),
        '--mm-level-spacing', str(mm_level_spacing),
        '--mm-spread-alpha', str(mm_spread_alpha),
        '--mm-backstop-quantity', str(mm_backstop_quantity),
        '--fund-vol', str(fund_vol)
    ]

    if log_dir:
        cmd += ['-l', log_dir]

    if seed:
        cmd += ['-s', str(seed)]

    if verbose:
        cmd += ['-v']

    if execution_agents:
        cmd += ['-e']

    # 执行命令并捕获输出
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    # 将输出实时显示到Gradio界面
    for line in process.stdout:
        yield line

# Gradio界面定义
iface = gr.Interface(
    fn=run_simulation,
    inputs=[
        gr.Textbox(label="配置文件(config)", value="rmsc03"),
        gr.Textbox(label="股票代码(ticker)", value="ABM"),
        gr.Textbox(label="历史模拟日期(historical-date)", value="20240403"),
        gr.Textbox(label="开始时间(start-time)", value="09:30:00"),
        gr.Textbox(label="结束时间(end-time)", value="16:30:00"),
        gr.Textbox(label="日志目录(log_dir)", value=""),
        gr.Number(label="随机种子(seed)", value=None),
        gr.Checkbox(label="详细输出(verbose)", value=False),
        gr.Checkbox(label="执行代理交易(execution_agents)", value=False),
        gr.Slider(label="执行代理交易占比(execution_pov)", minimum=0, maximum=1, step=0.01, value=0.1),
        gr.Slider(label="做市商交易量占比(mm_pov)", minimum=0, maximum=1, step=0.01, value=0.025),
        gr.Textbox(label="做市商窗口大小(mm_window_size)", value="adaptive"),
        gr.Number(label="做市商最小订单大小(mm_min_order_size)", value=1),
        gr.Number(label="做市商档位数量(mm_num_ticks)", value=10),
        gr.Textbox(label="做市商唤醒频率(mm_wake_up_freq)", value="10S"),
        gr.Number(label="做市商偏斜系数(mm_skew_beta)", value=0.0),
        gr.Number(label="做市商订单层间距(mm_level_spacing)", value=5.0),
        gr.Number(label="做市商点差因子(mm_spread_alpha)", value=0.75),
        gr.Number(label="做市商后备数量(mm_backstop_quantity)", value=50000),
        gr.Number(label="基础波动率(fund_vol)", value=1e-8)
    ],
    outputs=gr.Textbox(label="运行日志输出", lines=30),
    title="ABIDES仿真运行器 - RMSC03配置",
    description="设置参数并点击开始按钮启动ABIDES仿真。",
    allow_flagging='never'
)

iface.launch()