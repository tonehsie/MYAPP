import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime

# ================= 頁面設定 =================
st.set_page_config(page_title="富果五檔自動偵測雷達", layout="wide")
st.title("🎯 台股多檔：富果五檔撤單監控雷達 (上市/上櫃全支援)")
st.markdown("透過富果 API 即時監控「最佳五檔」的總掛單量變化，精準捕捉大單撤單與假牆。")

# ================= 系統參數 =================
# 🔑 請將你在富果取得的 API Key 貼在下方引號內
FUGLE_API_KEY = "你的富果API_KEY_請貼在這裡"

# ================= 狀態管理 (Session State) =================
if "prev_fugle_data_dict" not in st.session_state:
    st.session_state.prev_fugle_data_dict = {}

# ================= 側邊欄設定 =================
st.sidebar.header("⚙️ 追蹤參數設定")

stock_ids_input = st.sidebar.text_input("請輸入股票代碼 (半形逗號分隔，最多5支)", value="2330, 3169, 3231")
stock_list = [s.strip() for s in stock_ids_input.split(",") if s.strip()][:5]

wall_threshold = st.sidebar.number_input("五檔單邊總量撤單門檻 (張數)", value=200)

st.sidebar.markdown("---")
st.sidebar.header("🤖 自動偵測設定")

auto_detect = st.sidebar.toggle("🟢 啟動自動持續偵測")
refresh_rate = st.sidebar.slider("自動更新頻率 (秒)", min_value=3, max_value=30, value=5)

manual_refresh = False
if not auto_detect:
    manual_refresh = st.sidebar.button("🔄 手動更新單次快照")

# ================= 獲取富果資料函數 =================
def get_fugle_quote(symbol):
    """透過富果 MarketData API v1.0 取得即時報價與五檔"""
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"
    headers = {"X-API-KEY": FUGLE_API_KEY}
    try:
        res = requests.get(url, headers=headers, timeout=3)
        if res.status_code == 200:
            return res.json()
        return None
    except:
        return None

# ================= 主程式邏輯 =================
if auto_detect or manual_refresh:
    if FUGLE_API_KEY == "你的富果API_KEY_請貼在這裡":
        st.warning("⚠️ 請先在程式碼中填寫富果 API Key！")
        st.stop()
        
    if not stock_list:
        st.warning("請至少輸入一支股票代碼！")
        st.stop()
    
    placeholder = st.empty()
    
    with placeholder.container():
        for stock_id in stock_list:
            st.markdown(f"### 📌 標的：{stock_id}")
            
            raw_data = get_fugle_quote(stock_id)
            
            if not raw_data or 'bids' not in raw_data:
                st.warning(f"{stock_id} 目前無資料，可能無此代碼。")
                st.markdown("---")
                continue
                
            # 解析富果的資料結構
            quote_time = raw_data.get('updatedAt', datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
            # 轉換時間格式以便閱讀
            display_time = quote_time.split('T')[-1][:8] if 'T' in quote_time else quote_time
            
            curr_price = raw_data.get('closePrice', 'N/A')
            
            # 計算五檔買賣總量
            bids = raw_data.get('bids', [])
            asks = raw_data.get('asks', [])
            
            curr_total_buy = sum([item.get('size', 0) for item in bids])
            curr_total_sell = sum([item.get('size', 0) for item in asks])

            st.caption(f"🕒 更新時間：{display_time} | **最新成交價：** `{curr_price}`")
            
            prev_data = st.session_state.prev_fugle_data_dict.get(stock_id)
            
            col1, col2 = st.columns(2)
            
            if prev_data is not None:
                prev_total_buy = prev_data['total_buy']
                prev_total_sell = prev_data['total_sell']
                
                # 買盤五檔分析
                with col1:
                    buy_diff = curr_total_buy - prev_total_buy
                    st.metric(label="內盤五檔總委買", value=f"{curr_total_buy} 張", delta=int(buy_diff))
                    if buy_diff < -wall_threshold:
                        st.error("⚠️ 警告：下方買盤出現大額撤單，支撐假牆可能已消失！")
                        
                # 賣盤五檔分析
                with col2:
                    sell_diff = curr_total_sell - prev_total_sell
                    st.metric(label="外盤五檔總委賣", value=f"{curr_total_sell} 張", delta=int(sell_diff), delta_color="inverse")
                    if sell_diff < -wall_threshold:
                        st.success("🚀 提示：上方賣盤出現大額撤單，壓力假牆可能已消失！")
            else:
                with col1:
                    st.metric(label="內盤五檔總委買", value=f"{curr_total_buy} 張")
                with col2:
                    st.metric(label="外盤五檔總委賣", value=f"{curr_total_sell} 張")
                st.caption("🔄 等待下一秒比對量能差異...")
            
            # 記錄供下一次比對
            st.session_state.prev_fugle_data_dict[stock_id] = {
                'total_buy': curr_total_buy,
                'total_sell': curr_total_sell
            }
            st.markdown("---")

    # ===== 自動更新迴圈控制 =====
    if auto_detect:
        st.sidebar.success(f"🟢 自動偵測運行中... (每 {refresh_rate} 秒更新一次)")
        time.sleep(refresh_rate)
        st.rerun()
