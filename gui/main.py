import gradio as gr
from config.rmsc03_gui import build_simulation
from Kernel import Kernel
import argparse
import threading
import sys
import pandas as pd
import numpy as np
import contextlib
import io

# stop_signal = threading.Event()

def start_kernel_thread(sim_args):
    # global stop_signal
    # stop_signal.clear()

    simulation_params = build_simulation(sim_args)
    kernel = Kernel("RMSC03 Kernel", random_state=np.random.RandomState(sim_args.seed))

    # 重定向print输出到字符串
    with contextlib.redirect_stdout(io.StringIO()) as f:
        kernel.runner(
            agents=simulation_params['agents'],
            startTime=simulation_params['start_time'],
            stopTime=simulation_params['stop_time'],
            log_dir=simulation_params['log_dir'],
            oracle=simulation_params['oracle'],
            agentLatencyModel=simulation_params['agent_latency_model'],
            defaultComputationDelay=simulation_params['default_computation_delay']
        )

    return f.getvalue()

def run_simulation(config, ticker, historical_date, start_time, end_time,
                   log_dir, seed, verbose, execution_agents, execution_pov,
                   mm_pov, mm_window_size, mm_min_order_size, mm_num_ticks,
                   mm_wake_up_freq, mm_skew_beta, mm_level_spacing,
                   mm_spread_alpha, mm_backstop_quantity, fund_vol):

    sim_args = argparse.Namespace(
        config=config,
        ticker=ticker,
        historical_date=pd.to_datetime(historical_date),
        start_time=pd.to_datetime(start_time),
        end_time=pd.to_datetime(end_time),
        log_dir=log_dir if log_dir else None,
        seed=int(seed) if seed else int(pd.Timestamp.now().timestamp()) % (2 ** 32 - 1),
        verbose=verbose,
        execution_agents=execution_agents,
        execution_pov=execution_pov,
        mm_pov=mm_pov,
        mm_window_size=mm_window_size,
        mm_min_order_size=mm_min_order_size,
        mm_num_ticks=mm_num_ticks,
        mm_wake_up_freq=mm_wake_up_freq,
        mm_skew_beta=mm_skew_beta,
        mm_level_spacing=mm_level_spacing,
        mm_spread_alpha=mm_spread_alpha,
        mm_backstop_quantity=mm_backstop_quantity,
        fund_vol=fund_vol,
        config_help=False
    )

    output_holder = {}

    def run():
        output_holder['log'] = start_kernel_thread(sim_args)

    simulation_thread = threading.Thread(target=run)
    simulation_thread.start()
    simulation_thread.join()

    return output_holder['log']

# def stop_simulation():
#     stop_signal.set()
#     return "仿真已停止。"

iface = gr.Interface(
    fn=run_simulation,
    inputs=[
        gr.Textbox(label="配置文件(config)", value="rmsc03"),
        gr.Textbox(label="股票代码(ticker)", value="ABM"),
        gr.Textbox(label="历史模拟日期(historical-date)", value="20240403"),
        gr.Textbox(label="开始时间(start-time)", value="09:30:00"),
        gr.Textbox(label="结束时间(end-time)", value="10:30:00"),
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
    title="ABIDES仿真运行器 - RMSC03集成Kernel",
    description="设置参数并点击开始按钮启动ABIDES仿真。",
    allow_flagging='never'
)

# with gr.Blocks() as demo:
#     iface.render()
#     stop_btn = gr.Button("停止仿真")
#     stop_btn.click(fn=stop_simulation, outputs=iface.output_components)

# demo.launch()
iface.launch()