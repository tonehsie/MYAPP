import streamlit as st
import pandas as pd
import requests
import json
import numpy as np
import datetime
import re
import concurrent.futures
import urllib.request
import ssl
import urllib3
import gc  # 新增：強制垃圾回收模組
from io import StringIO
import streamlit.components.v1 as components
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="全息量化系統 (V70.16版)", initial_sidebar_state="expanded")

FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"
GITHUB_MANUAL_URL = "https://raw.githubusercontent.com/tonehsie/stock/refs/heads/main/README.md"

CSS = """
<style>
/* 將 max-height 拉長到 600px，完美容納 10 行資料不被遮擋 */
.table-container { overflow: auto; max-height: 600px; width: 100%; margin-bottom: 25px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.table-container table { width: max-content !important; min-width: 40%; border-collapse: separate !important; border-spacing: 0; font-size: 15px !important; font-family: sans-serif; background-color: #fff; }
.table-container th, .table-container td { white-space: nowrap !important; padding: 10px 12px !important; border-bottom: 1px solid #dee2e6; border-right: 1px solid #dee2e6; vertical-align: middle; }
.table-container th { border-top: 1px solid #dee2e6; word-break: keep-all !important; text-align: center !important; background-color: #f1f3f5 !important; color: #333 !important; font-weight: 700 !important; line-height: 1.4; position: sticky; top: 0; z-index: 3; }
.table-container th:first-child, .table-container td:first-child { position: sticky; left: 0; background-color: #f8f9fa; z-index: 4; font-weight: bold; text-align: center !important; border-left: 1px solid #dee2e6; }
.table-container thead th:first-child { z-index: 5; }
.text-left { text-align: left !important; }
.text-right { text-align: right !important; font-variant-numeric: tabular-nums; }
.loss-warning { color: #d9480f; font-weight: bold; }
.profit-warning { color: #6a1b9a; font-weight: 900; background-color: #f3e5f5; padding: 3px 6px; border-radius: 4px; border: 1px solid #ce93d8; }
.highlight-red { color: #d32f2f; font-weight: bold; }
.highlight-green { color: #2e7d32; font-weight: bold; }
.info-box { background-color: #f8f9fa; padding: 15px 20px; border-radius: 8px; margin-bottom: 25px; border-left: 6px solid #1e3a8a; font-size: 1.1rem; font-weight: bold; color: #1e3a8a; }
.section-title { margin-top: 35px; margin-bottom: 15px; color: #1e3a8a; border-bottom: 2px solid #1e3a8a; padding-bottom: 5px; font-size: 1.3rem !important; font-weight: 700 !important; }
.category-title { font-size: 1.6rem !important; font-weight: 900 !important; margin-top: 40px; color: #333; }
.stTabs [data-baseweb='tab-list'] { gap: 10px; }
.stTabs [data-baseweb='tab'] { height: 50px; white-space: pre-wrap; background-color: #f8f9fa; border-radius: 4px 4px 0 0; padding: 10px 20px; font-weight: bold; }
.stTabs [aria-selected='true'] { background-color: #e3f2fd !important; color: #1e3a8a !important; border-bottom: 3px solid #1e3a8a !important; }
.ai-report-box { background-color: #fcfdfe; border: 1px solid #e9ecef; border-left: 5px solid #1e3a8a; border-radius: 8px; padding: 25px; margin-bottom: 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); line-height: 1.6; }
.ai-report-box h4 { margin-top: 0; color: #1e3a8a; font-weight: 800; font-size: 1.2rem; border-bottom: 1px dashed #ccc; padding-bottom: 8px; margin-bottom: 15px; }
.ai-report-box ul { margin-bottom: 20px; }
.ai-report-box li { margin-bottom: 8px; font-size: 1.05rem; color: #333; }
.ai-conclusion { background-color: #fff3cd; padding: 15px; border-radius: 6px; border: 1px solid #ffe69c; font-weight: 700; color: #856404; }
.progress-text { font-size: 1.1rem; color: #1e3a8a; font-weight: bold; margin-bottom: 5px; }

/* 自動深/淺色模式切換 */
@media (prefers-color-scheme: dark) {
    .table-container table { background-color: #1e1e1e !important; color: #e0e0e0 !important; }
    .table-container th, .table-container td { border-color: #444 !important; color: #e0e0e0 !important; }
    .table-container th { background-color: #2d2d2d !important; color: #fff !important; }
    .table-container th:first-child, .table-container td:first-child { background-color: #252525 !important; }
    .info-box { background-color: #2d2d2d !important; color: #64b5f6 !important; border-left-color: #64b5f6 !important; }
    .section-title { color: #64b5f6 !important; border-bottom-color: #64b5f6 !important; }
    .category-title { color: #fff !important; }
    .stTabs [data-baseweb='tab'] { background-color: #2d2d2d !important; color: #aaa !important; }
    .stTabs [aria-selected='true'] { background-color: #1a237e !important; color: #64b5f6 !important; border-bottom-color: #64b5f6 !important; }
    .ai-report-box { background-color: #252525 !important; border-color: #444 !important; border-left-color: #64b5f6 !important; color: #e0e0e0 !important; }
    .ai-report-box h4 { color: #64b5f6 !important; border-bottom-color: #444 !important; }
    .ai-report-box li { color: #e0e0e0 !important; }
    .ai-conclusion { background-color: #3e2723 !important; border-color: #5d4037 !important; color: #ffb74d !important; }
    .progress-text { color: #64b5f6 !important; }
    .profit-warning { background-color: #4a148c !important; color: #e1bee7 !important; border-color: #7b1fa2 !important; }
    .loss-warning { color: #ff7043 !important; }
    .highlight-red { color: #ef5350 !important; }
    .highlight-green { color: #66bb6a !important; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

@st.cache_resource
def get_finmind_session():
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {FINMIND_TOKEN}", "User-Agent": "Mozilla/5.0"})
    retry = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

@st.cache_resource
def get_generic_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

FM_SESSION = get_finmind_session()
GENERIC_SESSION = get_generic_session()

_num_re = re.compile(r'\d+')
_LEVEL_MAP = {
    1: "1-999股", 2: "1-5張", 3: "5-10張", 4: "10-15張", 5: "15-20張",
    6: "20-30張", 7: "30-40張", 8: "40-50張", 9: "50-100張", 10: "100-200張",
    11: "200-400張", 12: "400-600張", 13: "600-800張", 14: "800-1000張", 15: "1000張以上"
}
_LEVEL_CLEAN_CACHE = {}

# 💡 記憶體優化：加入 max_entries 避免無上限快取吃光免費額度
@st.cache_data(ttl=86400, max_entries=5, show_spinner=False)
def fetch_github_manual(url):
    try:
        r = GENERIC_SESSION.get(url, timeout=5)
        if r.status_code == 200:
            r.encoding = 'utf-8'
            return r.text
        return "無法載入說明書，請確認 GitHub Raw 網址是否正確。"
    except Exception as e: return f"說明書載入失敗: {e}"

@st.cache_data(ttl=300, max_entries=2, show_spinner=False)
def get_api_usage(token):
    try:
        r = GENERIC_SESSION.get(f"https://api.web.finmindtrade.com/v2/user_info?token={token}", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data.get("user_count", 0), data.get("api_request_limit", 0)
    except: pass
    return None, None

# ==========================================
# 🔥 總開關：交易戰略大腦 (動態切換)
# ==========================================
st.sidebar.markdown("### 🧠 交易戰略大腦")
trade_strategy = st.sidebar.radio("交易戰略偏好 (自動切換排檔)", ["🚀 右側動能 (短線突破)", "🛡️ 左側潛伏 (中長線價值)"])
is_right_side = "右側" in trade_strategy

st.sidebar.header("戰術參數控制面板")
kline_days = st.sidebar.slider("K線顯示天數 (圖表景深)", 30, 600, 270, 10)
lookback_days = st.sidebar.selectbox("長線籌碼回溯天數 (全局黏著度分母)", [20, 60, 90, 120], index=1)
stickiness_threshold = st.sidebar.slider("主力黏著度門檻 (%)", 10.0, 80.0, 50.0, 5.0)

default_foot_days = 10 if is_right_side else 45
footprint_days = st.sidebar.slider("足跡明細追蹤天數 (顯示範圍)", 3, 90, default_foot_days, 1)
footprint_rows = st.sidebar.slider("足跡矩陣顯示筆數 (多空各 N 名)", 5, 50, 15, 5)

st.sidebar.divider()
st.sidebar.markdown("### 🥩 視覺系主菜：熱力圖設定")
heatmap_noise_pct = st.sidebar.slider("熱力圖雜訊過濾 (佔20日均量 %)", 0.0, 5.0, 0.5 if is_right_side else 1.0, 0.1)

st.sidebar.divider()
st.sidebar.markdown("### 🥗 防禦系配菜：警報器設定")
alert_smart_pct = st.sidebar.slider("警報: 聰明錢極端進出 (佔20日均量 %)", 1.0, 20.0, 10.0 if is_right_side else 5.0, 1.0)
alert_bias_drop = st.sidebar.slider("警報: 跌破主力防守乖離 < (%)", -20.0, 0.0, -3.0, 0.5)

st.sidebar.divider()
firepower_threshold = st.sidebar.slider("買方火力倍數門檻", 1.0, 5.0, 1.5, 0.1)

st.sidebar.divider()
st.sidebar.markdown("### AI 幾何形態與技術線")
enable_pattern = st.sidebar.checkbox("啟動 AI 幾何形態掃描", value=True)

pattern_mode = st.sidebar.selectbox("形態顯示模式", [
    "全自動智慧辨識 (Auto)", 
    "反轉：W底 (雙重底)", "反轉：M頭 (雙重頂)", 
    "反轉：頭肩底", "反轉：頭肩頂", 
    "反轉：三重底", "反轉：三重頂",
    "反轉：V型反轉",
    "連續：對稱三角形", 
    "連續：上升三角形", "連續：下降三角形",
    "連續：上升楔形", "連續：下降楔形",
    "連續：矩形 (箱型整理)"
])

lr_days = st.sidebar.slider("線性迴歸通道天數 (動態趨勢)", 20, 120, 20, 5)
pattern_order = st.sidebar.slider("形態辨識靈敏度 (Order)", 2, 20, 5, 1)

st.sidebar.divider()
st.sidebar.markdown("### 淨化籌碼引擎")
filter_day_trade = st.sidebar.checkbox("剔除散戶與當沖，計算純淨加權均價", value=True)
st.sidebar.divider()
ma_short = st.sidebar.number_input("短均線 (天)", min_value=1, max_value=20, value=10)
ma_mid = st.sidebar.number_input("中均線/防守線 (天)", min_value=20, max_value=100, value=60)
ma_long = st.sidebar.number_input("長均線 (天)", min_value=100, max_value=300, value=240)

st.title("全息量化系統 (V70.16 記憶體優化版)")
user_count, api_limit = get_api_usage(FINMIND_TOKEN)
usage_text = f" | FinMind 額度: {user_count} / {api_limit}" if user_count is not None else ""
st.caption(f"V70.16：導入 OOM 記憶體防護機制，降低背景併發數量與釋放快取，解決系統崩潰問題。{usage_text}")

with st.expander("點此閱讀【全息量化系統】四大核心模組終極實戰說明書", expanded=False):
    st.markdown(fetch_github_manual(GITHUB_MANUAL_URL), unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])
with col1: 
    user_stock_id = st.text_input("個股代號", value="2330")
with col2: 
    dead_chip_input = st.text_input("死籌碼 % (董監事持股、董監事＋大股東持股，留空自動抓)")
run_btn = st.button("啟動 V70.16 決策引擎", use_container_width=True, key="run_engine")

def safe_to_num(series, fill_val=0):
    if isinstance(series, pd.Series):
        if pd.api.types.is_numeric_dtype(series): return series.fillna(fill_val)
        try: return pd.to_numeric(series.astype(str).str.replace(',', '', regex=False).str.replace('%', '', regex=False).str.strip(), errors='coerce').fillna(fill_val)
        except: return pd.Series([fill_val] * len(series))
    elif isinstance(series, (int, float)): return series
    else:
        try: return float(str(series).replace(',', '').replace('%', '').strip())
        except: return fill_val

# 💡 記憶體優化：快取限制最多存 3 筆，防止無限膨脹
@st.cache_data(ttl=3600, max_entries=3, show_spinner=False)
def cached_finmind_api_call(url, params_tuple):
    r = FM_SESSION.get(url, params=dict(params_tuple), timeout=20)
    r.raise_for_status() 
    data = r.json().get("data")
    if data is None:
        raise ValueError("FinMind 回傳資料為空")
    return data

@st.cache_data(ttl=86400, max_entries=10, show_spinner=False)
def get_basic_info_finmind(tid):
    name, ind = "未知名稱", "未知產業"
    try:
        url = "https://api.finmindtrade.com/api/v4/data"
        p = {"dataset": "TaiwanStockInfo", "data_id": tid, "start_date": "2000-01-01"}
        data = cached_finmind_api_call(url, tuple(sorted(p.items())))
        if data:
            df = pd.DataFrame(data)
            if not df.empty:
                if 'stock_name' in df.columns: name = df['stock_name'].iloc[0]
                if 'industry_category' in df.columns: ind = df['industry_category'].iloc[0]
    except: pass
    return name, ind

def fetch_finmind_v50(ds, sd, tid=None, ed=None):
    url = "https://api.finmindtrade.com/api/v4/data"
    p = {"dataset": ds, "start_date": sd}
    if tid: p["data_id"] = tid
    if ed: p["end_date"] = ed
    try:
        data = cached_finmind_api_call(url, tuple(sorted(p.items())))
        return pd.DataFrame(data) if data else pd.DataFrame()
    except:
        return pd.DataFrame()

def fetch_heavy_data_sync_with_progress(user_stock_id, dates, max_len):
    b_results = []
    a_results = {}
    cb_info_list = []

    tdcc_sd = (datetime.date.today() - datetime.timedelta(days=180)).strftime("%Y-%m-%d")
    d_end = dates[max_len-1] if max_len > 0 else dates[0]
    dt_sd = (datetime.date.today() - datetime.timedelta(days=700)).strftime("%Y-%m-%d")

    api_targets = [
        ("TaiwanStockHoldingSharesPer", tdcc_sd, None, user_stock_id),
        ("TaiwanStockMarginPurchaseShortSale", d_end, None, user_stock_id),
        ("TaiwanStockDayTrading", dt_sd, None, user_stock_id),
        ("TaiwanStockInstitutionalInvestorsBuySell", d_end, None, user_stock_id),
        ("TaiwanStockMonthRevenue", "2022-01-01", None, user_stock_id),
        ("TaiwanFuturesInstitutionalInvestors", d_end, None, "TX"),
        ("TaiwanStockDividend", "2015-01-01", None, user_stock_id),
        ("TaiwanStockPER", d_end, None, user_stock_id),
        ("TaiwanStockDispositionSecuritiesPeriod", tdcc_sd, None, user_stock_id),
        ("TaiwanStockConvertibleBondDailyOverview", dates[0], None, None)
    ]

    total_tasks = max_len + len(api_targets)
    
    prog_container = st.empty()
    text_container = st.empty()
    prog_bar = prog_container.progress(0.0)

    def fetch_api(dataset, sd, ed, tid):
        url = "https://api.finmindtrade.com/api/v4/data"
        p = {"dataset": dataset, "start_date": sd}
        if tid: p["data_id"] = tid
        if ed: p["end_date"] = ed
        try:
            return dataset, cached_finmind_api_call(url, tuple(sorted(p.items())))
        except:
            return dataset, []

    def fetch_branch(d, tid):
        url = "https://api.finmindtrade.com/api/v4/data"
        p = {"dataset": "TaiwanStockTradingDailyReport", "data_id": tid, "start_date": d, "end_date": d}
        try:
            return cached_finmind_api_call(url, tuple(sorted(p.items())))
        except:
            return []

    # 💡 記憶體優化：調降最大線程數由 8 降為 4，避免瞬間吃光 1GB RAM
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_type = {}
        for d in dates[:max_len]:
            future_to_type[executor.submit(fetch_branch, d, user_stock_id)] = 'branch'
        for ds, sd, ed, tid in api_targets:
            future_to_type[executor.submit(fetch_api, ds, sd, ed, tid)] = 'api'

        completed = 0
        for future in concurrent.futures.as_completed(future_to_type):
            completed += 1
            prog_val = min(1.0, completed / total_tasks)
            prog_bar.progress(prog_val)
            text_container.markdown(f"<div class='progress-text'>⚡ 正在與 FinMind 伺服器同步巨量資料... (進度: {completed} / {total_tasks})</div>", unsafe_allow_html=True)

            f_type = future_to_type[future]
            if f_type == 'branch':
                res = future.result()
                if res: b_results.extend(res)
            else:
                ds, data = future.result()
                a_results[ds] = pd.DataFrame(data)

        df_cbas_raw = a_results.get("TaiwanStockConvertibleBondDailyOverview", pd.DataFrame())
        if not df_cbas_raw.empty and 'cb_id' in df_cbas_raw.columns:
            cb_mask = df_cbas_raw['cb_id'].astype(str).str.replace(',', '', regex=False).str.startswith(user_stock_id)
            target_cbs = df_cbas_raw[cb_mask]['cb_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.replace(',', '', regex=False).str.strip().unique()
            
            if len(target_cbs) > 0:
                text_container.markdown(f"<div class='progress-text'>🔍 正在掃描並擴充可轉債(CBAS)資訊...</div>", unsafe_allow_html=True)
                cb_futures = [executor.submit(fetch_api, "TaiwanStockConvertibleBondInfo", "2000-01-01", None, cid) for cid in target_cbs]
                for f in concurrent.futures.as_completed(cb_futures):
                    _, cb_data = f.result()
                    if cb_data: cb_info_list.extend(cb_data)

    prog_container.empty()
    text_container.empty()

    df_b = pd.DataFrame.from_records(b_results) if b_results else pd.DataFrame()
    df_cb_info = pd.DataFrame(cb_info_list)
    return df_b, a_results, df_cb_info

def safe_get_fubon(url):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        if hasattr(ssl, 'OP_LEGACY_SERVER_CONNECT'): ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as res: return res.read().decode('big5', errors='ignore')
    except:
        try:
            res = GENERIC_SESSION.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, verify=False)
            if res.status_code == 200: 
                res.encoding = 'big5'
                return res.text
        except: pass
    return ""

# 💡 記憶體優化：限制快取數
@st.cache_data(ttl=3600, max_entries=3, show_spinner=False)
def scrape_director_v50(tid):
    dd, sv = {}, 0.0
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Cookie": "CLIENT_KEY=20260413;", "Referer": f"https://goodinfo.tw/tw/StockDetail.asp?STOCK_ID={tid}"}
        r = GENERIC_SESSION.get(f"https://goodinfo.tw/tw/StockDirectorSharehold.asp?STOCK_ID={tid}", headers=headers, timeout=8)
        if r.status_code == 200:
            r.encoding = 'utf-8'
            for df in pd.read_html(StringIO(r.text)):
                if isinstance(df.columns, pd.MultiIndex): df.columns = ['_'.join(str(c) for c in col if 'Unnamed' not in str(c)).strip('_') for col in df.columns.values]
                else: df.columns = df.columns.astype(str)
                tc = next((c for c in df.columns if '全體董監持股' in str(c) and '持股(%)' in str(c).replace(' ', '')), None)
                mc = next((c for c in df.columns if '月別' in str(c)), None)
                if tc and mc:
                    lt = 0.0
                    for ro in df.to_dict('records'):
                        m, v = str(ro.get(mc, '')).replace('/', '-').strip(), str(ro.get(tc, '')).replace(',', '').strip()
                        if re.match(r'^\d{4}-\d{2}$', m) and v not in ['-', '', 'nan']:
                            try:
                                val = float(v)
                                if 0 < val < 100:
                                    dd[m] = val
                                    if lt == 0.0: lt = val
                            except: pass
                    if dd: return dd, lt, "Goodinfo", []
    except: pass
    
    try:
        html = safe_get_fubon(f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zck/zck_{tid}.djhtm")
        if html:
            tm = re.search(r'姓名/法人名稱(.*?)</table>', html, re.IGNORECASE | re.DOTALL)
            if tm:
                ed = {}
                for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', tm.group(1), re.IGNORECASE | re.DOTALL):
                    tds = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.IGNORECASE | re.DOTALL)
                    if len(tds) >= 4:
                        title = re.sub(r'<[^>]+>', '', tds[0]).strip()
                        name = re.sub(r'<[^>]+>', '', tds[1]).strip()
                        r_str = re.sub(r'<[^>]+>', '', tds[3]).replace('%', '').strip()
                        if ('董' in title or '監' in title) and '辭' not in title and '職稱' not in title:
                            try: ed[name.split('-')[0].strip()] = max(ed.get(name.split('-')[0].strip(), 0), float(r_str))
                            except: pass
                if 0 < sum(ed.values()) < 100: return {}, round(sum(ed.values()), 2), "富邦精算(備援)", []
    except: pass
    return {}, 0.0, "雙引擎皆失敗(請手動)", []

def get_dead_chip_info(ds, dci, dd, sv, ce):
    if dci and str(dci).strip() != "":
        try: return float(str(dci).replace('%', '').strip()), "手動輸入"
        except: pass
    mk = str(ds)[:7].replace('/', '-')
    if dd and mk in dd: return dd[mk], f"{ce}當月"
    if dd: return list(dd.values())[0], f"{ce}最新"
    return (sv, ce) if sv > 0 else (0.0, "缺數據")

def extract_fubon_table(ht, trg, cols):
    si = ht.find(trg)
    if si == -1: return []
    fh = ht[max(0, si - 500) : si + 35000]
    trs = re.compile(r'<tr[^>]*>([\s\S]*?)</tr>', re.IGNORECASE).findall(fh)
    tdp = re.compile(r'<t[dh][^>]*>([\s\S]*?)</t[dh]>', re.IGNORECASE)
    out, ist = [], False
    for tr in trs:
        tds = tdp.findall(tr)
        if tds:
            r = [re.sub(r'<[^>]+>', '', td).replace('&nbsp;', '').replace(' ', '').replace('\r', '').replace('\n', '').strip() for td in tds]
            if trg in "".join(r): ist = True
            elif ist and len(r) >= cols:
                if r[0] == "" or "註" in r[0]: ist = False
                else: out.append(r[:cols])
    return out

# 💡 記憶體優化：限制快取數
@st.cache_data(ttl=3600, max_entries=3, show_spinner=False)
def scrape_fubon_pledge(df_pr, tid):
    alld = []
    for i in range(3):
        html = safe_get_fubon(f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zc0/zc06_{tid}_{i}.djhtm")
        if html:
            p = extract_fubon_table(html, "設質人身", 7)
            if p: alld.extend(p)
    if not alld: return pd.DataFrame(), pd.DataFrame()
    sn, uq = set(), []
    for r in alld:
        if "|".join(r) not in sn: 
            sn.add("|".join(r))
            uq.append(r)
    df_all = pd.DataFrame(uq, columns=["日期", "身份別", "姓名", "設質(張)", "解質(張)", "累積質設(張)", "質權人"])
    cy, cm, py, pm = datetime.datetime.now().year, datetime.datetime.now().month, datetime.datetime.now().year, 99
    pdts = []
    for ds in df_all['日期']:
        if len(ds) == 5 and '/' in ds: 
            m = int(ds.split('/')[0])
            if pm == 99: py = cy - 1 if m > cm + 1 and cm < 3 else cy
            elif m > pm + 1: py -= 1
            pm = m
            pdts.append(f"{py}-{ds.replace('/', '-')}")
        elif len(ds) >= 7 and '/' in ds: 
            pts = ds.split('/')
            py, pm = int(pts[0]) + 1911, int(pts[1])
            pdts.append(f"{py}-{pts[1].strip()}-{pts[2].strip()}")
        else: pdts.append(ds)
    df_all['日期'] = pdts
    
    for c in ["設質(張)", "解質(張)", "累積質設(張)"]: 
        df_all[c] = safe_to_num(df_all[c]).astype(int)
        
    prd = {pd.to_datetime(r['date']).strftime('%Y-%m-%d'): r['close'] for _, r in df_pr.iterrows()}
    pps, mcs = [], []
    for r in df_all.to_dict('records'):
        fp, mc = "-", "-"
        if r['設質(張)'] > 0:
            try:
                td = pd.to_datetime(r['日期'])
                for i in range(20):
                    cd = (td - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
                    if cd in prd: 
                        fp = prd[cd]
                        mc = round(fp * 0.78, 2)
                        break
            except: pass
        pps.append(fp)
        mcs.append(mc)
    df_all['設質日收盤價'], df_all['強制賣出價(0.78)'] = pps, mcs
    sm = {}
    for r in df_all.to_dict('records'):
        if r['姓名'] not in sm: sm[r['姓名']] = {"title": r['身份別'], "balance": r['累積質設(張)'], "p": "-", "mc": "-"}
        if sm[r['姓名']]["p"] == "-" and r['設質(張)'] > 0: 
            sm[r['姓名']]["p"] = r['設質日收盤價']
            sm[r['姓名']]["mc"] = r['強制賣出價(0.78)']
    sr = [{"身份別": d["title"], "姓名": n, "目前剩餘質設(張)": d["balance"], "最後設質收盤價(元)": d["p"], "估算斷頭價(0.78)": d["mc"]} for n, d in sm.items() if d["balance"] > 0]
    return pd.DataFrame(sr), df_all

def get_v50_intelligence(df_b_raw, df_p_raw, stick_thresh, global_days, dates_list):
    if df_b_raw.empty or df_p_raw.empty: return {}, pd.DataFrame()
    
    actual_global_days = max(1, df_b_raw['date'].nunique())

    df_p = df_p_raw.copy()
    df_p['date'] = pd.to_datetime(df_p['date'])
    df_p = df_p.sort_values('date', ascending=False)
    
    df_p['actual_spread'] = df_p['close'] - df_p['close'].shift(-1).fillna(df_p['close'])
    range_diff = df_p['max'] - df_p['min']
    df_p['pos'] = 0.5 
    cond_normal = range_diff > 0
    df_p.loc[cond_normal, 'pos'] = (df_p['close'] - df_p['min']) / range_diff
    df_p.loc[(~cond_normal) & (df_p['actual_spread'] > 0), 'pos'] = 1.0
    df_p.loc[(~cond_normal) & (df_p['actual_spread'] < 0), 'pos'] = 0.0
    
    pos_dict = df_p.set_index('date')['pos'].to_dict()
    latest_close = df_p['close'].iloc[0] if not df_p.empty else 0

    df = df_b_raw.copy()
    df['date_dt'] = pd.to_datetime(df['date'])
    df['net_shares'] = df['buy'] - df['sell']
    
    df['v_buy_amt'] = np.where(df['buy'] > 0, df['buy'] * df['price'], 0)
    df['v_buy_vol'] = np.where(df['buy'] > 0, df['buy'], 0)
    df['v_sell_amt'] = np.where(df['sell'] > 0, df['sell'] * df['price'], 0)
    df['v_sell_vol'] = np.where(df['sell'] > 0, df['sell'], 0)

    d5 = dates_list[:5]
    d20 = dates_list[:20] if len(dates_list) >= 20 else dates_list
    d60 = dates_list[:60] if len(dates_list) >= 60 else dates_list

    g5_shares = df[df['date'].isin(d5)].groupby('securities_trader')['net_shares'].sum()
    g20_shares = df[df['date'].isin(d20)].groupby('securities_trader')['net_shares'].sum()
    g60_shares = df[df['date'].isin(d60)].groupby('securities_trader')['net_shares'].sum()
    
    stats = pd.DataFrame({
        'net_5d': (g5_shares / 1000).round(),
        'net_20d': (g20_shares / 1000).round(),
        'net_60d': (g60_shares / 1000).round()
    }).fillna(0).astype(int)

    g = df.groupby('securities_trader').agg(
        tb_shares=('buy', 'sum'),
        ts_shares=('sell', 'sum'),
        net_shares=('net_shares', 'sum'),
        buy_amt=('v_buy_amt', 'sum'),
        sell_amt=('v_sell_amt', 'sum'),
        valid_b_shares=('v_buy_vol', 'sum'),
        valid_s_shares=('v_sell_vol', 'sum'),
        active_days=('date_dt', 'nunique'),
        last_date=('date_dt', 'max')
    )
    
    g['stickiness'] = (g['active_days'] / actual_global_days) * 100
    
    g['hoard_ratio'] = np.where(g['net_shares'] > 0,
                                (g['net_shares'] / g['tb_shares'].replace(0, np.nan)) * 100,
                                (g['net_shares'].abs() / g['ts_shares'].replace(0, np.nan)) * 100)
    g['hoard_ratio'] = g['hoard_ratio'].fillna(0).round(1)

    g['avg_b'] = (g['buy_amt'] / g['valid_b_shares'].replace(0, np.nan)).fillna(0)
    g['avg_s'] = (g['sell_amt'] / g['valid_s_shares'].replace(0, np.nan)).fillna(0)
    
    g = g.join(stats).fillna(0)
    
    g['tb'] = (g['tb_shares'] / 1000).round().astype(int)
    g['ts'] = (g['ts_shares'] / 1000).round().astype(int)
    g['net_lots'] = (g['net_shares'] / 1000).round().astype(int)
    
    # 標籤邏輯
    cond_heavy = g['net_20d'].abs() >= 300
    cond_lock = (g['net_60d'] >= 200) & (g['net_20d'] >= 100) & (g['net_5d'] >= 50)
    cond_cover = (g['net_60d'] <= -100) & (g['net_5d'] >= 200)
    cond_profit = (g['net_60d'] >= 300) & (g['net_20d'] >= 100) & (g['net_5d'] <= -100)
    cond_exit = (g['net_60d'] <= -200) & (g['net_20d'] <= -100) & (g['net_5d'] <= -100)
    cond_snap = (g['net_60d'].between(-200, 200)) & (g['net_20d'].between(-200, 200)) & (g['net_5d'] >= 300)
    cond_maker = g['stickiness'] >= stick_thresh
    cond_follow = (g['stickiness'] < 10.0) & (g['net_5d'].abs() > 50)

    g['tag'] = np.select(
        [cond_heavy, cond_lock, cond_cover, cond_profit, cond_exit, cond_snap, cond_maker, cond_follow],
        ["【主力重砲】", "【波段鎖碼】", "【認錯回補】", "【獲利調節】", "【棄守提款】", "【隔日突擊】", "【避險造市】", "【跟風小戶】"],
        default="【路人雜訊】"
    )

    tags = g['tag'].to_dict()
    g = g[(g['tb_shares'] > 0) | (g['ts_shares'] > 0)].copy()
    
    cond_loss = (g['avg_b'] > latest_close) & (g['avg_b'] > 0) & (g['net_shares'] > 0)
    b_strs = g['avg_b'].apply(lambda x: f"{x:,.2f}" if x > 0 else "-")
    g['b_str'] = np.where(cond_loss, "(虧) " + b_strs, b_strs)
    g['pos'] = g['last_date'].map(pos_dict).fillna(0.5).round(2)
    
    res_df = pd.DataFrame({
        "分點名稱": g.index,
        "最終標籤": g['tag'],
        "近60日淨買(張)": g['net_60d'].astype(int),
        "近20日淨買(張)": g['net_20d'].astype(int),
        "近5日淨買(張)": g['net_5d'].astype(int),
        "黏著度(%)": g['stickiness'].round(1),
        "囤出貨率(%)": g['hoard_ratio'],
        "總買(張)": g['tb'],
        "總賣(張)": g['ts'],
        "淨留倉": g['net_lots'],
        "買均價": g['b_str'],
        "賣均價": np.where(g['avg_s'] > 0, g['avg_s'].round(2).astype(str), "-"),
        "收盤位階": g['pos']
    }).sort_values('近60日淨買(張)', ascending=False)

    return tags, res_df

def calculate_dynamic_radar_depth(df_b_raw, dates_list, total_lots, df_price):
    if total_lots <= 0 or df_b_raw.empty: return 15, "基本預設 (缺股本資料)"
    if total_lots < 300000: base_n, cap_desc = 10, "微型股本"
    elif total_lots < 1000000: base_n, cap_desc = 15, "中小型股"
    elif total_lots < 5000000: base_n, cap_desc = 30, "中大型股"
    else: base_n, cap_desc = 50, "大型權值"

    recent_dates = dates_list[:5]
    recent_pr = df_price[df_price['日期'].isin(recent_dates)]
    avg_vol = recent_pr['成交量(張)'].mean() if not recent_pr.empty else 0
    turnover_5d = (avg_vol / total_lots) * 100 if total_lots > 0 else 0

    turn_desc = ""
    final_n = base_n
    if turnover_5d > 10.0: 
        final_n = max(5, int(base_n * 0.7))
        turn_desc = " | 高週轉降噪"
    elif turnover_5d < 1.0: 
        final_n = min(50, int(base_n * 1.2))
        turn_desc = " | 低波擴散"

    df_20 = df_b_raw[df_b_raw['date'].isin(dates_list[:20])].copy()
    g = df_20.groupby('securities_trader')[['buy', 'sell']].sum()
    g['net'] = (g['buy'] - g['sell']) / 1000
    buyers = g[g['net'] > 0].sort_values('net', ascending=False)

    if len(buyers) > 5:
        top5_sum = buyers.head(5)['net'].sum()
        topN_sum = buyers.head(final_n)['net'].sum() if len(buyers) >= final_n else buyers['net'].sum()
        if topN_sum > 0 and (top5_sum / topN_sum) > 0.8:
            final_n = max(5, min(final_n, 10))
            turn_desc += " | 極度集中收斂"

    final_n = max(5, min(final_n, 50))
    return final_n, f"{cap_desc}{turn_desc}"

def calculate_pure_defense_line(df_b_raw, tags, is_filter_active, total_lots, dead_chip_ratio, dynamic_n):
    if df_b_raw.empty: return 0.0, 0, 0, 0.0, []
    df = df_b_raw.copy()
    df['tag'] = df['securities_trader'].map(tags).fillna("【路人雜訊】")
    
    if is_filter_active: 
        valid_df = df[~df['tag'].str.contains("【隔日突擊】|【跟風小戶】|【棄守提款】|【避險造市】", na=False)].copy()
    else: 
        valid_df = df

    if valid_df.empty: return 0.0, 0, 0, 0.0, []
    
    valid_df['valid_buy_amt'] = np.where(valid_df['price'] > 0, valid_df['buy'] * valid_df['price'], 0)
    valid_df['valid_buy_vol'] = np.where(valid_df['price'] > 0, valid_df['buy'], 0)
    
    broker_stats = valid_df.groupby('securities_trader').agg(
        buy_vol=('buy', 'sum'),
        sell_vol=('sell', 'sum'),
        buy_amt=('valid_buy_amt', 'sum'),
        valid_buy_vol=('valid_buy_vol', 'sum')
    )
    
    broker_stats['net_vol'] = broker_stats['buy_vol'] - broker_stats['sell_vol']
    top_buyers = broker_stats[broker_stats['net_vol'] > 0].sort_values('net_vol', ascending=False).head(dynamic_n)
    
    if top_buyers.empty: return 0.0, 0, 0, 0.0, []
    
    core_branch_names = top_buyers.index.tolist()
    
    top_buyers['avg_buy_price'] = (top_buyers['buy_amt'] / top_buyers['valid_buy_vol'].replace(0, np.nan)).fillna(0)
    valid_top_buyers = top_buyers[top_buyers['avg_buy_price'] > 0]
    total_net_vol = valid_top_buyers['net_vol'].sum()
    
    vwap = round((valid_top_buyers['avg_buy_price'] * valid_top_buyers['net_vol']).sum() / total_net_vol, 2) if total_net_vol > 0 else 0.0
    
    full_net_accum = int(top_buyers['net_vol'].sum() / 1000)
    active_buyers = len(top_buyers)
    
    c_value = 0.0
    if total_lots > 0:
        safe_dead_ratio = max(0.0, min(99.9, float(dead_chip_ratio)))
        free_float_ratio = (100.0 - safe_dead_ratio) / 100.0
        free_float_lots = total_lots * free_float_ratio
        if free_float_lots > 0:
            raw_c = (full_net_accum / free_float_lots) * 100
            c_value = round(min(98.0, raw_c), 2)

    return vwap, full_net_accum, active_buyers, c_value, core_branch_names

def get_core_period_net(df_raw, rank_dates, core_names):
    if df_raw.empty or not rank_dates or not core_names: return 0
    df_rank = df_raw[df_raw['date'].isin(rank_dates)].copy()
    df_rank = df_rank[df_rank['securities_trader'].isin(core_names)]
    net_shares = df_rank['buy'].sum() - df_rank['sell'].sum()
    return int(round(net_shares / 1000))

# ==========================================
# 【修復核心】：強制將股價轉為數字，防禦 API 文字格式錯誤
# ==========================================
def process_price(df):
    if df.empty: return pd.DataFrame()
    df_out = df.copy()
    
    for col in ["close", "open", "max", "min", "spread"]:
        if col in df_out.columns: 
            df_out[col] = safe_to_num(df_out[col])
            
    if 'Trading_Volume' in df_out.columns: df_out['成交量(張)'] = (safe_to_num(df_out['Trading_Volume']) / 1000).round().astype(int)
    elif 'Trading_volume' in df_out.columns: df_out['成交量(張)'] = (safe_to_num(df_out['Trading_volume']) / 1000).round().astype(int)
    else: df_out['成交量(張)'] = 0
    
    df_out = df_out.rename(columns={"date":"日期","close":"收盤價(元)","spread":"漲跌(元)","open":"開盤價(元)","max":"最高價(元)","min":"最低價(元)"})
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]
    
    df_out["斷頭價(0.78)"] = (df_out["收盤價(元)"] * 0.78).round(2)
    cols_to_keep = ['日期','成交量(張)','開盤價(元)','最高價(元)','最低價(元)','收盤價(元)','漲跌(元)','斷頭價(0.78)']
    return df_out[[c for c in cols_to_keep if c in df_out.columns]].sort_values('日期', ascending=False)

def render_footprint_heatmap(df_raw, display_dates, rank_dates, intel_tags, top_n, noise_threshold):
    if df_raw.empty or not display_dates or not rank_dates:
        st.warning("查無足夠資料產生熱力圖。")
        return

    df_rank = df_raw[df_raw['date'].isin(rank_dates)].copy()
    df_rank['net_shares'] = df_rank['buy'] - df_rank['sell']
    rank_sum = (df_rank.groupby('securities_trader')['net_shares'].sum() / 1000).round().astype(int)

    top_b = rank_sum[rank_sum > 0].nlargest(top_n).index.tolist()
    top_s = rank_sum[rank_sum < 0].nsmallest(top_n).index.tolist()
    target_traders = top_b + top_s
    
    if not target_traders:
        st.warning("無符合條件的活躍分點。")
        return

    df_disp = df_raw[df_raw['date'].isin(display_dates)].copy()
    df_disp['net_shares'] = df_disp['buy'] - df_disp['sell']
    p_shares = df_disp.groupby(['securities_trader', 'date'])['net_shares'].sum().reset_index()
    p_shares['net'] = (p_shares['net_shares'] / 1000).round().astype(int)
    p = p_shares.pivot(index='securities_trader', columns='date', values='net').fillna(0).astype(int)
    p = p.reindex(index=target_traders, columns=display_dates, fill_value=0)

    max_val = p.abs().max().max()
    if max_val == 0: max_val = 1

    html_parts = ["<div class='table-container' style='max-height: 600px;'><table><thead><tr>"]
    html_parts.append("<th style='min-width: 140px; position: sticky; left: 0; z-index: 6;'>分點名稱</th>")
    html_parts.append("<th style='min-width: 100px; position: sticky; left: 140px; z-index: 6;'>標籤</th>")
    for d in display_dates:
        html_parts.append(f"<th style='text-align: center; font-size: 13px; min-width: 50px;'>{d[5:]}</th>")
    html_parts.append("</tr></thead><tbody>")

    for trader in target_traders:
        html_parts.append("<tr>")
        tag = intel_tags.get(trader, "【路人雜訊】")
        html_parts.append(f"<td style='position: sticky; left: 0; background-color: #f8f9fa; z-index: 4; font-weight: bold;'>{trader}</td>")
        html_parts.append(f"<td style='position: sticky; left: 140px; background-color: #f8f9fa; z-index: 4;'>{tag}</td>")

        for d in display_dates:
            val = p.at[trader, d]
            if abs(val) < noise_threshold:
                bg = "transparent"
                txt = ""
            else:
                alpha = min(1.0, 0.2 + 0.8 * (abs(val) / max_val))
                if val > 0:
                    bg = f"rgba(229, 57, 53, {alpha:.2f})" 
                else:
                    bg = f"rgba(67, 160, 71, {alpha:.2f})" 
                txt = f"+{val}" if val > 0 else str(val)

            cell_style = f"background-color: {bg}; text-align: center; font-weight: bold; color: #fff !important; text-shadow: 1px 1px 2px rgba(0,0,0,0.6);" if txt else "text-align: center;"
            tooltip = f"日期: {d} | 分點: {trader} | 淨額: {val} 張"
            html_parts.append(f"<td style='{cell_style}' title='{tooltip}'>{txt}</td>")

        html_parts.append("</tr>")
    
    html_parts.append("<tr style='height: 30px;'><td style='position: sticky; left: 0; background-color: #f8f9fa; border-bottom: none;'>&nbsp;</td><td style='position: sticky; left: 140px; background-color: #f8f9fa; border-bottom: none;'>&nbsp;</td>")
    for _ in display_dates: html_parts.append("<td style='border-bottom: none;'></td>")
    html_parts.append("</tr>")
    html_parts.append("</tbody></table></div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def render_volume_profile(df_raw, rank_dates, top_n=15):
    if df_raw.empty or not rank_dates:
        st.warning("查無足夠資料產生建倉成本分佈圖。")
        return

    df_rank = df_raw[df_raw['date'].isin(rank_dates)].copy()
    df_rank['net_shares'] = df_rank['buy'] - df_rank['sell']
    rank_sum = (df_rank.groupby('securities_trader')['net_shares'].sum() / 1000).round().astype(int)
    
    top_b = rank_sum[rank_sum > 0].nlargest(top_n).index.tolist()
    top_s = rank_sum[rank_sum < 0].nsmallest(top_n).index.tolist()
    target_traders = top_b + top_s
    
    if not target_traders:
        st.warning("無符合條件的活躍分點。")
        return

    df_vp = df_rank[(df_rank['securities_trader'].isin(target_traders)) & (df_rank['price'] > 0)].copy()
    if df_vp.empty:
        st.warning("無有效價格資料進行成本區間分析。")
        return

    df_vp['buy_lots'] = df_vp['buy'] / 1000
    df_vp['sell_lots'] = df_vp['sell'] / 1000

    min_p = df_vp['price'].min()
    max_p = df_vp['price'].max()
    
    if min_p == max_p:
        labels = [f"{min_p:.2f}"]
        df_vp['price_bin'] = labels[0]
    else:
        bin_edges = np.linspace(min_p, max_p, num=16)
        labels = [f"{bin_edges[i]:.2f} - {bin_edges[i+1]:.2f}" for i in range(len(bin_edges)-1)]
        df_vp['price_bin'] = pd.cut(df_vp['price'], bins=bin_edges, labels=labels, include_lowest=True)

    vp_grouped = df_vp.groupby('price_bin', observed=False)[['buy_lots', 'sell_lots']].sum().fillna(0)
    vp_grouped['total_lots'] = vp_grouped['buy_lots'] + vp_grouped['sell_lots']
    vp_grouped['net_lots'] = vp_grouped['buy_lots'] - vp_grouped['sell_lots']
    
    if vp_grouped['total_lots'].sum() == 0:
        st.warning("該區間大戶無顯著成交量。")
        return

    poc_idx = vp_grouped['total_lots'].idxmax()
    max_vol_for_scale = vp_grouped[['buy_lots', 'sell_lots']].max().max()
    if max_vol_for_scale == 0: max_vol_for_scale = 1

    html_parts = ["<div class='table-container' style='max-height: 500px;'><table><thead><tr>"]
    html_parts.append("<th style='width: 20%;'>價位區間 (元)</th>")
    html_parts.append("<th style='width: 35%; text-align: left;'>買進量 (大戶建倉)</th>")
    html_parts.append("<th style='width: 35%; text-align: left;'>賣出量 (大戶倒貨)</th>")
    html_parts.append("<th style='width: 10%; text-align: right;'>淨買賣(張)</th>")
    html_parts.append("</tr></thead><tbody>")

    vp_grouped = vp_grouped.sort_index(ascending=False)

    for idx, row in vp_grouped.iterrows():
        b_vol = int(round(row['buy_lots']))
        s_vol = int(round(row['sell_lots']))
        n_vol = int(round(row['net_lots']))
        t_vol = row['total_lots']
        
        if t_vol == 0: continue

        b_width = min(100, (b_vol / max_vol_for_scale) * 100) if max_vol_for_scale > 0 else 0
        s_width = min(100, (s_vol / max_vol_for_scale) * 100) if max_vol_for_scale > 0 else 0

        is_poc = (idx == poc_idx)
        row_bg = "background-color: rgba(255, 193, 7, 0.15);" if is_poc else ""
        poc_star = " <br><span style='color:#f57c00; font-size:12px; font-weight:900;'>⭐ [POC 核心防守]</span>" if is_poc else ""

        html_parts.append(f"<tr style='{row_bg}'>")
        html_parts.append(f"<td style='font-weight: bold; font-size:14px;'>{idx}{poc_star}</td>")
        html_parts.append(f"<td><div style='display: flex; align-items: center;'><div style='width: {b_width}%; background-color: #e53935; height: 18px; border-radius: 2px; margin-right: 8px;'></div><span style='font-size: 13px; font-weight:bold;'>{b_vol:,}</span></div></td>")
        html_parts.append(f"<td><div style='display: flex; align-items: center;'><div style='width: {s_width}%; background-color: #43a047; height: 18px; border-radius: 2px; margin-right: 8px;'></div><span style='font-size: 13px; font-weight:bold;'>{s_vol:,}</span></div></td>")
        
        net_color = "#d32f2f" if n_vol > 0 else ("#2e7d32" if n_vol < 0 else "inherit")
        net_txt = f"+{n_vol:,}" if n_vol > 0 else f"{n_vol:,}"
        html_parts.append(f"<td style='color: {net_color}; font-weight: bold; text-align: right;'>{net_txt}</td>")
        html_parts.append("</tr>")
        
    html_parts.append("</tbody></table></div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)

def render_institutional_vs_local(df_branch_raw, df_inst, intel_tags, top_n=4):
    if df_branch_raw.empty or df_inst.empty:
        st.warning("查無法人或分點資料可供比對。")
        return
        
    dates_in_inst = df_inst['日期'].tolist()
    if not dates_in_inst: return
    
    df_recent = df_branch_raw[df_branch_raw['date'].isin(dates_in_inst)].copy()
    df_recent['net_shares'] = df_recent['buy'] - df_recent['sell']
    rank_sum = (df_recent.groupby('securities_trader')['net_shares'].sum() / 1000).round().astype(int)
    
    top_branches = rank_sum.abs().nlargest(top_n).index.tolist()
    if not top_branches: return
    
    p = df_recent.groupby(['date', 'securities_trader'])['net_shares'].sum().reset_index()
    p['net'] = (p['net_shares'] / 1000).round().astype(int)
    p_pivot = p.pivot(index='date', columns='securities_trader', values='net').fillna(0).astype(int)
    
    html_parts = ["<div class='table-container' style='max-height: 500px;'><table><thead><tr>"]
    html_parts.append("<th style='position: sticky; left: 0; z-index: 6;'>日期</th>")
    html_parts.append("<th style='text-align: right; background-color: #f1f3f5;'>外資(張)</th>")
    html_parts.append("<th style='text-align: right; background-color: #f1f3f5;'>投信(張)</th>")
    
    for tb in top_branches:
        tag_short = intel_tags.get(tb, "路人").replace("【", "").replace("】", "")[:4]
        html_parts.append(f"<th style='text-align: right;'>{tb}<br><span style='font-size:11px; color:#1e3a8a;'>{tag_short}</span></th>")
    
    html_parts.append("<th style='text-align: center; background-color: #e3f2fd;'>聯合作戰診斷</th></tr></thead><tbody>")
    
    for _, row in df_inst.iterrows():
        d = row['日期']
        f_net = row.get('外資買賣超(張)', 0)
        i_net = row.get('投信買賣超(張)', 0)
        
        html_parts.append("<tr>")
        html_parts.append(f"<td style='position: sticky; left: 0; background-color: #f8f9fa; z-index: 4; font-weight:bold; text-align:center;'>{d[5:]}</td>")
        
        def format_net(val):
            if val > 0: return f"<span style='color:#d32f2f; font-weight:bold;'>+{val:,}</span>"
            elif val < 0: return f"<span style='color:#2e7d32; font-weight:bold;'>{val:,}</span>"
            return "<span style='color:#bbb;'>0</span>"
            
        html_parts.append(f"<td style='text-align:right; background-color: #fdfdfd;'>{format_net(f_net)}</td>")
        html_parts.append(f"<td style='text-align:right; background-color: #fdfdfd;'>{format_net(i_net)}</td>")
        
        local_net_sum = 0
        for tb in top_branches:
            val = p_pivot.at[d, tb] if d in p_pivot.index and tb in p_pivot.columns else 0
            local_net_sum += val
            html_parts.append(f"<td style='text-align:right;'>{format_net(val)}</td>")
            
        inst_sum = f_net + i_net
        if inst_sum > 0 and local_net_sum > 0:
            diag = "💎 土洋共擊"
            bg = "rgba(229, 57, 53, 0.15)"
            color = "#c62828"
        elif inst_sum < 0 and local_net_sum < 0:
            diag = "🩸 多殺多撤退"
            bg = "rgba(67, 160, 71, 0.15)"
            color = "#2e7d32"
        elif inst_sum > 0 and local_net_sum < 0:
            diag = "🤝 法人接盤"
            bg = "transparent"
            color = "#555"
        elif inst_sum < 0 and local_net_sum > 0:
            diag = "⚔️ 地方硬扛"
            bg = "transparent"
            color = "#555"
        else:
            diag = "休兵盤整"
            bg = "transparent"
            color = "#aaa"
            
        html_parts.append(f"<td style='text-align:center; background-color:{bg}; color:{color}; font-weight:bold; font-size:13px;'>{diag}</td>")
        html_parts.append("</tr>")
        
    html_parts.append("</tbody></table></div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def process_footprint(df_raw, display_dates, rank_dates, intel_tags, df_fingerprint, top_n):
    if df_raw.empty or not display_dates or not rank_dates: return pd.DataFrame(), pd.DataFrame()
    
    df_rank = df_raw[df_raw['date'].isin(rank_dates)].copy()
    df_rank['net_shares'] = df_rank['buy'] - df_rank['sell']
    rank_sum_shares = df_rank.groupby('securities_trader')['net_shares'].sum()
    rank_sum = (rank_sum_shares / 1000).round().astype(int)
    
    top_b_names = rank_sum[rank_sum > 0].nlargest(top_n).index.tolist()
    top_s_names = rank_sum[rank_sum < 0].nsmallest(top_n).index.tolist()
    
    df_disp = df_raw[df_raw['date'].isin(display_dates)].copy()
    if df_disp.empty: return pd.DataFrame(), pd.DataFrame()
    
    df_disp['net_shares'] = df_disp['buy'] - df_disp['sell']
    p_shares = df_disp.groupby(['securities_trader', 'date'])['net_shares'].sum().reset_index()
    p_shares['net'] = (p_shares['net_shares'] / 1000).round().astype(int)
    p = p_shares.pivot(index='securities_trader', columns='date', values='net').fillna(0).astype(int)
    p = p.reindex(columns=display_dates, fill_value=0)
    
    fp_dict = {}
    if not df_fingerprint.empty:
        fp_dict = df_fingerprint.set_index('分點名稱')[['黏著度(%)', '囤出貨率(%)']].to_dict('index')
    
    def build_df(trader_list, is_sell_side=False):
        out = []
        for trader in trader_list:
            st_val = fp_dict.get(trader, {}).get('黏著度(%)', "-")
            hr_name = "出貨率(%)" if is_sell_side else "囤貨率(%)"
            hr_val = fp_dict.get(trader, {}).get('囤出貨率(%)', "-")
            total_val = rank_sum.get(trader, 0)
            
            row_dict = {
                "分點名稱": trader, 
                "標籤": intel_tags.get(trader, "【路人雜訊】"),
                "黏著度(%)": st_val, 
                hr_name: hr_val,
                f"區間累計(張)": f"+{total_val}" if total_val > 0 else str(total_val)
            }
            
            for i, d in enumerate(display_dates):
                v = p.at[trader, d] if trader in p.index and d in p.columns else 0
                row_dict[f"T-{i}" if i > 0 else "今日(T)"] = f"+{v}" if v > 0 else str(v)
            out.append(row_dict)
        return pd.DataFrame(out)

    return build_df(top_b_names, False), build_df(top_s_names, True)

def process_branch_v25(df_raw, period, actual_dates, intel_tags, df_price_raw, stick_thresh, global_days):
    if df_raw.empty or df_price_raw.empty: return pd.DataFrame()
    latest_close = df_price_raw.sort_values('date', ascending=False)['close'].iloc[0]
    df = df_raw[df_raw['date'].isin(actual_dates[:period])].copy()
    if df.empty: return pd.DataFrame()
    
    df['valid_buy'] = np.where(df['price'] > 0, df['buy'], 0)
    df['valid_sell'] = np.where(df['price'] > 0, df['sell'], 0)
    df['ba'] = df['valid_buy'] * df['price']
    df['sa'] = df['valid_sell'] * df['price']
    
    g = df.groupby('securities_trader').agg(
        bv=('buy', 'sum'), sv=('sell', 'sum'), 
        vbv=('valid_buy', 'sum'), vsv=('valid_sell', 'sum'),
        ba=('ba', 'sum'), sa=('sa', 'sum')
    ).reset_index()
    
    g['net'] = round((g['bv'] - g['sv']) / 1000).astype(int)
    g['avg_b'] = (g['ba'] / g['vbv'].replace(0, np.nan)).fillna(0)
    g['avg_s'] = (g['sa'] / g['vsv'].replace(0, np.nan)).fillna(0)
    
    b = g[g['net'] > 0].sort_values('net', ascending=False).head(15).reset_index(drop=True)
    s = g[g['net'] < 0].sort_values('net', ascending=True).head(15).reset_index(drop=True)
    out, tv = [], round(g['bv'].sum() / 1000) if g['bv'].sum() > 0 else 1
    
    for i in range(15):
        r = {}
        if i < len(b): 
            b_str = f"{round(b.loc[i,'avg_b'], 2):,.2f}" if b.loc[i,'avg_b'] > 0 else "-"
            if b.loc[i,'avg_b'] > latest_close and b.loc[i,'avg_b'] > 0 and b.loc[i,'net'] > 0: b_str = f"(虧) {b_str}"
            raw_tag = intel_tags.get(b.loc[i,'securities_trader'], '【路人雜訊】')
            attr = "短線" if any(x in raw_tag for x in ["【隔日突擊】", "【跟風小戶】"]) else "中長線" if any(x in raw_tag for x in ["【波段鎖碼】", "【避險造市】", "【主力重砲】"]) else "波段"
            r["買超分點"] = b.loc[i,'securities_trader']
            r["買_標籤"] = raw_tag
            r["買_週期"] = attr
            r["買超(張)"] = int(b.loc[i,'net'])
            r["買均價"] = b_str
            r["佔比"] = f"{(b.loc[i,'net']/tv)*100:.1f}%" if tv > 0 else "-"
        else: r["買超分點"], r["買_標籤"], r["買_週期"], r["買超(張)"], r["買均價"], r["佔比"] = "-", "-", "-", 0, "-", "-"
        
        if i < len(s): 
            raw_tag_s = intel_tags.get(s.loc[i,'securities_trader'], '【路人雜訊】')
            attr_s = "短線" if any(x in raw_tag_s for x in ["【隔日突擊】", "【跟風小戶】"]) else "中長線" if any(x in raw_tag_s for x in ["【波段鎖碼】", "【避險造市】", "【主力重砲】"]) else "波段"
            r["賣超分點"] = s.loc[i,'securities_trader']
            r["賣_標籤"] = raw_tag_s
            r["賣_週期"] = attr_s
            r["賣超(張)"] = abs(int(s.loc[i,'net']))
            r["賣均價"] = f"{round(s.loc[i,'avg_s'], 2):,.2f}" if s.loc[i,'avg_s'] > 0 else "-"
            r["佔比_"] = f"{(abs(s.loc[i,'net'])/tv)*100:.1f}%" if tv > 0 else "-"
        else: r["賣超分點"], r["賣_標籤"], r["賣_週期"], r["賣超(張)"], r["賣均價"], r["佔比_"] = "-", "-", "-", 0, "-", "-"
        out.append(r)
    return pd.DataFrame(out)

def get_smart_threshold(price, total_lots, dead_float):
    if pd.isna(price) or price <= 0: return 1000 
    
    base_lots = 15000 / price
    safe_dead_ratio = max(0.0, min(99.9, dead_float))
    free_float_ratio = max(0.05, (100 - safe_dead_ratio) / 100) 
    float_1pct_lots = total_lots * free_float_ratio * 0.01
    
    raw_threshold = min(base_lots, float_1pct_lots)
    raw_threshold = max(100, min(1000, raw_threshold))
    
    levels = [100, 200, 400, 600, 800, 1000]
    al = min(levels, key=lambda x: abs(x - raw_threshold))
    return al

def process_v27_ultimate_radar(df_wide, dead_chip_input, dynamic_dict, static_val, df_price, df_branch_raw, intel_tags):
    if df_wide.empty or len(df_wide) < 2: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df = df_wide.sort_values('日期', ascending=True).copy()
    df['dt_end'] = pd.to_datetime(df['日期'])
    
    if not df_price.empty:
        df_p = df_price.copy()
        df_p['dt'] = pd.to_datetime(df_p['日期'])
        df_p = df_p.drop_duplicates(subset=['dt']).sort_values('dt')
        df_p['ma20'] = df_p['收盤價(元)'].rolling(20, min_periods=1).mean()
        df = pd.merge_asof(df.sort_values('dt_end'), df_p[['dt', '收盤價(元)', 'ma20']], left_on='dt_end', right_on='dt', direction='backward')
    else: df['收盤價(元)'], df['ma20'] = 0, 0
        
    df['總人數變率(%)'] = (df['總人數(人)'].pct_change() * 100).round(2)
    
    levels_cols = ['100-200張_比例(%)', '200-400張_比例(%)', '400-600張_比例(%)', '600-800張_比例(%)', '800-1000張_比例(%)', '1000張以上_比例(%)']
    for col in levels_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0) if col in df.columns else 0.0
        
    df['pct_1000'] = df['1000張以上_比例(%)']
    df['pct_800'] = df['pct_1000'] + df['800-1000張_比例(%)']
    df['pct_600'] = df['pct_800'] + df['600-800張_比例(%)']
    df['pct_400'] = df['pct_600'] + df['400-600張_比例(%)']
    df['pct_200'] = df['pct_400'] + df['200-400張_比例(%)']
    df['pct_100'] = df['pct_200'] + df['100-200張_比例(%)']

    def get_pct(row_dict, threshold):
        if threshold <= 100: return row_dict.get('pct_100', 0)
        if threshold <= 200: return row_dict.get('pct_200', 0)
        if threshold <= 400: return row_dict.get('pct_400', 0)
        if threshold <= 600: return row_dict.get('pct_600', 0)
        if threshold <= 800: return row_dict.get('pct_800', 0)
        return row_dict.get('pct_1000', 0)
    
    fake_dict = {}
    if not df_branch_raw.empty:
        df_b_tagged = df_branch_raw[['date', 'securities_trader', 'buy', 'sell']].copy()
        df_b_tagged['tag'] = df_b_tagged['securities_trader'].map(intel_tags).fillna("")
        mask_short = df_b_tagged['tag'].str.contains("【隔日突擊】|【跟風小戶】", na=False)
        df_fake = df_b_tagged[mask_short]
        if not df_fake.empty:
            df_fake_daily = df_fake.groupby(['date', 'securities_trader'])[['buy', 'sell']].sum().reset_index()
            df_fake_daily['net_buy_exact'] = (df_fake_daily['buy'] - df_fake_daily['sell']) / 1000
            fake_dict = df_fake_daily.groupby('date').apply(lambda x: x[['securities_trader', 'net_buy_exact']].to_dict('records')).to_dict()

    arr_dates_str = np.sort(df_branch_raw['date'].unique()) if not df_branch_raw.empty else np.array([])
    arr_dates_dt = pd.to_datetime(arr_dates_str) if len(arr_dates_str) > 0 else []

    out, d_math, d_fri = [], [], []
    prev_row = None
    
    for row in df.to_dict('records'):
        d_str = row['日期']
        d_dt = row['dt_end']
        p = row.get('收盤價(元)', 0)
        total_lots = row.get('總張數', 0)
        
        if pd.isna(p) or p <= 0 or total_lots <= 0: 
            out.append({"日期": d_str, "大戶原持股(%)": 0, "原始大戶變動(%)": 0, "純淨變動": 0, "雜訊": 0, "診斷": "初始化/數據不全"})
            prev_row = row
            continue
            
        cur_dead, _ = get_dead_chip_info(d_str, dead_chip_input, dynamic_dict, static_val, "")
        safe_dead_ratio = max(0.0, min(99.9, cur_dead))
        ct = get_smart_threshold(p, total_lots, safe_dead_ratio)
        current_large_pct = get_pct(row, ct)
        
        if prev_row is None:
            raw_chg, p_chg, f_impact = 0.0, 0.0, 0.0
            adv = ["初始化 (基準建立)"]
        else:
            prev_large_pct_adj = get_pct(prev_row, ct)
            raw_chg = round(current_large_pct - prev_large_pct_adj, 2)
            f_vol_exact, f_impact = 0, 0.0
            
            if len(arr_dates_str) > 0:
                idx = np.searchsorted(arr_dates_str, d_str, side='right') - 1
                if idx >= 0:
                    last_trading_date = arr_dates_str[idx]
                    days_diff = (d_dt - arr_dates_dt[idx]).days
                    
                    if days_diff <= 7 and last_trading_date in fake_dict:
                        fake_traders = fake_dict[last_trading_date]
                        for fr in fake_traders:
                            if fr['net_buy_exact'] >= ct:
                                f_vol_exact += fr['net_buy_exact']
                                d_fri.append({"日期": d_str, "分點": fr['securities_trader'], "張數": round(fr['net_buy_exact'])})
                        f_impact = (f_vol_exact / max(1, total_lots)) * 100 
                    
            p_chg = round(raw_chg - f_impact, 2)
            d_math.append({"日期": d_str, "原始變動": raw_chg, "當沖干擾": round(f_impact, 2), "純淨變動": p_chg})
            
            lev = 100 / (100 - safe_dead_ratio) if 0 <= safe_dead_ratio < 100 else 1
            adv = []
            if row.get('總人數變率(%)', 0) > 2.0 and p_chg < 0: adv.append(f"[逃命波] 散戶增{row.get('總人數變率(%)', 0)}%，大戶實質倒貨{abs(p_chg)}%")
            else:
                if p_chg * lev > 2.5 and row.get('收盤價(元)', 0) > row.get('ma20', 0): adv.append(f"[強勢軋空] 站上月線且大戶純淨買超{round(p_chg*lev, 2)}%")
                elif p_chg > 0.4 and row.get('收盤價(元)', 0) < row.get('ma20', 0): adv.append(f"[底位建倉] 跌破月線但主力吃貨{p_chg}%")
                elif p_chg < -1.0: adv.append(f"[主力撤退] 大戶實質流出{abs(p_chg)}%")
                if f_impact > 1.2: adv.append(f"[短線干擾] 虛胖買盤潛藏{round(f_impact, 2)}%倒貨危機")
                
        prev_row = row
        out.append({"日期": d_str, "大戶原持股(%)": round(current_large_pct, 2), "原始大戶變動(%)": raw_chg, "純淨變動": p_chg, "雜訊": round(f_impact, 2), "診斷": " | ".join(adv) if adv else "盤整"})
        
    ddf = pd.DataFrame(out)
    df = pd.merge(df, ddf, on='日期', how='left')
    df['專家雷達診斷'] = df['診斷']
    df['純淨大戶變動(%)'] = df['純淨變動']
    df['當沖虛胖(%)'] = df['雜訊']
    res_df = df[['日期', '收盤價(元)', '大戶原持股(%)', '總人數變率(%)', '原始大戶變動(%)', '當沖虛胖(%)', '純淨大戶變動(%)', '專家雷達診斷']].sort_values('日期', ascending=False)
    res_df = res_df[~res_df['專家雷達診斷'].str.contains('初始化', na=False)]
    return res_df, pd.DataFrame(d_math), pd.DataFrame(d_fri)

def process_branch_diff(df_raw, actual_dates, fire_thresh, period_days=10):
    if df_raw.empty or not actual_dates: return pd.DataFrame()
    out = []
    branch_grouped = dict(tuple(df_raw[['date', 'securities_trader', 'buy', 'sell']].groupby('date')))
    for d in actual_dates[:period_days]:
        if d not in branch_grouped: continue
        df_d = branch_grouped[d]
        buy_branches, sell_branches = df_d[df_d['buy'] > 0], df_d[df_d['sell'] > 0]
        
        buy_count = buy_branches['securities_trader'].nunique()
        sell_count = sell_branches['securities_trader'].nunique()
        diff_count = buy_count - sell_count
        
        active_count = df_d[(df_d['buy'] > 0) | (df_d['sell'] > 0)]['securities_trader'].nunique()
        concentration = ((sell_count - buy_count) / active_count * 100) if active_count > 0 else 0
        
        total_buy_vol, total_sell_vol = buy_branches['buy'].sum(), sell_branches['sell'].sum()
        avg_b = total_buy_vol / buy_count if buy_count > 0 else 0
        avg_s = total_sell_vol / sell_count if sell_count > 0 else 0
        firepower = (avg_b / avg_s) if avg_s > 0 else (99.9 if avg_b > 0 else 1.0)
        
        diag = []
        if firepower >= fire_thresh and concentration > 5: diag.append(f"大戶火力壓制 ({fire_thresh}倍↑)")
        elif firepower < 0.7 and diff_count > 50: diag.append("散戶進場 (主力倒貨)")
        elif active_count > 500 and firepower < 1.0: diag.append("籌碼極度發散 (熱門當沖雷區)")
        
        out.append({"日期": d, "活躍家數": active_count, "買賣家數差": diff_count, "籌碼集中度(%)": round(concentration, 1), "買方火力(倍)": round(firepower, 2), "鷹眼診斷": " | ".join(diag) if diag else "中性換手"})
    return pd.DataFrame(out)

def process_v30_daily_tracking(df_branch_raw, intel_tags, df_price, df_branch_diff, actual_dates, fire_thresh, period_days=5):
    if df_branch_raw.empty or len(actual_dates) < period_days: return pd.DataFrame(), pd.DataFrame()
    out, audit_smart_money = [], []
    df_b = df_branch_raw[['date', 'securities_trader', 'buy', 'sell', 'price']].rename(columns={'buy': 'bs', 'sell': 'ss', 'price': 'pr'})
    df_b['tag'] = df_b['securities_trader'].map(intel_tags).fillna("【路人雜訊】")
    
    smart_set = {"【波段鎖碼】", "【避險造市】", "【獲利調節】", "【棄守提款】", "【主力重砲】", "【認錯回補】"}
    short_set = {"【隔日突擊】", "【跟風小戶】"}
    df_b['is_smart'] = df_b['tag'].isin(smart_set)
    df_b['is_short'] = df_b['tag'].isin(short_set)
    
    df_b['valid_bs'] = np.where(df_b['pr'] > 0, df_b['bs'], 0)
    df_b['valid_ss'] = np.where(df_b['pr'] > 0, df_b['ss'], 0)
    df_b['buy_amt'] = df_b['valid_bs'] * df_b['pr']
    df_b['sell_amt'] = df_b['valid_ss'] * df_b['pr']

    df_smart_all = df_b[df_b['is_smart']].groupby(['date', 'securities_trader', 'tag']).agg(
        bs=('bs','sum'), ss=('ss','sum'), buy_amt=('buy_amt','sum'), sell_amt=('sell_amt','sum')
    ).reset_index()
    
    df_smart_all['net_vol'] = ((df_smart_all['bs'] - df_smart_all['ss']) / 1000).round().astype(int)
    smart_dict = dict(tuple(df_smart_all.groupby('date'))) if not df_smart_all.empty else {}

    df_short_all = df_b[df_b['is_short']].groupby(['date', 'securities_trader']).agg(bs=('bs','sum'), ss=('ss','sum')).reset_index()
    df_short_all['net_vol'] = ((df_short_all['bs'] - df_short_all['ss']) / 1000).round().astype(int)
    short_dict = dict(tuple(df_short_all.groupby('date'))) if not df_short_all.empty else {}

    price_dict = df_price.set_index('日期').to_dict('index') if not df_price.empty else {}
    diff_dict = df_branch_diff.set_index('日期').to_dict('index') if not df_branch_diff.empty else {}
    
    for d in actual_dates[:period_days]:
        pr_row = price_dict.get(d, {})
        cp = pr_row.get('收盤價(元)', 0)
        op = pr_row.get('開盤價(元)', 0)
        hp = pr_row.get('最高價(元)', 0)
        lp = pr_row.get('最低價(元)', 0)
        sp_raw = pr_row.get('漲跌(元)', 0)
        
        try: sp_num = float(str(sp_raw).replace('+', '').replace(',', '').strip())
        except: sp_num = 0.0
        
        diff_row = diff_dict.get(d, {})
        bsd = diff_row.get('買賣家數差', 0)
        firepower = diff_row.get('買方火力(倍)', 1.0)
        active_cnt = diff_row.get('活躍家數', 0)
        concentration = diff_row.get('籌碼集中度(%)', 0)
        eye_diag = diff_row.get('鷹眼診斷', "")

        smart_grouped = smart_dict.get(d, pd.DataFrame(columns=['securities_trader', 'tag', 'bs', 'ss', 'buy_amt', 'sell_amt', 'net_vol']))
        short_grouped = short_dict.get(d, pd.DataFrame(columns=['securities_trader', 'bs', 'ss', 'net_vol']))
        
        if d == actual_dates[0]:
            for r in smart_grouped.to_dict('records'):
                if r['net_vol'] != 0: audit_smart_money.append({"日期": d, "分點": r['securities_trader'], "標籤": r['tag'], "淨買超(張)": r['net_vol']})
        
        smart_net = smart_grouped['net_vol'].sum() if not smart_grouped.empty else 0
        short_trap = short_grouped[short_grouped['net_vol'] > 0]['net_vol'].sum() if not short_grouped.empty else 0
        
        total_n = 0
        if not smart_grouped.empty:
            s_ret = smart_grouped.copy()
            s_ret['net_shares'] = s_ret['bs'] - s_ret['ss']
            s_ret['net_amt'] = s_ret['buy_amt'] - s_ret['sell_amt']
            s_ret_long = s_ret[s_ret['net_shares'] > 0]
            total_n = s_ret_long['net_shares'].sum()
            total_net_amt = s_ret_long['net_amt'].sum()
            smart_avg_cost = max(0.0, total_net_amt / total_n) if total_n > 0 else 0.0
        else: 
            smart_avg_cost = 0.0
            
        gap = cp - smart_avg_cost if smart_avg_cost > 0 and cp > 0 else 0
        
        adv = []
        if cp <= 0: adv.append("股價無紀錄或暫停交易")
        else:
            day_range = hp - lp
            lower_shadow = min(cp, op) - lp
            if day_range > 0 and (lower_shadow / day_range) > 0.5 and smart_net > 0: adv.append("探底洗盤成功，主力護盤")
            
            if smart_avg_cost == 0 and smart_net < 0: adv.append("【危險】主力零成本無本出貨中")
            elif smart_net > 300 and firepower > 1.5: adv.append("【重擊點火】大戶重力掃貨推升")
            elif smart_net > 50 and gap > 0: adv.append("主動鎖碼/強勢推升")
            elif smart_net > 50 and gap < 0: adv.append("大戶承接/弱勢護盤")
            elif smart_net < -100 and sp_num > 0: adv.append("拉高派發/撤退")
            elif smart_net < -100 and sp_num <= 0: adv.append("波段棄守/多殺多")
            
        if eye_diag and eye_diag != "中性換手": adv.append(eye_diag)
        elif not adv: adv.append("盤整/無明顯特徵")

        out.append({
            "日期": d, "收盤價(元)": cp if cp > 0 else "-", "漲跌(元)": sp_raw if cp > 0 else "-", "聰明錢淨流(張)": int(smart_net), 
            "大戶淨加權均價": round(smart_avg_cost, 2) if smart_avg_cost > 0 else ("0 (無本獲利)" if smart_avg_cost == 0 and total_n > 0 else "-"), 
            "均價落差": round(gap, 2) if smart_avg_cost > 0 and cp > 0 else "-", 
            "活躍家數": active_cnt, "買賣家數差": bsd, "籌碼集中度(%)": concentration,
            "買方火力(倍)": firepower, "潛在賣壓(張)": int(short_trap), "綜合診斷": " | ".join(adv)
        })
    return pd.DataFrame(out), pd.DataFrame(audit_smart_money).sort_values('淨買超(張)', ascending=False) if audit_smart_money else pd.DataFrame()

# ==========================================
# 啟動運算引擎後，強制釋放記憶體
# ==========================================
        
        # ... (前述所有系統報表輸出代碼維持原狀) ...
        
        st.divider()
        st.info("請將下方所需資料複製後貼給 AI 進行深度分析或稽核。")
        with st.expander(f"給 AI 的 V70.16 實戰精華資料包 (CSV格式)", expanded=True):
            p1 = f"請依下面最新的盤後資料與系統兵推報告幫我深度分析 {user_stock_id} {name} 的量化籌碼，必須以我給的資料優先使用。\n\n"
            p1 += f"{company_info_text}\n\n"
            
            clean_ai_report = re.sub(r'<[^>]+>', '', report_md)
            clean_ai_report = clean_ai_report.replace('&nbsp;', ' ').strip()
            
            p1 += f"▼▼▼ 系統 AI 全息籌碼深度診斷總結 ▼▼▼\n"
            p1 += f"{clean_ai_report}\n\n"
            
            if latest_lr_upper > 0:
                p1 += f"【線性迴歸通道上軌 (壓力)】: {latest_lr_upper:.2f} 元\n"
                p1 += f"【線性迴歸通道中軌 (趨勢)】: {latest_lr_mid:.2f} 元\n"
                p1 += f"【線性迴歸通道下軌 (支撐)】: {latest_lr_lower:.2f} 元\n\n"
            
            p1 += f"【系統算出之純淨主力加權防守價 (Net VWAP)】: {vwap_str} 元\n"
            p1 += f"【核心分點控盤率 (相對於自由流通籌碼)】: {core_c_value}%\n\n"
            p1 += f"【核心主力3日淨留倉】: {net_3} 張\n"
            p1 += f"【核心主力10日淨留倉】: {net_10} 張\n"
            p1 += f"【核心主力45日淨留倉】: {net_45} 張\n"
            p1 += f"【核心主力60日淨留倉】: {net_60} 張\n\n"
            
            p1 += format_to_csv_string(df_daily_tracker, "02. 平日戰情追蹤矩陣 (近15日)")
            p1 += format_to_csv_string(df_combined_display.head(4) if not df_combined_display.empty else df_combined_display, "03. 一週集保籌碼雷達 (近4週)")
            p1 += format_to_csv_string(df_inst.head(10) if not df_inst.empty else df_inst, "04. 法人買賣超 (近10天)")
            p1 += format_to_csv_string(df_margin.head(10) if not df_margin.empty else df_margin, "05. 散戶資券餘額 (近10天)")
            p1 += format_to_csv_string(df_day_trade.head(10) if not df_day_trade.empty else df_day_trade, "06. 現股當沖明細 (近10天)")
            p1 += format_to_csv_string(df_fut.head(10) if not df_fut.empty else df_fut, "07. 台指期貨三大法人未平倉 (大盤)")
            p1 += format_to_csv_string(df_rev.head(12) if not df_rev.empty else df_rev, "08. 月營收 (百萬元) (近12個月)")
            p1 += format_to_csv_string(df_p_sum, "10. 董監大股東質設總覽")
            p1 += format_to_csv_string(df_per.head(10) if not df_per.empty else df_per, "13. 本益比、淨值比與殖利率")
            p1 += format_to_csv_string(df_disp, "14. 處置有價證券狀態")
            p1 += format_to_csv_string(df_cbas, "15. CBAS 可轉債數據")
            st.code(p1, language="text")

        st.divider()
        st.markdown("<div class='category-title'>系統底層數據 Raw Data Dump 驗證區 (CSV 格式 / 60天)</div>", unsafe_allow_html=True)
        with st.expander("點此展開系統原始擷取數據 (供驗證 00, 01 等模組計算邏輯)", expanded=False):
            st.info("這裡傾印了供你人工或稽核技術面與主力戰情所需的近 60 天核心基礎資料。")
            dump_text = "請協助驗證以下底層 Raw Data 邏輯是否正確：\n\n"
            
            df_price_dump = df_price.head(60).copy() if not df_price.empty else pd.DataFrame()
            dump_text += format_to_csv_string(df_price_dump, "Raw 00: 股價與成交量原始數據 (近 60 天)")
            dump_text += format_to_csv_string(df_b_diff_60, "Raw 01-A: 活躍券商與買賣家數差數據 (近 60 天)")
            dump_text += format_to_csv_string(df_daily_tracker_60, "Raw 01-B: 主力戰場追蹤矩陣 (近 60 天)")
            
            df_tdcc_dump = df_s_wide.head(10).copy() if not df_s_wide.empty else pd.DataFrame()
            dump_text += format_to_csv_string(df_tdcc_dump, "Raw 02: 集保股權分散表原始數據 (近 10 週)")
            
            st.code(dump_text, language="text")
            
        # 💡 記憶體優化：強迫系統清道夫上工，收回運算過程產生的垃圾
        gc.collect()