import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from scipy.signal import argrelextrema

st.set_page_config(layout="wide", page_title="專業級量化分析系統 V5 Pro")
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

st.title("高階圖表：幾何填色與目標價預測")

with st.sidebar:
    st.header("演算法參數設定")
    stock_id = st.text_input("股票代號", "2330")
    start_date = st.text_input("起始日期", "2023-01-01")
    scan_target = st.selectbox("選擇要掃描的形態", ["頭肩頂 (Pro視覺)", "W底 (Pro視覺)"])
    order_val = st.slider("轉折靈敏度 (Order)", 5, 30, 10)
    tolerance = st.slider("幾何誤差容忍度 (%)", 1.0, 10.0, 3.0, 0.5)

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
    peaks_idx = argrelextrema(df['max'].values, np.greater, order=order_val)[0]
    troughs_idx = argrelextrema(df['min'].values, np.less, order=order_val)[0]
    
    df['peak'] = np.nan
    df.iloc[peaks_idx, df.columns.get_loc('peak')] = df.iloc[peaks_idx]['max']
    df['trough'] = np.nan
    df.iloc[troughs_idx, df.columns.get_loc('trough')] = df.iloc[troughs_idx]['min']

    turns = []
    for d, r in df.dropna(subset=['peak']).iterrows(): turns.append({'date': d, 'type': 'peak', 'price': r['peak']})
    for d, r in df.dropna(subset=['trough']).iterrows(): turns.append({'date': d, 'type': 'trough', 'price': r['trough']})
    turns = sorted(turns, key=lambda x: x['date'])

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['max'], low=df['min'], close=df['close'], name="K線", increasing_line_color='#FF3333', decreasing_line_color='#00FF00'), row=1, col=1)

    # === W底 Pro 視覺化 ===
    if scan_target == "W底 (Pro視覺)":
        for i in range(len(turns) - 2):
            p1, p2, p3 = turns[i], turns[i+1], turns[i+2]
            if p1['type'] == 'trough' and p2['type'] == 'peak' and p3['type'] == 'trough':
                if abs(p1['price'] - p3['price']) / p1['price'] * 100 <= tolerance:
                    # 繪製半透明幾何填色 (連起三個點與頸線形成封閉多邊形)
                    fig.add_trace(go.Scatter(x=[p1['date'], p2['date'], p3['date'], p1['date']], 
                                             y=[p1['price'], p2['price'], p3['price'], p1['price']], 
                                             fill='toself', fillcolor='rgba(255, 215, 0, 0.15)', 
                                             line=dict(color='rgba(255, 215, 0, 0.8)', width=2), name="W底區域"), row=1, col=1)
                    
                    # 頸線延伸與目標價預測
                    neck_price = p2['price']
                    bottom_avg = (p1['price'] + p3['price']) / 2
                    target_price = neck_price + (neck_price - bottom_avg) # 等幅測量
                    
                    fig.add_trace(go.Scatter(x=[p2['date'], p3['date'] + pd.Timedelta(days=20)], y=[neck_price, neck_price], mode='lines', line=dict(color='gold', width=2, dash='dash'), name="突破頸線"), row=1, col=1)
                    fig.add_trace(go.Scatter(x=[p3['date'] + pd.Timedelta(days=10), p3['date'] + pd.Timedelta(days=10)], y=[neck_price, target_price], mode='lines+text', line=dict(color='#00FFcc', width=2, dash='dot'), text=["", f"🎯 目標預測: {target_price:.1f}"], textposition="top right", name="測量目標"), row=1, col=1)

    # === 頭肩頂 Pro 視覺化 ===
    if scan_target == "頭肩頂 (Pro視覺)":
        for i in range(len(turns) - 4):
            p1, t1, p2, t2, p3 = turns[i], turns[i+1], turns[i+2], turns[i+3], turns[i+4]
            if p1['type'] == 'peak' and t1['type'] == 'trough' and p2['type'] == 'peak' and t2['type'] == 'trough' and p3['type'] == 'peak':
                if p2['price'] > p1['price'] and p2['price'] > p3['price']:
                    if abs(p1['price'] - p3['price']) / p1['price'] * 100 <= tolerance:
                        if abs(t1['price'] - t2['price']) / t1['price'] * 100 <= tolerance:
                            # 繪製半透明幾何填色 (五個點連成封閉多邊形)
                            fig.add_trace(go.Scatter(x=[p1['date'], t1['date'], p2['date'], t2['date'], p3['date'], p1['date']], 
                                                     y=[p1['price'], t1['price'], p2['price'], t2['price'], p3['price'], p1['price']], 
                                                     fill='toself', fillcolor='rgba(0, 255, 255, 0.1)', 
                                                     line=dict(color='rgba(0, 255, 255, 0.8)', width=2), name="頭肩頂區域"), row=1, col=1)
                            
                            # 標註文字
                            annotations = [
                                dict(x=p1['date'], y=p1['price'], text="左肩", showarrow=True, arrowhead=2, ax=0, ay=-30, font=dict(color="cyan")),
                                dict(x=p2['date'], y=p2['price'], text="頭部", showarrow=True, arrowhead=2, ax=0, ay=-30, font=dict(color="cyan", size=16)),
                                dict(x=p3['date'], y=p3['price'], text="右肩", showarrow=True, arrowhead=2, ax=0, ay=-30, font=dict(color="cyan"))
                            ]
                            for ann in annotations: fig.add_annotation(**ann, row=1, col=1)
                            
                            # 等幅測量預測跌幅
                            neck_avg = (t1['price'] + t2['price']) / 2
                            drop_height = p2['price'] - neck_avg
                            target_drop = neck_avg - drop_height
                            
                            fig.add_trace(go.Scatter(x=[t2['date'], p3['date'] + pd.Timedelta(days=20)], y=[neck_avg, neck_avg], mode='lines', line=dict(color='cyan', width=2, dash='dash'), name="跌破頸線"), row=1, col=1)
                            fig.add_trace(go.Scatter(x=[p3['date'] + pd.Timedelta(days=10), p3['date'] + pd.Timedelta(days=10)], y=[neck_avg, target_drop], mode='lines+text', line=dict(color='#FF33cc', width=2, dash='dot'), text=["", f"⚠️ 測量跌幅: {target_drop:.1f}"], textposition="bottom right", name="測量目標"), row=1, col=1)

    colors = ['#FF3333' if r['close'] >= r['open'] else '#00FF00' for i, r in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Trading_Volume'], marker_color=colors, name="成交量"), row=2, col=1)

    # 專業深色質感微調
    fig.update_layout(template="plotly_dark", height=850, xaxis_rangeslider_visible=False,
                      plot_bgcolor='rgb(17, 17, 17)', paper_bgcolor='rgb(17, 17, 17)',
                      hovermode='x unified')
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])], gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(gridcolor='rgba(255,255,255,0.1)')
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("讀取失敗，請檢查代號或 Token。")
