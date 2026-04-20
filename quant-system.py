import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from scipy.signal import argrelextrema

# 介面設定
st.set_page_config(layout="wide", page_title="專業級量化分析系統 V2")

TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

st.title("高階圖表：自動型態轉折辨識系統")

# 控制面板
with st.sidebar:
    st.header("演算法參數設定")
    stock_id = st.text_input("股票代號", "2330")
    start_date = st.text_input("起始日期", "2023-01-01")
    # order 參數決定了型態的「規模」，數值越大，抓到的轉折越具代表性
    order_val = st.slider("辨識靈敏度 (Order)", min_value=5, max_value=30, value=10)

@st.cache_data
def get_data(stock_id, start_date):
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {"dataset": "TaiwanStockPrice", "data_id": stock_id, "start_date": start_date, "token": TOKEN}
    res = requests.get(url, params=params).json()
    if res.get("status") == 200 and len(res.get("data", [])) > 0:
        df = pd.DataFrame(res["data"])
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        return df
    return None

df = get_data(stock_id, start_date)

if df is not None:
    # 數學運算：尋找波峰與波谷
    # 使用 scipy 尋找局部極大值與極小值
    df['peak'] = df.iloc[argrelextrema(df['max'].values, np.greater, order=order_val)[0]]['max']
    df['trough'] = df.iloc[argrelextrema(df['min'].values, np.less, order=order_val)[0]]['min']

    # 繪圖
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])

    # K 線圖
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['max'], low=df['min'], close=df['close'], name="K線",
                                 increasing_line_color='red', decreasing_line_color='green'), row=1, col=1)

    # 自動標註波峰 (紅點)
    fig.add_trace(go.Scatter(x=df.index, y=df['peak'], mode='markers', 
                             marker=dict(color='white', size=8, symbol='triangle-down', line=dict(color='red', width=2)),
                             name="波峰 (Peak)"), row=1, col=1)

    # 自動標註波谷 (綠點)
    fig.add_trace(go.Scatter(x=df.index, y=df['trough'], mode='markers', 
                             marker=dict(color='white', size=8, symbol='triangle-up', line=dict(color='green', width=2)),
                             name="波谷 (Trough)"), row=1, col=1)

    # 成交量
    colors = ['red' if r['close'] >= r['open'] else 'green' for i, r in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Trading_Volume'], marker_color=colors, name="成交量"), row=2, col=1)

    fig.update_layout(template="plotly_dark", height=800, xaxis_rangeslider_visible=False)
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("讀取失敗，請檢查代號或 Token。")
