import pandas as pd
import plotly.graph_objects as go
import gradio as gr
from io import StringIO


from pathlib import Path

def parse_and_plot(file):
    # file 是一个路径字符串或 NamedString，我们先读取文件内容
    if hasattr(file, "name"):  # 兼容 NamedString 类型
        file_path = file.name
    else:
        file_path = file

    # 读取 CSV 文件
    df = pd.read_csv(file_path, header=0)
    df.columns = [
        "Code", "Date", "Time", "Open", "High", "Low", "Close",
        "Volume", "Turnover", "MatchItems", "Interest"
    ]

    # 拼接时间字段
    df['Datetime'] = pd.to_datetime(df['Date'].astype(str) + df['Time'].astype(str).str.zfill(6), format='%Y%m%d%H%M%S')
    df.sort_values('Datetime', inplace=True)

    # 画蜡烛图
    fig = go.Figure(data=[
        go.Candlestick(
            x=df['Datetime'],
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            increasing_line_color='red',
            decreasing_line_color='green'
        )
    ])
    fig.update_layout(
        title='股票分时蜡烛图',
        xaxis_title='时间',
        yaxis_title='价格',
        xaxis_rangeslider_visible=True,
        height=600
    )

    return fig


# 使用 Gradio 创建界面
iface = gr.Interface(
    fn=parse_and_plot,
    inputs=gr.File(label="上传股票分钟级CSV文件（无表头）"),
    outputs=gr.Plot(label="交互式蜡烛图"),
    title="股票蜡烛图展示器",
    description="支持分钟级数据的交互式蜡烛图显示，支持缩放、拖动、文件上传"
)

# 启动服务
if __name__ == "__main__":
    iface.launch()
