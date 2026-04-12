import streamlit as st
import requests
import pandas as pd
import numpy as np
import datetime
from io import StringIO
import re
import concurrent.futures
import urllib.request
import ssl
import urllib3

# 關閉所有憑證警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 設定網頁標題與佈局
st.set_page_config(page_title="V25.0 終極全息量化系統", layout="wide")

# 內建最新 Token
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

# 注入 CSS (優化表格對齊與診斷文字強調)
st.markdown("""
<style>
table.dataframe th, table.dataframe td { white-space: nowrap !important; text-align: center !important; }
.radar-table td:last-child { text-align: left !important; color: #ff4b4b; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🤖 V25.0 終極全息量化系統")
st.caption("自動化指紋辨識 + 隔日沖數據除水 + 技術位階融合診斷")

# UI 輸入區
col1, col2 = st.columns([1, 1])
with col1:
    user_stock_id = st.text_input("個股代號", value="1785")
with col2:
    dead_chip_input = st.text_input("死籌碼 %", placeholder="若留空則依董監持股自動計算")

run_btn = st.button("🚀 啟動 V25.0 全息引擎", use_container_width=True)

st.divider()

# ==========================================
# 📌 模組一：V25.0 分點指紋識別引擎
# ==========================================
def get_v25_broker_intelligence(df_raw):
    """
    分析 60 天分點路徑，自動標記：[隔日沖]、[波段主]、[真鎖碼]、[官股]
    """
    if df_raw.empty: return {}
    df = df_raw.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['securities_trader', 'date'])
    df['b_vol'] = (pd.to_numeric(df['buy'], errors='coerce').fillna(0) / 1000).astype(int)
    df['s_vol'] = (pd.to_numeric(df['sell'], errors='coerce').fillna(0) / 1000).astype(int)
    
    broker_tags = {}
    gov_list = ["台銀", "土銀", "彰銀", "第一", "兆豐", "華南", "合庫", "台企銀"]
    
    for trader, group in df.groupby('securities_trader'):
        total_buy = group['b_vol'].sum()
        total_sell = group['s_vol'].sum()
        net_buy = total_buy - total_sell
        trade_days = group['date'].nunique()
        
        # 隔日傾向：當日買進後，次二日內的賣出比例
        group['next_2d_sell'] = group['s_vol'].shift(-1).fillna(0) + group['s_vol'].shift(-2).fillna(0)
        flipper_ratio = group[group['b_vol'] > 50]['next_2d_sell'].sum() / total_buy if total_buy > 0 else 0
        loyalty = net_buy / total_buy if total_buy > 0 else 0
        
        if any(g in trader for g in gov_list): tag = "🏦 [官股]"
        elif flipper_ratio > 0.75 and total_buy > 300: tag = "⚡ [隔日沖]"
        elif trade_days >= 15 and loyalty > 0.7: tag = "📈 [波段主]"
        elif total_buy > 1000 and loyalty > 0.85: tag = "🧱 [真鎖碼]"
        else: tag = "🔵 一般"
        broker_tags[trader] = tag
    return broker_tags

# ==========================================
# 📌 模組二：V25.0 數據除水與專家診斷引擎
# ==========================================
def process_v25_radar(df_share_wide, df_price, df_branch_raw, dead_chip_input, dynamic_dict, static_val):
    if df_share_wide.empty or df_price.empty: return pd.DataFrame()
    
    # 預先計算技術位階 (MA20)
    df_p_calc = df_price.sort_values('日期', ascending=True).copy()
    df_p_calc['ma20'] = df_p_calc['收盤價(元)'].rolling(20).mean()
    
    # 取得分點標籤
    labels = get_v25_broker_intelligence(df_branch_raw)
    
    df_s = df_share_wide.sort_values('日期', ascending=True).copy()
    out = []
    
    for i in range(len(df_s)):
        row = df_s.iloc[i]
        d_str = row['日期']
        
        # 1. 取得當週價格與技術位階
        price_row = df_p_calc[df_p_calc['日期'] == d_str]
        cur_p = price_row['收盤價(元)'].iloc[0] if not price_row.empty else 0
        m20 = price_row['ma20'].iloc[0] if not price_row.empty else 0
        
        # 2. 數據除水：計算該週「最後一天(週五)」的隔日沖干擾張數
        df_friday = df_branch_raw[df_branch_raw['date'] == d_str]
        flipper_vol = 0
        if not df_friday.empty:
            df_friday['tag'] = df_friday['securities_trader'].map(labels)
            flipper_vol = df_friday[df_friday['tag'] == "⚡ [隔日沖]"]['buy'].sum() / 1000
            
        total_shares = row['總張數']
        flipper_impact = (flipper_vol / total_shares) * 100 if total_shares > 0 else 0
        
        # 3. 計算真實變動
        raw_change = 0 if i == 0 else row['1000張以上_比例(%)'] - df_s.iloc[i-1]['1000張以上_比例(%)']
        pure_change = round(raw_change - flipper_impact, 2)
        
        # 4. 槓桿與強度
        current_dead, _ = get_dead_chip_info(d_str, dead_chip_input, dynamic_dict, static_val, "")
        leverage = 100 / (100 - current_dead) if 0 < current_dead < 100 else 1
        pure_intensity = round(pure_change * leverage, 2)
        
        # 5. K值計算 (中實戶規律)
        mid_ppl_diff = 0 if i == 0 else row['200-400張_人數'] - df_s.iloc[i-1]['200-400張_人數']
        mid_vol_diff = 0 if i == 0 else row['200-400張_張數'] - df_s.iloc[i-1]['200-400張_張數']
        k_val = round(mid_vol_diff / mid_ppl_diff, 1) if mid_ppl_diff >= 2 and mid_vol_diff > 0 else 0
        
        # 6. V25.0 融合診斷
        advice = "🔵 趨勢盤整"
        if pure_intensity > 2.5 and cur_p > m20: advice = "🚀 [真·暴力軋空]"
        elif pure_intensity < -1.2: advice = "💀 [主力大舉出貨]"
        elif flipper_impact > 1.2: advice = "⚡ [隔日沖虛假訊號]"
        elif pure_change > 0.4 and cur_p < m20: advice = "🧱 [主力低檔建倉]"
        elif k_val > 200: advice = "🔴 [分身集團集結]"

        out.append({
            "日期": d_str, "收盤價": cur_p, "真實大戶變動(%)": pure_change, 
            "除水強度": pure_intensity, "K_Value": k_val, "V25.0 專家診斷": advice
        })
        
    return pd.DataFrame(out).sort_values('日期', ascending=False)

# ==========================================
# (其餘爬蟲與處理函式：維持原本你貼給我的邏輯)
# ==========================================

# 為了節省空間，這裡保留你程式中的 get_stock_name, safe_get_fubon, fetch_fm, scrape_director_holding, process_tdcc 等函式
# 我已將它們整合在最終執行流程中

# ... (此處省略你原始程式碼中的其餘爬蟲函式，請直接使用你貼給我的完整版本) ...

# ==========================================
# 📌 整合後的執行主引擎
# ==========================================
if run_btn:
    with st.spinner(f"正在執行 V25.0 全息掃描，並還原真實籌碼..."):
        
        # 1. 抓取基本面與股價
        stock_name = get_stock_name(user_stock_id)
        start_date = (datetime.date.today() - datetime.timedelta(days=730)).strftime("%Y-%m-%d")
        df_p_raw = fetch_fm("TaiwanStockPrice", start_date, user_stock_id)
        if df_p_raw.empty: st.error("查無股價資料"); st.stop()
        
        actual_dates = sorted(df_p_raw['date'].unique().tolist(), reverse=True)
        df_price = process_price(df_p_raw)
        
        # 2. 抓取死籌碼引擎
        dynamic_dict, static_val, chip_engine, _ = scrape_director_holding(user_stock_id)
        
        # 3. 抓取分點資料 (60天) 並辨識指紋
        df_branch_raw = fetch_fm_branch_fast_parallel(actual_dates[:60], user_stock_id)
        broker_intel = get_v25_broker_intelligence(df_branch_raw)
        
        # 4. 抓取集保資料
        df_share_raw = fetch_fm("TaiwanStockHoldingSharesPer", actual_dates[60], user_stock_id)
        df_share_wide, df_share_unit, df_share_people = process_tdcc(df_share_raw)
        
        # 5. 【核心】執行 V25.0 去水雷達
        df_v25_radar = process_v25_radar(df_share_wide, df_price, df_branch_raw, dead_chip_input, dynamic_dict, static_val)
        
        # 6. 抓取其他輔助資料 (法人、資券、當沖...)
        df_inst = process_inst(fetch_fm("TaiwanStockInstitutionalInvestorsBuySell", actual_dates[60], user_stock_id))
        df_margin = process_margin(fetch_fm("TaiwanStockMarginPurchaseShortSale", actual_dates[60], user_stock_id))
        
        # --- 開始排版呈現 ---
        st.subheader(f"📊 {user_stock_id} {stock_name} V25.0 AI 量化戰報")
        
        # 專家雷達顯示
        st.markdown("#### ▼▼▼ 1. V25.0 專家診斷雷達 (除水還原版) ▼▼▼")
        st.table(df_v25_radar.head(8))
        
        # 顯示主力分點 Top 15 (含指紋標籤)
        st.markdown("#### ▼▼▼ 2. 主力分點 - 近60日 (指紋識別標記) ▼▼▼")
        df_b_60 = process_branch_top15(df_branch_raw, 60, actual_dates) # 這裡會自動帶入標籤
        # 修改 process_branch_top15 顯示邏輯
        df_b_60['買超分點'] = df_b_60['買超分點'].apply(lambda x: f"{broker_intel.get(x, '🔵')} {x}" if x != "-" else "-")
        df_b_60['賣超分點'] = df_b_60['賣超分點'].apply(lambda x: f"{broker_intel.get(x, '🔵')} {x}" if x != "-" else "-")
        st.table(df_b_60)
        
        # 顯示集保張數表與人數表 (原本的 2-1, 2-2)
        st.markdown("#### ▼▼▼ 3. 集保分級張數表 ▼▼▼")
        st.table(df_share_unit.head(8))

        # --- 生成給 Gemini 的戰報包 ---
        st.divider()
        with st.expander("📋 【點擊複製：給 Gemini 的 V25.0 量化戰報資料包】"):
            p_msg = f"請分析 {user_stock_id} {stock_name} 的籌碼多空強度：\n"
            p_msg += f"1. V25.0 除水診斷：{df_v25_radar['V25.0 專家診斷'].iloc[0]}\n"
            p_msg += f"2. 去水後真實變動：{df_v25_radar['真實大戶變動(%)'].iloc[0]}%\n"
            p_msg += f"3. 除水強度係數：{df_v25_radar['除水強度'].iloc[0]}\n"
            p_msg += f"4. 隔日沖干擾度：{df_v25_radar['雜訊佔比(%)'].iloc[0]}%\n"
            p_msg += f"5. 投信連買天數：{len(df_inst[df_inst['投信買賣超(張)']>0]) if not df_inst.empty else 0}\n"
            p_msg += f"6. 60天核心鎖碼分點：{df_b_60['買超分點'].head(5).tolist()}\n"
            p_msg += "\n請依據以上去水後的純淨數據，判斷下週的「多空操作等級 (1-10)」並給出具體應對建議。"
            st.code(p_msg, language="text")

# (其餘所有 process_price, process_margin, process_inst 等原始函式請務必保留)
