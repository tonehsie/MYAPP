import streamlit as st
import pandas as pd
import requests
from FinMind.data import DataLoader
from datetime import datetime
import time

# ================= 頁面設定 =================
st.set_page_config(page_title="雙刀流撤單監控雷達", layout="wide")
st.title("⚔️ 台股雙引擎：全自動撤單監控雷達 (含五檔明細)")
st.markdown("上市股自動路由至 **FinMind (最佳一檔)**，上櫃股自動切換至 **Fugle (完整五檔)**。")

# ================= 系統參數 (API Keys) =================
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"
FUGLE_API_KEY = "1bfa6213-22b4-43f2-b66d-33a79baca01f"

# ================= 初始化 FinMind =================
@st.cache_resource
def init_finmind():
    dl = DataLoader()
    dl.login_by_token(api_token=FINMIND_TOKEN)
    return dl

dl = init_finmind()

# ================= 狀態管理 =================
if "prev_data_dict" not in st.session_state:
    st.session_state.prev_data_dict = {}

# ================= 側邊欄設定 =================
st.sidebar.header("⚙️ 追蹤參數設定")

stock_ids_input = st.sidebar.text_input("請輸入股票代碼 (半形逗號分隔)", value="2330, 3169, 2317, 3231")
stock_list = [s.strip() for s in stock_ids_input.split(",") if s.strip()][:8]

wall_threshold = st.sidebar.number_input("大單撤單警告門檻 (張數)", value=100)

st.sidebar.markdown("---")
st.sidebar.header("🤖 自動偵測設定")

auto_detect = st.sidebar.toggle("🟢 啟動自動持續偵測")
refresh_rate = st.sidebar.slider("自動更新頻率 (秒)", min_value=3, max_value=30, value=6)

manual_refresh = False
if not auto_detect:
    manual_refresh = st.sidebar.button("🔄 手動更新單次快照")

# ================= 核心獲取資料函數 =================
def get_stock_data(symbol):
    """智慧路由：先試 FinMind，失敗再找 Fugle"""
    
    # 1. 嘗試呼叫 FinMind (上市)
    try:
        df_tick = dl.taiwan_stock_tick_snapshot(stock_id=symbol)
        if not df_tick.empty:
            data = df_tick.iloc[0]
            update_time = data.get('date', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            # 整理成陣列格式以供表格顯示
            bids = [{'price': data.get('buy_price', 0), 'size': data.get('buy_volume', 0)}]
            asks = [{'price': data.get('sell_price', 0), 'size': data.get('sell_volume', 0)}]
            
            return {
                'source': '🔵 FinMind (上市 - 最佳一檔)',
                'time': update_time,
                'price': data.get('close', 'N/A'),
                'buy_vol': data.get('buy_volume', 0),
                'sell_vol': data.get('sell_volume', 0),
                'buy_label': f"委買大門 (價: {data.get('buy_price', 0)})",
                'sell_label': f"委賣大門 (價: {data.get('sell_price', 0)})",
                'bids': bids,
                'asks': asks
            }
    except Exception:
        pass 

    # 2. 切換呼叫 Fugle (上櫃)
    url = f"https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"
    headers = {"X-API-KEY": FUGLE_API_KEY}
    try:
        res = requests.get(url, headers=headers, timeout=3)
        if res.status_code == 200:
            raw_data = res.json()
            if 'bids' in raw_data:
                quote_time = raw_data.get('updatedAt', datetime.now().strftime("%H:%M:%S"))
                display_time = quote_time.split('T')[-1][:8] if 'T' in quote_time else quote_time
                
                bids = raw_data.get('bids', [])
                asks = raw_data.get('asks', [])
                total_buy = sum([item.get('size', 0) for item in bids])
                total_sell = sum([item.get('size', 0) for item in asks])
                
                return {
                    'source': '🟠 Fugle (上櫃 - 完整五檔)',
                    'time': display_time,
                    'price': raw_data.get('closePrice', 'N/A'),
                    'buy_vol': total_buy,
                    'sell_vol': total_sell,
                    'buy_label': "內盤五檔總委買",
                    'sell_label': "外盤五檔總委賣",
                    'bids': bids,
                    'asks': asks
                }
    except Exception:
        pass

    return None

# ================= 產生五檔表格函數 =================
def render_order_book(bids, asks):
    """將 bids 和 asks 轉換為 Streamlit 易讀的 DataFrame"""
    max_len = max(len(bids), len(asks), 1)
    
    # 補齊長度
    bids_padded = bids + [{'price': '-', 'size': '-'}] * (max_len - len(bids))
    asks_padded = asks + [{'price': '-', 'size': '-'}] * (max_len - len(asks))
    
    # 賣盤在上方通常要反轉 (符合看盤軟體習慣)，但這裡我們用左右對照表
    df = pd.DataFrame({
        "委買價": [b.get('price', '-') for b in bids_padded],
        "委買量": [b.get('size', '-') for b in bids_padded],
        "|": ["|" for _ in range(max_len)], # 分隔線
        "委賣價": [a.get('price', '-') for a in asks_padded],
        "委賣量": [a.get('size', '-') for a in asks_padded]
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
            curr_data = get_stock_data(stock_id)
            
            if not curr_data:
                st.markdown(f"### 📌 標的：{stock_id}")
                st.warning(f"目前無資料，可能無此代碼或非盤中時間。")
                st.markdown("---")
                continue

            st.markdown(f"### 📌 標的：{stock_id}  |  {curr_data['source']}")
            st.caption(f"🕒 更新時間：{curr_data['time']} | **最新成交價：** `{curr_data['price']}`")
            
            prev_data = st.session_state.prev_data_dict.get(stock_id)
            col1, col2 = st.columns(2)
            
            # --- 警示與總量變化區塊 ---
            if prev_data is not None:
                with col1:
                    buy_diff = curr_data['buy_vol'] - prev_data['buy_vol']
                    st.metric(label=curr_data['buy_label'], value=f"{int(curr_data['buy_vol'])} 張", delta=int(buy_diff))
                    if buy_diff < -wall_threshold:
                        st.error("⚠️ 警告：下方買盤大額撤單，支撐可能為假！")
                with col2:
                    sell_diff = curr_data['sell_vol'] - prev_data['sell_vol']
                    st.metric(label=curr_data['sell_label'], value=f"{int(curr_data['sell_vol'])} 張", delta=int(sell_diff), delta_color="inverse")
                    if sell_diff < -wall_threshold:
                        st.success("🚀 提示：上方賣盤大額撤單，壓力可能為假！")
            else:
                with col1:
                    st.metric(label=curr_data['buy_label'], value=f"{int(curr_data['buy_vol'])} 張")
                with col2:
                    st.metric(label=curr_data['sell_label'], value=f"{int(curr_data['sell_vol'])} 張")
                st.caption("🔄 等待下一秒比對量能差異...")
            
            # --- 五檔明細區塊 ---
            with st.expander("📊 查看委託檔位明細", expanded=False):
                df_order_book = render_order_book(curr_data['bids'], curr_data['asks'])
                st.dataframe(df_order_book, use_container_width=True, hide_index=True)
            
            st.session_state.prev_data_dict[stock_id] = curr_data
            st.markdown("---")

    # ===== 自動更新迴圈控制 =====
    if auto_detect:
        st.sidebar.success(f"🟢 自動偵測運行中... (每 {refresh_rate} 秒更新一次)")
        time.sleep(refresh_rate)
        st.rerun()
