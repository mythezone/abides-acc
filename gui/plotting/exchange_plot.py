import os
import pandas as pd
import plotly.graph_objects as go
import gradio as gr
from plotly.subplots import make_subplots


DATA_FOLDER = "data/ochl/10m"  # 替换为你的实际目录
# DATA_FOLDER = "data/ochl/tick"

def get_stock_file_list():
    files = [f for f in os.listdir(DATA_FOLDER) if f.endswith(('.csv', '.CSV', '.txt'))]
    stock_list = []
    for fname in sorted(files):
        base = os.path.splitext(fname)[0]
        parts = base.split('-')
        if len(parts) >= 2:
            display_name = f"{parts[0]} ({parts[1]})"
        else:
            display_name = base
        stock_list.append((display_name, fname))
    return stock_list

def make_plot(file_name):
    file_path = os.path.join(DATA_FOLDER, file_name)
    with open(file_path, 'r') as f:
        first_line = f.readline()
    has_header = 'Date' in first_line

    df = pd.read_csv(file_path, header=0 if has_header else None)
    if not has_header:
        df.columns = [
            "Code", "Date", "Time", "Open", "High", "Low", "Close",
            "Volume", "Turnover", "MatchItems", "Interest"
        ]
        # Code,Date,Time,Price,MatchItems,BSFlag,AccVolume,AccTurover,High,Low,Open,Close,PreClose,IOPV,NAV,ChangePCT1,ChangePCT2,PE1,PE2,TradingPhaseCode,AskPrice1,AskPrice2,AskPrice3,AskPrice4,AskPrice5,AskVolume1,AskVolume2,AskVolume3,AskVolume4,AskVolume5,BidPrice1,BidPrice2,BidPrice3,BidPrice4,BidPrice5,BidVolume1,BidVolume2,BidVolume3,BidVolume4,BidVolume5
        # df.columns = [
        #     "Code", "Date", "Time", "Price", "MatchItems", "BSFlag",
        #     "AccVolume", "AccTurnover", "High", "Low", "Open", "Close",
        #     "PreClose", "IOPV", "NAV", "ChangePCT1", "ChangePCT2",
        #     "PE1", "PE2", "TradingPhaseCode", "AskPrice1", "AskPrice2",
        #     "AskPrice3", "AskPrice4", "AskPrice5", "AskVolume1",
        #     "AskVolume2", "AskVolume3", "AskVolume4", "AskVolume5",
        #     "BidPrice1", "BidPrice2", "BidPrice3", "BidPrice4",
        #     "BidPrice5", "BidVolume1", "BidVolume2", "BidVolume3",
        #     "BidVolume4", "BidVolume5"
        # ]
    df = df[df['Date'] != 'Date']

    df['Datetime'] = pd.to_datetime(
        df['Date'].astype(str) + df['Time'].astype(str).str.zfill(6),
        format='%Y%m%d%H%M%S'
    )

    # 仅保留交易时段
    df = df[(df['Datetime'].dt.time >= pd.to_datetime("09:30:00").time()) &
            (df['Datetime'].dt.time <= pd.to_datetime("11:30:00").time()) |
            (df['Datetime'].dt.time >= pd.to_datetime("13:00:00").time()) &
            (df['Datetime'].dt.time <= pd.to_datetime("15:00:00").time())]

    df = df.sort_values('Datetime').reset_index(drop=True)

    # 构造横轴 index 和显示时间
    index = list(range(len(df)))
    tickvals = index
    ticktext = df['Datetime'].dt.strftime('%H:%M')

    # 构造 hover 信息
    df['TimeStr'] = df['Datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
    customdata = df[['TimeStr', 'Open', 'High', 'Low', 'Close', 'Volume']].values

    hovertext_list = [
    f"时间: {row.TimeStr}<br>"
    f"开盘: {row.Open:.2f}<br>"
    f"最高: {row.High:.2f}<br>"
    f"最低: {row.Low:.2f}<br>"
    f"收盘: {row.Close:.2f}<br>"
    f"成交量: {int(row.Volume):,}"
    for row in df.itertuples()
    ]

    fig = go.Figure()
    # # 创建上下两图布局（共享 x 轴）
    # fig = make_subplots(rows=2, cols=1,
    #                     shared_xaxes=True,
    #                     row_heights=[0.7, 0.3],
    #                     vertical_spacing=0.02,
    #                     specs=[[{"type": "candlestick"}], [{"type": "bar"}]])

    # # 成交量（下图）
    # fig.add_trace(go.Bar(
    #     x=index,
    #     y=df['Volume'],
    #     name='成交量',
    #     marker_color='lightgray',
    #     hovertext=hovertext_list,
    #     hoverinfo='text'
    # ), row=2, col=1)

    # # 蜡烛图（上图）
    # fig.add_trace(go.Candlestick(
    #     x=index,
    #     open=df['Open'],
    #     high=df['High'],
    #     low=df['Low'],
    #     close=df['Close'],
    #     name='价格',
    #     increasing_line_color='red',
    #     decreasing_line_color='green',
    #     hovertext=hovertext_list,
    #     hoverinfo='text'
    # ), row=1, col=1)

    # # 设置 x 轴显示为时间字符串
    # tickvals = index
    # ticktext = df['Datetime'].dt.strftime('%H:%M')

    # fig.update_layout(
    #     height=600,
    #     xaxis=dict(
    #         tickmode='array',
    #         tickvals=tickvals[::30],
    #         ticktext=ticktext[::30],
    #         title='时间'
    #     ),
    #     yaxis=dict(title='价格'),
    #     yaxis2=dict(title='成交量'),
    #     showlegend=False,
    #     hovermode='x unified'
    # )
    # 成交量柱图
    fig.add_trace(go.Bar(
        x=index,
        y=df['Volume'],
        name='成交量',
        # marker_color='lightgray',
        yaxis='y2',
        customdata=customdata,
        marker_color='rgba(200, 200, 200, 0.5)',
    ))

    # 蜡烛图
    fig.add_trace(go.Candlestick(
        x=index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='价格',
        increasing_line_color='red',
        decreasing_line_color='green',
        customdata=customdata,
        hovertext=hovertext_list,
        hoverinfo='text',
    ))

    

    fig.update_layout(
        title=file_name,
        xaxis=dict(
            title='时间',
            tickmode='array',
            tickvals=tickvals[::30],
            ticktext=ticktext[::30]
        ),
        yaxis=dict(title='价格', side='right'),
        yaxis2=dict(title='成交量', overlaying='y', side='left', showgrid=False),
        xaxis_rangeslider_visible=False,
        height=500,
        legend=dict(orientation='h', x=0, y=1.1),
        hovermode='x unified'
    )
    return fig

def plot_multiple(file_names):
    plots = [make_plot(f) for f in file_names]
    while len(plots) < 3:
        plots.append(None)
    return plots[:3]

file_choices = get_stock_file_list()

with gr.Blocks() as demo:
    gr.Markdown("# 📈 多股票交互式蜡烛图")
    selector = gr.CheckboxGroup(choices=file_choices, label="选择股票（最多选3个）")
    plot1 = gr.Plot()
    plot2 = gr.Plot()
    plot3 = gr.Plot()

    selector.change(fn=plot_multiple, inputs=selector, outputs=[plot1, plot2, plot3])

if __name__ == "__main__":
    demo.launch()
