import streamlit as st
import pandas as pd
import requests
import numpy as np
import datetime
import concurrent.futures
import urllib3
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 頁面與基礎設定
# ==========================================
st.set_page_config(layout="wide", page_title="全息量化系統 (動態門檻雷達)", initial_sidebar_state="expanded")

FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiVG9uZTEiLCJlbWFpbCI6InRvbmVoc2llQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjJ9.LQ9tOV7cgcr27W5jIrdriUnvz-6wIFxCOKzuB9F2A-0"

CSS = """
<style>
.table-container { overflow: auto; max-height: 700px; width: 100%; margin-bottom: 25px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding-bottom: 10px; }
.table-container table { width: 100% !important; border-collapse: separate !important; border-spacing: 0; font-size: 15px !important; font-family: sans-serif; background-color: #fff; }
.table-container th, .table-container td { white-space: nowrap !important; padding: 12px 15px !important; border-bottom: 1px solid #dee2e6; border-right: 1px solid #dee2e6; vertical-align: middle; text-align: center; }
.table-container th { border-top: 1px solid #dee2e6; background-color: #f1f3f5 !important; color: #333 !important; font-weight: 700 !important; position: sticky; top: 0; z-index: 3; }
.table-container th:first-child, .table-container td:first-child { position: sticky; left: 0; background-color: #f8f9fa; z-index: 4; font-weight: bold; border-left: 1px solid #dee2e6; }
.info-box { background-color: #f8f9fa; padding: 15px 20px; border-radius: 8px; margin-bottom: 25px; border-left: 6px solid #1e3a8a; font-size: 1.1rem; font-weight: bold; color: #1e3a8a; }
.highlight-red { color: #d32f2f; font-weight: bold; }
.highlight-green { color: #2e7d32; font-weight: bold; }
.threshold-badge { background-color: #e3f2fd; color: #1e3a8a; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 13px;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ==========================================
# 核心連線引擎
# ==========================================
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
    try:
        r = FM_SESSION.get(url, params=dict(params_tuple), timeout=15)
        if r.status_code != 200: return []
        return r.json().get("data", [])
    except:
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_stock_info():
    url = "https://api.finmindtrade.com/api/v4/data"
    p = {"dataset": "TaiwanStockInfo", "start_date": "2000-01-01"}
    df = pd.DataFrame(cached_finmind_api_call(url, tuple(sorted(p.items()))))
    if not df.empty and 'stock_id' in df.columns:
        df = df[df['industry_category'] != '']
        mask = df['stock_id'].astype(str).str.len() == 4
        return df[mask].drop_duplicates('stock_id')
    return pd.DataFrame()

def fetch_single_tdcc(stock_id, date_str):
    url = "https://api.finmindtrade.com/api/v4/data"
    p = {"dataset": "TaiwanStockHoldingSharesPer", "data_id": stock_id, "start_date": date_str, "end_date": date_str}
    return pd.DataFrame(cached_finmind_api_call(url, tuple(sorted(p.items()))))

def render_clean_html_table(df):
    if df.empty: return
    cols = df.columns.tolist()
    html = ["<div class='table-container'><table><thead><tr>"]
    html.extend([f"<th>{c}</th>" for c in cols])
    html.append("</tr></thead><tbody>")
    
    for row in df.itertuples(index=False):
        html.append("<tr>")
        for val in row:
            s = str(val).strip()
            if s.startswith("+"): s = f"<span class='highlight-red'>{s}</span>"
            elif s.startswith("-") and len(s) > 1 and s[1].isdigit(): s = f"<span class='highlight-green'>{s}</span>"
            elif "張" in s and len(s) <= 6: s = f"<span class='threshold-badge'>{s}</span>"
            html.append(f"<td>{s}</td>")
        html.append("</tr>")
    html.append("</tbody></table></div>")
    st.markdown("".join(html), unsafe_allow_html=True)

# ==========================================
# 介面與參數
# ==========================================
st.sidebar.header("🎯 雷達掃描參數")

df_info = fetch_stock_info()
industry_list = ["全市場暴力掃描 (需較長時間)"] + sorted(df_info['industry_category'].unique().tolist()) if not df_info.empty else ["全市場暴力掃描 (需較長時間)"]
scan_mode = st.sidebar.selectbox("掃描範圍", industry_list, index=0)

capital_limit = st.sidebar.number_input("股本上限 (億)", min_value=1, max_value=200, value=50, step=5)

st.sidebar.divider()
st.sidebar.markdown("### 🧠 系統自動計算：大戶精算門檻")
st.sidebar.caption("系統將自動套用 V75.9 邏輯，依據每檔股票總發行量的 1% (界於100~1000張) 自動捕捉最適合的大戶級距。您不需手動設定。")

diff_threshold = st.sidebar.slider("單週大戶增加門檻 (%)", 0.1, 10.0, 0.3, 0.1)

st.sidebar.divider()
run_btn = st.sidebar.button("🚀 啟動多執行緒雷達掃描", use_container_width=True)

st.title("全息量化系統 (V76.9 動態精算門檻雷達)")
st.caption("已全面掛載 AI 級距辨識與動態股本計算引擎。系統會為每一檔中小型股自動分配最佳的「大戶門檻」，精準度大幅提升。")

if run_btn:
    if df_info.empty:
        st.error("無法取得台股代號清單。")
        st.stop()

    with st.spinner("定位集保結算日..."):
        p_tsmc = {"dataset": "TaiwanStockHoldingSharesPer", "data_id": "2330", "start_date": (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")}
        df_tsmc = pd.DataFrame(cached_finmind_api_call("https://api.finmindtrade.com/api/v4/data", tuple(sorted(p_tsmc.items()))))
        if df_tsmc.empty or len(df_tsmc['date'].unique()) < 2:
            st.error("集保日期取得失敗。")
            st.stop()
        tdcc_dates = sorted(df_tsmc['date'].unique(), reverse=True)
        latest_date, prev_date = tdcc_dates[0], tdcc_dates[1]
        st.markdown(f"<div class='info-box'>📅 比對區間：<b>{latest_date}</b> vs <b>{prev_date}</b></div>", unsafe_allow_html=True)

    target_stocks = df_info['stock_id'].tolist() if "全市場" in scan_mode else df_info[df_info['industry_category'] == scan_mode]['stock_id'].tolist()
    total_stocks = len(target_stocks)
    
    st.info(f"鎖定【{scan_mode}】板塊，共計 {total_stocks} 檔個股。啟動多管線併發抓取...")
    
    prog_bar = st.progress(0.0)
    status_text = st.empty()
    
    all_results = []
    completed = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        future_to_stock = {}
        for sid in target_stocks:
            future_to_stock[executor.submit(fetch_single_tdcc, sid, latest_date)] = ('latest', sid)
            future_to_stock[executor.submit(fetch_single_tdcc, sid, prev_date)] = ('prev', sid)
            
        for future in concurrent.futures.as_completed(future_to_stock):
            req_type, sid = future_to_stock[future]
            res = future.result()
            if not res.empty:
                res['period'] = req_type
                all_results.append(res)
            
            completed += 0.5
            prog_bar.progress(min(1.0, completed / total_stocks))
            status_text.text(f"資料下載中... ({int(completed)} / {total_stocks})")
            
    prog_bar.empty()
    status_text.empty()

    if not all_results:
        st.error("額度耗盡或無資料回傳。")
        st.stop()

    df_all = pd.concat(all_results, ignore_index=True)
    stocks_with_data = df_all['stock_id'].nunique()
    st.success(f"資料庫建置完成！成功對齊 {stocks_with_data} 檔個股數據。")

    with st.spinner("AI 引擎運算中：套用個股動態門檻精算籌碼流向..."):
        val_col = 'unit' if 'unit' in df_all.columns else 'HoldingShares'
        df_all[val_col] = pd.to_numeric(df_all[val_col], errors='coerce').fillna(0)
        
        # 💡 將 HoldingSharesLevel 統一轉換為下限張數 (floor_lots)
        def parse_level_to_floor_lots(s):
            s = str(s).replace(',', '').strip()
            if s.isdigit():
                v = int(s)
                if v == 10: return 100
                elif v == 11: return 200
                elif v == 12: return 400
                elif v == 13: return 600
                elif v == 14: return 800
                elif v >= 15: return 1000
                elif v < 10: return 0
                return v // 1000
            else:
                nums = [int(n) for n in re.findall(r'\d+', s)]
                if not nums: return 0
                val = nums[0] // 1000
                
            if val >= 1000: return 1000
            elif val >= 800: return 800
            elif val >= 600: return 600
            elif val >= 400: return 400
            elif val >= 200: return 200
            elif val >= 100: return 100
            return 0

        df_all['floor_lots'] = df_all['HoldingSharesLevel'].apply(parse_level_to_floor_lots)

        def calc_dynamic_smart_pct(df_sub):
            # 1. 取得各股總張數
            g = df_sub.groupby('stock_id')
            total_shares = g[val_col].sum() / 1000
            
            # 2. 為每檔股票動態計算大戶門檻 (ct) -> 1%股本，區間100~1000
            levels = np.array([100, 200, 400, 600, 800, 1000])
            raw_threshold = np.clip(total_shares * 0.01, 100, 1000)
            
            diffs = np.abs(raw_threshold.to_numpy()[:, None] - levels)
            ct_values = levels[diffs.argmin(axis=1)]
            ct_series = pd.Series(ct_values, index=total_shares.index)
            
            # 3. 映射門檻回 DataFrame
            df_sub['ct'] = df_sub['stock_id'].map(ct_series)
            
            # 4. 只加總超過該股專屬門檻的級距
            smart_mask = df_sub['floor_lots'] >= df_sub['ct']
            smart_shares = df_sub[smart_mask].groupby('stock_id')[val_col].sum() / 1000
            
            smart_pct = (smart_shares / total_shares * 100).fillna(0)
            
            return pd.DataFrame({
                'Total_Shares': total_shares,
                'Smart_Pct': smart_pct,
                'Dynamic_CT': ct_series
            })

        df_l = calc_dynamic_smart_pct(df_all[df_all['period'] == 'latest'].copy())
        df_p = calc_dynamic_smart_pct(df_all[df_all['period'] == 'prev'].copy())

        df_scan = df_l.join(df_p, lsuffix='_latest', rsuffix='_prev').dropna()
        df_scan = df_scan[df_scan['Total_Shares_latest'] <= (capital_limit * 10000)]
        df_scan['Diff_Pct'] = df_scan['Smart_Pct_latest'] - df_scan['Smart_Pct_prev']
        df_scan = df_scan[df_scan['Diff_Pct'] >= diff_threshold].sort_values('Diff_Pct', ascending=False)

        if df_scan.empty:
            st.warning(f"掃描結束！在過濾股本後，本次區間的確沒有個股大戶增加超過 {diff_threshold}%。")
        else:
            stock_names = df_info.set_index('stock_id')['stock_name'].to_dict()
            out_data = []
            for sid, row in df_scan.iterrows():
                out_data.append({
                    "代號": sid, 
                    "名稱": stock_names.get(str(sid), ""),
                    "預估股本(億)": f"{row['Total_Shares_latest']/10000:.2f}",
                    "系統精算大戶門檻": f"{int(row['Dynamic_CT_latest'])} 張",
                    "上週大戶(%)": f"{row['Smart_Pct_prev']:.2f}%",
                    "最新大戶(%)": f"{row['Smart_Pct_latest']:.2f}%",
                    "大戶增減(%)": f"+{row['Diff_Pct']:.2f}%" if row['Diff_Pct']>0 else f"{row['Diff_Pct']:.2f}%"
                })
            st.balloons()
            render_clean_html_table(pd.DataFrame(out_data))
