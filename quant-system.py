import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from scipy.signal import argrelextrema

# 介面設定
st.set_page_config(layout="wide", page_title="專業級量化分析系統 V3")

TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

st.title("高階圖表：W底 (雙底) 形態自動掃描與繪製")

with st.sidebar:
    st.header("演算法參數設定")
    stock_id = st.text_input("股票代號", "2330")
    start_date = st.text_input("起始日期", "2023-01-01")
    order_val = st.slider("轉折靈敏度 (Order)", min_value=5, max_value=30, value=10)
    # 新增：雙底誤差容忍度
    tolerance = st.slider("底部價格誤差容忍度 (%)", min_value=1.0, max_value=10.0, value=3.0, step=0.5)

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
    # 1. 尋找所有局部極值 (波峰與波谷)
    peaks_idx = argrelextrema(df['max'].values, np.greater, order=order_val)[0]
    troughs_idx = argrelextrema(df['min'].values, np.less, order=order_val)[0]
    
    df['peak'] = np.nan
    df.iloc[peaks_idx, df.columns.get_loc('peak')] = df.iloc[peaks_idx]['max']
    
    df['trough'] = np.nan
    df.iloc[troughs_idx, df.columns.get_loc('trough')] = df.iloc[troughs_idx]['min']

    # 2. 幾何形態辨識邏輯：W底 (雙底)
    # 將波峰與波谷依時間順序合併成一個序列
    turns = []
    for date, row in df.dropna(subset=['peak']).iterrows():
        turns.append({'date': date, 'type': 'peak', 'price': row['peak']})
    for date, row in df.dropna(subset=['trough']).iterrows():
        turns.append({'date': date, 'type': 'trough', 'price': row['trough']})
    
    # 依日期排序轉折點
    turns = sorted(turns, key=lambda x: x['date'])
    
    w_patterns = []
    # 掃描連續三個轉折點
    for i in range(len(turns) - 2):
        p1, p2, p3 = turns[i], turns[i+1], turns[i+2]
        
        # 條件 1: 必須是 谷 -> 峰 -> 谷
        if p1['type'] == 'trough' and p2['type'] == 'peak' and p3['type'] == 'trough':
            # 條件 2: 兩個谷底的價格誤差在容忍度內 (例如 3%)
            price_diff_pct = abs(p1['price'] - p3['price']) / p1['price'] * 100
            if price_diff_pct <= tolerance:
                # 條件符合，記錄這個 W 底的座標
                w_patterns.append([p1, p2, p3])

    # 3. 繪製高階圖表
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])

    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['max'], low=df['min'], close=df['close'], name="K線",
                                 increasing_line_color='red', decreasing_line_color='green'), row=1, col=1)

    # 畫出系統找到的所有 W 底形態連線與頸線
    for idx, pattern in enumerate(w_patterns):
        t1, p_neck, t2 = pattern
        
        # 畫 V 字與倒 V 字的連線 (W的形狀)
        x_vals = [t1['date'], p_neck['date'], t2['date']]
        y_vals = [t1['price'], p_neck['price'], t2['price']]
        fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='lines', 
                                 line=dict(color='yellow', width=3, dash='solid'),
                                 name=f"W底形態 {idx+1}"), row=1, col=1)
        
        # 畫出水平頸線 (突破參考線)
        fig.add_trace(go.Scatter(x=[t1['date'], t2['date'] + pd.Timedelta(days=20)], 
                                 y=[p_neck['price'], p_neck['price']], 
                                 mode='lines', line=dict(color='cyan', width=2, dash='dash'),
                                 name=f"頸線 {idx+1}"), row=1, col=1)

    colors = ['red' if r['close'] >= r['open'] else 'green' for i, r in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Trading_Volume'], marker_color=colors, name="成交量"), row=2, col=1)

    fig.update_layout(template="plotly_dark", height=800, xaxis_rangeslider_visible=False)
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("讀取失敗，請檢查代號或 Token。")
