import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from scipy.signal import argrelextrema

# 介面設定
st.set_page_config(layout="wide", page_title="專業級量化分析系統 V4")

TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

st.title("高階圖表：多重形態自動辨識與框架")

with st.sidebar:
    st.header("演算法參數設定")
    stock_id = st.text_input("股票代號", "2330")
    start_date = st.text_input("起始日期", "2023-01-01")
    
    # 新增：形態選擇器
    st.subheader("形態掃描設定")
    scan_target = st.selectbox("選擇要掃描的形態", ["W底 (雙底)", "M頭 (雙頂)", "頭肩頂", "全部顯示 (綜合掃描)"])
    
    order_val = st.slider("轉折靈敏度 (Order)", min_value=5, max_value=30, value=10)
    tolerance = st.slider("幾何誤差容忍度 (%)", min_value=1.0, max_value=10.0, value=3.0, step=0.5)

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
    # 1. 尋找所有局部極值
    peaks_idx = argrelextrema(df['max'].values, np.greater, order=order_val)[0]
    troughs_idx = argrelextrema(df['min'].values, np.less, order=order_val)[0]
    
    df['peak'] = np.nan
    df.iloc[peaks_idx, df.columns.get_loc('peak')] = df.iloc[peaks_idx]['max']
    df['trough'] = np.nan
    df.iloc[troughs_idx, df.columns.get_loc('trough')] = df.iloc[troughs_idx]['min']

    # 建立依時間排序的轉折點序列
    turns = []
    for date, row in df.dropna(subset=['peak']).iterrows():
        turns.append({'date': date, 'type': 'peak', 'price': row['peak']})
    for date, row in df.dropna(subset=['trough']).iterrows():
        turns.append({'date': date, 'type': 'trough', 'price': row['trough']})
    turns = sorted(turns, key=lambda x: x['date'])
    
    # 儲存辨識結果的清單
    detected_w = []
    detected_m = []
    detected_hns = []

    # 2. 幾何形態辨識邏輯模組
    # 掃描 W底 與 M頭 (需要連續3個轉折)
    for i in range(len(turns) - 2):
        p1, p2, p3 = turns[i], turns[i+1], turns[i+2]
        
        # W底 (谷-峰-谷)
        if p1['type'] == 'trough' and p2['type'] == 'peak' and p3['type'] == 'trough':
            if abs(p1['price'] - p3['price']) / p1['price'] * 100 <= tolerance:
                detected_w.append([p1, p2, p3])
                
        # M頭 (峰-谷-峰)
        if p1['type'] == 'peak' and p2['type'] == 'trough' and p3['type'] == 'peak':
            if abs(p1['price'] - p3['price']) / p1['price'] * 100 <= tolerance:
                detected_m.append([p1, p2, p3])

    # 掃描 頭肩頂 (需要連續5個轉折: 左肩-頸線1-頭部-
