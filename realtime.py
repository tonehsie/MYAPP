import streamlit as st
import pandas as pd
from FinMind.data import DataLoader
from datetime import datetime

# ================= 頁面設定 =================
st.set_page_config(page_title="五檔假牆與撤單監控系統", layout="wide")
st.title("🎯 台股五檔假牆與撤單監控雷達")
st.markdown("透過比對兩次快照的掛單量差異，找出可能的「假牆」與「高頻撤單」跡象。")

# ================= 狀態管理 (Session State) =================
# 用來儲存「上一次」的五檔資料，才能算出差額
if "prev_b5_data" not in st.session_state:
    st.session_state.prev_b5_data = None

# ================= 側邊欄設定 =================
st.sidebar.header("系統參數設定")
api_token = st.sidebar.text_input("請輸入 FinMind API Token (Sponsor專屬)", type="password")
stock_id = st.sidebar.text_input("請輸入股票代碼", value="2330")

# 判斷大單假牆的門檻 (張數)
wall_threshold = st.sidebar.number_input("假牆過濾門檻 (單檔張數大於)", value=100)

refresh_btn = st.sidebar.button("🔄 手動更新即時五檔")

# ================= 主程式邏輯 =================
if refresh_btn:
    if not api_token:
        st.warning("請先輸入 FinMind API Token！")
    else:
        dl = DataLoader()
        dl.login_by_token(api_token=api_token)
        
        with st.spinner('正在抓取即時資料...'):
            try:
                # 抓取即時五檔快照
                df_b5 = dl.taiwan_stock_best_five_snapshot(stock_id=stock_id)
                
                if df_b5.empty:
                    st.error("目前無資料，請確認是否為盤中時間，或 API Token 權限是否正確。")
                else:
                    # 展開資料 (FinMind 回傳通常會將五檔包在 list 中)
                    # 這裡抓取第一筆 (最新的快照)
                    latest_data = df_b5.iloc[0]
                    update_time = latest_data.get('Time', datetime.now().strftime("%H:%M:%S"))
                    
                    st.subheader(f"代碼：{stock_id} | 更新時間：{update_time}")
                    
                    # 整理成易讀的 DataFrame
                    b5_table = pd.DataFrame({
                        "賣出價 (外盤)": latest_data['best_five_sell_price'],
                        "賣出量 (張)": latest_data['best_five_sell_volume'],
                        "買進價 (內盤)": latest_data['best_five_buy_price'],
                        "買進量 (張)": latest_data['best_five_buy_volume']
                    })
                    
                    # 排版：將賣價反轉，讓最低賣價在最下方，符合看盤軟體習慣
                    b5_table = b5_table.sort_index(ascending=False).reset_index(drop=True)
                    
                    # ================= 假牆與撤單分析邏輯 =================
                    st.markdown("### 🔍 檔位變化與假牆分析")
                    
                    if st.session_state.prev_b5_data is not None:
                        prev_data = st.session_state.prev_b5_data
                        
                        # 比較前一次與這一次的總掛單量
                        prev_total_buy = sum(prev_data['best_five_buy_volume'])
                        curr_total_buy = sum(latest_data['best_five_buy_volume'])
                        prev_total_sell = sum(prev_data['best_five_sell_volume'])
                        curr_total_sell = sum(latest_data['best_five_sell_volume'])
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            buy_diff = curr_total_buy - prev_total_buy
                            st.metric(label="五檔總買量變化 (潛在撤單/補單)", value=f"{curr_total_buy} 張", delta=f"{buy_diff} 張")
                            if buy_diff < -wall_threshold:
                                st.error("⚠️ 警告：下方買盤出現大額撤單，支撐可能為假！")
                                
                        with col2:
                            sell_diff = curr_total_sell - prev_total_sell
                            st.metric(label="五檔總賣量變化 (潛在撤單/補單)", value=f"{curr_total_sell} 張", delta=f"{sell_diff} 張", delta_color="inverse")
                            if sell_diff < -wall_threshold:
                                st.success("🚀 提示：上方賣盤出現大額撤單，壓力可能為假！")
                    else:
                        st.info("這是第一次抓取，請再次點擊「更新」來進行量能差異比對。")
                    
                    # 記錄本次資料供下次比對
                    st.session_state.prev_b5_data = latest_data
                    
                    # ================= 顯示五檔明細 =================
                    st.markdown("### 📊 五檔明細快照")
                    
                    # 針對大單(假牆)進行高亮標示
                    def highlight_walls(s):
                        if isinstance(s, (int, float)) and s >= wall_threshold:
                            return 'background-color: #ffcccc; color: black; font-weight: bold'
                        return ''
                    
                    styled_table = b5_table.style.applymap(
                        highlight_walls, subset=['賣出量 (張)', '買進量 (張)']
                    )
                    
                    st.dataframe(styled_table, use_container_width=True)
                    
            except Exception as e:
                st.error(f"執行發生錯誤，錯誤訊息：{e}")
