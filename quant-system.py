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
from io import StringIO
import streamlit.components.v1 as components

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="全息量化系統 (V60.34版)", initial_sidebar_state="expanded")

FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"
GITHUB_MANUAL_URL = "https://raw.githubusercontent.com/tonehsie/stock/refs/heads/main/README.md"

CSS = """
<style>
.table-container { overflow: auto; max-height: 480px; width: 100%; margin-bottom: 25px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
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
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_github_manual(url):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            r.encoding = 'utf-8'
            return r.text
        return "無法載入說明書，請確認 GitHub Raw 網址是否正確。"
    except Exception as e: return f"說明書載入失敗: {e}"

@st.cache_data(ttl=300, show_spinner=False)
def get_api_usage(token):
    try:
        r = requests.get(f"https://api.web.finmindtrade.com/v2/user_info?token={token}", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data.get("user_count", 0), data.get("api_request_limit", 0)
    except: pass
    return None, None

st.sidebar.header("戰術參數控制面板")
kline_days = st.sidebar.slider("K線顯示天數 (圖表景深)", 30, 600, 270, 10)
lookback_days = st.sidebar.selectbox("長線籌碼回溯天數 (全局黏著度分母)", [20, 60, 90, 120], index=1)
stickiness_threshold = st.sidebar.slider("主力黏著度門檻 (%)", 10.0, 80.0, 50.0, 5.0)
footprint_days = st.sidebar.slider("足跡明細追蹤天數 (顯示範圍)", 3, 60, 20, 1)
footprint_rows = st.sidebar.slider("足跡矩陣顯示筆數 (多空各 N 名)", 5, 50, 15, 5)
firepower_threshold = st.sidebar.slider("買方火力倍數門檻", 1.0, 5.0, 1.5, 0.1)

st.sidebar.divider()
st.sidebar.markdown("### AI 幾何形態與技術線")
enable_pattern = st.sidebar.checkbox("啟動 AI 幾何形態掃描", value=True)

pattern_mode = st.sidebar.selectbox("形態顯示模式", [
    "全自動智能辨識 (Auto)", 
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

st.title("全息量化系統 (V60.34 工業級防呆版)")
user_count, api_limit = get_api_usage(FINMIND_TOKEN)
usage_text = f" | FinMind 額度: {user_count} / {api_limit}" if user_count is not None else ""
st.caption(f"V60.34：全面加裝 API 資料遺失護盾，徹底解決 KeyError 當機問題。{usage_text}")

with st.expander("點此閱讀【全息量化系統】四大核心模組終極實戰說明書", expanded=False):
    manual_text = fetch_github_manual(GITHUB_MANUAL_URL)
    st.markdown(manual_text, unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])
with col1: 
    user_stock_id = st.text_input("個股代號", value="2330")
with col2: 
    dead_chip_input = st.text_input("死籌碼 % (董監事持股、董監事＋大股東持股，留空自動抓)")
run_btn = st.button("啟動 V60.34 決策引擎", use_container_width=True, key="run_engine")

def safe_to_num(series, fill_val=0):
    if isinstance(series, pd.Series):
        if pd.api.types.is_numeric_dtype(series): return series.fillna(fill_val)
        try: return pd.to_numeric(series.astype(str).str.replace(',', '', regex=False).str.replace('%', '', regex=False).str.strip(), errors='coerce').fillna(fill_val)
        except: return pd.Series([fill_val] * len(series))
    elif isinstance(series, (int, float)): return series
    else:
        try: return float(str(series).replace(',', '').replace('%', '').strip())
        except: return fill_val

@st.cache_data(ttl=3600, show_spinner=False)
def get_stock_name_v50(tid):
    try:
        r = requests.get(f"https://tw.stock.yahoo.com/quote/{tid}.TW", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code == 200:
            m = re.search(r'<title>(.*?)\s*\(', r.text)
            return m.group(1).strip() if m else ""
    except: pass
    return ""

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_finmind_v50(ds, sd, tid=None, ed=None):
    url = "https://api.finmindtrade.com/api/v4/data"
    p = {"dataset": ds, "start_date": sd}
    if tid: p["data_id"] = tid
    if ed: p["end_date"] = ed
    try: 
        r = requests.get(url, params=p, headers={"Authorization": f"Bearer {FINMIND_TOKEN}"}, timeout=15)
        if r.status_code == 200:
            data = r.json().get("data", [])
            # 防呆：確保回傳的必定是有效的 list，避免髒字串毀掉 DataFrame
            return pd.DataFrame(data) if isinstance(data, list) and len(data) > 0 else pd.DataFrame()
    except: pass
    return pd.DataFrame()

def _fetch_heavy_data_cache_core(user_stock_id, dates, max_len):
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

    with requests.Session() as session:
        session.headers.update({"Authorization": f"Bearer {FINMIND_TOKEN}"})

        def fetch_api(dataset, sd, ed, tid):
            url = "https://api.finmindtrade.com/api/v4/data"
            p = {"dataset": dataset, "start_date": sd}
            if tid: p["data_id"] = tid
            if ed: p["end_date"] = ed
            try:
                r = session.get(url, params=p, timeout=20)
                if r.status_code == 200: 
                    data = r.json().get("data", [])
                    return dataset, data if isinstance(data, list) else []
            except: pass
            return dataset, []

        def fetch_branch(d, tid):
            url = "https://api.finmindtrade.com/api/v4/data"
            p = {"dataset": "TaiwanStockTradingDailyReport", "data_id": tid, "start_date": d, "end_date": d}
            try:
                r = session.get(url, params=p, timeout=20)
                if r.status_code == 200: 
                    data = r.json().get("data", [])
                    return data if isinstance(data, list) else []
            except: pass
            return []

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_type = {}
            for d in dates[:max_len]:
                future_to_type[executor.submit(fetch_branch, d, user_stock_id)] = 'branch'
            for ds, sd, ed, tid in api_targets:
                future_to_type[executor.submit(fetch_api, ds, sd, ed, tid)] = 'api'

            for future in concurrent.futures.as_completed(future_to_type):
                f_type = future_to_type[future]
                if f_type == 'branch':
                    res = future.result()
                    if res: b_results.extend(res)
                else:
                    ds, data = future.result()
                    a_results[ds] = pd.DataFrame(data) if data else pd.DataFrame()

            df_cbas_raw = a_results.get("TaiwanStockConvertibleBondDailyOverview", pd.DataFrame())
            if not df_cbas_raw.empty and 'cb_id' in df_cbas_raw.columns:
                cb_mask = df_cbas_raw['cb_id'].astype(str).str.replace(',', '', regex=False).str.startswith(user_stock_id)
                target_cbs = df_cbas_raw[cb_mask]['cb_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.replace(',', '', regex=False).str.strip().unique()
                if len(target_cbs) > 0:
                    cb_futures = [executor.submit(fetch_api, "TaiwanStockConvertibleBondInfo", "2000-01-01", None, cid) for cid in target_cbs]
                    for f in concurrent.futures.as_completed(cb_futures):
                        _, cb_data = f.result()
                        if cb_data: cb_info_list.extend(cb_data)

    df_b = pd.DataFrame(b_results)
    if not df_b.empty:
        for c in ['buy', 'sell', 'price']:
            if c in df_b.columns: df_b[c] = safe_to_num(df_b[c])
            else: df_b[c] = 0.0

    df_cb_info = pd.DataFrame(cb_info_list)
    return df_b, a_results, df_cb_info

def fetch_heavy_data_sync_with_progress(user_stock_id, dates, max_len):
    prog_container = st.empty()
    text_container = st.empty()
    prog_bar = prog_container.progress(0.1)
    text_container.markdown(f"<div class='progress-text'>⚡ 正在與 FinMind 伺服器建立全併發連線 (預估 3-5 秒)...</div>", unsafe_allow_html=True)
    
    df_b, a_results, df_cb_info = _fetch_heavy_data_cache_core(user_stock_id, dates, max_len)
    
    prog_bar.progress(1.0)
    prog_container.empty()
    text_container.empty()
    return df_b, a_results, df_cb_info

def fetch_heavy_data_smart(user_stock_id, dates, max_len):
    cache_key = f"heavy_data_{user_stock_id}_{max_len}_{dates[0] if dates else 'na'}"
    if 'heavy_cache' not in st.session_state:
        st.session_state['heavy_cache'] = {}
        
    if cache_key in st.session_state['heavy_cache']:
        return st.session_state['heavy_cache'][cache_key]
    else:
        df_b, a_results, df_cb_info = fetch_heavy_data_sync_with_progress(user_stock_id, dates, max_len)
        st.session_state['heavy_cache'].clear()
        st.session_state['heavy_cache'][cache_key] = (df_b, a_results, df_cb_info)
        return df_b, a_results, df_cb_info

@st.cache_data(ttl=3600, show_spinner=False)
def scrape_block_v50(tid, ad):
    if not ad: return pd.DataFrame(), []
    td, bd, dl = ad[:3], [], []
    with requests.Session() as session:
        session.headers.update({"User-Agent": "Mozilla/5.0"})
        def fd(d):
            dtw = d.replace("-", "")
            dtp = f"{int(d.split('-')[0])-1911}/{d.split('-')[1]}/{d.split('-')[2]}"
            rl = []
            try:
                r = session.get(f"https://www.twse.com.tw/rwd/zh/block/BFIAUU?date={dtw}&response=json", timeout=5, verify=False)
                if r.status_code == 200 and isinstance(r.json().get("data"), list):
                    for ro in r.json()["data"]:
                        if tid in str(ro): rl.append([d, "TWSE", ro])
            except: pass
            try:
                r = session.get(f"https://www.tpex.org.tw/www/zh-tw/blockTrade/quote?date={dtp}&id=&response=json", timeout=5, verify=False)
                if r.status_code == 200 and "tables" in r.json() and r.json()["tables"]:
                    if isinstance(r.json()["tables"][0].get("data"), list):
                        for ro in r.json()["tables"][0]["data"]:
                            if tid in str(ro): rl.append([d, "TPEx", ro])
            except: pass
            return rl
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            for data in ex.map(fd, td):
                if data: bd.extend(data)
    if not bd: return pd.DataFrame(), list(set(dl))
    p = []
    for i in bd:
        date, src, row = i
        nums = []
        for c in row:
            c_str = re.sub(r'<[^>]+>', '', str(c)).replace(',', '').strip()
            if c_str and ':' not in c_str and c_str.replace('.', '', 1).isdigit(): nums.append(float(c_str))
        nums.sort(reverse=True)
        if len(nums) >= 3:
            amt = nums[0] / 10000 if nums[0] > 100000 else nums[0]
            vol = nums[1] / 1000 if nums[1] > 1000 else nums[1]
            tt = next((re.sub(r'<[^>]+>', '', str(c)).strip() for c in row if any(x in str(c) for x in ["配對","交易","單一","組合","逐筆"])), "鉅額")
            p.append({"日期": date, "交易別": tt, "成交量(張)": int(vol), "成交價(元)": round(nums[2], 2), "成交金額(萬元)": int(amt)})
    return pd.DataFrame(p).sort_values("日期", ascending=False), list(set(dl))

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
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, verify=False)
            if res.status_code == 200: 
                res.encoding = 'big5'
                return res.text
        except: pass
    return ""

@st.cache_data(ttl=3600, show_spinner=False)
def scrape_director_v50(tid):
    dd, sv = {}, 0.0
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Cookie": "CLIENT_KEY=20260413;", "Referer": f"https://goodinfo.tw/tw/StockDetail.asp?STOCK_ID={tid}"}
        r = requests.get(f"https://goodinfo.tw/tw/StockDirectorSharehold.asp?STOCK_ID={tid}", headers=headers, timeout=8)
        if r.status_code == 200:
            r.encoding = 'utf-8'
            for df in pd.read_html(StringIO(r.text)):
                if isinstance(df.columns, pd.MultiIndex): df.columns = ['_'.join(str(c) for c in col if 'Unnamed' not in str(c)).strip('_') for col in df.columns.values]
                else: df.columns = df.columns.astype(str)
                tc = next((c for c in df.columns if '全體董監持股' in str(c) and '持股(%)' in str(c).replace(' ', '')), None)
                mc = next((c for c in df.columns if '月別' in str(c)), None)
                if tc and mc:
                    lt = 0.0
                    for _, ro in df.iterrows():
                        m, v = str(ro[mc]).replace('/', '-').strip(), str(ro[tc]).replace(',', '').strip()
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

@st.cache_data(ttl=86400, show_spinner=False)
def get_company_profile(tid):
    ind, addr = "未知產業", "查無地址"
    try:
        f = fetch_finmind_v50("TaiwanStockInfo", "2020-01-01")
        if not f.empty and 'stock_id' in f.columns:
            m = f[f['stock_id'] == str(tid)]
            if not m.empty: ind = m['industry_category'].iloc[0]
        r = requests.get(f"https://tw.stock.yahoo.com/quote/{tid}/profile", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code == 200:
            m = re.search(r'公司地址\|+([^|]+)', re.sub(r'<[^>]+>', '|', r.text))
            if m: addr = m.group(1).strip()
    except: pass
    return ind, addr

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

@st.cache_data(ttl=3600, show_spinner=False)
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
    for _, r in df_all.iterrows():
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
    for _, r in df_all.iterrows():
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
    
    price_stats = df_p.set_index('date')[['pos']].to_dict('index')
    latest_close = df_p['close'].iloc[0] if not df_p.empty else 0

    df = df_b_raw.copy()
    df['date_dt'] = pd.to_datetime(df['date'])
    df['net_shares'] = df['buy'] - df['sell']
    
    df['valid_buy_amt'] = np.where(df['price'] > 0, df['buy'] * df['price'], 0)
    df['valid_buy_vol'] = np.where(df['price'] > 0, df['buy'], 0)
    df['valid_sell_amt'] = np.where(df['price'] > 0, df['sell'] * df['price'], 0)
    df['valid_sell_vol'] = np.where(df['price'] > 0, df['sell'], 0)

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
        buy_amt=('valid_buy_amt', 'sum'),
        sell_amt=('valid_sell_amt', 'sum'),
        valid_b_shares=('valid_buy_vol', 'sum'),
        valid_s_shares=('valid_sell_vol', 'sum'),
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
    
    cond_dump = (g['net_60d'] >= 300) & (g['net_20d'] >= 100) & (g['net_5d'] <= -100)
    cond_core = (g['net_60d'] >= 200) & (g['net_20d'] >= 100) & (g['net_5d'] >= 50)
    cond_bear = (g['net_60d'] <= -200) & (g['net_20d'] <= -100) & (g['net_5d'] <= -100)
    cond_cover = (g['net_60d'] <= -100) & (g['net_5d'] >= 200)
    cond_sniper = (g['net_60d'].between(-200, 200)) & (g['net_20d'].between(-200, 200)) & (g['net_5d'] >= 300)
    cond_maker = g['stickiness'] >= stick_thresh
    cond_flash = (g['stickiness'] < 10.0) & (g['net_5d'].abs() > 50)

    g['tag'] = np.select(
        [cond_dump, cond_core, cond_bear, cond_cover, cond_sniper, cond_maker, cond_flash],
        ["[逢高派發]", "[波段鐵粉]", "[長線倒貨]", "[低檔回補]", "[短線狙擊]", "[常駐造市]", "[快閃散戶]"],
        default="[隨波逐流]"
    )

    tags = g['tag'].to_dict()
    g = g[(g['tb_shares'] > 0) | (g['ts_shares'] > 0)].copy()
    
    cond_loss = (g['avg_b'] > latest_close) & (g['avg_b'] > 0) & (g['net_shares'] > 0)
    b_strs = g['avg_b'].apply(lambda x: f"{x:,.2f}")
    g['b_str'] = np.where(cond_loss, "(虧) " + b_strs, b_strs)
    g['pos'] = g['last_date'].map(lambda x: price_stats.get(x, {'pos': 0.5})['pos']).fillna(0.5).round(2)
    
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
    df['tag'] = df['securities_trader'].map(tags).fillna("[隨波逐流]")
    
    if is_filter_active: 
        valid_df = df[~df['tag'].str.contains("短線狙擊|快閃散戶|長線倒貨", na=False)].copy()
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
            c_value = round((full_net_accum / free_float_lots) * 100, 2)

    return vwap, full_net_accum, active_buyers, c_value, core_branch_names

def get_core_period_net(df_raw, rank_dates, core_names):
    if df_raw.empty or not rank_dates or not core_names: return 0
    df_rank = df_raw[df_raw['date'].isin(rank_dates)].copy()
    df_rank = df_rank[df_rank['securities_trader'].isin(core_names)]
    net_shares = df_rank['buy'].sum() - df_rank['sell'].sum()
    return int(round(net_shares / 1000))

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
                "標籤": intel_tags.get(trader, "[隨波逐流]"),
                "黏著度(%)": st_val, 
                hr_name: hr_val,
                f"區間累計(張)": f"+{total_val}" if total_val > 0 else str(total_val)
            }
            
            for i, d in enumerate(display_dates):
                v = p.loc[trader, d] if trader in p.index and d in p.columns else 0
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
            b_str = f"{round(b.loc[i,'avg_b'], 2):,.2f}"
            if b.loc[i,'avg_b'] > latest_close and b.loc[i,'avg_b'] > 0 and b.loc[i,'net'] > 0: b_str = f"(虧) {b_str}"
            raw_tag = intel_tags.get(b.loc[i,'securities_trader'], '[隨波逐流]')
            attr = "短線" if any(x in raw_tag for x in ["短線狙擊", "快閃散戶", "低檔回補"]) else "中長線" if any(x in raw_tag for x in ["波段鐵粉", "常駐造市"]) else "波段"
            r["買超分點"] = b.loc[i,'securities_trader']
            r["買_標籤"] = raw_tag
            r["買_週期"] = attr
            r["買超(張)"] = int(b.loc[i,'net'])
            r["買均價"] = b_str
            r["佔比"] = f"{(b.loc[i,'net']/tv)*100:.1f}%" if tv > 0 else "-"
        else: r["買超分點"], r["買_標籤"], r["買_週期"], r["買超(張)"], r["買均價"], r["佔比"] = "-", "-", "-", 0, "-", "-"
        
        if i < len(s): 
            raw_tag_s = intel_tags.get(s.loc[i,'securities_trader'], '[隨波逐流]')
            attr_s = "短線" if any(x in raw_tag_s for x in ["短線狙擊", "快閃散戶", "低檔回補"]) else "中長線" if any(x in raw_tag_s for x in ["波段鐵粉", "常駐造市"]) else "波段"
            r["賣超分點"] = s.loc[i,'securities_trader']
            r["賣_標籤"] = raw_tag_s
            r["賣_週期"] = attr_s
            r["賣超(張)"] = abs(int(s.loc[i,'net']))
            r["賣均價"] = f"{round(s.loc[i,'avg_s'], 2):,.2f}"
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

    def get_pct(row, threshold):
        if threshold <= 100: return row['pct_100']
        if threshold <= 200: return row['pct_200']
        if threshold <= 400: return row['pct_400']
        if threshold <= 600: return row['pct_600']
        if threshold <= 800: return row['pct_800']
        return row['pct_1000']
    
    fake_dict = {}
    if not df_branch_raw.empty:
        df_b_tagged = df_branch_raw[['date', 'securities_trader', 'buy', 'sell']].copy()
        df_b_tagged['tag'] = df_b_tagged['securities_trader'].map(intel_tags).fillna("")
        mask_short = df_b_tagged['tag'].str.contains("短線狙擊|低檔回補|快閃散戶", na=False)
        df_fake = df_b_tagged[mask_short]
        if not df_fake.empty:
            df_fake_daily = df_fake.groupby(['date', 'securities_trader'])[['buy', 'sell']].sum().reset_index()
            df_fake_daily['net_buy_exact'] = (df_fake_daily['buy'] - df_fake_daily['sell']) / 1000
            fake_dict = df_fake_daily.groupby('date').apply(lambda x: x[['securities_trader', 'net_buy_exact']].to_dict('records')).to_dict()

    arr_dates_str = np.sort(df_branch_raw['date'].unique()) if not df_branch_raw.empty else np.array([])
    arr_dates_dt = pd.to_datetime(arr_dates_str) if len(arr_dates_str) > 0 else []

    out, d_math, d_fri = [], [], []
    prev_row = None
    
    for i, row in df.iterrows():
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
            if row['總人數變率(%)'] > 2.0 and p_chg < 0: adv.append(f"[逃命波] 散戶增{row['總人數變率(%)']}%，大戶實質倒貨{abs(p_chg)}%")
            else:
                if p_chg * lev > 2.5 and row['收盤價(元)'] > row['ma20']: adv.append(f"[強勢軋空] 站上月線且大戶純淨買超{round(p_chg*lev, 2)}%")
                elif p_chg > 0.4 and row['收盤價(元)'] < row['ma20']: adv.append(f"[底位建倉] 跌破月線但主力吃貨{p_chg}%")
                elif p_chg < -1.0: adv.append(f"[主力撤退] 大戶實質流出{abs(p_chg)}%")
                if f_impact > 1.2: adv.append(f"[當沖/短沖陷阱] 虛胖買盤潛藏{round(f_impact, 2)}%倒貨危機")
                
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
    df_b['tag'] = df_b['securities_trader'].map(intel_tags).fillna("[隨波逐流]")
    
    df_b['is_smart'] = df_b['tag'].str.contains('波段鐵粉|常駐造市|逢高派發|長線倒貨', na=False)
    df_b['is_short'] = df_b['tag'].str.contains('短線狙擊|低檔回補|快閃散戶', na=False)
    
    df_b['valid_bs'] = np.where(df_b['pr'] > 0, df_b['bs'], 0)
    df_b['valid_ss'] = np.where(df_b['pr'] > 0, df_b['ss'], 0)
    df_b['buy_amt'] = df_b['valid_bs'] * df_b['pr']
    df_b['sell_amt'] = df_b['valid_ss'] * df_b['pr']

    df_smart_all = df_b[df_b['is_smart']].groupby(['date', 'securities_trader', 'tag']).agg(
        bs=('bs','sum'), 
        ss=('ss','sum'), 
        buy_amt=('buy_amt','sum'), 
        sell_amt=('sell_amt','sum')
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
            for _, r in smart_grouped.iterrows():
                if r['net_vol'] != 0: audit_smart_money.append({"日期": d, "分點": r['securities_trader'], "標籤": r['tag'], "淨買超(張)": r['net_vol']})
        
        smart_net = smart_grouped['net_vol'].sum() if not smart_grouped.empty else 0
        short_trap = short_grouped[short_grouped['net_vol'] > 0]['net_vol'].sum() if not short_grouped.empty else 0
        
        if not smart_grouped.empty:
            s_ret = smart_grouped.copy()
            s_ret['net_shares'] = s_ret['bs'] - s_ret['ss']
            s_ret['net_amt'] = s_ret['buy_amt'] - s_ret['sell_amt']
            
            s_ret_long = s_ret[s_ret['net_shares'] > 0]
            total_n = s_ret_long['net_shares'].sum()
            total_net_amt = s_ret_long['net_amt'].sum()
            
            if total_n > 0:
                smart_avg_cost = total_net_amt / total_n
                smart_avg_cost = max(0.0, smart_avg_cost)
            else: 
                smart_avg_cost = 0.0
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

_num_re = re.compile(r'\d+')
def clean_level_by_math(x):
    s = str(x).replace(',','').replace(' ','')
    if s in ["17","17.0","合計","總計"]: return "合計"
    n = _num_re.findall(s)
    if not n: return s
    m = {1:"1-999股",2:"1-5張",3:"5-10張",4:"10-15張",5:"15-20張",6:"20-30張",7:"30-40張",8:"40-50張",9:"50-100張",10:"100-200張",11:"200-400張",12:"400-600張",13:"600-800張",14:"800-1000張",15:"1000張以上"}
    v = int(n[0])
    if len(n)==1 and v<=15: return m.get(v,s)
    u = int(n[-1])
    if u<=999: return "1-999股"
    elif u<=5000: return "1-5張"
    elif u<=10000: return "5-10張"
    elif u<=15000: return "10-15張"
    elif u<=20000: return "15-20張"
    elif u<=30000: return "20-30張"
    elif u<=40000: return "30-40張"
    elif u<=50000: return "40-50張"
    elif u<=100000: return "50-100張"
    elif u<=200000: return "100-200張"
    elif u<=400000: return "200-400張"
    elif u<=600000: return "400-600張"
    elif u<=800000: return "600-800張"
    elif u<=1000000: return "800-1000張" 
    else: return "1000張以上" 

# 【V60.34 防護裝甲】加入 KeyError 安全護盾
def process_tdcc(df):
    if df.empty or 'HoldingSharesLevel' not in df.columns or 'date' not in df.columns: 
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df = df[~df['HoldingSharesLevel'].astype(str).str.contains('差異數')].copy()
    df['LevelClean'] = df['HoldingSharesLevel'].apply(clean_level_by_math)
    df['unit'] = (safe_to_num(df.get('unit', 0)) / 1000).round().astype(int)
    df['people'] = safe_to_num(df.get('people', 0)).astype(int)
    dates = sorted(df['date'].unique(), reverse=True)[:15]
    df = df[df['date'].isin(dates)]
    df_levels = df[~df['LevelClean'].str.contains('合計|總計')]
    if df_levels.empty: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    p_u = df_levels.pivot_table(index='date', columns='LevelClean', values='unit', aggfunc='sum').reset_index().fillna(0)
    p_p = df_levels.pivot_table(index='date', columns='LevelClean', values='people', aggfunc='sum').reset_index().fillna(0)
    lvls = ['1-999股', '1-5張', '5-10張', '10-15張', '15-20張', '20-30張', '30-40張', '40-50張', '50-100張', '100-200張', '200-400張', '400-600張', '600-800張', '800-1000張', '1000張以上']
    for l in lvls:
        if l not in p_u.columns: p_u[l] = 0
        if l not in p_p.columns: p_p[l] = 0
    df_t = pd.DataFrame({'date': p_u['date']})
    df_t['總張數'] = p_u[lvls].sum(axis=1)
    df_t['總人數(人)'] = p_p[lvls].sum(axis=1)
    df_w = df_t.copy()
    for l in lvls: df_w[f"{l}_張數"], df_w[f"{l}_人數"], df_w[f"{l}_比例(%)"] = p_u[l], p_p[l], (p_u[l] / df_t['總張數'].replace(0, np.nan) * 100).fillna(0).round(2)
    df_w = df_w.rename(columns={'date': '日期'}).sort_values('日期', ascending=False)
    df_unit = pd.merge(df_t[['date', '總張數']], p_u[['date']+lvls], on='date').rename(columns={'date': '日期'}).sort_values('日期', ascending=False)
    df_ppl = pd.merge(df_t[['date', '總人數(人)']], p_p[['date']+lvls], on='date').rename(columns={'date': '日期'}).sort_values('日期', ascending=False)
    return df_w, df_unit, df_ppl

def process_tdcc_dynamic(df_share_wide, df_price, dead_chip_input, dynamic_dict, static_val, chip_engine):
    if df_share_wide.empty or df_price.empty or '日期' not in df_share_wide.columns: return pd.DataFrame()
    df_s, df_p = df_share_wide.copy(), df_price.copy()
    df_s['dt'], df_p['dt'] = pd.to_datetime(df_s['日期']), pd.to_datetime(df_p['日期'])
    df_p = df_p.drop_duplicates(subset=['dt']).sort_values('dt')
    df_m = pd.merge_asof(df_s.sort_values('dt'), df_p[['dt', '收盤價(元)']], on='dt', direction='backward').sort_values('dt', ascending=False)

    levels_cols = ['100-200張_比例(%)', '200-400張_比例(%)', '400-600張_比例(%)', '600-800張_比例(%)', '800-1000張_比例(%)', '1000張以上_比例(%)']
    for col in levels_cols:
        df_m[col] = pd.to_numeric(df_m[col], errors='coerce').fillna(0.0) if col in df_m.columns else 0.0

    df_m['pct_1000'] = df_m['1000張以上_比例(%)']
    df_m['pct_800'] = df_m['pct_1000'] + df_m['800-1000張_比例(%)']
    df_m['pct_600'] = df_m['pct_800'] + df_m['600-800張_比例(%)']
    df_m['pct_400'] = df_m['pct_600'] + df_m['400-600張_比例(%)']
    df_m['pct_200'] = df_m['pct_400'] + df_m['200-400張_比例(%)']
    df_m['pct_100'] = df_m['pct_200'] + df_m['100-200張_比例(%)']

    def get_pct(row, threshold):
        if threshold <= 100: return row['pct_100']
        if threshold <= 200: return row['pct_200']
        if threshold <= 400: return row['pct_400']
        if threshold <= 600: return row['pct_600']
        if threshold <= 800: return row['pct_800']
        return row['pct_1000']

    out = []
    for _, row in df_m.iterrows():
        p = row.get('收盤價(元)', 0)
        if pd.isna(p) or p <= 0: continue
        cur_dead, cl = get_dead_chip_info(row['日期'], dead_chip_input, dynamic_dict, static_val, chip_engine)
        total_lots = row.get('總張數', 0)
        safe_dead_ratio = max(0.0, min(99.9, cur_dead))
        ct = get_smart_threshold(p, total_lots, safe_dead_ratio)
        lp = get_pct(row, ct)
        cd, st_val = "-", "無董監事持股數據"
        if 0 < safe_dead_ratio < 100:
            cv = max(0, (lp - safe_dead_ratio) / (100.0 - safe_dead_ratio))
            st_val = "強勢控盤" if cv >= 0.5 else "偏強鎖碼" if cv >= 0.3 else "初步集結" if cv >= 0.15 else "籌碼渙散"
            cd = round(cv * 100, 2)
        out.append({"日期": row['日期'], "收盤價(元)": p, "大戶精算門檻": f"系統判定 ({int(ct)}張)", "大戶原持股(%)": round(lp, 2), "董監死籌碼(%)": f"{float(safe_dead_ratio):.2f}% ({cl})" if safe_dead_ratio > 0 else "-", "純淨活大戶C_Value(%)": cd, "實戰判定": st_val})
    return pd.DataFrame(out)

def process_day_trading(df):
    if df.empty or 'date' not in df.columns: return pd.DataFrame()
    df_out = df.copy()
    if 'DayTradingVolume' in df_out.columns: df_out['當沖總股數'] = df_out['DayTradingVolume']
    elif 'Volume' in df_out.columns: df_out['當沖總股數'] = df_out['Volume']
    df_out = df_out.rename(columns={"date": "日期", "BuyAfterSale": "先買後賣股數", "SellAfterBuy": "先賣後買股數"})
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]
    for col in ["當沖總股數", "先買後賣股數", "先賣後買股數"]:
        if col in df_out.columns: 
            v_num = safe_to_num(df_out[col])
            df_out[col.replace('股數', '張數')] = (v_num / 1000).round().astype(int)
            df_out = df_out.drop(columns=[col])
    cols = ['日期'] + [c for c in df_out.columns if '張數' in c or '率' in c]
    return df_out[cols].tail(10).sort_values('日期', ascending=False)

def process_margin(df):
    if df.empty or 'date' not in df.columns: return pd.DataFrame()
    for c in ["MarginPurchaseBuy", "MarginPurchaseSell", "MarginPurchaseCashRepayment", "MarginPurchaseTodayBalance", "MarginPurchaseYesterdayBalance", "ShortSaleBuy", "ShortSaleSell", "ShortSaleCashRepayment", "ShortSaleTodayBalance", "OffsetLoanAndShort", "ShortSaleYesterdayBalance"]:
        if c in df.columns: df[c] = safe_to_num(df[c]).round().astype(int)
    df = df.rename(columns={
        "date": "日期", "MarginPurchaseBuy": "融資買進(萬元)", "MarginPurchaseSell": "融資賣出(萬元)", 
        "MarginPurchaseCashRepayment": "融資現償(萬元)", "MarginPurchaseTodayBalance": "融資餘額(萬元)", 
        "ShortSaleBuy": "融券買進(張)", "ShortSaleSell": "融券賣出(張)", 
        "ShortSaleTodayBalance": "融券餘額(張)", "OffsetLoanAndShort": "資券相抵(張)"
    })
    df = df.loc[:, ~df.columns.duplicated()]
    if '融資餘額(萬元)' in df.columns and 'MarginPurchaseYesterdayBalance' in df.columns:
        prev_margin = safe_to_num(df['MarginPurchaseYesterdayBalance']).round().astype(int)
        df['融資增減(萬元)'] = df['融資餘額(萬元)'] - prev_margin
    if '融券餘額(張)' in df.columns and 'ShortSaleYesterdayBalance' in df.columns:
        prev_short = safe_to_num(df['ShortSaleYesterdayBalance']).round().astype(int)
        df['融券增減(張)'] = df['融券餘額(張)'] - prev_short
    cols = [c for c in ['日期','融資買進(萬元)','融資賣出(萬元)','融資現償(萬元)','融資餘額(萬元)','融資增減(萬元)','融券買進(張)','融券賣出(張)','融券餘額(張)','融券增減(張)','資券相抵(張)'] if c in df.columns]
    return df[cols].tail(10).sort_values('日期', ascending=False)

def process_inst(df):
    if df.empty or 'date' not in df.columns or 'name' not in df.columns: return pd.DataFrame()
    pdf = df.pivot_table(index='date', columns='name', values=['buy', 'sell'], fill_value=0).reset_index()
    pdf.columns = ['_'.join(c).strip('_') for c in pdf.columns.values]
    out = pd.DataFrame({'日期': pdf['date']})
    length = len(pdf)
    f_b = safe_to_num(pdf.get('buy_Foreign_Investor', pd.Series([0]*length)))
    f_s = safe_to_num(pdf.get('sell_Foreign_Investor', pd.Series([0]*length)))
    out['外資買賣超(張)'] = ((f_b - f_s) / 1000).round().astype(int)
    i_b = safe_to_num(pdf.get('buy_Investment_Trust', pd.Series([0]*length)))
    i_s = safe_to_num(pdf.get('sell_Investment_Trust', pd.Series([0]*length)))
    out['投信買賣超(張)'] = ((i_b - i_s) / 1000).round().astype(int)
    ds_b = safe_to_num(pdf.get('buy_Dealer_self', pdf.get('buy_Dealer', pd.Series([0]*length))))
    ds_s = safe_to_num(pdf.get('sell_Dealer_self', pdf.get('sell_Dealer', pd.Series([0]*length))))
    out['自營商(自行)買賣超(張)'] = ((ds_b - ds_s) / 1000).round().astype(int)
    dh_b = safe_to_num(pdf.get('buy_Dealer_Hedging', pd.Series([0]*length)))
    dh_s = safe_to_num(pdf.get('sell_Dealer_Hedging', pd.Series([0]*length)))
    out['自營商(避險)買賣超(張)'] = ((dh_b - dh_s) / 1000).round().astype(int)
    out['三大法人買賣超(張)'] = out['外資買賣超(張)'] + out['投信買賣超(張)'] + out['自營商(自行)買賣超(張)'] + out['自營商(避險)買賣超(張)']
    return out.tail(10).sort_values('日期', ascending=False)

def process_fut_inst(df):
    if df.empty or 'date' not in df.columns or 'institutional_investors' not in df.columns: return pd.DataFrame()
    df['net'] = safe_to_num(df.get('long_open_interest_balance_volume', 0)) - safe_to_num(df.get('short_open_interest_balance_volume', 0))
    pdf = df.pivot_table(index='date', columns='institutional_investors', values='net', fill_value=0).reset_index()
    pdf.columns.name = None
    for col in ['Foreign_Investor', 'Investment_Trust', 'Dealer']:
        if col not in pdf.columns: pdf[col] = 0
    return pdf.rename(columns={'date': '日期', 'Foreign_Investor': '外資多空(口)', 'Investment_Trust': '投信多空(口)', 'Dealer': '自營多空(口)'}).tail(10).sort_values('日期', ascending=False)

def process_per(df):
    if df.empty or 'date' not in df.columns: return pd.DataFrame()
    df_out = df.copy().rename(columns={"date":"日期","dividend_yield":"殖利率(%)","PER":"本益比(倍)","PBR":"淨值比(倍)"})
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]
    for col in ["殖利率(%)", "本益比(倍)", "淨值比(倍)"]: 
        if col in df_out.columns: df_out[col] = safe_to_num(df_out[col]).round(2)
    cols = [c for c in ['日期', '本益比(倍)', '淨值比(倍)', '殖利率(%)'] if c in df_out.columns]
    return df_out[cols].tail(10).sort_values('日期', ascending=False)

def process_disp(df):
    if df.empty or 'date' not in df.columns: return pd.DataFrame()
    df_out = df.copy().rename(columns={"date":"公告日期","disposition_cnt":"處置次數","condition":"處置條件","measure":"處置措施","period_start":"處置起日","period_end":"處置迄日"})
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]
    cols = [c for c in ['公告日期', '處置次數', '處置起日', '處置迄日', '處置條件', '處置措施'] if c in df_out.columns]
    return df_out[cols].tail(5).sort_values('公告日期', ascending=False)

def process_div(df):
    if df.empty or 'date' not in df.columns: return pd.DataFrame()
    df_out = df.rename(columns={"date": "公告日期", "year": "股利年份", "StockEarningsDistribution": "盈餘配股(元)", "StockStatutorySurplus": "公積配股(元)", "CashEarningsDistribution": "盈餘配息(元)", "CashStatutorySurplus": "公積配息(元)"})
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]
    cols = [c for c in ["公告日期", "股利年份", "盈餘配息(元)", "公積配息(元)", "盈餘配股(元)", "公積配股(元)"] if c in df_out.columns]
    if '股利年份' in df_out.columns:
        year_num = safe_to_num(df_out['股利年份'].astype(str).str.replace('年', '').str.strip(), fill_val=np.nan)
        recent = sorted(year_num.dropna().unique(), reverse=True)[:5]
        return df_out[year_num.isin(recent)][cols].sort_values('公告日期', ascending=False)
    return df_out[cols].sort_values('公告日期', ascending=False).head(10)

def process_cbas(df, current_stock_price, df_cb_info=None):
    if df.empty or 'date' not in df.columns: return pd.DataFrame()
    df_out = df.copy().rename(columns={"date": "日期", "cb_id": "可轉債代號", "cb_name": "可轉債名稱", "conversion_price": "轉換價(元)", "ConversionPrice": "轉換價(元)", "underlying_stock_price": "標的股價(元)", "PriceOfUnderlyingStock": "標的股價(元)", "outstanding_amount": "未償還餘額", "OutstandingAmount": "未償還餘額", "outstanding_balance": "未償還餘額", "close": "CB收盤價", "closing_price": "CB收盤價", "conversion_premium_rate": "溢價率(%)", "premium_rate": "溢價率(%)", "PremiumRate": "溢價率(%)", "theoretical_value": "轉換價值", "TheoreticalValue": "轉換價值"})
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]
    
    if "可轉債代號" in df_out.columns: df_out['可轉債代號'] = df_out['可轉債代號'].astype(str).str.replace(r'\.0$', '', regex=True).str.replace(',', '', regex=False).str.strip()
    for c in ["轉換價(元)", "標的股價(元)", "未償還餘額", "CB收盤價", "溢價率(%)", "轉換價值"]:
        if c in df_out.columns: df_out[c] = safe_to_num(df_out[c], fill_val=np.nan)
    if "標的股價(元)" not in df_out.columns or df_out["標的股價(元)"].isna().all(): df_out["標的股價(元)"] = current_stock_price
    if "標的股價(元)" in df_out.columns and "轉換價(元)" in df_out.columns:
        df_out["轉換價(元)"] = df_out["轉換價(元)"].replace(0, np.nan)
        if "轉換價值" not in df_out.columns or df_out["轉換價值"].isna().all(): df_out["轉換價值"] = (df_out["標的股價(元)"] / df_out["轉換價(元)"] * 100).round(2)
        if "溢價率(%)" not in df_out.columns or df_out["溢價率(%)"].isna().all():
            if "CB收盤價" in df_out.columns and "轉換價值" in df_out.columns:
                df_out["轉換價值"] = df_out["轉換價值"].replace(0, np.nan) 
                df_out["溢價率(%)"] = ((df_out["CB收盤價"] - df_out["轉換價值"]) / df_out["轉換價值"] * 100).round(2)
            else: df_out["溢價率(%)"] = "-"
    if df_cb_info is not None and not df_cb_info.empty and "未償還餘額" in df_out.columns:
        df_cb_info_clean = df_cb_info.rename(columns={"stock_id": "可轉債代號", "bond_id": "可轉債代號", "cb_id": "可轉債代號", "issue_amount": "發行總額", "IssueAmount": "發行總額", "IssuanceAmount": "發行總額", "DueDateOfConversion": "到期日", "maturity_date": "到期日"})
        df_cb_info_clean = df_cb_info_clean.loc[:, ~df_cb_info_clean.columns.duplicated()]
        if "可轉債代號" in df_cb_info_clean.columns:
            df_cb_info_clean['可轉債代號'] = df_cb_info_clean['可轉債代號'].astype(str).str.replace(r'\.0$', '', regex=True).str.replace(',', '', regex=False).str.strip()
            cols_to_merge = ['可轉債代號']
            if "發行總額" in df_cb_info_clean.columns: cols_to_merge.append("發行總額")
            if "到期日" in df_cb_info_clean.columns: cols_to_merge.append("到期日")
            df_out = pd.merge(df_out, df_cb_info_clean[cols_to_merge].drop_duplicates('可轉債代號'), on='可轉債代號', how='left')
            if "發行總額" in df_out.columns:
                df_out["發行總額"] = safe_to_num(df_out["發行總額"], fill_val=np.nan).replace(0, np.nan)
                df_out["未償還比例(%)"] = (df_out["未償還餘額"] / df_out["發行總額"] * 100).round(2)
            else: df_out["未償還比例(%)"] = "缺發行總額"
        else: df_out["未償還比例(%)"] = "缺代號"
    else: df_out["未償還比例(%)"] = "需原始發行總額"
    display_cols = ["日期", "可轉債代號", "可轉債名稱", "CB收盤價", "標的股價(元)", "轉換價(元)", "轉換價值", "溢價率(%)", "未償還餘額", "未償還比例(%)", "到期日"]
    return df_out[[c for c in display_cols if c in df_out.columns]]

def render_clean_html_table(df, title=""):
    if df is None or df.empty:
        if title: st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
        st.warning("此區塊查無數據。")
        return
    text_keywords = ['日期', '分點', '標籤', '週期', '名稱', '姓名', '身份別', '條件', '措施', '診斷', '代號']
    html = ""
    if title: html += f"<div class='section-title'>{title}</div>"
    html += "<div class='table-container'><table><thead><tr>"
    for col in df.columns: html += f"<th>{col}</th>"
    html += "</tr></thead><tbody>"
    for _, row in df.iterrows():
        html += "<tr>"
        for col in df.columns:
            val = row[col]
            align_class = "text-left" if any(k in str(col) for k in text_keywords) else "text-right"
            display_val = "-"
            if pd.notna(val) and str(val).strip() != "" and str(val).strip().lower() != "nan":
                s = str(val).strip()
                if "無本獲利" in s:
                    display_val = f"<span class='profit-warning'>{s}</span>"
                elif "(虧)" in s:
                    clean_num = s.replace("(虧)", "").strip()
                    display_val = f"<span class='loss-warning'>(虧) {clean_num}</span>"
                elif s.startswith("+"):
                    display_val = f"<span class='highlight-red'>{s}</span>"
                elif s.startswith("-") and len(s) > 1 and s[1].isdigit():
                    display_val = f"<span class='highlight-green'>{s}</span>"
                else:
                    try:
                        if "%" in s: display_val = s
                        else:
                            f_val = float(s.replace(',', ''))
                            display_val = f"{f_val:,.2f}" if "." in s else f"{int(f_val):,}"
                    except: display_val = s
            html += f"<td class='{align_class}'>{display_val}</td>"
        html += "</tr>"
    html += "</tbody></table></div>"
    st.markdown(html, unsafe_allow_html=True)

def format_to_csv_string(df, title):
    header = f"▼▼▼ {title} ▼▼▼\n"
    if df is None or df.empty: return header + "此區塊查無數據或無發行紀錄\n"
    return header + df.to_csv(index=False) + "\n"

# ==========================================
# 執行主引擎
# ==========================================
if run_btn:
    if not user_stock_id.strip(): 
        st.warning("請先在上方輸入股票代號！")
        st.stop()

    with st.spinner(f"正在啟動 V60.34 全網防護決策引擎..."):
        name = get_stock_name_v50(user_stock_id)
        if not name: 
            st.error(f"查無股票代號 {user_stock_id} 的基本資料。")
            st.stop()
            
        industry, address = get_company_profile(user_stock_id)
        
        df_p_raw = fetch_finmind_v50("TaiwanStockPrice", (datetime.date.today() - datetime.timedelta(days=700)).strftime("%Y-%m-%d"), user_stock_id)
        if df_p_raw.empty: 
            st.error("查無歷史股價資料。")
            st.stop()
        
        dates = sorted(df_p_raw['date'].unique().tolist(), reverse=True)
        if not dates: st.stop()
            
        max_len = lookback_days if len(dates) >= lookback_days else len(dates)
        if max_len == 0: max_len = 1
        d_end = dates[max_len-1]
        
        df_price = process_price(df_p_raw)
        curr_price = df_price['收盤價(元)'].iloc[0] if not df_price.empty else 0
        df_ta_full = process_technical_analysis(df_price, ma_short, ma_mid, ma_long)
        
        df_lr_channel = process_linear_regression(df_price, lr_days)
        latest_lr_upper = df_lr_channel['LR_Upper'].iloc[-1] if not df_lr_channel.empty else 0.0
        latest_lr_mid = df_lr_channel['LR_Mid'].iloc[-1] if not df_lr_channel.empty else 0.0
        latest_lr_lower = df_lr_channel['LR_Lower'].iloc[-1] if not df_lr_channel.empty else 0.0
        
        pat_data = {}
        if enable_pattern:
            pat_data = process_geometric_patterns(df_price, kline_days, pattern_order, pattern_mode, curr_price)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as bg_executor:
            f_dir = bg_executor.submit(scrape_director_v50, user_stock_id)
            f_ple = bg_executor.submit(scrape_fubon_pledge, df_p_raw, user_stock_id)
            f_blk = bg_executor.submit(scrape_block_v50, user_stock_id, dates)

            df_b_raw, ds_dict, df_cb_info = fetch_heavy_data_smart(user_stock_id, dates, max_len)

            dynamic_dict, s_val, chip_eng, _ = f_dir.result()
            df_p_sum, df_p_det = f_ple.result()
            df_twse, _ = f_blk.result()

        if df_b_raw.empty:
            st.error(f"查無 {user_stock_id} 的分點進出資料，可能為暫停交易或 API 狀態異常，請稍後再試。")
            st.stop()
            
        tags, df_debug_tags = get_v50_intelligence(df_b_raw, df_p_raw, stickiness_threshold, max_len, dates)
        
        df_s_raw = ds_dict.get("TaiwanStockHoldingSharesPer", pd.DataFrame())
        df_s_wide, df_s_unit, df_s_ppl = process_tdcc(df_s_raw)
        
        current_total_shares = df_s_wide['總張數'].iloc[0] if not df_s_wide.empty else 0
        capital_str = f"{current_total_shares / 10000:.2f} 億" if current_total_shares > 0 else "計算中..."
        
        latest_director_holding, holding_src = get_dead_chip_info(dates[0], dead_chip_input, dynamic_dict, s_val, chip_eng)
        director_holding_str = f"{latest_director_holding:.2f}% ({holding_src})" if latest_director_holding > 0 else "無數據"

        dynamic_n, radar_reason = calculate_dynamic_radar_depth(df_b_raw, dates, current_total_shares, df_price)
        pure_vwap, main_force_vol, active_main_branches, core_c_value, core_branch_names = calculate_pure_defense_line(
            df_b_raw, tags, filter_day_trade, current_total_shares, latest_director_holding, dynamic_n
        )
        
        net_3 = get_core_period_net(df_b_raw, dates[:3], core_branch_names)
        net_10 = get_core_period_net(df_b_raw, dates[:10], core_branch_names)
        net_60 = get_core_period_net(df_b_raw, dates[:60] if len(dates)>=60 else dates, core_branch_names)
        
        df_b_diff = process_branch_diff(df_b_raw, dates, firepower_threshold, period_days=10)
        df_b_diff_60 = process_branch_diff(df_b_raw, dates, firepower_threshold, period_days=60)
        
        df_daily_tracker, df_audit_smart = process_v30_daily_tracking(df_b_raw, tags, df_price, df_b_diff, dates, firepower_threshold, period_days=5)
        df_daily_tracker_60, _ = process_v30_daily_tracking(df_b_raw, tags, df_price, df_b_diff_60, dates, firepower_threshold, period_days=60)
        
        df_s_dyn = process_tdcc_dynamic(df_s_wide, df_price, dead_chip_input, dynamic_dict, s_val, chip_eng)
        df_v27_radar, df_debug_math, _ = process_v27_ultimate_radar(df_s_wide, dead_chip_input, dynamic_dict, s_val, df_price, df_b_raw, tags)

        df_combined_display = pd.DataFrame()
        if not df_v27_radar.empty and not df_s_dyn.empty:
            df_v27_clean = df_v27_radar.drop(columns=['大戶原持股(%)', '收盤價(元)'], errors='ignore')
            df_combined_radar = pd.merge(df_s_dyn, df_v27_clean, on=['日期'], how='inner')
            if not df_combined_radar.empty:
                df_combined_radar['終極籌碼診斷'] = df_combined_radar['實戰判定'].astype(str) + " | " + df_combined_radar['專家雷達診斷'].astype(str)
                display_cols = ['日期', '收盤價(元)', '純淨活大戶C_Value(%)', '純淨大戶變動(%)', '總人數變率(%)', '大戶精算門檻', '當沖虛胖(%)', '終極籌碼診斷']
                df_combined_display = df_combined_radar[[c for c in display_cols if c in df_combined_radar.columns]].sort_values('日期', ascending=False).head(8)

        df_margin = process_margin(ds_dict.get("TaiwanStockMarginPurchaseShortSale", pd.DataFrame()))
        df_day_trade = process_day_trading(ds_dict.get("TaiwanStockDayTrading", pd.DataFrame()))
        df_inst = process_inst(ds_dict.get("TaiwanStockInstitutionalInvestorsBuySell", pd.DataFrame()))
        
        df_rev_raw = ds_dict.get("TaiwanStockMonthRevenue", pd.DataFrame())
        df_rev = pd.DataFrame()
        if not df_rev_raw.empty and 'revenue_year' in df_rev_raw.columns:
            df_rev_raw['營收月份'] = df_rev_raw['revenue_year'].astype(str) + "-" + df_rev_raw['revenue_month'].astype(str).str.zfill(2)
            df_rev = df_rev_raw.rename(columns={"revenue":"月營收(百萬元)"})[['營收月份','月營收(百萬元)']].tail(24)
            df_rev['月營收(百萬元)'] = (safe_to_num(df_rev['月營收(百萬元)'])/1000000).round().astype(int)
            df_rev = df_rev.sort_values('營收月份', ascending=False)

        df_b_today = process_branch_v25(df_b_raw, 1, dates, tags, df_p_raw, stickiness_threshold, max_len)
        df_b_prev1 = process_branch_v25(df_b_raw, 1, dates[1:], tags, df_p_raw, stickiness_threshold, max_len)
        df_b_3 = process_branch_v25(df_b_raw, 3, dates, tags, df_p_raw, stickiness_threshold, max_len)
        df_b_10 = process_branch_v25(df_b_raw, 10, dates, tags, df_p_raw, stickiness_threshold, max_len)
        df_b_60 = process_branch_v25(df_b_raw, max_len, dates, tags, df_p_raw, stickiness_threshold, max_len)
        
        df_fut = process_fut_inst(ds_dict.get("TaiwanFuturesInstitutionalInvestors", pd.DataFrame()))
        df_div = process_div(ds_dict.get("TaiwanStockDividend", pd.DataFrame()))
        df_per = process_per(ds_dict.get("TaiwanStockPER", pd.DataFrame()))
        df_disp = process_disp(ds_dict.get("TaiwanStockDispositionSecuritiesPeriod", pd.DataFrame()))
        
        df_cbas_raw = ds_dict.get("TaiwanStockConvertibleBondDailyOverview", pd.DataFrame())
        if not df_cbas_raw.empty and 'cb_id' in df_cbas_raw.columns:
            cb_mask = df_cbas_raw['cb_id'].astype(str).str.replace(',', '', regex=False).str.startswith(user_stock_id)
            df_cbas = process_cbas(df_cbas_raw[cb_mask], curr_price, df_cb_info)
        else:
            df_cbas = pd.DataFrame()
        
        market_cap_str = "計算中..."
        if not df_price.empty and current_total_shares > 0: market_cap_str = f"{(curr_price * current_total_shares) / 100000:,.2f} 億"
            
        company_info_text = f"【產業】 {industry} ｜ 【股本】 {capital_str} ｜ 【市值】 {market_cap_str} ｜ 【公司地址】 {address} ｜ 【董監死籌碼】 {director_holding_str}"
        
        st.subheader(f"{user_stock_id} {name} 全息戰報 (V60.34 防護裝甲版)")
        st.markdown(f"<div class='info-box'>{company_info_text}</div>", unsafe_allow_html=True)

        if not df_ta_full.empty:
            st.markdown(f"<div class='section-title'>高階技術分析 (極緻緊湊版 - {ma_short}/{ma_mid}/{ma_long}極細均線)</div>", unsafe_allow_html=True)
            df_plot = df_price.head(kline_days).copy()
            df_t_plot = df_ta_full[['日期', f'MA{ma_short}', f'MA{ma_mid}(中線)', f'MA{ma_long}(長線)']].head(kline_days).copy()
            df_plot = pd.merge(df_plot, df_t_plot, on='日期', how='inner').sort_values('日期', ascending=True)
            
            df_day_trade_raw = ds_dict.get("TaiwanStockDayTrading", pd.DataFrame())
            if not df_day_trade_raw.empty:
                df_dt_chart = df_day_trade_raw.copy()
                df_dt_chart = df_dt_chart.rename(columns={"date": "日期"})
                vol_col = 'DayTradingVolume' if 'DayTradingVolume' in df_dt_chart.columns else 'Volume'
                if vol_col in df_dt_chart.columns:
                    df_dt_chart['當沖總張數'] = (safe_to_num(df_dt_chart[vol_col]) / 1000).round().astype(int)
                    df_plot = pd.merge(df_plot, df_dt_chart[['日期', '當沖總張數']], on='日期', how='left')
                else:
                    df_plot['當沖總張數'] = 0
            else:
                df_plot['當沖總張數'] = 0
                
            df_plot['當沖總張數'] = df_plot['當沖總張數'].fillna(0)

            if not df_plot.empty:
                lr_data_json = "{}"
                if not df_lr_channel.empty:
                    df_plot = pd.merge(df_plot, df_lr_channel, on='日期', how='left')
                    df_plot_lr = df_plot.dropna(subset=['LR_Upper']).sort_values('日期', ascending=True)
                    lr_data = {
                        "upper": [{"time": str(t), "value": float(v)} for t, v in zip(df_plot_lr['日期'], df_plot_lr['LR_Upper'])],
                        "mid": [{"time": str(t), "value": float(v)} for t, v in zip(df_plot_lr['日期'], df_plot_lr['LR_Mid'])],
                        "lower": [{"time": str(t), "value": float(v)} for t, v in zip(df_plot_lr['日期'], df_plot_lr['LR_Lower'])]
                    }
                    lr_data_json = json.dumps(lr_data)

                pat_js = "[]"
                neck_js = "[]"
                pat_color_js = "'transparent'"
                if pat_data:
                    pat_list = [{"time": str(x), "value": float(y)} for x, y in zip(pat_data['shape_x'], pat_data['shape_y'])]
                    neck_list = [{"time": str(x), "value": float(y)} for x, y in zip(pat_data['neck_x'], pat_data['neck_y'])]
                    pat_list = sorted(pat_list, key=lambda k: k['time'])
                    neck_list = sorted(neck_list, key=lambda k: k['time'])
                    pat_js = json.dumps(pat_list)
                    neck_js = json.dumps(neck_list)
                    pat_color_js = f"'{pat_data.get('color', '#000000')}'"

                time_series = df_plot['日期'].astype(str).tolist()
                kline_data = [
                    {'time': t, 'open': float(o), 'high': float(h), 'low': float(l), 'close': float(c)}
                    for t, o, h, l, c in zip(time_series, df_plot['開盤價(元)'], df_plot['最高價(元)'], df_plot['最低價(元)'], df_plot['收盤價(元)'])
                ]
                
                total_vol_data = [
                    {'time': t, 'value': float(v), 'color': '#E0E3EB'}
                    for t, v in zip(time_series, df_plot['成交量(張)'])
                ]
                day_trade_vol_data = [
                    {'time': t, 'value': float(dtv), 'color': '#FF9800'}
                    for t, dtv in zip(time_series, df_plot['當沖總張數'])
                ]

                def prep_ma(series, times):
                    valid_mask = series.notna()
                    return [{'time': t, 'value': round(float(v), 2)} for t, v, is_valid in zip(times, series, valid_mask) if is_valid]

                ma_data = {
                    "ma_short": prep_ma(df_plot[f'MA{ma_short}'], time_series),
                    "ma_mid": prep_ma(df_plot[f'MA{ma_mid}(中線)'], time_series),
                    "ma_long": prep_ma(df_plot[f'MA{ma_long}(長線)'], time_series)
                }

                html_template = """
                <!DOCTYPE html>
                <html>
                <head>
                    <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
                    <style>
                        body { margin: 0; background: #fff; font-family: sans-serif; display: flex; flex-direction: column; height: 100vh; overflow: hidden;}
                        #chart-main { flex: 3.2; border-bottom: 2px solid #f0f3fa; position: relative; }
                        #chart-vol { flex: 0.8; position: relative;}
                        .legend { position: absolute; top: 4px; left: 8px; z-index: 10; font-size: 13px; pointer-events: none; background: rgba(255,255,255,0.7); padding: 2px 6px; border-radius: 4px; color: #333;}
                    </style>
                </head>
                <body>
                    <div id="chart-main"><div id="legend" class="legend"></div></div>
                    <div id="chart-vol"></div>
                    <script>
                        const kData = KLINE_DATA;
                        const tVol = TOTAL_VOL;
                        const dtVol = DAYTRADE_VOL;
                        const ma = MA_DATA;

                        const commonLocalization = {
                            timeFormatter: businessDayOrTimestamp => {
                                if (businessDayOrTimestamp.year) {
                                    const y = String(businessDayOrTimestamp.year).slice(-2);
                                    const m = String(businessDayOrTimestamp.month).padStart(2, '0');
                                    const d = String(businessDayOrTimestamp.day).padStart(2, '0');
                                    return `${y}/${m}/${d}`;
                                }
                                if (typeof businessDayOrTimestamp === 'string') {
                                    return businessDayOrTimestamp.substring(2).replace(/-/g, '/');
                                }
                                return businessDayOrTimestamp;
                            }
                        };

                        const mainOptions = {
                            autoSize: true,
                            localization: commonLocalization,
                            layout: { background: { color: '#ffffff' }, textColor: '#333' },
                            grid: { vertLines: { color: '#f5f5f5' }, horzLines: { color: '#f5f5f5' } },
                            rightPriceScale: { borderColor: '#eee', autoScale: true, scaleMargins: { top: 0.01, bottom: 0.01 } },
                            timeScale: { visible: false }
                        };

                        const volOptions = {
                            autoSize: true,
                            localization: commonLocalization,
                            layout: { background: { color: '#ffffff' }, textColor: '#333' },
                            grid: { vertLines: { color: '#f5f5f5' }, horzLines: { color: '#f5f5f5' } },
                            rightPriceScale: { borderColor: '#eee', autoScale: true, scaleMargins: { top: 0.02, bottom: 0 } },
                            timeScale: { borderColor: '#eee' }
                        };

                        const mainChart = LightweightCharts.createChart(document.getElementById('chart-main'), mainOptions);
                        const volChart = LightweightCharts.createChart(document.getElementById('chart-vol'), volOptions);

                        const candleSeries = mainChart.addCandlestickSeries({
                            upColor: '#ffffff', borderUpColor: '#000000', wickUpColor: '#000000',
                            downColor: '#000000', borderDownColor: '#000000', wickDownColor: '#000000'
                        });
                        candleSeries.setData(kData);

                        const lineOpt = { lineWidth: 1, lastValueVisible: false, priceLineVisible: false, crosshairMarkerVisible: false };
                        mainChart.addLineSeries({ color: '#ff9800', ...lineOpt }).setData(ma.ma_short);
                        mainChart.addLineSeries({ color: '#2196f3', ...lineOpt }).setData(ma.ma_mid);
                        mainChart.addLineSeries({ color: '#9c27b0', ...lineOpt }).setData(ma.ma_long);

                        const lr = LR_DATA;
                        if (lr && lr.upper && lr.upper.length > 0) {
                            mainChart.addLineSeries({ color: 'rgba(30, 58, 138, 0.4)', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Solid, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }).setData(lr.upper);
                            mainChart.addLineSeries({ color: 'rgba(30, 58, 138, 0.6)', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }).setData(lr.mid);
                            mainChart.addLineSeries({ color: 'rgba(30, 58, 138, 0.4)', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Solid, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }).setData(lr.lower);
                        }

                        const pat = PAT_DATA;
                        const neck = NECK_DATA;
                        const patColor = PAT_COLOR;
                        if (pat && pat.length > 0) {
                            mainChart.addLineSeries({ color: patColor, lineWidth: 2, lineStyle: LightweightCharts.LineStyle.Solid, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }).setData(pat);
                        }
                        if (neck && neck.length > 0) {
                            mainChart.addLineSeries({ color: patColor, lineWidth: 2, lineStyle: LightweightCharts.LineStyle.Dotted, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }).setData(neck);
                        }

                        const totalVolSeries = volChart.addHistogramSeries({ priceFormat: { type: 'volume' } });
                        totalVolSeries.setData(tVol);
                        const dayTradeVolSeries = volChart.addHistogramSeries({ priceFormat: { type: 'volume' } });
                        dayTradeVolSeries.setData(dtVol);

                        const legend = document.getElementById('legend');
                        const updateLegend = (p) => {
                            const d = p.time ? kData.find(x => x.time === p.time) : kData[kData.length-1];
                            const dtData = p.time ? dtVol.find(x => x.time === p.time) : dtVol[dtVol.length-1];
                            if (d && dtData) {
                                const tv = tVol.find(x => x.time === d.time);
                                const tvVal = tv ? tv.value : 0;
                                const shortDate = d.time.substring(2).replace(/-/g, '/');
                                legend.innerHTML = `<b>${shortDate}</b> &nbsp; 開:${d.open} 高:${d.high} 低:${d.low} 收:<span style="color:#000000">${d.close}</span> &nbsp; <span style="color:#888">總量:${Math.round(tvVal)}</span> &nbsp; <span style="color:#FF9800">當沖:${Math.round(dtData.value)}</span>`;
                            }
                        };
                        updateLegend({time: null});

                        mainChart.subscribeCrosshairMove(p => {
                            updateLegend(p);
                            if (p.time) volChart.setCrosshairPosition(0, p.time, totalVolSeries);
                            else volChart.clearCrosshairPosition();
                        });
                        volChart.subscribeCrosshairMove(p => {
                            updateLegend(p);
                            if (p.time) mainChart.setCrosshairPosition(0, p.time, candleSeries);
                            else mainChart.clearCrosshairPosition();
                        });

                        mainChart.timeScale().subscribeVisibleLogicalRangeChange(r => volChart.timeScale().setVisibleLogicalRange(r));
                        volChart.timeScale().subscribeVisibleLogicalRangeChange(r => mainChart.timeScale().setVisibleLogicalRange(r));
                    </script>
                </body>
                </html>
                """
                html_code = html_template.replace("KLINE_DATA", json.dumps(kline_data))\
                                         .replace("TOTAL_VOL", json.dumps(total_vol_data))\
                                         .replace("DAYTRADE_VOL", json.dumps(day_trade_vol_data))\
                                         .replace("MA_DATA", json.dumps(ma_data))\
                                         .replace("LR_DATA", lr_data_json)\
                                         .replace("PAT_DATA", pat_js)\
                                         .replace("NECK_DATA", neck_js)\
                                         .replace("PAT_COLOR", pat_color_js)
                components.html(html_code, height=736)

        st.markdown("<div class='category-title'>AI 全息籌碼深度診斷總結</div>", unsafe_allow_html=True)
        
        bias = ((curr_price - pure_vwap) / pure_vwap * 100) if pure_vwap > 0 else 0
        vwap_str = f"{pure_vwap:,.2f}" if pure_vwap > 0 else "-"
        
        today_smart_net = 0
        today_gap = 0.0
        if not df_daily_tracker.empty:
            today_smart_net = df_daily_tracker.iloc[0].get('聰明錢淨流(張)', 0)
            gap_raw = df_daily_tracker.iloc[0].get('均價落差', 0)
            try: today_gap = float(str(gap_raw).replace('+', '').replace(',', '').strip())
            except: today_gap = 0.0

        today_fp = 1.0
        today_diff_cnt = 0
        if not df_b_diff.empty:
            today_fp = df_b_diff.iloc[0].get('買方火力(倍)', 1.0)
            today_diff_cnt = df_b_diff.iloc[0].get('買賣家數差', 0)

        radar_c_val = 0.0
        radar_chg = 0.0
        c_val_text = "[數據擷取中或不足]"
        chg_text = "[變動率計算中或不足]"
        
        if not df_combined_display.empty:
            try: 
                c_val_raw = df_combined_display.iloc[0].get('純淨活大戶C_Value(%)', 0)
                if str(c_val_raw).strip() == "-":
                    c_val_text = f"{df_combined_display.iloc[0].get('大戶原持股(%)', 0)}% (原始大戶比例)"
                else:
                    radar_c_val = float(str(c_val_raw).replace('+', '').replace(',', '').replace('%', '').strip())
                    c_val_text = f"{radar_c_val}%"
            except: pass
            
            try: 
                radar_chg = float(str(df_combined_display.iloc[0].get('純淨大戶變動(%)', 0)).replace('+', '').replace(',', '').replace('%', '').strip())
                if radar_chg > 0: dir_str = "增加"
                elif radar_chg < 0: dir_str = "減少"
                else: dir_str = "無變動"
                chg_text = f"{dir_str} {abs(radar_chg)}%" if radar_chg != 0 else f"{dir_str} 0.0%"
            except: pass

        if curr_price >= latest_lr_upper and latest_lr_upper > 0: lr_pos_text = "股價已觸碰或突破通道上軌 (極度過熱區)"
        elif curr_price >= latest_lr_mid and latest_lr_mid > 0: lr_pos_text = "股價運行於通道上半部 (強勢多頭區)"
        elif curr_price <= latest_lr_lower and latest_lr_lower > 0: lr_pos_text = "股價已觸碰或跌破通道下軌 (極度超跌區)"
        elif latest_lr_mid > 0: lr_pos_text = "股價運行於通道下半部 (弱勢空頭區)"
        else: lr_pos_text = "通道資料不足"

        report_md = "<div class='ai-report-box'>\n\n"

        report_md += "#### 第零層：幾何形態與結構 (AI 視覺辨識)\n"
        report_md += "<ul>"
        if pat_data:
            report_md += f"<li>【觸發形態】：{pat_data['desc']}。</li>\n"
            if pat_data['signal'] == 'bullish': pat_diag = "圖形結構偏多，若配合聰明錢流入，突破成功率極高。"
            elif pat_data['signal'] == 'bearish': pat_diag = "圖形結構偏空，上檔頸線或壓力沉重，提防假突破真倒貨。"
            else: pat_diag = "圖形面臨收斂末端或箱型邊界，即將表態，請密切觀察突破方向與籌碼跟進狀況。"
            report_md += f"<li>解讀：{pat_diag}</li>"
        else:
            report_md += f"<li>【觸發形態】：目前設定下無明顯標準幾何形態。</li>\n"
            report_md += f"<li>解讀：可嘗試調降「形態辨識靈敏度」或切換為強制鎖定模式以尋找次級波段形態。</li>"
        report_md += "</ul>\n\n"

        report_md += "#### 第一層：長線底盤與動態通道 (防守線與價格重心)\n"
        report_md += "<ul>"
        report_md += f"<li>【防守價與乖離】：系統算出核心主力加權防守價為 {vwap_str} 元。今日收盤價 {curr_price} 元，主力成本乖離率 {bias:.1f}%。</li>\n"
        if latest_lr_upper > 0:
            report_md += f"<li>【線性迴歸通道】：{lr_days}日動態通道上軌 {latest_lr_upper:.2f}，中軌 {latest_lr_mid:.2f}，下軌 {latest_lr_lower:.2f}。</li>\n"
        report_md += f"<li>【核心底單水位】：近60日核心主力淨留倉 {net_60:+,} 張，近10日 {net_10:+,} 張，近3日 {net_3:+,} 張。</li>\n"
        
        if bias >= 10 and net_60 > 0: layer1_diag = f"主力成本乖離達10%以上，為台灣市場波段趨勢啟動特徵，{lr_pos_text}，且長線大戶籌碼鎖定。"
        elif bias >= 0 and net_60 > 0: layer1_diag = f"股價貼近主力成本且{lr_pos_text}，長線大戶默默吸籌，處於安全建倉區。"
        elif bias < 0 and net_60 > 0: layer1_diag = f"股價跌破防守線且{lr_pos_text}，主力帳面出現虧損，進入弱勢防守戰。"
        else: layer1_diag = f"長線大戶無明顯囤貨或呈現淨流出，{lr_pos_text}，底部支撐脆弱。"
        report_md += f"<li>解讀：{layer1_diag}</li>"
        report_md += "</ul>\n\n"

        report_md += "#### 第二層：中線籌碼 (集保大戶與鎖碼流向)\n"
        report_md += "<ul>"
        report_md += f"<li>【大戶真實鎖碼率】：波段大戶吸納了約 {c_val_text} 的市場自由流通籌碼。</li>\n"
        report_md += f"<li>【波段籌碼流向】：排除當沖雜訊後，最新一週波段大戶實質持股 {chg_text}。</li>\n"
        if df_combined_display.empty: layer2_diag = "集保大戶數據不足 (可能為新上市或資料未滿兩週)，無法計算變動率。"
        elif radar_chg >= 1.0: layer2_diag = "中線大戶持續吃貨鎖碼，籌碼集中度顯著提升。"
        elif radar_chg <= -1.0: layer2_diag = "中線大戶出現逢高減碼或倒貨跡象，籌碼流向散戶。"
        else: layer2_diag = "中線大戶籌碼水位無明顯極端變動，處於觀望或盤整。"
        report_md += f"<li>解讀：{layer2_diag}</li>"
        report_md += "</ul>\n\n"

        report_md += "#### 第三層：短線肉搏 (今日聰明錢與散戶對決)\n"
        report_md += "<ul>"
        dir_smart = "淨流入" if today_smart_net > 0 else "淨流出"
        report_md += f"<li>【今日主力動向】：聰明錢今日 {dir_smart} {abs(today_smart_net):,} 張。</li>\n"
        report_md += f"<li>【買賣力道對決】：買方火力 {today_fp} 倍，買賣家數差為 {today_diff_cnt} 家。</li>\n"

        if today_smart_net < 0 and today_diff_cnt > 0: layer3_diag = "聰明錢撤退，且買賣家數差為正(散戶湧入接刀)，標準的主力倒貨特徵。"
        elif today_smart_net > 0 and float(today_fp) >= float(firepower_threshold): layer3_diag = "聰明錢積極買進，且買方火力強大，主力強勢鎖碼推升。"
        elif today_smart_net < 0 and today_diff_cnt <= 0: layer3_diag = "聰明錢流出，但籌碼未發散至散戶手中，偏向特定大戶換手或壓盤洗盤。"
        else: layer3_diag = "短線多空交戰，無極端偏離，屬自然換手。"
        report_md += f"<li>解讀：{layer3_diag}</li>"
        report_md += "</ul>\n\n"

        report_md += "#### 第四層：綜合兵推與最終操作定調\n"
        
        pat_is_breakout = pat_data and pat_data['signal'] == 'bullish' and ('突破' in pat_data['desc'] or '深V' in pat_data['desc'])
        pat_is_breakdown = pat_data and pat_data['signal'] == 'bearish' and ('跌破' in pat_data['desc'] or '衰退' in pat_data['desc'])

        if pat_is_breakdown and today_smart_net < 0:
            conclusion = "【形態轉弱 / 主力撤退，立刻停損】"
            action = f"視覺形態確認跌破或轉弱，且今日聰明錢果斷撤退。技術面與籌碼面雙重轉空，請立刻停損逃命，嚴禁留戀！"
        elif pat_is_breakout and today_smart_net > 0:
            conclusion = "【形態突破 / 主力點火，強勢追擊】"
            action = f"視覺形態確認突破頸線或形成強力反轉，且今日聰明錢大舉淨流入點火。技術面與籌碼面完美共振，此為高勝率買點，請順勢抱緊！"
        elif radar_chg < -1.0 and today_smart_net < -500 and today_diff_cnt > 0:
            conclusion = "【高檔派發 / 趨勢反轉，準備逃命】"
            action = f"中線大戶已在減碼，今日短線聰明錢大舉倒貨給散戶。目前{lr_pos_text}，請忽略長線的靜態支撐，立刻以短線逃命訊號為主，逢高減碼，嚴防接刀多殺多！"
        elif curr_price >= latest_lr_upper and latest_lr_upper > 0 and today_smart_net < 0:
            conclusion = "【通道過熱 / 逢高派發，準備停利】"
            action = f"股價已頂到 {lr_days} 日通道上軌（極度過熱區），且短線聰明錢開始趁高檔撤退。請逢高停利一趟，嚴防主力順勢出貨，切勿在此追高！"
        elif curr_price <= latest_lr_lower and latest_lr_lower > 0 and radar_chg >= 0 and today_smart_net > 0:
            conclusion = "【超跌反轉 / 左側掃貨，絕佳買點】"
            action = f"股價打到 {lr_days} 日通道下軌（極度超跌區），但中線大戶籌碼安定，且今日短線聰明錢大舉淨流入！主力趁暴跌吃貨，此為極具安全邊際的高勝率左側買點。"
        elif radar_chg > 1.0 and today_smart_net > 500 and float(today_fp) > 1.2:
            conclusion = "【強勢推升 / 主力鎖碼，順勢抱緊】"
            action = "中線大戶持續吸籌，今日短線火力全開且聰明錢大舉淨流入。籌碼高度集中於特定主力手中，趨勢呈強勢多頭，沿防守線抱緊，切勿輕易被洗下車。"
        elif net_60 > 0 and today_smart_net < -200 and today_diff_cnt <= 0:
            conclusion = "【高檔震盪 / 壓盤洗盤，觀察防守】"
            action = "長線底單依然穩固，今日雖有聰明錢流出，但散戶並未瘋狂接刀(家數差未極端發散)。偏向主力順勢調節或刻意壓盤洗浮額。請密切關注股價是否能守住加權防守價，未破線前無須恐慌殺出。"
        elif bias < -5.0 and net_60 <= 0 and net_10 <= 0 and net_3 <= 0:
            conclusion = "【兵敗如山 / 全面套牢，嚴禁摸底】"
            action = "股價跌破防守價，且短中長線主力全面大舉倒貨。籌碼與技術面雙雙潰敗，此處的任何反彈都應視為逃命波，嚴禁進場摸底接刀。"
        elif bias < 0 and net_60 > 0 and today_smart_net > 0:
            conclusion = "【破線抵抗 / 逢低護盤，等待站回】"
            action = "股價雖跌破防守價導致主力套牢，但今日見到聰明錢進場抵抗。這顯示主力並未完全放棄，正在嘗試逢低護盤。需確認股價能帶量重新站回防守價，才可視為危機解除。"
        else:
            conclusion = "【籌碼中性 / 多空膠著，靜待表態】"
            action = "目前長、中、短線籌碼動向不一，未出現極端的集中或發散訊號。盤勢由一般市場力量主導，建議縮小部位，靜待主力給出更明確的方向表態。"

        report_md += f"<div class='ai-conclusion'>{conclusion}<br><span style='font-weight:normal; font-size:1.05rem; display:block; margin-top:8px;'>{action}</span></div>\n"
        report_md += "</div>"
        
        st.markdown(report_md, unsafe_allow_html=True)
        st.caption(f"備註：所有數據皆已透過 AI 自動過濾。加權防守價已排除高頻刷量誤差。核心分點控盤率為核心券商佔自由流通籌碼之比例，C_Value 為大戶整體鎖碼率。")

        st.markdown("---")
        actual_foot_days = footprint_days if len(dates) >= footprint_days else len(dates)
        display_dates = dates[:actual_foot_days]
        
        st.markdown("<div class='category-title'>01. 主力分點全息透視區 (全維度折疊展開)</div>", unsafe_allow_html=True)
        st.info("所有分點足跡與明細已集中於此，點擊展開即可查看。表格支援上下左右雙向滑動，直向顯示約 10 行以維持版面整潔。")
        
        df_fb_3, df_fs_3 = process_footprint(df_b_raw, display_dates, dates[:3], tags, df_debug_tags, footprint_rows)
        with st.expander(f"【近 3 日急單動向】 買賣超前 {footprint_rows} 大 (顯示 {actual_foot_days} 日足跡)"):
            render_clean_html_table(df_fb_3, f"【近 3 日急單動向】 近 3 日買超前 {footprint_rows} 大 (顯示 {actual_foot_days} 日足跡)")
            render_clean_html_table(df_fs_3, f"【近 3 日急單動向】 近 3 日賣超前 {footprint_rows} 大 (顯示 {actual_foot_days} 日足跡)")
            
        df_fb_10, df_fs_10 = process_footprint(df_b_raw, display_dates, dates[:10], tags, df_debug_tags, footprint_rows)
        with st.expander(f"【近 10 日波段動向】 買賣超前 {footprint_rows} 大 (顯示 {actual_foot_days} 日足跡)"):
            render_clean_html_table(df_fb_10, f"【近 10 日波段動向】 近 10 日買超前 {footprint_rows} 大 (顯示 {actual_foot_days} 日足跡)")
            render_clean_html_table(df_fs_10, f"【近 10 日波段動向】 近 10 日賣超前 {footprint_rows} 大 (顯示 {actual_foot_days} 日足跡)")
            
        df_fb_60, df_fs_60 = process_footprint(df_b_raw, display_dates, dates[:max_len], tags, df_debug_tags, footprint_rows)
        with st.expander(f"【近 {max_len} 日長線動向】 買賣超前 {footprint_rows} 大 (顯示 {actual_foot_days} 日足跡)"):
            render_clean_html_table(df_fb_60, f"【近 {max_len} 日長線動向】 近 {max_len} 日買超前 {footprint_rows} 大 (顯示 {actual_foot_days} 日足跡)")
            render_clean_html_table(df_fs_60, f"【近 {max_len} 日長線動向】 近 {max_len} 日賣超前 {footprint_rows} 大 (顯示 {actual_foot_days} 日足跡)")

        with st.expander(f"主力分點 - 今日 ({dates[0]})"):
            render_clean_html_table(df_b_today)
        with st.expander(f"主力分點 - 前一日"):
            render_clean_html_table(df_b_prev1)
        with st.expander(f"點此展開過渡期分點 (近3日 / 10日 / {max_len}日總和)"):
            render_clean_html_table(df_b_3, "主力分點 - 近 3 日")
            render_clean_html_table(df_b_10, "主力分點 - 近 10 日")
            render_clean_html_table(df_b_60, f"主力分點 - 近 {max_len} 日")
        with st.expander("主力分點圖鑑 (三維動態檢驗)"):
            render_clean_html_table(df_debug_tags)

        render_clean_html_table(df_daily_tracker, "02. 平日戰情追蹤矩陣 (合併家數差與火力)")
        render_clean_html_table(df_combined_display, "03. 一週集保籌碼雷達 (大戶存量與流量雙解碼)") 

        render_clean_html_table(df_inst, "04. 法人買賣超 (近10天)")
        render_clean_html_table(df_margin, "05. 散戶資券餘額 (近10天)")
        render_clean_html_table(df_day_trade, "06. 現股當沖明細 (近10天)")
        render_clean_html_table(df_fut, "07. 台指期貨三大法人未平倉 (大盤)")

        render_clean_html_table(df_rev, "08. 月營收 (百萬元) (近24個月)")
        
        with st.expander("點此展開集保分級表 (近8週)", expanded=False):
            render_clean_html_table(df_s_unit, "09-1. 集保分級 - 張數表")
            render_clean_html_table(df_s_ppl, "09-2. 集保分級 - 人數表")
            
        render_clean_html_table(df_p_sum, "10. 董監大股東質設總覽")
        with st.expander("點此展開董監大股東質設明細", expanded=False):
            render_clean_html_table(df_p_det, "11. 董監大股東質設明細")
            
        render_clean_html_table(df_twse, "12. 鉅額交易明細 (近3天)")
        render_clean_html_table(df_div, "13. 歷年股利政策 (近5年)")
        render_clean_html_table(df_per, "14. 本益比、淨值比與殖利率")
        render_clean_html_table(df_disp, "15. 處置有價證券狀態")
        render_clean_html_table(df_cbas, "16. CBAS 可轉債數據")

        st.divider()
        st.info("請將下方所需資料複製後貼給 AI 進行深度分析或稽核。")
        with st.expander(f"給 AI 的 V60.34 實戰精華資料包 (CSV格式)", expanded=True):
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
            p1 += f"【核心主力60日淨留倉】: {net_60} 張\n\n"
            
            p1 += format_to_csv_string(df_daily_tracker, "02. 平日戰情追蹤矩陣 (近5日)")
            p1 += format_to_csv_string(df_combined_display.head(4) if not df_combined_display.empty else df_combined_display, "03. 一週集保籌碼雷達 (近4週)")
            p1 += format_to_csv_string(df_inst.head(10) if not df_inst.empty else df_inst, "04. 法人買賣超 (近10天)")
            p1 += format_to_csv_string(df_margin.head(10) if not df_margin.empty else df_margin, "05. 散戶資券餘額 (近10天)")
            p1 += format_to_csv_string(df_day_trade.head(10) if not df_day_trade.empty else df_day_trade, "06. 現股當沖明細 (近10天)")
            p1 += format_to_csv_string(df_fut.head(10) if not df_fut.empty else df_fut, "07. 台指期貨三大法人未平倉 (大盤)")
            p1 += format_to_csv_string(df_rev.head(12) if not df_rev.empty else df_rev, "08. 月營收 (百萬元) (近12個月)")
            p1 += format_to_csv_string(df_p_sum, "10. 董監大股東質設總覽")
            p1 += format_to_csv_string(df_twse, "12. 鉅額交易明細 (近3日)")
            p1 += format_to_csv_string(df_per.head(10) if not df_per.empty else df_per, "14. 本益比、淨值比與殖利率")
            p1 += format_to_csv_string(df_disp, "15. 處置有價證券狀態")
            p1 += format_to_csv_string(df_cbas, "16. CBAS 可轉債數據")
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
