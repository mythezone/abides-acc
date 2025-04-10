import gradio as gr 
from gui.init.agent import Agents
from core.symbol import Symbol, Symbol
from gui.init.simulator import Simulator


simulator = Simulator()
# TODO: 待完善下面的Symbol调用
symbols = Symbol()
agents = Agents(simulator=simulator)



with gr.Blocks() as demo:
    gr.Markdown("## ABIDES仿真运行器 - 集成Kernel")

    with gr.Column():
        gr.Markdown("### 配置仿真器")

        with gr.Row():
            gr.Markdown("#### 仿真器配置")

            

            historical_date = gr.Textbox(label="历史模拟日期(historical-date)", value="20240403")
            
            start_time = gr.Textbox(label="开始时间(start-time)", value="09:30:00")
            end_time = gr.Textbox(label="结束时间(end-time)", value="16:30:00")
            stream_history_length = gr.Textbox(label="历史数据流长度(stream_history)", value="25000")
            with gr.Accordion():
                log_dir = gr.Textbox(label="日志目录(log_dir)", value="./logs")
                verbose = gr.Checkbox(label="详细输出(verbose)", value=False)
                exchange_log_orders = gr.Checkbox(label="交易所记录订单日志", value=False)
                log_orders = gr.Checkbox(label="执行代理记录订单日志", value=False)
                book_freq = gr.Textbox(label="订单簿更新频率", value="0")
                starting_cash = gr.Number(label="初始现金（分）(starting_cash)", value=1000000)

            init_market_btn = gr.Button("初始化仿真器")
            ### 初始化仿真器函数
            init_market_btn.click(
                fn=simulator.init,
                inputs=[historical_date, start_time, end_time, stream_history_length, log_dir, verbose, exchange_log_orders, book_freq,starting_cash],
                outputs=None
            )

        with gr.Row():
            gr.Markdown("#### 股票参数")

            name = gr.Textbox(label="股票代码(ticker)", value="ABM")
            starting_cash = gr.Number(label="初始现金（分）(starting_cash)", value=1000000)

            r_bar = gr.Number(label="R_bar", value=1e5)
            kappa = gr.Number(label="Kappa", value=1.67e-15)
            sigma_s = gr.Number(label="Sigma_s", value=0)
            lambda_a = gr.Number(label="Lambda_a", value=7e-11)
            fund_vol = gr.Number(label="基础波动率(fund_vol)", value=1e-8)
            megashock_lambda_a = gr.Number(label="Megashock_lambda_a", value=2.77778e-18)
            megashock_mean = gr.Number(label="Megashock_mean", value=1e3)
            megashock_var = gr.Number(label="Megashock_var", value=5e4)

            add_symbol_btn = gr.Button("添加股票")


            ### 添加股票函数
            add_symbol_btn.click(
                fn=symbols.add_symbol,
                inputs=[name, r_bar, kappa, sigma_s, fund_vol, megashock_lambda_a, megashock_mean, megashock_var],
                outputs=None
            )


        with gr.Row():
            gr.Markdown("#### 代理类型")
            with gr.Tabs():

                with gr.Tab("执行代理"):
                    gr.Markdown("##### EXCHANGE_AGENT")
                    exchange_agent_type = gr.Textbox(label="代理类型", value="ExchangeAgent")
                    exchange_agent_simbols = gr.Textbox(label="股票代码(ticker),多个请用逗号隔开", value="ABM")

                    
                    add_exchange_agent_btn = gr.Button("添加执行代理")

                with gr.Tab("噪声代理"):
                    gr.Markdown("##### Noise Agents")
                    noise_agent_type = gr.Textbox(label="代理类型", value="NoiseAgent")
                    noise_agent_simbols = gr.Textbox(label="股票代码(ticker)", value="ABM")
                    noise_agent_num = gr.Number(label="噪声代理数量", value=5000)

                    add_noise_agent_btn = gr.Button("添加噪声代理")


            ### 添加执行代理函数
            add_exchange_agent_btn.click(
                fn=agents.add_agent,
                inputs=[exchange_agent_type, exchange_agent_simbols],
                outputs=None
            )
            add_noise_agent_btn.click(
                fn=agents.add_agent,
                inputs=[noise_agent_type, noise_agent_simbols,noise_agent_num],
                outputs=None
            )


demo.launch(debug=True)

                



