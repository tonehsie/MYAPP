import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from scipy.signal import argrelextrema

st.set_page_config(layout="wide", page_title="專業級量化分析系統 V6 Debug")
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

st.title("高階圖表：底層轉折點除錯視角")

with st.sidebar:
    st.header("特徵提取參數")
    stock_id = st.text_input("股票代號", "2330")
    start_date = st.text_input("起始日期", "2023-01-01")
    st.markdown("---")
    st.subheader("核心參數調整")
    order_val = st.slider("轉折靈敏度 (Order)", min_value=3, max_value=40, value=10, 
                          help="決定掃描的視窗大小。數值越小，抓出的轉折點越多；數值越大，只保留大波段轉折。")

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
    # 使用 scipy 嚴格抓取極端值
    peaks_idx = argrelextrema(df['max'].values, np.greater, order=order_val)[0]
    troughs_idx = argrelextrema(df['min'].values, np.less, order=order_val)[0]
    
    df['peak'] = np.nan
    df.iloc[peaks_idx, df.columns.get_loc('peak')] = df.iloc[peaks_idx]['max']
    
    df['trough'] = np.nan
    df.iloc[troughs_idx, df.columns.get_loc('trough')] = df.iloc[troughs_idx]['min']

    # 繪製圖表
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
    
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['max'], low=df['min'], close=df['close'], 
                                 name="K線", increasing_line_color='#FF3333', decreasing_line_color='#00FF00'), row=1, col=1)

    # 顯示所有偵測到的波峰 (紅色倒三角形)
    fig.add_trace(go.Scatter(x=df.index, y=df['peak'], mode='markers', 
                             marker=dict(color='black', size=10, symbol='triangle-down', line=dict(color='#FF3333', width=2)),
                             name=f"波峰 (Order={order_val})"), row=1, col=1)

    # 顯示所有偵測到的波谷 (綠色正三角形)
    fig.add_trace(go.Scatter(x=df.index, y=df['trough'], mode='markers', 
                             marker=dict(color='black', size=10, symbol='triangle-up', line=dict(color='#00FF00', width=2)),
                             name=f"波谷 (Order={order_val})"), row=1, col=1)

    # 為了方便觀察，將相鄰的波峰波谷用虛線連起來，呈現價格的折線輪廓
    turns = []
    for d, r in df.dropna(subset=['peak']).iterrows(): turns.append({'date': d, 'price': r['peak']})
    for d, r in df.dropna(subset=['trough']).iterrows(): turns.append({'date': d, 'price': r['trough']})
    turns = sorted(turns, key=lambda x: x['date'])
    
    if len(turns) > 0:
        fig.add_trace(go.Scatter(x=[t['date'] for t in turns], y=[t['price'] for t in turns], 
                                 mode='lines', line=dict(color='rgba(255,255,255,0.3)', width=1, dash='dot'), 
                                 name="價格輪廓線"), row=1, col=1)

    colors = ['#FF3333' if r['close'] >= r['open'] else '#00FF00' for i, r in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Trading_Volume'], marker_color=colors, name="成交量"), row=2, col=1)

    fig.update_layout(template="plotly_dark", height=850, xaxis_rangeslider_visible=False,
                      plot_bgcolor='rgb(17, 17, 17)', paper_bgcolor='rgb(17, 17, 17)', hovermode='x unified')
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])], gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(gridcolor='rgba(255,255,255,0.1)')
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("讀取失敗，請檢查資料來源或 Token。")
