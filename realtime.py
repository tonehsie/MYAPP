import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
from datetime import datetime
import time

# ================= 頁面設定 =================
st.set_page_config(page_title="多檔最佳一檔自動偵測雷達", layout="wide")
st.title("🎯 台股多檔：全自動撤單監控雷達")
st.markdown("開啟自動偵測後，系統將持續為你輪詢監控多檔股票的「最佳一檔」量能變化。")

# ================= 系統參數 (已寫入 Token) =================
# 你的專屬 FinMind API Token
API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

# ================= 狀態管理 (Session State) =================
# 改用字典來儲存多檔股票的前一次狀態
if "prev_tick_data_dict" not in st.session_state:
    st.session_state.prev_tick_data_dict = {}

# ================= 側邊欄設定 =================
st.sidebar.header("⚙️ 追蹤參數設定")

# 讓使用者輸入多支股票，用逗號分隔
stock_ids_input = st.sidebar.text_input("請輸入股票代碼 (請用半形逗號分隔，最多5支)", value="2330, 2317, 3231")
# 處理字串，轉成 List，並限制最多 5 支
stock_list = [s.strip() for s in stock_ids_input.split(",") if s.strip()][:5]

wall_threshold = st.sidebar.number_input("大單過濾門檻 (張數大於)", value=100)

st.sidebar.markdown("---")
st.sidebar.header("🤖 自動偵測設定")

auto_detect = st.sidebar.toggle("🟢 啟動自動持續偵測")
refresh_rate = st.sidebar.slider("自動更新頻率 (秒)", min_value=3, max_value=30, value=5, help="監控多檔時建議維持 5 秒以上，避免 API 請求超載。")

manual_refresh = False
if not auto_detect:
    manual_refresh = st.sidebar.button("🔄 手動更新單次快照")

# ================= 主程式邏輯 =================
if auto_detect or manual_refresh:
    if not stock_list:
        st.warning("請至少輸入一支股票代碼！")
        st.stop()
        
    dl = DataLoader()
    dl.login_by_token(api_token=API_TOKEN)
    
    placeholder = st.empty()
    
    with placeholder.container():
        # 迴圈處理每一支股票
        for stock_id in stock_list:
            st.markdown(f"### 📌 標的：{stock_id}")
            try:
                # 抓取即時快照
                df_tick = dl.taiwan_stock_tick_snapshot(stock_id=stock_id)
                
                if df_tick.empty:
                    st.warning(f"{stock_id} 目前無資料，可能無此代碼或非盤中時間。")
                    st.markdown("---")
                    continue
                    
                latest_data = df_tick.iloc[0]
                update_time = latest_data.get('date', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                
                curr_buy_vol = latest_data.get('buy_volume', 0)
                curr_sell_vol = latest_data.get('sell_volume', 0)
                curr_buy_price = latest_data.get('buy_price', 0)
                curr_sell_price = latest_data.get('sell_price', 0)
                curr_close_price = latest_data.get('close', 'N/A')

                st.caption(f"🕒 更新時間：{update_time} | **最新成交價：** `{curr_close_price}`")
                
                # 取得這支股票前一次的狀態
                prev_data = st.session_state.prev_tick_data_dict.get(stock_id)
                
                col1, col2 = st.columns(2)
                
                if prev_data is not None:
                    prev_buy_vol = prev_data.get('buy_volume', 0)
                    prev_sell_vol = prev_data.get('sell_volume', 0)
                    
                    # 買方分析
                    with col1:
                        buy_diff = curr_buy_vol - prev_buy_vol
                        st.metric(label=f"委買大門 (價: {curr_buy_price})", value=f"{int(curr_buy_vol)} 張", delta=int(buy_diff))
                        if curr_buy_vol >= wall_threshold:
                            st.info("🛡️ 防守大單 (潛在買方牆)")
                        if buy_diff < -wall_threshold:
                            st.error("⚠️ 大額撤單，小心支撐為假！")
                            
                    # 賣方分析
                    with col2:
                        sell_diff = curr_sell_vol - prev_sell_vol
                        st.metric(label=f"委賣大門 (價: {curr_sell_price})", value=f"{int(curr_sell_vol)} 張", delta=int(sell_diff), delta_color="inverse")
                        if curr_sell_vol >= wall_threshold:
                            st.info("🧱 壓力大單 (潛在賣方牆)")
                        if sell_diff < -wall_threshold:
                            st.success("🚀 賣單大額撤銷，上方壓力可能為假！")
                else:
                    with col1:
                        st.metric(label=f"委買量 (價: {curr_buy_price})", value=f"{int(curr_buy_vol)} 張")
                    with col2:
                        st.metric(label=f"委賣量 (價: {curr_sell_price})", value=f"{int(curr_sell_vol)} 張")
                    st.caption("🔄 等待下一秒比對量能差異...")
                
                # 記錄本次資料供下一次比對
                st.session_state.prev_tick_data_dict[stock_id] = latest_data
                st.markdown("---") # 分隔線
                
            except Exception as e:
                st.error(f"{stock_id} 執行發生錯誤：{e}")
                st.markdown("---")

    # ===== 自動更新迴圈控制 =====
    if auto_detect:
        st.sidebar.success(f"🟢 自動偵測運行中... (每 {refresh_rate} 秒更新一次)")
        time.sleep(refresh_rate)
        st.rerun()
