import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
from datetime import datetime

# ================= 頁面設定 =================
st.set_page_config(page_title="最佳一檔撤單與大單監控系統", layout="wide")
st.title("🎯 台股最佳一檔撤單監控雷達")
st.markdown("由於 FinMind 即時 API 提供的是**最佳一檔（Best Bid/Ask）**的快照，本雷達針對「最逼近成交價」的買賣單量變化進行監控，捕捉最前線的撤單跡象。")

# ================= 狀態管理 (Session State) =================
if "prev_tick_data" not in st.session_state:
    st.session_state.prev_tick_data = None

# ================= 側邊欄設定 =================
st.sidebar.header("系統參數設定")
api_token = st.sidebar.text_input("請輸入 FinMind API Token (Sponsor專屬)", type="password")
stock_id = st.sidebar.text_input("請輸入股票代碼", value="2330")

# 判斷大單假牆的門檻 (張數)
wall_threshold = st.sidebar.number_input("大單過濾門檻 (單檔張數大於)", value=100)

refresh_btn = st.sidebar.button("🔄 手動更新即時快照")

# ================= 主程式邏輯 =================
if refresh_btn:
    if not api_token:
        st.warning("請先輸入 FinMind API Token！")
    else:
        dl = DataLoader()
        dl.login_by_token(api_token=api_token)
        
        with st.spinner('正在抓取即時資料...'):
            try:
                # 呼叫正確的 FinMind API 函數 (即時快照)
                df_tick = dl.taiwan_stock_tick_snapshot(stock_id=stock_id)
                
                if df_tick.empty:
                    st.error("目前無資料，請確認是否為盤中時間，或 API Token 權限是否正確。")
                else:
                    # 抓取第一筆 (最新的快照)
                    latest_data = df_tick.iloc[0]
                    update_time = latest_data.get('date', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    
                    st.subheader(f"代碼：{stock_id} | 更新時間：{update_time}")
                    st.markdown(f"**最新成交價：** `{latest_data.get('close', 'N/A')}`")
                    
                    # 取得最佳一檔買賣價量
                    curr_buy_vol = latest_data.get('buy_volume', 0)
                    curr_sell_vol = latest_data.get('sell_volume', 0)
                    curr_buy_price = latest_data.get('buy_price', 0)
                    curr_sell_price = latest_data.get('sell_price', 0)
                    
                    # ================= 假牆與撤單分析邏輯 =================
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
                                st.error("⚠️ 警告：買單出現大額撤銷，支撐可能為假！")
                                
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
                                st.success("🚀 提示：賣單出現大額撤銷，壓力可能為假！")
                    else:
                        st.info("這是第一次抓取，請再次點擊「更新」來進行量能差異比對。")
                        col1, col2 = st.columns(2)
                        col1.metric(label=f"委買量 (價: {curr_buy_price})", value=f"{int(curr_buy_vol)} 張")
                        col2.metric(label=f"委賣量 (價: {curr_sell_price})", value=f"{int(curr_sell_vol)} 張")
                    
                    # 記錄本次資料供下次比對
                    st.session_state.prev_tick_data = latest_data
                    
            except Exception as e:
                st.error(f"執行發生錯誤，錯誤訊息：{e}")
