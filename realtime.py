import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
from datetime import datetime
import time

# ================= 頁面設定 =================
st.set_page_config(page_title="最佳一檔自動偵測雷達", layout="wide")
st.title("🎯 台股最佳一檔：全自動撤單監控雷達")
st.markdown("開啟側邊欄的自動偵測後，系統將持續掛著，為你自動比對每一次快照的量能變化。")

# ================= 狀態管理 (Session State) =================
if "prev_tick_data" not in st.session_state:
    st.session_state.prev_tick_data = None

# ================= 側邊欄設定 =================
st.sidebar.header("⚙️ 系統參數設定")
api_token = st.sidebar.text_input("請輸入 FinMind API Token", type="password")
stock_id = st.sidebar.text_input("請輸入股票代碼", value="2330")
wall_threshold = st.sidebar.number_input("大單過濾門檻 (張數大於)", value=100)

st.sidebar.markdown("---")
st.sidebar.header("🤖 自動偵測設定")

# 加入自動更新的開關與頻率控制
auto_detect = st.sidebar.toggle("🟢 啟動自動持續偵測")
refresh_rate = st.sidebar.slider("自動更新頻率 (秒)", min_value=3, max_value=30, value=5, help="建議維持 3~5 秒以上，避免 API 請求過度頻繁被鎖。")

# 保留手動按鈕，以防你想關閉自動時使用
manual_refresh = False
if not auto_detect:
    manual_refresh = st.sidebar.button("🔄 手動更新單次快照")

# ================= 主程式邏輯 =================
# 如果有開啟自動，或者是點了手動按鈕，就執行抓取
if auto_detect or manual_refresh:
    if not api_token:
        st.sidebar.error("⚠️ 請先輸入 API Token！")
        st.stop()
        
    dl = DataLoader()
    dl.login_by_token(api_token=api_token)
    
    # 建立一個佔位符，讓畫面更新時不會一直閃爍
    placeholder = st.empty()
    
    with placeholder.container():
        try:
            # 抓取即時快照
            df_tick = dl.taiwan_stock_tick_snapshot(stock_id=stock_id)
            
            if df_tick.empty:
                st.error("目前無資料，請確認是否為盤中時間，或 API Token 權限是否正確。")
            else:
                latest_data = df_tick.iloc[0]
                update_time = latest_data.get('date', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                
                # 取得最佳一檔買賣價量
                curr_buy_vol = latest_data.get('buy_volume', 0)
                curr_sell_vol = latest_data.get('sell_volume', 0)
                curr_buy_price = latest_data.get('buy_price', 0)
                curr_sell_price = latest_data.get('sell_price', 0)
                curr_close_price = latest_data.get('close', 'N/A')

                st.subheader(f"📊 代碼：{stock_id} | 更新時間：{update_time}")
                st.markdown(f"**最新成交價：** `{curr_close_price}`")
                st.markdown("### 🔍 最佳買賣檔位變化分析")
                
                if st.session_state.prev_tick_data is not None:
                    prev_data = st.session_state.prev_tick_data
                    prev_buy_vol = prev_data.get('buy_volume', 0)
                    prev_sell_vol = prev_data.get('sell_volume', 0)
                    
                    col1, col2 = st.columns(2)
                    
                    # 買方分析
                    with col1:
                        buy_diff = curr_buy_vol - prev_buy_vol
                        st.metric(
                            label=f"委買大門 (價: {curr_buy_price})", 
                            value=f"{int(curr_buy_vol)} 張", 
                            delta=int(buy_diff)
                        )
                        if curr_buy_vol >= wall_threshold:
                            st.info("🛡️ 買一出現防守大單 (潛在買方牆)")
                        if buy_diff < -wall_threshold:
                            st.error("⚠️ 警告：買單出現大額撤銷，小心支撐為假！")
                            
                    # 賣方分析
                    with col2:
                        sell_diff = curr_sell_vol - prev_sell_vol
                        st.metric(
                            label=f"委賣大門 (價: {curr_sell_price})", 
                            value=f"{int(curr_sell_vol)} 張", 
                            delta=int(sell_diff), 
                            delta_color="inverse"
                        )
                        if curr_sell_vol >= wall_threshold:
                            st.info("🧱 賣一出現壓力大單 (潛在賣方牆)")
                        if sell_diff < -wall_threshold:
                            st.success("🚀 提示：賣單出現大額撤銷，上方壓力可能為假！")
                else:
                    st.info("🔄 這是啟動後第一筆資料，等待下一秒進行量能差異比對...")
                    col1, col2 = st.columns(2)
                    col1.metric(label=f"委買量 (價: {curr_buy_price})", value=f"{int(curr_buy_vol)} 張")
                    col2.metric(label=f"委賣量 (價: {curr_sell_price})", value=f"{int(curr_sell_vol)} 張")
                
                # 記錄本次資料供下一次比對
                st.session_state.prev_tick_data = latest_data
                
        except Exception as e:
            st.error(f"執行發生錯誤，錯誤訊息：{e}")

    # ===== 自動更新迴圈控制 =====
    if auto_detect:
        st.sidebar.success(f"🟢 自動偵測運行中... (每 {refresh_rate} 秒更新一次)")
        time.sleep(refresh_rate)
        st.rerun() # 強制網頁重新執行，達到無限掛著偵測的效果
