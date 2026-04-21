import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 設定網頁全寬與標題
st.set_page_config(layout="wide", page_title="專業級量化互動圖表")

# 帶入您的 FinMind Token
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

st.title("高階互動式技術分析圖表")

# 建立輸入介面
col1, col2 = st.columns(2)
with col1:
    stock_id = st.text_input("輸入股票代號 (例如: 2330)", "2330")
with col2:
    start_date = st.text_input("輸入起始日期 (例如: 2023-01-01)", "2023-01-01")

# 透過 FinMind API 抓取資料
@st.cache_data
def get_stock_data(stock_id, start_date):
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": stock_id,
        "start_date": start_date,
        "token": TOKEN
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    if data.get("status") == 200 and len(data.get("data", [])) > 0:
        df = pd.DataFrame(data["data"])
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        # 計算常用的高階參考線：10日、20日、60日均線
        df['MA10'] = df['close'].rolling(window=10).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()
        df['MA60'] = df['close'].rolling(window=60).mean()
        return df
    return None

df = get_stock_data(stock_id, start_date)

if df is not None:
    # 建立多副圖的專業版面：上方 K 線與均線，下方成交量
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, 
                        row_heights=[0.7, 0.3])

    # 1. 繪製 K 線圖 (Candlestick)，設定為台灣習慣的紅漲綠跌
    fig.add_trace(go.Candlestick(x=df.index,
                                 open=df['open'], high=df['max'],
                                 low=df['min'], close=df['close'],
                                 name="K線",
                                 increasing_line_color='red',
                                 decreasing_line_color='green'),
                  row=1, col=1)

    # 2. 繪製均線系統
    fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], line=dict(color='orange', width=1.5), name="10日均線"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='cyan', width=1.5), name="20日均線"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='magenta', width=1.5), name="60日季線"), row=1, col=1)

    # 3. 繪製成交量柱狀圖 (配合漲跌變色)
    colors = ['red' if row['close'] >= row['open'] else 'green' for index, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Trading_Volume'], marker_color=colors, name="成交量"), row=2, col=1)

    # 4. 圖表版面高階質感微調與互動控制
    fig.update_layout(
        template="plotly_dark",
        height=850,
        xaxis_rangeslider_visible=True,  # 開啟下方時間滑桿
        dragmode="pan",                  # 預設滑鼠左鍵為「平移」
        showlegend=True,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    # 隱藏週末無交易的空白區間，讓線型連續
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])

    # 5. 輸出圖表，強制開啟滾輪縮放與工具列
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': True})
else:
    st.error("查無資料，請確認代號或日期是否正確，或您的 Token 權限是否正常。")
