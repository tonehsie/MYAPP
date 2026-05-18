import streamlit as st
import pandas as pd
import requests
import numpy as np
import datetime
import re
import urllib3
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 頁面與基礎設定
# ==========================================
st.set_page_config(layout="wide", page_title="全息量化系統 (中小型股雷達)", initial_sidebar_state="expanded")

FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiVG9uZTEiLCJlbWFpbCI6InRvbmVoc2llQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjJ9.LQ9tOV7cgcr27W5jIrdriUnvz-6wIFxCOKzuB9F2A-0"

# ==========================================
# 前端語法模板集中區 (CSS)
# ==========================================
CSS = """
<style>
.table-container { overflow: auto; max-height: 700px; width: 100%; margin-bottom: 25px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding-bottom: 10px; }
.table-container table { width: 100% !important; border-collapse: separate !important; border-spacing: 0; font-size: 15px !important; font-family: sans-serif; background-color: #fff; }
.table-container th, .table-container td { white-space: nowrap !important; padding: 12px 15px !important; border-bottom: 1px solid #dee2e6; border-right: 1px solid #dee2e6; vertical-align: middle; text-align: center; }
.table-container th { border-top: 1px solid #dee2e6; background-color: #f1f3f5 !important; color: #333 !important; font-weight: 700 !important; position: sticky; top: 0; z-index: 3; }
.table-container th:first-child, .table-container td:first-child { position: sticky; left: 0; background-color: #f8f9fa; z-index: 4; font-weight: bold; border-left: 1px solid #dee2e6; }
.table-container thead th:first-child { z-index: 5; }

.highlight-red { color: #d32f2f; font-weight: bold; }
.highlight-green { color: #2e7d32; font-weight: bold; }
.info-box { background-color: #f8f9fa; padding: 15px 20px; border-radius: 8px; margin-bottom: 25px; border-left: 6px solid #1e3a8a; font-size: 1.1rem; font-weight: bold; color: #1e3a8a; }
.section-title { margin-top: 35px; margin-bottom: 15px; color: #1e3a8a; border-bottom: 2px solid #1e3a8a; padding-bottom: 5px; font-size: 1.3rem !important; font-weight: 700 !important; }

@media (prefers-color-scheme: dark) {
    .table-container table { background-color: #1e1e1e !important; color: #e0e0e0 !important; }
    .table-container th, .table-container td { border-color: #444 !important; color: #e0e0e0 !important; }
    .table-container th { background-color: #2d2d2d !important; color: #fff !important; }
    .table-container th:first-child, .table-container td:first-child { background-color: #252525 !important; }
    .info-box { background-color: #2d2d2d !important; color: #64b5f6 !important; border-left-color: #64b5f6 !important; }
    .highlight-red { color: #ef5350 !important; }
    .highlight-green { color: #66bb6a !important; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ==========================================
# 核心連線與工具函式
# ==========================================
def is_valid(df, min_len=1):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty or len(df) < min_len: return False
    return True

@st.cache_resource(max_entries=3)
def get_finmind_session():
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {FINMIND_TOKEN}", "User-Agent": "Mozilla/5.0"})
    retry = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

FM_SESSION = get_finmind_session()

def cached_finmind_api_call(url, params_tuple):
    r = FM_SESSION.get(url, params=dict(params_tuple), timeout=25)
    r.raise_for_status() 
    data = r.json().get("data")
    return data if data else []

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_stock_info():
    url = "https://api.finmindtrade.com/api/v4/data"
    p = {"dataset": "TaiwanStockInfo", "start_date": "2000-01-01"}
    try:
        data = cached_finmind_api_call(url, tuple(sorted(p.items())))
        df = pd.DataFrame(data)
        if not df.empty and 'stock_id' in df.columns:
            # 只保留 4 碼的普通股
            df = df[df['industry_category'] != '']
            mask = df['stock_id'].astype(str).str.len() == 4
            return df[mask].drop_duplicates('stock_id').set_index('stock_id')['stock_name'].to_dict()
    except: pass
    return {}

def fetch_market_tdcc_by_date(date_str):
    url = "https://api.finmindtrade.com/api/v4/data"
    p = {"dataset": "TaiwanStockHoldingSharesPer", "start_date": date_str, "end_date": date_str}
    try:
        data = cached_finmind_api_call(url, tuple(sorted(p.items())))
        return pd.DataFrame(data)
    except: return pd.DataFrame()

def render_clean_html_table(df, title=""):
    if not is_valid(df):
        if title: st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
        st.warning("查無符合條件的個股。")
        return
        
    cols = df.columns.tolist()
    html_parts = []
    if title: html_parts.append(f"<div class='section-title'>{title}</div>")
        
    html_parts.append("<div class='table-container'><table><thead><tr>")
    html_parts.extend([f"<th>{col}</th>" for col in cols])
    html_parts.append("</tr></thead><tbody>")
    
    for row in df.itertuples(index=False):
        html_parts.append("<tr>")
        for val in row:
            display_val = "-"
            if pd.notna(val):
                s = str(val).strip()
                if s.startswith("+"):
                    display_val = f"<span class='highlight-red'>{s}</span>"
                elif s.startswith("-") and len(s) > 1 and s[1].isdigit():
                    display_val = f"<span class='highlight-green'>{s}</span>"
                else:
                    display_val = s
            html_parts.append(f"<td>{display_val}</td>")
        html_parts.append("</tr>")
        
    html_parts.append("</tbody></table></div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)

# ==========================================
# 側邊欄：戰術參數設定
# ==========================================
st.sidebar.header("🎯 雷達掃描參數")

capital_limit = st.sidebar.number_input("股本上限 (億)", min_value=1, max_value=200, value=50, step=5)
st.sidebar.caption(f"提示：{capital_limit} 億股本約為 {capital_limit * 10000:,} 張發行量。")

st.sidebar.divider()
smart_money_level = st.sidebar.selectbox("大戶聰明錢定義", [
    "400張以上 (中實戶+大戶)", 
    "600張以上 (主力大戶)", 
    "800張以上 (核心大戶)", 
    "1000張以上 (超級大戶)"
], index=0)

diff_threshold = st.sidebar.slider("單週大戶持股增加門檻 (%)", 0.1, 10.0, 1.0, 0.1)

st.sidebar.divider()
run_btn = st.sidebar.button("啟動集保雷達掃描 🚀", use_container_width=True)

# ==========================================
# 主畫面與掃描邏輯
# ==========================================
st.title("全息量化系統 (V76.4 聰明錢突擊雷達版)")
st.caption("專注掃描台股特定股本以下之中小型股，透過集保股權分佈，抓出近期大戶聰明錢異常暴增的潛在飆股。本系統採用全市場快照比對，極度節省 API 額度。")

if run_btn:
    with st.spinner("正在初始化雷達... 取得最新集保日期..."):
        # 1. 利用台積電找出最近兩次的集保結算日
        url = "https://api.finmindtrade.com/api/v4/data"
        p_tsmc = {"dataset": "TaiwanStockHoldingSharesPer", "data_id": "2330", "start_date": (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")}
        tsmc_data = cached_finmind_api_call(url, tuple(sorted(p_tsmc.items())))
        df_tsmc = pd.DataFrame(tsmc_data)
        
        if df_tsmc.empty:
            st.error("無法取得集保日期，請確認 API 狀態或 Token 額度。")
            st.stop()
            
        tdcc_dates = sorted(df_tsmc['date'].unique(), reverse=True)
        if len(tdcc_dates) < 2:
            st.error("集保歷史日期不足，無法進行單週比對。")
            st.stop()
            
        latest_date = tdcc_dates[0]
        prev_date = tdcc_dates[1]
        
        st.markdown(f"<div class='info-box'>📅 鎖定比對日期區間：最新週 <b>{latest_date}</b> vs 前一週 <b>{prev_date}</b></div>", unsafe_allow_html=True)

    with st.spinner(f"正在向 FinMind 請求全市場 {latest_date} 與 {prev_date} 的集保數據 (僅需2次請求)..."):
        # 2. 抓取全市場兩日的集保資料
        df_latest = fetch_market_tdcc_by_date(latest_date)
        df_prev = fetch_market_tdcc_by_date(prev_date)
        
        if df_latest.empty or df_prev.empty:
            st.error("全市場集保數據抓取失敗。FinMind 可能限制了無 data_id 的大範圍請求，請稍後再試。")
            st.stop()

    with st.spinner("資料解析中... 進行股本過濾與大戶增減計算..."):
        # 3. 定義大戶級距
        if "400張" in smart_money_level: target_levels = [12, 13, 14, 15]
        elif "600張" in smart_money_level: target_levels = [13, 14, 15]
        elif "800張" in smart_money_level: target_levels = [14, 15]
        else: target_levels = [15]

        def process_market_snapshot(df_snap):
            df_snap['HoldingShares'] = pd.to_numeric(df_snap['HoldingShares'], errors='coerce').fillna(0)
            df_snap['level_int'] = pd.to_numeric(df_snap['HoldingSharesLevel'], errors='coerce').fillna(0).astype(int)
            
            # 過濾出有效的普通股 (長度為4)
            df_snap = df_snap[df_snap['stock_id'].astype(str).str.len() == 4]
            
            # 計算每檔股票的總張數
            g = df_snap.groupby('stock_id')
            total_shares = g['HoldingShares'].sum() / 1000
            
            # 計算大戶張數
            smart_mask = df_snap['level_int'].isin(target_levels)
            smart_shares = df_snap[smart_mask].groupby('stock_id')['HoldingShares'].sum() / 1000
            
            # 轉換為百分比
            smart_pct = (smart_shares / total_shares * 100).fillna(0)
            
            return pd.DataFrame({
                'Total_Shares': total_shares,
                'Smart_Pct': smart_pct
            })

        res_latest = process_market_snapshot(df_latest)
        res_prev = process_market_snapshot(df_prev)

        # 4. 合併兩期資料
        df_scan = res_latest.join(res_prev, lsuffix='_latest', rsuffix='_prev').dropna()

        # 5. 進行股本過濾 (1億 = 10,000張)
        max_shares_limit = capital_limit * 10000
        df_scan = df_scan[df_scan['Total_Shares_latest'] <= max_shares_limit]

        # 6. 計算增減並篩選
        df_scan['Diff_Pct'] = df_scan['Smart_Pct_latest'] - df_scan['Smart_Pct_prev']
        df_scan = df_scan[df_scan['Diff_Pct'] >= diff_threshold]

        if df_scan.empty:
            st.warning(f"掃描完成！但在股本 {capital_limit} 億以下，沒有找到大戶持股單週增加超過 {diff_threshold}% 的個股。")
            st.stop()

        # 7. 整理最終輸出表
        stock_names = fetch_stock_info()
        
        # 排除 0 開頭的 ETF 或非普通股，只留 1-9 開頭的普通股
        common_stocks = [s for s in df_scan.index if str(s)[0] in '12345689']
        df_scan = df_scan.loc[common_stocks].copy()
        
        df_scan = df_scan.sort_values('Diff_Pct', ascending=False)
        
        out_data = []
        for sid, row in df_scan.iterrows():
            name = stock_names.get(str(sid), "未知")
            capital_yi = row['Total_Shares_latest'] / 10000
            diff = row['Diff_Pct']
            
            out_data.append({
                "股票代號": sid,
                "股票名稱": name,
                "預估股本(億)": f"{capital_yi:.2f}",
                "上週大戶比例(%)": f"{row['Smart_Pct_prev']:.2f}%",
                "最新大戶比例(%)": f"{row['Smart_Pct_latest']:.2f}%",
                "單週大戶增減(%)": f"+{diff:.2f}%" if diff > 0 else f"{diff:.2f}%"
            })
            
        df_out = pd.DataFrame(out_data)

    # 8. 顯示結果
    st.success(f"掃描完畢！共抓出 {len(df_out)} 檔符合「股本 <= {capital_limit} 億」且「大戶單週增加 >= {diff_threshold}%」的個股。")
    render_clean_html_table(df_out, "🚨 聰明錢大戶突擊雷達結果")
    
else:
    st.info("請設定左側參數，並點擊「啟動集保雷達掃描 🚀」開始執行全市場透視。")
