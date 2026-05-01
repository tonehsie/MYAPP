import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime

# ================= 頁面設定 =================
st.set_page_config(page_title="全五檔撤單監控雷達", layout="wide")
st.title("🎯 台股純富果：全五檔撤單監控雷達 (上市/上櫃全支援)")
st.markdown("全面採用 Fugle API，為你提供**每一檔標的的完整五檔明細**與總量變化分析。")

# ================= 系統參數 (API Key) =================
# 🔑 你的富果 API Key
FUGLE_API_KEY = "1bfa6213-22b4-43f2-b66d-33a79baca01f"

# ================= 狀態管理 =================
if "prev_data_dict" not in st.session_state:
    st.session_state.prev_data_dict = {}

# ================= 側邊欄設定 =================
st.sidebar.header("⚙️ 追蹤參數設定")
st.sidebar.info("⚠️ 基本方案 API 限制：每分鐘 60 次。\n建議追蹤 4 支以內，頻率 5 秒以上。")

stock_ids_input = st.sidebar.text_input("請輸入股票代碼 (半形逗號分隔，建議最多4支)", value="2330, 3169, 2317")
stock_list = [s.strip() for s in stock_ids_input.split(",") if s.strip()][:4]

wall_threshold = st.sidebar.number_input("五檔單邊總量撤單門檻 (張數)", value=150)

st.sidebar.markdown("---")
st.sidebar.header("🤖 自動偵測設定")

auto_detect = st.sidebar.toggle("🟢 啟動自動持續偵測")
refresh_rate = st.sidebar.slider("自動更新頻率 (秒)", min_value=3, max_value=30, value=5)

manual_refresh = False
if not auto_detect:
    manual_refresh = st.sidebar.button("🔄 手動更新單次快照")

# ================= 產生五檔表格函數 =================
def render_order_book(bids, asks):
    """將富果的 bids 和 asks 轉換為對稱的五檔 DataFrame"""
    max_len = max(len(bids), len(asks), 5) # 確保至少顯示5格
    
    # 補齊長度，沒有資料的檔位補 '-'
    bids_padded = bids + [{'price': '-', 'size': '-'}] * (max_len - len(bids))
    asks_padded = asks + [{'price': '-', 'size': '-'}] * (max_len - len(asks))
    
    df = pd.DataFrame({
        "委買價": [b.get('price', '-') for b in bids_padded][:5],
        "委買量": [b.get('size', '-') for b in bids_padded][:5],
        "|": ["|" for _ in range(5)], # 中間的分隔線
        "委賣價": [a.get('price', '-') for a in asks_padded][:5],
        "委賣量": [a.get('size', '-') for a in asks_padded][:5]
    })
    return df

# ================= 主程式邏輯 =================
if auto_detect or manual_refresh:
    if not stock_list:
        st.warning("請至少輸入一支股票代碼！")
        st.stop()
    
    placeholder = st.empty()
    
    with placeholder.container():
        for stock_id in stock_list:
            
            # 統一呼叫 Fugle API
            url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{stock_id}"
            headers = {"X-API-KEY": FUGLE_API_KEY}
            
            try:
                res = requests.get(url, headers=headers, timeout=3)
                if res.status_code == 200:
                    raw_data = res.json()
                    if 'bids' not in raw_data:
                        st.warning(f"{stock_id} 目前無五檔資料 (可能非盤中時間)。")
                        st.markdown("---")
                        continue
                        
                    # 解析時間與成交價
                    quote_time = raw_data.get('updatedAt', datetime.now().strftime("%H:%M:%S"))
                    display_time = quote_time.split('T')[-1][:8] if 'T' in quote_time else quote_time
                    curr_price = raw_data.get('closePrice', 'N/A')
                    
                    # 擷取五檔陣列
                    bids = raw_data.get('bids', [])
                    asks = raw_data.get('asks', [])
                    
                    # 計算五檔總和
                    total_buy = sum([item.get('size', 0) for item in bids])
                    total_sell = sum([item.get('size', 0) for item in asks])
                    
                    st.markdown(f"### 📌 標的：{stock_id}")
                    st.caption(f"🕒 更新時間：{display_time} | **最新成交價：** `{curr_price}`")
                    
                    prev_data = st.session_state.prev_data_dict.get(stock_id)
                    col1, col2 = st.columns(2)
                    
                    # --- 警示與總量變化區塊 ---
                    if prev_data is not None:
                        with col1:
                            buy_diff = total_buy - prev_data['total_buy']
                            st.metric(label="內盤五檔總委買", value=f"{total_buy} 張", delta=int(buy_diff))
                            if buy_diff < -wall_threshold:
                                st.error("⚠️ 警告：下方買盤五檔出現大額撤單，支撐可能為假！")
                        with col2:
                            sell_diff = total_sell - prev_data['total_sell']
                            st.metric(label="外盤五檔總委賣", value=f"{total_sell} 張", delta=int(sell_diff), delta_color="inverse")
                            if sell_diff < -wall_threshold:
                                st.success("🚀 提示：上方賣盤五檔出現大額撤單，壓力可能為假！")
                    else:
                        with col1:
                            st.metric(label="內盤五檔總委買", value=f"{total_buy} 張")
                        with col2:
                            st.metric(label="外盤五檔總委賣", value=f"{total_sell} 張")
                        st.caption("🔄 等待下一秒比對量能差異...")
                    
                    # --- 五檔明細展開區塊 ---
                    with st.expander("📊 查看完整五檔明細", expanded=False):
                        df_order_book = render_order_book(bids, asks)
                        st.dataframe(df_order_book, use_container_width=True, hide_index=True)
                    
                    # 記錄狀態
                    st.session_state.prev_data_dict[stock_id] = {
                        'total_buy': total_buy,
                        'total_sell': total_sell
                    }
                    st.markdown("---")
                else:
                    st.error(f"{stock_id} API 呼叫失敗，請確認代碼或 API 額度。")
                    
            except Exception as e:
                st.error(f"{stock_id} 連線異常：{e}")
                st.markdown("---")

    # ===== 自動更新迴圈控制 =====
    if auto_detect:
        st.sidebar.success(f"🟢 自動偵測運行中... (每 {refresh_rate} 秒更新一次)")
        time.sleep(refresh_rate)
        st.rerun()
