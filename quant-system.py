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
import gc
from io import StringIO
import streamlit.components.v1 as components
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="全息量化系統 (老手盤感升級版)", initial_sidebar_state="expanded")

FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"
GITHUB_MANUAL_URL = "https://raw.githubusercontent.com/tonehsie/stock/refs/heads/main/README.md"

CSS = """
<style>
.table-container { overflow: auto; max-height: 600px; width: 100%; margin-bottom: 25px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding-bottom: 10px; }
.table-container table { width: max-content!important; min-width: 40%; border-collapse: separate!important; border-spacing: 0; font-size: 15px!important; font-family: sans-serif; background-color: #fff; }
.table-container th,.table-container td { white-space: nowrap!important; padding: 10px 12px!important; border-bottom: 1px solid #dee2e6; border-right: 1px solid #dee2e6; vertical-align: middle; }
.table-container th { border-top: 1px solid #dee2e6; word-break: keep-all!important; text-align: center!important; background-color: #f1f3f5!important; color: #333!important; font-weight: 700!important; line-height: 1.4; position: sticky; top: 0; z-index: 3; }
.table-container th:first-child,.table-container td:first-child { position: sticky; left: 0; background-color: #f8f9fa; z-index: 4; font-weight: bold; text-align: center!important; border-left: 1px solid #dee2e6; }
.full-table-container { overflow-x: auto; overflow-y: visible; width: 100%; margin-bottom: 25px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); display: block; padding-bottom: 10px; }
.full-table-container table { width: max-content!important; min-width: 40%; border-collapse: separate!important; border-spacing: 0; font-size: 15px!important; background-color: #fff; }
.full-table-container th,.full-table-container td { white-space: nowrap!important; padding: 10px 12px!important; border-bottom: 1px solid #dee2e6; border-right: 1px solid #dee2e6; }
.full-table-container th { border-top: 1px solid #dee2e6; background-color: #f1f3f5!important; position: sticky; top: 0; z-index: 3; }
.full-table-container th:first-child,.full-table-container td:first-child { position: sticky; left: 0; background-color: #f8f9fa; z-index: 4; }
.text-left { text-align: left!important; }
.text-right { text-align: right!important; font-variant-numeric: tabular-nums; }
.loss-warning { color: #d9480f; font-weight: bold; }
.profit-warning { color: #6a1b9a; font-weight: 900; background-color: #f3e5f5; padding: 3px 6px; border-radius: 4px; border: 1px solid #ce93d8; }
.highlight-red { color: #d32f2f; font-weight: bold; }
.highlight-green { color: #2e7d32; font-weight: bold; }
.info-box { background-color: #f8f9fa; padding: 15px 20px; border-radius: 8px; margin-bottom: 25px; border-left: 6px solid #1e3a8a; font-size: 1.1rem; font-weight: bold; color: #1e3a8a; }
.section-title { margin-top: 35px; margin-bottom: 15px; color: #1e3a8a; border-bottom: 2px solid #1e3a8a; padding-bottom: 5px; font-size: 1.3rem!important; font-weight: 700!important; }
.category-title { font-size: 1.6rem!important; font-weight: 900!important; margin-top: 40px; color: #333; }
.ai-report-box { background-color: #fcfdfe; border: 1px solid #e9ecef; border-left: 5px solid #1e3a8a; border-radius: 8px; padding: 25px; margin-bottom: 30px; line-height: 1.6; }
.ai-conclusion { background-color: #fff3cd; padding: 15px; border-radius: 6px; border: 1px solid #ffe69c; font-weight: 700; color: #856404; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

def optimize_memory(df):
    if df.empty: return df
    for col in df.columns:
        col_type = df[col].dtype
        if col_type == 'float64': df[col] = df[col].astype('float32')
        elif col_type == 'int64': df[col] = df[col].astype('int32')
        elif col_type == 'object':
            if 'trader' in col or '分點' in col or '標籤' in col:
                df[col] = df[col].astype('category')
    return df

@st.cache_resource(max_entries=3)
def get_generic_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.3, status_forcelist=)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

FM_SESSION = get_generic_session()
FM_SESSION.headers.update({"Authorization": f"Bearer {FINMIND_TOKEN}", "User-Agent": "Mozilla/5.0"})
GENERIC_SESSION = get_generic_session()

_num_re = re.compile(r'\d+')
_LEVEL_MAP = {
    1: "1-999股", 2: "1-5張", 3: "5-10張", 4: "10-15張", 5: "15-20張",
    6: "20-30張", 7: "30-40張", 8: "40-50張", 9: "50-100張", 10: "100-200張",
    11: "200-400張", 12: "400-600張", 13: "600-800張", 14: "800-1000張", 15: "1000張以上"
}
_LEVEL_CLEAN_CACHE = {}

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

st.sidebar.markdown("### 交易戰略大腦")
trade_strategy = st.sidebar.radio("交易戰略偏好", ["右側動能 (短線突破)", "左側潛伏 (中長線價值)"])
is_right_side = "右側" in trade_strategy

st.sidebar.header("戰術參數控制面板")
kline_days = st.sidebar.slider("K線顯示天數 (圖表景深)", 30, 600, 270, 10)
lookback_days = st.sidebar.selectbox("長線籌碼回溯天數 (全局黏著度分母)", , index=1)
stickiness_threshold = st.sidebar.slider("主力黏著度門檻 (%)", 10.0, 80.0, 50.0, 5.0)

footprint_stat_days = st.sidebar.select_slider("買賣超排行統計天數", options=, value=10 if is_right_side else 45)
footprint_days = st.sidebar.slider("足跡明細追蹤天數 (顯示範圍)", 3, 90, 20, 1)
footprint_rows = st.sidebar.slider("足跡矩陣顯示筆數 (多空各 N 名)", 5, 50, 15, 5)

st.sidebar.divider()
st.sidebar.markdown("### 視覺系主菜：熱力圖設定")
heatmap_noise_pct = st.sidebar.slider("熱力圖雜訊過濾 (佔20日均量 %)", 0.0, 5.0, 0.5 if is_right_side else 1.0, 0.1)

st.sidebar.divider()
st.sidebar.markdown("### 防禦系配菜：警報器設定")
alert_smart_pct = st.sidebar.slider("警報: 聰明錢極端進出 (佔20日均量 %)", 1.0, 20.0, 10.0 if is_right_side else 5.0, 1.0)
alert_bias_drop = st.sidebar.slider("警報: 跌破主力防守乖離 < (%)", -20.0, 0.0, -3.0, 0.5)

st.sidebar.divider()
firepower_threshold = st.sidebar.slider("買方火力倍數門檻", 1.0, 5.0, 1.5, 0.1)

st.sidebar.divider()
st.sidebar.markdown("### AI 幾何形態與技術線")
enable_pattern = st.sidebar.checkbox("啟動 AI 幾何形態掃描", value=True)

pattern_mode = st.sidebar.selectbox("形態顯示模式",)

lr_days = st.sidebar.slider("線性迴歸通道天數 (動態趨勢)", 20, 120, 20, 5)
pattern_order = st.sidebar.slider("形態辨識靈敏度 (Order)", 2, 20, 5, 1)

st.sidebar.divider()
st.sidebar.markdown("### 淨化籌碼引擎")
filter_day_trade = st.sidebar.checkbox("剔除散戶與當沖，計算純淨加權均價", value=True)
st.sidebar.divider()

ma_short = int(st.sidebar.number_input("短均線 (天)", min_value=1, max_value=20, value=10))
ma_mid = int(st.sidebar.number_input("中均線/防守線 (天)", min_value=20, max_value=100, value=60))
ma_long = int(st.sidebar.number_input("長均線 (天)", min_value=100, max_value=300, value=240))

st.title("全息量化系統 (老手盤感升級版)")
user_count, api_limit = get_api_usage(FINMIND_TOKEN)
usage_text = f" | FinMind 額度: {user_count} / {api_limit}" if user_count is not None else ""
st.caption(f"系統升級：核心重構加入大戶持股甜區篩選、處置股預測及主力成交力防騙線機制。{usage_text}")

with st.expander("點此閱讀【全息量化系統】四大核心模組終極實戰說明書", expanded=False):
    st.markdown(fetch_github_manual(GITHUB_MANUAL_URL), unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])
with col1: 
    user_stock_id = st.text_input("個股代號", value="2330")
with col2: 
    dead_chip_input = st.text_input("死籌碼 % (董監事持股、董監事＋大股東持股，留空自動抓)")
run_btn = st.button("啟動決策引擎", use_container_width=True, key="run_engine")

def safe_to_num(series, fill_val=0):
    if isinstance(series, pd.Series):
        if pd.api.types.is_numeric_dtype(series): return series.fillna(fill_val)
        valid_mask = series.notna()
        converted = pd.Series(fill_val, index=series.index, dtype=float)
        if valid_mask.any():
            cleaned = series[valid_mask].astype(str).str.replace(',', '', regex=False).str.replace('%', '', regex=False).str.replace('＊', '', regex=False).str.replace('*', '', regex=False).str.strip()
            temp_converted = pd.to_numeric(cleaned, errors='coerce')
            converted.loc[valid_mask] = temp_converted.fillna(fill_val)
        return converted
    elif isinstance(series, (int, float)): 
        return series
    else:
        if pd.isna(series): return fill_val
        s_str = str(series).replace(',', '').replace('%', '').replace('＊', '').replace('*', '').strip()
        if not s_str or s_str.lower() in ['nan', 'none', '-', 'y', 'n', 'x', '<na>', 'na', 'null']: return fill_val
        try: return float(s_str)
        except: return fill_val

@st.cache_data(ttl=3600, max_entries=3, show_spinner=False)
def cached_finmind_api_call(url, params_tuple):
    r = FM_SESSION.get(url, params=dict(params_tuple), timeout=20)
    r.raise_for_status() 
    data = r.json().get("data")
    if data is None:
        raise ValueError("FinMind 回傳資料為空")
    return data

@st.cache_data(ttl=86400, max_entries=5, show_spinner=False)
def get_basic_info_finmind(tid):
    name, ind = "未知名稱", "未知產業"
    try:
        url = "https://api.finmindtrade.com/api/v4/data"
        p = {"dataset": "TaiwanStockInfo", "data_id": tid, "start_date": "2000-01-01"}
        data = cached_finmind_api_call(url, tuple(sorted(p.items())))
        if data:
            df = pd.DataFrame(data)
            if not df.empty:
                if 'stock_name' in df.columns: name = df['stock_name'].iloc
                if 'industry_category' in df.columns: ind = df['industry_category'].iloc
    except: pass
    return name, ind

@st.cache_data(ttl=3600, max_entries=3, show_spinner=False)
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

@st.cache_data(ttl=3600, max_entries=3, show_spinner=False)
def fetch_heavy_data_sync_with_progress(user_stock_id, dates_tuple, max_len):
    dates = list(dates_tuple) 
    b_results =
    a_results = {}
    cb_info_list =

    tdcc_sd = (datetime.date.today() - datetime.timedelta(days=180)).strftime("%Y-%m-%d")
    d_end = dates[max_len-1] if max_len > 0 else dates
    dt_sd = (datetime.date.today() - datetime.timedelta(days=700)).strftime("%Y-%m-%d")

    api_targets =, None, None)
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
            return dataset,

    def fetch_branch(d, tid):
        url = "https://api.finmindtrade.com/api/v4/data"
        p = {"dataset": "TaiwanStockTradingDailyReport", "data_id": tid, "start_date": d, "end_date": d}
        try:
            return cached_finmind_api_call(url, tuple(sorted(p.items())))
        except:
            return

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
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
            text_container.markdown(f"<div class='progress-text'>⚡ 系統載入中... 正在與 FinMind 同步資料 (進度: {completed} / {total_tasks})</div>", unsafe_allow_html=True)

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
                cb_futures =
                for f in concurrent.futures.as_completed(cb_futures):
                    _, cb_data = f.result()
                    if cb_data: cb_info_list.extend(cb_data)

    prog_container.empty()
    text_container.empty()

    df_b = optimize_memory(pd.DataFrame.from_records(b_results)) if b_results else pd.DataFrame()
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
                tc_dir = next((c for c in df.columns if '董監' in str(c) and '持股' in str(c).replace(' ', '')), None)
                tc_large = next((c for c in df.columns if '大股東' in str(c) and '持股' in str(c).replace(' ', '')), None)
                mc = next((c for c in df.columns if '月別' in str(c)), None)
                
                if mc and (tc_dir or tc_large):
                    lt = 0.0
                    for ro in df.to_dict('records'):
                        m = str(ro.get(mc, '')).replace('/', '-').strip()
                        if re.match(r'^\d{4}-\d{2}$', m):
                            v_dir = str(ro.get(tc_dir, '0')).replace(',', '').strip() if tc_dir else '0'
                            v_large = str(ro.get(tc_large, '0')).replace(',', '').strip() if tc_large else '0'
                            try:
                                val_dir = float(v_dir) if v_dir not in ['-', '', 'nan'] else 0.0
                                val_large = float(v_large) if v_large not in ['-', '', 'nan'] else 0.0
                                val = val_dir + val_large
                                if 0 < val < 100:
                                    dd[m] = val
                                    if lt == 0.0: lt = val
                            except: pass
                    if dd: return dd, lt, "Goodinfo(含大股東)",
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
                        title = re.sub(r'<[^>]+>', '', tds).strip()
                        name = re.sub(r'<[^>]+>', '', tds[1]).strip()
                        r_str = re.sub(r'<[^>]+>', '', tds[2]).replace('%', '').strip()
                        if ('董' in title or '監' in title) and '辭' not in title and '職稱' not in title:
                            try: ed[name.split('-').strip()] = max(ed.get(name.split('-').strip(), 0), float(r_str))
                            except: pass
                if 0 < sum(ed.values()) < 100: return {}, round(sum(ed.values()), 2), "富邦精算(備援)",
    except: pass
    return {}, 0.0, "雙引擎皆失敗(請手動)",

def get_dead_chip_info(ds, dci, dd, sv, ce):
    if dci and str(dci).strip()!= "":
        try: return float(str(dci).replace('%', '').strip()), "手動輸入"
        except: pass
    mk = str(ds)[:7].replace('/', '-')
    if dd and mk in dd: return dd[mk], f"{ce}當月"
    if dd: return list(dd.values()), f"{ce}最新"
    return (sv, ce) if sv > 0 else (0.0, "缺數據")

def extract_fubon_table(ht, trg, cols):
    si = ht.find(trg)
    if si == -1: return
    fh = ht[max(0, si - 500) : si + 35000]
    trs = re.compile(r'<tr[^>]*>(*?)</tr>', re.IGNORECASE).findall(fh)
    tdp = re.compile(r'<t[dh][^>]*>(*?)</t[dh]>', re.IGNORECASE)
    out, ist =, False
    for tr in trs:
        tds = tdp.findall(tr)
        if tds:
            r = [re.sub(r'<[^>]+>', '', td).replace('&nbsp;', '').replace(' ', '').replace('\r', '').replace('\n', '').strip() for td in tds]
            if trg in "".join(r): ist = True
            elif ist and len(r) >= cols:
                if r == "" or "註" in r: ist = False
                else: out.append(r[:cols])
    return out

@st.cache_data(ttl=3600, max_entries=3, show_spinner=False)
def scrape_fubon_pledge(df_pr, tid):
    alld =
    for i in range(3):
        html = safe_get_fubon(f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zc0/zc06_{tid}_{i}.djhtm")
        if html:
            p = extract_fubon_table(html, "設質人身", 7)
            if p: alld.extend(p)
    if not alld: return pd.DataFrame(), pd.DataFrame()
    sn, uq = set(),
    for r in alld:
        if "|".join(r) not in sn: 
            sn.add("|".join(r))
            uq.append(r)
    df_all = pd.DataFrame(uq, columns=["日期", "身份別", "姓名", "設質(張)", "解質(張)", "累積質設(張)", "質權人"])
    cy, cm, py, pm = datetime.datetime.now().year, datetime.datetime.now().month, datetime.datetime.now().year, 99
    pdts =
    for ds in df_all['日期']:
        if len(ds) == 5 and '/' in ds: 
            m = int(ds.split('/'))
            if pm == 99: py = cy - 1 if m > cm + 1 and cm < 3 else cy
            elif m > pm + 1: py -= 1
            pm = m
            pdts.append(f"{py}-{ds.replace('/', '-')}")
        elif len(ds) >= 7 and '/' in ds: 
            pts = ds.split('/')
            py, pm = int(pts) + 1911, int(pts[1])
            pdts.append(f"{py}-{pts.[1]strip()}-{pts.[3]strip()}")
        else: pdts.append(ds)
    df_all['日期'] = pdts
    
    for c in ["設質(張)", "解質(張)", "累積質設(張)"]: 
        df_all[c] = safe_to_num(df_all[c]).astype(int)
        
    prd = {pd.to_datetime(r['date']).strftime('%Y-%m-%d'): r['close'] for _, r in df_pr.iterrows()}
    pps, mcs =,
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
    
    vol_col = 'Trading_Volume' if 'Trading_Volume' in df_p_raw.columns else 'Trading_volume'
    if vol_col in df_p_raw.columns:
        avg_vol_lots = (pd.to_numeric(df_p_raw[vol_col], errors='coerce').head(20).mean()) / 1000
    else:
        avg_vol_lots = 3000
    if pd.isna(avg_vol_lots) or avg_vol_lots <= 0: avg_vol_lots = 3000

    scale = max(0.2, min(20.0, avg_vol_lots / 3000.0))
    t_50 = max(10, int(50 * scale))
    t_100 = max(20, int(100 * scale))
    t_200 = max(40, int(200 * scale))
    t_300 = max(60, int(300 * scale))

    df_p['actual_spread'] = df_p['close'] - df_p['close'].shift(-1).fillna(df_p['close'])
    range_diff = df_p['max'] - df_p['min']
    df_p['pos'] = 0.5 
    cond_normal = range_diff > 0
    df_p.loc[cond_normal, 'pos'] = (df_p['close'] - df_p['min']) / range_diff
    df_p.loc[(~cond_normal) & (df_p['actual_spread'] > 0), 'pos'] = 1.0
    df_p.loc[(~cond_normal) & (df_p['actual_spread'] < 0), 'pos'] = 0.0
    
    pos_dict = df_p.set_index('date')['pos'].to_dict()
    latest_close = df_p['close'].iloc if not df_p.empty else 0

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
    
    cond_heavy = g['net_20d'].abs() >= t_300
    cond_lock = (g['net_60d'] >= t_200) & (g['net_20d'] >= t_100) & (g['net_5d'] >= t_50)
    cond_cover = (g['net_60d'] <= -t_100) & (g['net_5d'] >= t_200)
    cond_profit = (g['net_60d'] >= t_300) & (g['net_20d'] >= t_100) & (g['net_5d'] <= -t_100)
    cond_exit = (g['net_60d'] <= -t_200) & (g['net_20d'] <= -t_100) & (g['net_5d'] <= -t_100)
    cond_snap = (g['net_60d'].between(-t_200, t_200)) & (g['net_20d'].between(-t_200, t_200)) & (g['net_5d'] >= t_300)
    cond_maker = g['stickiness'] >= stick_thresh
    cond_follow = (g['stickiness'] < 10.0) & (g['net_5d'].abs() > t_50)

    g['tag'] = np.select(
        [cond_heavy, cond_lock, cond_cover, cond_profit, cond_exit, cond_snap, cond_maker, cond_follow],
        ["主力重砲", "波段鎖碼", "認錯回補", "獲利調節", "棄守提款", "隔日突擊", "避險造市", "跟風小戶"],
        default="路人雜訊"
    )

    tags = g['tag'].to_dict()
    g = g[(g['tb_shares'] > 0) | (g['ts_shares'] > 0)].copy()
    
    cond_loss = (g['avg_b'] > latest_close) & (g['avg_b'] > 0) & (g['net_shares'] > 0)
    b_strs = g['avg_b'].apply(lambda x: f"{x:,.2f}" if x > 0 else "-")
    g['b_str'] = np.where(cond_loss, "(亏) " + b_strs, b_strs)
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
    if df_b_raw.empty: return 0.0, 0, 0, 0.0,
    df = df_b_raw.copy()
    df['tag'] = df['securities_trader'].map(tags).fillna("路人雜訊")
    
    if is_filter_active: 
        valid_df = df[~df['tag'].str.contains("隔日突擊|跟風小戶|棄守提款|避險造市", na=False)].copy()
    else: 
        valid_df = df

    if valid_df.empty: return 0.0, 0, 0, 0.0,
    
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
    
    if top_buyers.empty: return 0.0, 0, 0, 0.0,
    
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

def process_price(df):
    if df.empty: return pd.DataFrame()
    df_out = df.copy()
    
    for col in ["close", "open", "max", "min", "spread"]:
        if col in df_out.columns: 
            df_out[col] = safe_to_num(df_out[col])
            
    if 'Trading_Volume' in df_out.columns: df_out['成交量(張)'] = (safe_to_num(df_out) / 1000).round().astype(int)
    elif 'Trading_volume' in df_out.columns: df_out['成交量(張)'] = (safe_to_num(df_out) / 1000).round().astype(int)
    else: df_out['成交量(張)'] = 0
    
    df_out = df_out.rename(columns={"date":"日期","close":"收盤價(元)","spread":"漲跌(元)","open":"開盤價(元)","max":"最高價(元)","min":"最低價(元)"})
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]
    
    df_out["斷頭價(0.78)"] = (df_out["收盤價(元)"] * 0.78).round(2)
    cols_to_keep = ['日期','成交量(張)','開盤價(元)','最高價(元)','最低價(元)','收盤價(元)','漲跌(元)','斷頭價(0.78)']
    return df_out[[c for c in cols_to_keep if c in df_out.columns]].sort_values('日期', ascending=False)

def detect_orderbook_spoofing(order_book_tick, trade_tick):
    total_ask_vol = sum([order_book_tick.get(f'ask_vol_{i}', 0) for i in range(1, 6)])
    total_bid_vol = sum([order_book_tick.get(f'bid_vol_{i}', 0) for i in range(1, 6)])
    
    if total_ask_vol > total_bid_vol * 1.5:
        if trade_tick.get('trade_type') == 'inside': return "短線偏空：賣方主動讓價，買盤被動承接"
        elif trade_tick.get('cancel_rate_ask', 0) > 0.8: return "誘空假牆：上方大單頻繁撤單，準備向上突圍"
            
    if total_bid_vol > total_ask_vol * 1.5:
        if trade_tick.get('trade_type') == 'outside': return "短線偏多：買方主動吃價，賣盤被動成交"
        elif trade_tick.get('cancel_rate_bid', 0) > 0.8: return "誘多假牆：下方大單為虛假支撐，慎防破底"
    return "結構正常"

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

    html_parts = ["""
    <style>
 .heatmap-wrapper.noise-cell { background-color: transparent!important; }
 .heatmap-wrapper.noise-cell span { display: none; }
    #heatmap-toggle:checked ~.heatmap-wrapper.noise-cell { background-color: var(--bg-color)!important; }
    #heatmap-toggle:checked ~.heatmap-wrapper.noise-cell span { display: inline; color: var(--txt-color)!important; text-shadow: 1px 1px 2px rgba(0,0,0,0.6); }
    #heatmap-toggle:checked ~.heatmap-wrapper.noise-cell.val-zero span { text-shadow: none!important; }
 .heatmap-toggle-label { display: inline-block; margin-bottom: 12px; padding: 6px 12px; background-color: #f1f3f5; border-radius: 6px; border: 1px solid #ccc; cursor: pointer; font-weight: bold; color: #1e3a8a; user-select: none; }
    #heatmap-toggle:checked +.heatmap-toggle-label { background-color: #e3f2fd; border-color: #90caf9; }
    </style>
    <input type="checkbox" id="heatmap-toggle" style="display: none;">
    <label for="heatmap-toggle" class="heatmap-toggle-label">👁️ 切換顯示：所有隱藏數值 (含 0 與雜訊)</label>
    <div class='full-table-container heatmap-wrapper'><table><thead><tr>
    """]
    html_parts.append("<th style='min-width: 140px; position: sticky; left: 0; z-index: 6;'>分點名稱</th>")
    html_parts.append("<th style='min-width: 100px; position: sticky; left: 140px; z-index: 6;'>標籤</th>")
    for d in display_dates:
        html_parts.append(f"<th style='text-align: center; font-size: 13px; min-width: 50px;'>{d[5:]}</th>")
    html_parts.append("</tr></thead><tbody>")

    for trader in target_traders:
        html_parts.append("<tr>")
        tag = intel_tags.get(trader, "路人雜訊")
        html_parts.append(f"<td style='position: sticky; left: 0; background-color: #f8f9fa; z-index: 4; font-weight: bold;'>{trader}</td>")
        html_parts.append(f"<td style='position: sticky; left: 140px; background-color: #f8f9fa; z-index: 4;'>{tag}</td>")

        for d in display_dates:
            val = p.at[trader, d]
            is_noise = abs(val) < noise_threshold
            alpha = min(1.0, 0.2 + 0.8 * (abs(val) / max_val)) if max_val > 0 else 0.2
            
            if val > 0: bg, txt, txt_color, zero_class = f"rgba(229, 57, 53, {alpha:.2f})", f"+{val}", "#fff", ""
            elif val < 0: bg, txt, txt_color, zero_class = f"rgba(67, 160, 71, {alpha:.2f})", str(val), "#fff", ""
            else: bg, txt, txt_color, zero_class = "transparent", "0", "#aaa", "val-zero"
            if val == 0: is_noise = True 

            cell_class = f"noise-cell {zero_class}".strip() if is_noise else ""
            cell_style = f"--bg-color: {bg}; --txt-color: {txt_color}; text-align: center; font-weight: bold; "
            if not is_noise: cell_style += f"background-color: {bg}; color: {txt_color}!important; text-shadow: 1px 1px 2px rgba(0,0,0,0.6);"
            else: cell_style += "background-color: transparent;"

            tooltip = f"日期: {d} | 分點: {trader} | 淨額: {val} 張"
            html_parts.append(f"<td class='{cell_class}' style='{cell_style}' title='{tooltip}'><span>{txt}</span></td>")

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
    
    if not target_traders: return
    df_vp = df_rank[(df_rank['securities_trader'].isin(target_traders)) & (df_rank['price'] > 0)].copy()
    if df_vp.empty: return

    df_vp['buy_lots'] = df_vp['buy'] / 1000
    df_vp['sell_lots'] = df_vp['sell'] / 1000

    min_p, max_p = df_vp['price'].min(), df_vp['price'].max()
    if min_p == max_p:
        df_vp['price_bin'] = f"{min_p:.2f}"
    else:
        bin_edges = np.linspace(min_p, max_p, num=16)
        labels = [f"{bin_edges[i]:.2f} - {bin_edges[i+1]:.2f}" for i in range(len(bin_edges)-1)]
        df_vp['price_bin'] = pd.cut(df_vp['price'], bins=bin_edges, labels=labels, include_lowest=True)

    vp_grouped = df_vp.groupby('price_bin', observed=False)[['buy_lots', 'sell_lots']].sum().fillna(0)
    vp_grouped['total_lots'] = vp_grouped['buy_lots'] + vp_grouped['sell_lots']
    vp_grouped['net_lots'] = vp_grouped['buy_lots'] - vp_grouped['sell_lots']
    if vp_grouped['total_lots'].sum() == 0: return

    poc_idx = vp_grouped['total_lots'].idxmax()
    max_vol = max(1, vp_grouped[['buy_lots', 'sell_lots']].max().max())

    html_parts = ["<div class='full-table-container'><table><thead><tr>"]
    html_parts.extend(["<th style='width: 20%;'>價位區間 (元)</th>", "<th style='width: 35%; text-align: left;'>買進量 (大戶建倉)</th>", "<th style='width: 35%; text-align: left;'>賣出量 (大戶倒貨)</th>", "<th style='width: 10%; text-align: right;'>淨買賣(張)</th></tr></thead><tbody>"])

    vp_grouped = vp_grouped.sort_index(ascending=False)

    for idx, row in vp_grouped.iterrows():
        if row['total_lots'] == 0: continue
        b_vol, s_vol, n_vol = int(round(row['buy_lots'])), int(round(row['sell_lots'])), int(round(row['net_lots']))
        b_width, s_width = min(100, (b_vol / max_vol) * 100), min(100, (s_vol / max_vol) * 100)
        is_poc = (idx == poc_idx)
        row_bg = "background-color: rgba(255, 193, 7, 0.15);" if is_poc else ""
        poc_star = " <br><span style='color:#f57c00; font-size:12px; font-weight:900;'>[POC 核心防守]</span>" if is_poc else ""

        html_parts.append(f"<tr style='{row_bg}'><td style='font-weight: bold; font-size:14px;'>{idx}{poc_star}</td>")
        html_parts.append(f"<td><div style='display: flex; align-items: center;'><div style='width: {b_width}%; background-color: #e53935; height: 18px; border-radius: 2px; margin-right: 8px;'></div><span style='font-size: 13px; font-weight:bold;'>{b_vol:,}</span></div></td>")
        html_parts.append(f"<td><div style='display: flex; align-items: center;'><div style='width: {s_width}%; background-color: #43a047; height: 18px; border-radius: 2px; margin-right: 8px;'></div><span style='font-size: 13px; font-weight:bold;'>{s_vol:,}</span></div></td>")
        net_color, net_txt = ("#d32f2f", f"+{n_vol:,}") if n_vol > 0 else ("#2e7d32", f"{n_vol:,}") if n_vol < 0 else ("", "")
        html_parts.append(f"<td style='color: {net_color}; font-weight: bold; text-align: right;'>{net_txt}</td></tr>")
        
    html_parts.append("</tbody></table></div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)

def render_institutional_vs_local(df_branch_raw, df_inst, intel_tags, top_n=4):
    if df_branch_raw.empty or df_inst.empty: return
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
    
    html_parts = ["<div class='full-table-container'><table><thead><tr>"]
    html_parts.extend(["<th style='position: sticky; left: 0; z-index: 6;'>日期</th>", "<th style='text-align: right; background-color: #f1f3f5;'>外資(張)</th>", "<th style='text-align: right; background-color: #f1f3f5;'>投信(張)</th>"])
    for tb in top_branches: html_parts.append(f"<th style='text-align: right;'>{tb}<br><span style='font-size:11px; color:#1e3a8a;'>{intel_tags.get(tb, '路人')[:4]}</span></th>")
    html_parts.append("<th style='text-align: center; background-color: #e3f2fd;'>聯合作戰診斷</th></tr></thead><tbody>")
    
    for _, row in df_inst.iterrows():
        d, f_net, i_net = row['日期'], row.get('外資買賣超(張)', 0), row.get('投信買賣超(張)', 0)
        html_parts.append(f"<tr><td style='position: sticky; left: 0; background-color: #f8f9fa; z-index: 4; font-weight:bold; text-align:center;'>{d[5:]}</td>")
        
        def fmt_net(val): return f"<span style='color:#d32f2f; font-weight:bold;'>+{val:,}</span>" if val > 0 else f"<span style='color:#2e7d32; font-weight:bold;'>{val:,}</span>" if val < 0 else "<span style='color:#bbb;'>0</span>"
            
        html_parts.extend([f"<td style='text-align:right; background-color: #fdfdfd;'>{fmt_net(f_net)}</td>", f"<td style='text-align:right; background-color: #fdfdfd;'>{fmt_net(i_net)}</td>"])
        
        local_net_sum = 0
        for tb in top_branches:
            val = p_pivot.at[d, tb] if d in p_pivot.index and tb in p_pivot.columns else 0
            local_net_sum += val
            html_parts.append(f"<td style='text-align:right;'>{fmt_net(val)}</td>")
            
        inst_sum = f_net + i_net
        if inst_sum > 0 and local_net_sum > 0: diag, bg, color = "土洋共擊", "rgba(229, 57, 53, 0.15)", "#c62828"
        elif inst_sum < 0 and local_net_sum < 0: diag, bg, color = "多殺多撤退", "rgba(67, 160, 71, 0.15)", "#2e7d32"
        elif inst_sum > 0 and local_net_sum < 0: diag, bg, color = "法人接盤", "transparent", "#555"
        elif inst_sum < 0 and local_net_sum > 0: diag, bg, color = "地方硬扛", "transparent", "#555"
        else: diag, bg, color = "休兵盤整", "transparent", "#aaa"
            
        html_parts.append(f"<td style='text-align:center; background-color:{bg}; color:{color}; font-weight:bold; font-size:13px;'>{diag}</td></tr>")
        
    html_parts.append("</tbody></table></div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)

def process_footprint(df_raw, display_dates, rank_dates, intel_tags, df_fingerprint, top_n):
    if df_raw.empty or not display_dates or not rank_dates: return pd.DataFrame(), pd.DataFrame()
    df_rank = df_raw[df_raw['date'].isin(rank_dates)].copy()
    df_rank['net_shares'] = df_rank['buy'] - df_rank['sell']
    rank_sum = (df_rank.groupby('securities_trader')['net_shares'].sum() / 1000).round().astype(int)
    
    top_b_names = rank_sum[rank_sum > 0].nlargest(top_n).index.tolist()
    top_s_names = rank_sum[rank_sum < 0].nsmallest(top_n).index.tolist()
    
    df_disp = df_raw[df_raw['date'].isin(display_dates)].copy()
    if df_disp.empty: return pd.DataFrame(), pd.DataFrame()
    df_disp['net_shares'] = df_disp['buy'] - df_disp['sell']
    p = df_disp.groupby(['securities_trader', 'date'])['net_shares'].sum().reset_index()
    p['net'] = (p['net_shares'] / 1000).round().astype(int)
    p = p.pivot(index='securities_trader', columns='date', values='net').fillna(0).astype(int)
    p = p.reindex(columns=display_dates, fill_value=0)
    
    fp_dict = df_fingerprint.set_index('分點名稱')[['黏著度(%)', '囤出貨率(%)']].to_dict('index') if not df_fingerprint.empty else {}
    
    def build_df(traders, is_sell=False):
        out =
        for t in traders:
            row_dict = {
                "分點名稱": t, "標籤": intel_tags.get(t, "路人雜訊"),
                "黏著度(%)": fp_dict.get(t, {}).get('黏著度(%)', "-"),
                "出貨率(%)" if is_sell else "囤貨率(%)": fp_dict.get(t, {}).get('囤出貨率(%)', "-"),
                "區間累計(張)": f"+{rank_sum.get(t, 0)}" if rank_sum.get(t, 0) > 0 else str(rank_sum.get(t, 0))
            }
            for i, d in enumerate(display_dates):
                v = p.at[t, d] if t in p.index and d in p.columns else 0
                row_dict = f"+{v}" if v > 0 else str(v)
            out.append(row_dict)
        return pd.DataFrame(out)

    return build_df(top_b_names, False), build_df(top_s_names, True)

def process_branch_v25(df_raw, period, actual_dates, intel_tags, df_price_raw, stick_thresh, global_days):
    try:
        if df_raw.empty or df_price_raw.empty: return pd.DataFrame()
        latest_close = df_price_raw.sort_values('date', ascending=False)['close'].iloc
        df = df_raw[df_raw['date'].isin(actual_dates[:period])].copy()
        if df.empty: return pd.DataFrame()
        
        df['valid_buy'] = np.where(df['price'] > 0, df['buy'], 0)
        df['valid_sell'] = np.where(df['price'] > 0, df['sell'], 0)
        df['ba'], df['sa'] = df['valid_buy'] * df['price'], df['valid_sell'] * df['price']
        
        g = df.groupby('securities_trader').agg(bv=('buy', 'sum'), sv=('sell', 'sum'), vbv=('valid_buy', 'sum'), vsv=('valid_sell', 'sum'), ba=('ba', 'sum'), sa=('sa', 'sum')).reset_index()
        g['net'] = round((g['bv'] - g['sv']) / 1000).astype(int)
        g['avg_b'] = (g['ba'] / g['vbv'].replace(0, np.nan)).fillna(0)
        g['avg_s'] = (g['sa'] / g['vsv'].replace(0, np.nan)).fillna(0)
        
        b = g[g['net'] > 0].sort_values('net', ascending=False).head(15).reset_index(drop=True)
        s = g[g['net'] < 0].sort_values('net', ascending=True).head(15).reset_index(drop=True)
        out, tv =, round(g['bv'].sum() / 1000) if g['bv'].sum() > 0 else 1
        
        for i in range(15):
            r = {}
            if i < len(b): 
                b_str = f"{round(b.loc[i,'avg_b'], 2):,.2f}" if b.loc[i,'avg_b'] > 0 else "-"
                if b.loc[i,'avg_b'] > latest_close and b.loc[i,'avg_b'] > 0 and b.loc[i,'net'] > 0: b_str = f"(虧) {b_str}"
                raw_tag = intel_tags.get(b.loc[i,'securities_trader'], '路人雜訊')
                attr = "短線" if any(x in raw_tag for x in ["隔日突擊", "跟風小戶"]) else "中長線" if any(x in raw_tag for x in ["波段鎖碼", "避險造市", "主力重砲"]) else "波段"
                r["買超分點"], r["買_標籤"], r["買_週期"], r["買超(張)"], r["買均價"], r["佔比"] = b.loc[i,'securities_trader'], raw_tag, attr, int(b.loc[i,'net']), b_str, f"{(b.loc[i,'net']/tv)*100:.1f}%" if tv > 0 else "-"
            else: r["買超分點"], r["買_標籤"], r["買_週期"], r["買超(張)"], r["買均價"], r["佔比"] = "-", "-", "-", 0, "-", "-"
            
            if i < len(s): 
                raw_tag_s = intel_tags.get(s.loc[i,'securities_trader'], '路人雜訊')
                attr_s = "短線" if any(x in raw_tag_s for x in ["隔日突擊", "跟風小戶"]) else "中長線" if any(x in raw_tag_s for x in ["波段鎖碼", "避險造市", "主力重砲"]) else "波段"
                r["賣超分點"], r["賣_標籤"], r["賣_週期"], r["賣超(張)"], r["賣均價"], r["佔比_"] = s.loc[i,'securities_trader'], raw_tag_s, attr_s, abs(int(s.loc[i,'net'])), f"{round(s.loc[i,'avg_s'], 2):,.2f}" if s.loc[i,'avg_s'] > 0 else "-", f"{(abs(s.loc[i,'net'])/tv)*100:.1f}%" if tv > 0 else "-"
            else: r["賣超分點"], r["賣_標籤"], r["賣_週期"], r["賣超(張)"], r["賣均價"], r["佔比_"] = "-", "-", "-", 0, "-", "-"
            out.append(r)
        return pd.DataFrame(out)
    except Exception: return pd.DataFrame()

def get_smart_threshold(price, total_lots, dead_float):
    if pd.isna(price) or price <= 0: return 1000 
    base_lots = 15000 / price
    safe_dead_ratio = max(0.0, min(99.9, dead_float))
    free_float_ratio = max(0.05, (100 - safe_dead_ratio) / 100) 
    float_1pct_lots = total_lots * free_float_ratio * 0.01
    raw_threshold = max(100, min(1000, min(base_lots, float_1pct_lots)))
    levels = 
    return min(levels, key=lambda x: abs(x - raw_threshold))

def process_branch_diff(df_raw, actual_dates, fire_thresh, period_days=10):
    if df_raw.empty or not actual_dates: return pd.DataFrame()
    out =
    branch_grouped = dict(tuple(df_raw[['date', 'securities_trader', 'buy', 'sell']].groupby('date')))
    for d in actual_dates[:period_days]:
        if d not in branch_grouped: continue
        df_d = branch_grouped[d]
        daily_total_vol = df_d['buy'].sum()
        if daily_total_vol == 0: continue
        
        buy_branches, sell_branches = df_d[df_d['buy'] > 0], df_d[df_d['sell'] > 0]
        buy_count, sell_count = buy_branches['securities_trader'].nunique(), sell_branches['securities_trader'].nunique()
        diff_count = buy_count - sell_count
        active_count = df_d[(df_d['buy'] > 0) | (df_d['sell'] > 0)]['securities_trader'].nunique()
        concentration = ((sell_count - buy_count) / active_count * 100) if active_count > 0 else 0
        
        total_buy_vol, total_sell_vol = buy_branches['buy'].sum(), sell_branches['sell'].sum()
        avg_b = total_buy_vol / buy_count if buy_count > 0 else 0
        avg_s = total_sell_vol / sell_count if sell_count > 0 else 0
        firepower = (avg_b / avg_s) if avg_s > 0 else (99.9 if avg_b > 0 else 1.0)
        
        g_net = df_d.groupby('securities_trader').apply(lambda x: x['buy'].sum() - x['sell'].sum())
        top_15_buy_vol = g_net[g_net > 0].nlargest(15).sum()
        top_15_sell_vol = abs(g_net[g_net < 0].nsmallest(15).sum())
        main_power = (top_15_buy_vol - top_15_sell_vol) / daily_total_vol * 100
        
        diag =
        if main_power > 15: diag.append(f"大戶重兵集結 (買力 {main_power:.1f}%)")
        elif main_power < -15: diag.append(f"大戶強力倒貨 (賣力 {abs(main_power):.1f}%)")
        
        if firepower >= fire_thresh and concentration > 5: diag.append(f"火力壓制 ({fire_thresh}倍↑)")
        elif firepower < 0.7 and diff_count > 50: diag.append("散戶進場 (主力倒貨)")
        elif active_count > 500 and firepower < 1.0: diag.append("籌碼極度發散 (熱門當沖雷區)")
        
        out.append({"日期": d, "活躍家數": active_count, "買賣家數差": diff_count, "籌碼集中度(%)": round(concentration, 1), "主力成交力(%)": round(main_power, 2), "買方火力(倍)": round(firepower, 2), "鷹眼診斷": " | ".join(diag) if diag else "中性換手"})
    return pd.DataFrame(out)

def process_v30_daily_tracking(df_branch_raw, intel_tags, df_price, df_branch_diff, actual_dates, fire_thresh, period_days=5):
    if df_branch_raw.empty or len(actual_dates) < period_days: return pd.DataFrame(), pd.DataFrame()
    out, audit_smart_money =,
    df_b = df_branch_raw[['date', 'securities_trader', 'buy', 'sell', 'price']].rename(columns={'buy': 'bs', 'sell': 'ss', 'price': 'pr'})
    df_b['tag'] = df_b['securities_trader'].map(intel_tags).fillna("路人雜訊")
    
    df_b['is_smart'] = df_b['tag'].isin({"波段鎖碼", "避險造市", "獲利調節", "棄守提款", "主力重砲", "認錯回補"})
    df_b['is_short'] = df_b['tag'].isin({"隔日突擊", "跟風小戶"})
    df_b['valid_bs'], df_b['valid_ss'] = np.where(df_b['pr'] > 0, df_b['bs'], 0), np.where(df_b['pr'] > 0, df_b['ss'], 0)
    df_b['buy_amt'], df_b['sell_amt'] = df_b['valid_bs'] * df_b['pr'], df_b['valid_ss'] * df_b['pr']

    df_smart_all = df_b[df_b['is_smart']].groupby(['date', 'securities_trader', 'tag']).agg(bs=('bs','sum'), ss=('ss','sum'), buy_amt=('buy_amt','sum'), sell_amt=('sell_amt','sum')).reset_index()
    df_smart_all['net_vol'] = ((df_smart_all['bs'] - df_smart_all['ss']) / 1000).round().astype(int)
    smart_dict = dict(tuple(df_smart_all.groupby('date'))) if not df_smart_all.empty else {}

    df_short_all = df_b[df_b['is_short']].groupby(['date', 'securities_trader']).agg(bs=('bs','sum'), ss=('ss','sum')).reset_index()
    df_short_all['net_vol'] = ((df_short_all['bs'] - df_short_all['ss']) / 1000).round().astype(int)
    short_dict = dict(tuple(df_short_all.groupby('date'))) if not df_short_all.empty else {}

    price_dict = df_price.set_index('日期').to_dict('index') if not df_price.empty else {}
    diff_dict = df_branch_diff.set_index('日期').to_dict('index') if not df_branch_diff.empty else {}
    
    for d in actual_dates[:period_days]:
        pr_row, diff_row = price_dict.get(d, {}), diff_dict.get(d, {})
        cp, op, hp, lp, sp_raw = pr_row.get('收盤價(元)', 0), pr_row.get('開盤價(元)', 0), pr_row.get('最高價(元)', 0), pr_row.get('最低價(元)', 0), pr_row.get('漲跌(元)', 0)
        try: sp_num = float(str(sp_raw).replace('+', '').replace(',', '').strip())
        except: sp_num = 0.0
        
        bsd, firepower, active_cnt, concentration, eye_diag = diff_row.get('買賣家數差', 0), diff_row.get('買方火力(倍)', 1.0), diff_row.get('活躍家數', 0), diff_row.get('籌碼集中度(%)', 0), diff_row.get('鷹眼診斷', "")

        smart_grouped = smart_dict.get(d, pd.DataFrame(columns=['securities_trader', 'tag', 'bs', 'ss', 'buy_amt', 'sell_amt', 'net_vol']))
        short_grouped = short_dict.get(d, pd.DataFrame(columns=['securities_trader', 'bs', 'ss', 'net_vol']))
        
        if d == actual_dates:
            for r in smart_grouped.to_dict('records'):
                if r['net_vol']!= 0: audit_smart_money.append({"日期": d, "分點": r['securities_trader'], "標籤": r['tag'], "淨買超(張)": r['net_vol']})
        
        smart_net = smart_grouped['net_vol'].sum() if not smart_grouped.empty else 0
        short_trap = short_grouped[short_grouped['net_vol'] > 0]['net_vol'].sum() if not short_grouped.empty else 0
        
        total_n = 0
        if not smart_grouped.empty:
            s_ret = smart_grouped.copy()
            s_ret['net_shares'], s_ret['net_amt'] = s_ret['bs'] - s_ret['ss'], s_ret['buy_amt'] - s_ret['sell_amt']
            s_ret_long = s_ret[s_ret['net_shares'] > 0]
            total_n, total_net_amt = s_ret_long['net_shares'].sum(), s_ret_long['net_amt'].sum()
            smart_avg_cost = max(0.0, total_net_amt / total_n) if total_n > 0 else 0.0
        else: smart_avg_cost = 0.0
            
        gap = cp - smart_avg_cost if smart_avg_cost > 0 and cp > 0 else 0
        adv =
        if cp <= 0: adv.append("股價無紀錄或暫停交易")
        else:
            day_range, lower_shadow = hp - lp, min(cp, op) - lp
            if day_range > 0 and (lower_shadow / day_range) > 0.5 and smart_net > 0: adv.append("探底洗盤成功，主力護盤")
            if smart_avg_cost == 0 and smart_net < 0: adv.append("[危險]主力零成本無本出貨中")
            elif smart_net > 300 and firepower > 1.5: adv.append("[重擊點火]大戶重力掃貨推升")
            elif smart_net > 50 and gap > 0: adv.append("主動鎖碼/強勢推升")
            elif smart_net > 50 and gap < 0: adv.append("大戶承接/弱勢護盤")
            elif smart_net < -100 and sp_num > 0: adv.append("拉高派發/撤退")
            elif smart_net < -100 and sp_num <= 0: adv.append("波段棄守/多殺多")
            
        if eye_diag and eye_diag!= "中性換手": adv.append(eye_diag)
        elif not adv: adv.append("盤整/無明顯特徵")

        out.append({"日期": d, "收盤價(元)": cp if cp > 0 else "-", "漲跌(元)": sp_raw if cp > 0 else "-", "聰明錢淨流(張)": int(smart_net), "大戶淨加權均價": round(smart_avg_cost, 2) if smart_avg_cost > 0 else ("0 (無本獲利)" if smart_avg_cost == 0 and total_n > 0 else "-"), "均價落差": round(gap, 2) if smart_avg_cost > 0 and cp > 0 else "-", "活躍家數": active_cnt, "買賣家數差": bsd, "籌碼集中度(%)": concentration, "買方火力(倍)": firepower, "潛在賣壓(張)": int(short_trap), "綜合診斷": " | ".join(adv)})
    return pd.DataFrame(out), pd.DataFrame(audit_smart_money).sort_values('淨買超(張)', ascending=False) if audit_smart_money else pd.DataFrame()

def clean_level_by_math(x):
    s = str(x).replace(',', '').replace(' ', '').replace('.0', '')
    if "以上" in s or "1000" in s: return "1000張以上"
    if "合計" in s or "總計" in s or "差異數" in s or "99" == s: return "合計"
    nums = _num_re.findall(s)
    if not nums: return s
    v = int(nums[-1])
    if v <= 999: return "1-999股"
    if v <= 5000: return "1-5張"
    if v <= 10000: return "5-10張"
    if v <= 15000: return "10-15張"
    if v <= 20000: return "15-20張"
    if v <= 30000: return "20-30張"
    if v <= 40000: return "30-40張"
    if v <= 50000: return "40-50張"
    if v <= 100000: return "50-100張"
    if v <= 200000: return "100-200張"
    if v <= 400000: return "200-400張"
    if v <= 600000: return "400-600張"
    if v <= 800000: return "600-800張"
    if v <= 1000000: return "800-1000張"
    return "1000張以上"

def process_tdcc(df):
    if df.empty or 'HoldingSharesLevel' not in df.columns: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df = df.astype(str).str.contains('差異數', na=False)].copy()
    df['LevelClean'] = df.apply(clean_level_by_math)
    
    if 'HoldingShares' in df.columns: df['unit'] = (safe_to_num(df) / 1000).round().astype(int)
    elif 'unit' in df.columns: df['unit'] = (safe_to_num(df['unit']) / 1000).round().astype(int)
    else: df['unit'] = 0
    df['people'] = safe_to_num(df['people']).astype(int) if 'people' in df.columns else 0

    dates = sorted(df['date'].unique(), reverse=True)[:15]
    df_levels = df[df['date'].isin(dates) & ~df['LevelClean'].str.contains('合計|總計', na=False)]
    if df_levels.empty: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    p_u = df_levels.pivot_table(index='date', columns='LevelClean', values='unit', aggfunc='sum').reset_index().fillna(0)
    p_p = df_levels.pivot_table(index='date', columns='LevelClean', values='people', aggfunc='sum').reset_index().fillna(0)
    lvls = ['1-999股', '1-5張', '5-10張', '10-15張', '15-20張', '20-30張', '30-40張', '40-50張', '50-100張', '100-200張', '200-400張', '400-600張', '600-800張', '800-1000張', '1000張以上']
    
    for l in lvls:
        if l not in p_u.columns: p_u[l] = 0
        if l not in p_p.columns: p_p[l] = 0
        
    df_t = pd.DataFrame({'date': p_u['date']})
    df_t['總張數'], df_t['總人數(人)'] = p_u[lvls].sum(axis=1), p_p[lvls].sum(axis=1)
    df_w = df_t.copy()
    
    for l in lvls: df_w[f"{l}_張數"], df_w[f"{l}_人數"], df_w[f"{l}_比例(%)"] = p_u[l], p_p[l], (p_u[l] / df_t['總張數'].replace(0, np.nan) * 100).fillna(0).round(2)
    df_w = df_w.rename(columns={'date': '日期'}).sort_values('日期', ascending=False)
    df_unit = pd.merge(df_t[['date', '總張數']], p_u[['date']+lvls], on='date').rename(columns={'date': '日期'}).sort_values('日期', ascending=False)
    df_ppl = pd.merge(df_t[['date', '總人數(人)']], p_p[['date']+lvls], on='date').rename(columns={'date': '日期'}).sort_values('日期', ascending=False)
    return df_w, df_unit, df_ppl

def process_tdcc_dynamic(df_share_wide, df_price, dead_chip_input, dynamic_dict, static_val, chip_engine):
    if df_share_wide.empty or df_price.empty: return pd.DataFrame()
    df_s, df_p = df_share_wide.copy(), df_price.copy()
    df_s['dt'], df_p['dt'] = pd.to_datetime(df_s['日期']), pd.to_datetime(df_p['日期'])
    df_m = pd.merge_asof(df_s.sort_values('dt'), df_p.drop_duplicates(subset=['dt']).sort_values('dt')[['dt', '收盤價(元)']], on='dt', direction='backward').sort_values('dt', ascending=False)

    df_m['pct_1000'] = pd.to_numeric(df_m.get('1000張以上_比例(%)', 0), errors='coerce').fillna(0.0)
    df_m['pct_800'] = df_m['pct_1000'] + pd.to_numeric(df_m.get('800-1000張_比例(%)', 0), errors='coerce').fillna(0.0)
    df_m['pct_600'] = df_m['pct_800'] + pd.to_numeric(df_m.get('600-800張_比例(%)', 0), errors='coerce').fillna(0.0)
    df_m['pct_400'] = df_m['pct_600'] + pd.to_numeric(df_m.get('400-600張_比例(%)', 0), errors='coerce').fillna(0.0)
    df_m['pct_200'] = df_m['pct_400'] + pd.to_numeric(df_m.get('200-400張_比例(%)', 0), errors='coerce').fillna(0.0)
    df_m['pct_100'] = df_m['pct_200'] + pd.to_numeric(df_m.get('100-200張_比例(%)', 0), errors='coerce').fillna(0.0)

    def get_pct(row_dict, threshold):
        if threshold <= 100: return row_dict.get('pct_100', 0)
        if threshold <= 200: return row_dict.get('pct_200', 0)
        if threshold <= 400: return row_dict.get('pct_400', 0)
        if threshold <= 600: return row_dict.get('pct_600', 0)
        if threshold <= 800: return row_dict.get('pct_800', 0)
        return row_dict.get('pct_1000', 0)

    out =
    for row in df_m.to_dict('records'):
        p = row.get('收盤價(元)', 0)
        if pd.isna(p) or p <= 0: continue
        cur_dead, cl = get_dead_chip_info(row['日期'], dead_chip_input, dynamic_dict, static_val, chip_engine)
        total_lots = row.get('總張數', 0)
        safe_dead_ratio = max(0.0, min(99.9, cur_dead))
        ct = get_smart_threshold(p, total_lots, safe_dead_ratio)
        lp = get_pct(row, ct)
        
        st_val = "籌碼渙散"
        if 40.0 <= lp <= 70.0: st_val = "波段甜區 (易吸量推升)"
        elif lp > 80.0: st_val = "極度集中 (防無量倒貨)"
        elif lp > 70.0: st_val = "高度鎖碼"
            
        cd = "-"
        if 0 < safe_dead_ratio < 100:
            cv = max(0, (lp - safe_dead_ratio) / (100.0 - safe_dead_ratio))
            cd = round(cv * 100, 2)
            
        out.append({"日期": row['日期'], "收盤價(元)": round(float(p), 2), "大戶精算門檻": f"系統判定 ({int(ct)}張)", "大戶原持股(%)": round(lp, 2), "董監死籌碼(%)": f"{float(safe_dead_ratio):.2f}% ({cl})" if safe_dead_ratio > 0 else "-", "純淨活大戶C_Value(%)": cd, "實戰判定": st_val})
    return pd.DataFrame(out)

def process_day_trading(df):
    if df.empty: return pd.DataFrame()
    df_out = df.copy()
    if 'DayTradingVolume' in df_out.columns: df_out['當沖總張數'] = (safe_to_num(df_out) / 1000).round().astype(int)
    elif 'Volume' in df_out.columns: df_out['當沖總張數'] = (safe_to_num(df_out['Volume']) / 1000).round().astype(int)
    df_out = df_out.rename(columns={"date": "日期"}).loc[:, ~df_out.columns.duplicated()]
    return df_out[[c for c in ['日期', '當沖總張數'] if c in df_out.columns]].tail(10).sort_values('日期', ascending=False)

def process_margin(df):
    if df.empty: return pd.DataFrame()
    for c in:
        if c in df.columns: df[c] = safe_to_num(df[c]).round().astype(int)
    df = df.rename(columns={"date": "日期", "MarginPurchaseBuy": "融資買進(萬元)", "MarginPurchaseSell": "融資賣出(萬元)", "MarginPurchaseCashRepayment": "融資現償(萬元)", "MarginPurchaseTodayBalance": "融資餘額(萬元)", "ShortSaleBuy": "融券買進(張)", "ShortSaleSell": "融券賣出(張)", "ShortSaleTodayBalance": "融券餘額(張)", "OffsetLoanAndShort": "資券相抵(張)"})
    df = df.loc[:, ~df.columns.duplicated()]
    if '融資餘額(萬元)' in df.columns and 'MarginPurchaseYesterdayBalance' in df.columns:
        df['融資增減(萬元)'] = df['融資餘額(萬元)'] - safe_to_num(df).round().astype(int)
    if '融券餘額(張)' in df.columns and 'ShortSaleYesterdayBalance' in df.columns:
        df['融券增減(張)'] = df['融券餘額(張)'] - safe_to_num(df).round().astype(int)
    cols = [c for c in ['日期','融資買進(萬元)','融資賣出(萬元)','融資現償(萬元)','融資餘額(萬元)','融資增減(萬元)','融券買進(張)','融券賣出(張)','融券餘額(張)','融券增減(張)','資券相抵(張)'] if c in df.columns]
    return df[cols].tail(10).sort_values('日期', ascending=False)

def process_inst(df):
    if df.empty: return pd.DataFrame()
    pdf = df.pivot_table(index='date', columns='name', values=['buy', 'sell'], fill_value=0).reset_index()
    pdf.columns = ['_'.join(c).strip('_') for c in pdf.columns.values]
    out = pd.DataFrame({'日期': pdf['date']})
    length = len(pdf)
    f_b, f_s = safe_to_num(pdf.get('buy_Foreign_Investor', pd.Series(*length))), safe_to_num(pdf.get('sell_Foreign_Investor', pd.Series(*length)))
    i_b, i_s = safe_to_num(pdf.get('buy_Investment_Trust', pd.Series(*length))), safe_to_num(pdf.get('sell_Investment_Trust', pd.Series(*length)))
    ds_b, ds_s = safe_to_num(pdf.get('buy_Dealer_self', pdf.get('buy_Dealer', pd.Series(*length)))), safe_to_num(pdf.get('sell_Dealer_self', pdf.get('sell_Dealer', pd.Series(*length))))
    dh_b, dh_s = safe_to_num(pdf.get('buy_Dealer_Hedging', pd.Series(*length))), safe_to_num(pdf.get('sell_Dealer_Hedging', pd.Series(*length)))
    out['外資買賣超(張)'], out['投信買賣超(張)'] = ((f_b - f_s) / 1000).round().astype(int), ((i_b - i_s) / 1000).round().astype(int)
    out['自營商(自行)買賣超(張)'], out['自營商(避險)買賣超(張)'] = ((ds_b - ds_s) / 1000).round().astype(int), ((dh_b - dh_s) / 1000).round().astype(int)
    out['三大法人買賣超(張)'] = out['外資買賣超(張)'] + out['投信買賣超(張)'] + out['自營商(自行)買賣超(張)'] + out['自營商(避險)買賣超(張)']
    return out.tail(10).sort_values('日期', ascending=False)

def process_fut_inst(df):
    if df.empty: return pd.DataFrame()
    df['net'] = safe_to_num(df['long_open_interest_balance_volume']) - safe_to_num(df['short_open_interest_balance_volume'])
    pdf = df.pivot_table(index='date', columns='institutional_investors', values='net', fill_value=0).reset_index()
    pdf.columns.name = None
    for col in:
        if col not in pdf.columns: pdf[col] = 0
    return pdf.rename(columns={'date': '日期', 'Foreign_Investor': '外資多空(口)', 'Investment_Trust': '投信多空(口)', 'Dealer': '自營多空(口)'}).tail(10).sort_values('日期', ascending=False)

def process_per(df):
    if df.empty: return pd.DataFrame()
    df_out = df.copy().rename(columns={"date":"日期","dividend_yield":"殖利率(%)","PER":"本益比(倍)","PBR":"淨值比(倍)"}).loc[:, ~df_out.columns.duplicated()]
    for col in ["殖利率(%)", "本益比(倍)", "淨值比(倍)"]: 
        if col in df_out.columns: df_out[col] = safe_to_num(df_out[col]).round(2)
    return df_out[[c for c in ['日期', '本益比(倍)', '淨值比(倍)', '殖利率(%)'] if c in df_out.columns]].tail(10).sort_values('日期', ascending=False)

def process_disp(df):
    if df.empty: return pd.DataFrame()
    df_out = df.copy().rename(columns={"date":"公告日期","disposition_cnt":"處置次數","condition":"處置條件","measure":"處置措施","period_start":"處置起日","period_end":"處置迄日"}).loc[:, ~df_out.columns.duplicated()]
    return df_out[[c for c in ['公告日期', '處置次數', '處置起日', '處置迄日', '處置條件', '處置措施'] if c in df_out.columns]].tail(5).sort_values('公告日期', ascending=False)

def process_div(df):
    if df.empty: return pd.DataFrame()
    df_out = df.rename(columns={"date": "公告日期", "year": "股利年份", "StockEarningsDistribution": "盈餘配股(元)", "StockStatutorySurplus": "公積配股(元)", "CashEarningsDistribution": "盈餘配息(元)", "CashStatutorySurplus": "公積配息(元)"}).loc[:, ~df_out.columns.duplicated()]
    cols = [c for c in ["公告日期", "股利年份", "盈餘配息(元)", "公積配息(元)", "盈餘配股(元)", "公積配股(元)"] if c in df_out.columns]
    if '股利年份' in df_out.columns:
        valid_year_mask = df_out['股利年份'].notna() & (~df_out['股利年份'].astype(str).str.lower().isin(['nan', '<na>', 'none', '']))
        extracted_year = pd.Series(index=df_out.index, dtype='object', name='股利年份')
        extracted_year[valid_year_mask] = df_out.loc[valid_year_mask, '股利年份'].astype(str).str.extract(r'^(\d+)', expand=False)
        year_num = safe_to_num(extracted_year, fill_val=np.nan)
        return df_out)][cols].sort_values('公告日期', ascending=False).head(10)
    return df_out[cols].sort_values('公告日期', ascending=False).head(10)

def process_cbas(df, current_stock_price, df_cb_info=None):
    if df.empty: return pd.DataFrame()
    df_out = df.copy().rename(columns={"date": "日期", "cb_id": "可轉債代號", "cb_name": "可轉債名稱", "conversion_price": "轉換價(元)", "ConversionPrice": "轉換價(元)", "underlying_stock_price": "標的股價(元)", "PriceOfUnderlyingStock": "標的股價(元)", "outstanding_amount": "未償還餘額", "OutstandingAmount": "未償還餘額", "outstanding_balance": "未償還餘額", "close": "CB收盤價", "closing_price": "CB收盤價", "conversion_premium_rate": "溢價率(%)", "premium_rate": "溢價率(%)", "PremiumRate": "溢價率(%)", "theoretical_value": "轉換價值", "TheoreticalValue": "轉換價值"}).loc[:, ~df_out.columns.duplicated()]
    if "可轉債代號" in df_out.columns: df_out['可轉債代號'] = df_out['可轉債代號'].astype(str).str.replace(r'\.0$', '', regex=True).str.replace(',', '', regex=False).str.strip()
    for c in:
        if c in df_out.columns: df_out[c] = safe_to_num(df_out[c], fill_val=np.nan)
    if "標的股價(元)" not in df_out.columns or df_out["標的股價(元)"].isna().all(): df_out["標的股價(元)"] = current_stock_price
    if "標的股價(元)" in df_out.columns and "轉換價(元)" in df_out.columns:
        df_out["轉換價(元)"] = df_out["轉換價(元)"].replace(0, np.nan)
        if "轉換價值" not in df_out.columns or df_out["轉換價值"].isna().all(): df_out["轉換價值"] = (df_out["標的股價(元)"] / df_out["轉換價(元)"] * 100).round(2)
        if "溢價率(%)" not in df_out.columns or df_out["溢價率(%)"].isna().all():
            if "CB收盤價" in df_out.columns and "轉換價值" in df_out.columns: df_out["溢價率(%)"] = ((df_out - df_out["轉換價值"].replace(0, np.nan)) / df_out["轉換價值"].replace(0, np.nan) * 100).round(2)
            else: df_out["溢價率(%)"] = "-"
    if df_cb_info is not None and not df_cb_info.empty and "未償還餘額" in df_out.columns:
        df_cb_info_clean = df_cb_info.rename(columns={"stock_id": "可轉債代號", "bond_id": "可轉債代號", "cb_id": "可轉債代號", "issue_amount": "發行總額", "IssueAmount": "發行總額", "IssuanceAmount": "發行總額", "DueDateOfConversion": "到期日", "maturity_date": "到期日"}).loc[:, ~df_cb_info_clean.columns.duplicated()]
        if "可轉債代號" in df_cb_info_clean.columns:
            df_cb_info_clean['可轉債代號'] = df_cb_info_clean['可轉債代號'].astype(str).str.replace(r'\.0$', '', regex=True).str.replace(',', '', regex=False).str.strip()
            cols_to_merge = ['可轉債代號']
            if "發行總額" in df_cb_info_clean.columns: cols_to_merge.append("發行總額")
            if "到期日" in df_cb_info_clean.columns: cols_to_merge.append("到期日")
            df_out = pd.merge(df_out, df_cb_info_clean[cols_to_merge].drop_duplicates('可轉債代號'), on='可轉債代號', how='left')
            if "發行總額" in df_out.columns: df_out["未償還比例(%)"] = (df_out["未償還餘額"] / safe_to_num(df_out["發行總額"], fill_val=np.nan).replace(0, np.nan) * 100).round(2)
            else: df_out["未償還比例(%)"] = "缺發行總額"
        else: df_out["未償還比例(%)"] = "缺代號"
    else: df_out["未償還比例(%)"] = "需原始發行總額"
    display_cols =
    return df_out[[c for c in display_cols if c in df_out.columns]]

def calculate_disposition_thresholds(df_price, df_day_trade, total_lots):
    if df_price.empty or len(df_price) < 6: return None
    df_asc = df_price.sort_values('日期', ascending=True).reset_index(drop=True)
    closes, lows, volumes_lots = df_asc['收盤價(元)'].tolist(), df_asc['最低價(元)'].tolist(), df_asc['成交量(張)'].tolist()

    res = {
        'limit_6d': closes[-6] * 1.32 if len(closes) >= 6 else None,
        'limit_amp': min(lows[-5:]) * 1.25 if len(lows) >= 5 else None,
        'limit_30d': closes[-30] * 2.0 if len(closes) >= 30 else None,
        'limit_60d': closes[-60] * 2.3 if len(closes) >= 60 else None,
        'day_trade_warning': False
    }

    if not df_day_trade.empty and len(df_day_trade) >= 2:
        dt_vol = df_day_trade['當沖總張數'].tolist()[:6]
        vol_recent = volumes_lots[-len(dt_vol):]
        dt_ratios = [d / v if v > 0 else 0 for d, v in zip(dt_vol, reversed(vol_recent))]
        if len(dt_ratios) >= 2 and dt_ratios > 0.6 and dt_ratios[1] > 0.6:
            res['day_trade_warning'] = True

    if total_lots > 0:
        recent_5d_vol_lots = sum(volumes_lots[-5:])
        res['current_5d_turnover'] = (recent_5d_vol_lots / total_lots) * 100
        res['turnover_warning'] = res['current_5d_turnover'] > 10.0
        res['max_vol_6d'] = (total_lots * 0.5) - recent_5d_vol_lots
        res['max_vol_1d'] = total_lots * 0.1
    else:
        res['current_5d_turnover'], res['turnover_warning'], res['max_vol_6d'], res['max_vol_1d'] = 0, False, None, None
    return res

def process_technical_analysis(df_price, s_ma, m_ma, l_ma):
    try:
        if df_price is None or df_price.empty or len(df_price) < 30 or '收盤價(元)' not in df_price.columns or '日期' not in df_price.columns: return pd.DataFrame()
        s_ma, m_ma, l_ma = int(s_ma), int(m_ma), int(l_ma) 
        df_ta = df_price.sort_values('日期', ascending=True).copy()
        df_ta['收盤價(元)'] = pd.to_numeric(df_ta['收盤價(元)'], errors='coerce').astype('float64')
        df_ta[f'MA{s_ma}'] = df_ta['收盤價(元)'].rolling(window=s_ma, min_periods=1).mean().round(2)
        df_ta[f'MA{m_ma}(中線)'] = df_ta['收盤價(元)'].rolling(window=m_ma, min_periods=1).mean().round(2)
        df_ta[f'MA{l_ma}(長線)'] = df_ta['收盤價(元)'].rolling(window=l_ma, min_periods=1).mean().round(2)
        df_ta['中線乖離(%)'] = ((df_ta['收盤價(元)'] - df_ta[f'MA{m_ma}(中線)']) / df_ta[f'MA{m_ma}(中線)'].replace(0, np.nan) * 100).round(2)
        cond_up, cond_down = df_ta['收盤價(元)'] > df_ta[f'MA{m_ma}(中線)'], df_ta['收盤價(元)'] < df_ta[f'MA{m_ma}(中線)']
        df_ta['技術面診斷'] = np.select([cond_up, cond_down], ["站上中線防守", "跌破中線防守"], default="盤整")
        return df_ta.sort_values('日期', ascending=False)
    except Exception: return pd.DataFrame()

def process_linear_regression(df_price, lr_days):
    try:
        if df_price is None or df_price.empty or len(df_price) < 2 or '收盤價(元)' not in df_price.columns: return pd.DataFrame()
        df_lr = df_price.head(lr_days).sort_values('日期', ascending=True).copy()
        df_lr['收盤價(元)'] = pd.to_numeric(df_lr['收盤價(元)'], errors='coerce').astype('float64')
        y = df_lr['收盤價(元)'].dropna().values
        if len(y) < 2: return pd.DataFrame()
        x = np.arange(len(y))
        A = np.vstack([x, np.ones(len(x))]).T
        m, c = np.linalg.lstsq(A, y, rcond=None)
        y_pred = m * x + c
        std_err = np.std(y - y_pred)
        df_lr, df_lr, df_lr = y_pred, y_pred + 2 * std_err, y_pred - 2 * std_err
        return df_lr]
    except Exception: return pd.DataFrame()

def process_geometric_patterns(df_price, kline_days, order, mode, current_price):
    try:
        if df_price.empty or len(df_price) < order * 2: return {}
        df = df_price.head(kline_days).sort_values('日期', ascending=True).reset_index(drop=True)
        lows_vals, highs_vals, dates_vals = df['最低價(元)'].values, df['最高價(元)'].values, df['日期'].values
        highs, lows =,
        for i in range(order, len(df) - order):
            if lows_vals[i] == np.min(lows_vals[i-order:i+order+1]): lows.append((dates_vals[i], float(lows_vals[i]), i))
            if highs_vals[i] == np.max(highs_vals[i-order:i+order+1]): highs.append((dates_vals[i], float(highs_vals[i]), i))
        if len(lows) < 2 or len(highs) < 2: return {}
        return {'name': "Auto", 'shape_x': [highs[-2], highs[-1]], 'shape_y': [highs[-2][1], highs[-1][1]], 'neck_x': [lows[-2], lows[-1]], 'neck_y': [lows[-2][1], lows[-1][1]], 'color': "#2196f3", 'desc': "自動辨識區間", 'signal': "neutral"}
    except Exception: return {}

def render_clean_html_table(df, title=""):
    if df is None or df.empty:
        if title: st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
        st.warning("此區塊查無數據。")
        return
    text_keywords = {'日期', '分點', '標籤', '週期', '名稱', '姓名', '身份別', '條件', '措施', '診斷', '代號'}
    cols = df.columns.tolist()
    align_classes = ["text-left" if any(k in str(col) for k in text_keywords) else "text-right" for col in cols]
    html_parts =
    if title: html_parts.append(f"<div class='section-title'>{title}</div>")
    html_parts.append("<div class='table-container'><table><thead><tr>")
    html_parts.extend([f"<th>{col}</th>" for col in cols])
    html_parts.append("</tr></thead><tbody>")
    
    for row in df.itertuples(index=False):
        html_parts.append("<tr>")
        for i, val in enumerate(row):
            display_val = "-"
            if pd.notna(val):
                s = str(val).strip()
                if s and s.lower()!= "nan":
                    if "無本獲利" in s: display_val = f"<span class='profit-warning'>{s}</span>"
                    elif "(虧)" in s: display_val = f"<span class='loss-warning'>(虧) {s.replace('(虧)', '').strip()}</span>"
                    elif s.startswith("+"): display_val = f"<span class='highlight-red'>{s}</span>"
                    elif s.startswith("-") and len(s) > 1 and s.[1]isdigit():
                        try: display_val = f"<span class='highlight-green'>{float(s.replace(',', '')):,.2f}</span>" if "." in s else f"<span class='highlight-green'>{int(float(s.replace(',', ''))):,}</span>"
                        except: display_val = f"<span class='highlight-green'>{s}</span>"
                    else:
                        if "%" in s: display_val = s
                        else:
                            try: display_val = f"{float(s.replace(',', '')):,.2f}" if "." in s else f"{int(float(s.replace(',', ''))):,}"
                            except: display_val = s
            html_parts.append(f"<td class='{align_classes[i]}'>{display_val}</td>")
        html_parts.append("</tr>")
    html_parts.append("</tbody></table></div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)

def format_to_csv_string(df, title):
    header = f"▼▼▼ {title} ▼▼▼\n"
    if df is None or df.empty: return header + "此區塊查無數據或無發行紀錄\n"
    return header + df.to_csv(index=False) + "\n"

if run_btn:
    if not user_stock_id.strip(): 
        st.warning("請先在上方輸入股票代號！")
        st.stop()

    with st.spinner(f"正在啟動 V71.12.5 老手盤感升級版..."):
        name, industry = get_basic_info_finmind(user_stock_id)
        if name == "未知名稱": 
            st.error(f"查無股票代號 {user_stock_id} 的基本資料。請確認代號是否正確或 FinMind API 是否正常連線。")
            st.stop()
            
        df_p_raw = fetch_finmind_v50("TaiwanStockPrice", (datetime.date.today() - datetime.timedelta(days=700)).strftime("%Y-%m-%d"), user_stock_id)
        if df_p_raw.empty or 'date' not in df_p_raw.columns: 
            st.error("查無歷史股價資料。")
            st.stop()
        
        valid_dates = df_p_raw['date'].dropna().astype(str)
        dates = sorted(valid_dates[valid_dates!= ""].unique().tolist(), reverse=True)
        if not dates: st.stop()
            
        max_len = lookback_days if len(dates) >= lookback_days else len(dates)
        if max_len == 0: max_len = 1
        d_end = dates[max_len-1]
        
        df_price = optimize_memory(process_price(df_p_raw))
        curr_price = round(float(df_price['收盤價(元)'].iloc), 2) if not df_price.empty and '收盤價(元)' in df_price.columns else 0
        df_ta_full = process_technical_analysis(df_price, ma_short, ma_mid, ma_long)
        
        recent_20_vol = df_price['成交量(張)'].head(20).mean() if not df_price.empty else 1000
        if pd.isna(recent_20_vol) or recent_20_vol == 0: recent_20_vol = 1000
        
        dynamic_noise_threshold = int(recent_20_vol * (heatmap_noise_pct / 100.0))
        dynamic_alert_threshold = int(recent_20_vol * (alert_smart_pct / 100.0))

        df_lr_channel = process_linear_regression(df_price, lr_days)
        latest_lr_upper = df_lr_channel.iloc[-1] if not df_lr_channel.empty else 0.0
        latest_lr_mid = df_lr_channel.iloc[-1] if not df_lr_channel.empty else 0.0
        latest_lr_lower = df_lr_channel.iloc[-1] if not df_lr_channel.empty else 0.0
        
        pat_data = {}
        if enable_pattern: pat_data = process_geometric_patterns(df_price, kline_days, pattern_order, pattern_mode, curr_price)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as bg_executor:
            f_dir = bg_executor.submit(scrape_director_v50, user_stock_id)
            f_ple = bg_executor.submit(scrape_fubon_pledge, df_p_raw, user_stock_id)
            df_b_raw, ds_dict, df_cb_info = fetch_heavy_data_sync_with_progress(user_stock_id, tuple(dates), max_len)
            dynamic_dict, s_val, chip_eng, _ = f_dir.result()
            df_p_sum, df_p_det = f_ple.result()

        if df_b_raw.empty:
            st.error(f"查無 {user_stock_id} 的分點進出資料，可能為暫停交易或 API 狀態異常，請稍後再試。")
            st.stop()
            
        df_b_raw['price'] = safe_to_num(df_b_raw['price'])
        df_b_raw['buy'], df_b_raw['sell'] = safe_to_num(df_b_raw['buy']), safe_to_num(df_b_raw['sell'])
        df_b_raw['valid_buy'], df_b_raw['valid_sell'] = np.where(df_b_raw['price'] > 0, df_b_raw['buy'], 0), np.where(df_b_raw['price'] > 0, df_b_raw['sell'], 0)
        df_b_raw['valid_buy_amt'], df_b_raw['valid_sell_amt'] = df_b_raw['valid_buy'] * df_b_raw['price'], df_b_raw['valid_sell'] * df_b_raw['price']
        df_b_raw['net_shares'] = df_b_raw['buy'] - df_b_raw['sell']
        df_b_raw['date_dt'] = pd.to_datetime(df_b_raw['date'])

        parsed_dead_chip = None
        if dead_chip_input and str(dead_chip_input).strip()!= "":
            try: parsed_dead_chip = float(str(dead_chip_input).replace('%', '').strip())
            except: pass

        tags, df_debug_tags = get_v50_intelligence(df_b_raw, df_p_raw, stick_thresh=stickiness_threshold, global_days=max_len, dates_list=dates)
        
        df_s_raw = ds_dict.get("TaiwanStockHoldingSharesPer", pd.DataFrame())
        df_s_wide, df_s_unit, df_s_ppl = process_tdcc(df_s_raw)
        
        current_total_shares = df_s_wide['總張數'].iloc if not df_s_wide.empty else 0
        capital_str = f"{current_total_shares / 10000:.2f} 億" if current_total_shares > 0 else "計算中..."
        latest_director_holding, holding_src = get_dead_chip_info(dates, parsed_dead_chip, dynamic_dict, s_val, chip_eng)
        director_holding_str = f"{latest_director_holding:.2f}% ({holding_src})" if latest_director_holding > 0 else "無數據"

        df_day_trade = optimize_memory(process_day_trading(ds_dict.get("TaiwanStockDayTrading", pd.DataFrame())))
        dynamic_n, radar_reason = calculate_dynamic_radar_depth(df_b_raw, dates, current_total_shares, df_price)
        
        pure_vwap, main_force_vol, active_main_branches, core_c_value, core_branch_names = calculate_pure_defense_line(df_b_raw, tags, filter_day_trade, current_total_shares, latest_director_holding, dynamic_n)
        
        net_3, net_10, net_45, net_60 = get_core_period_net(df_b_raw, dates[:3], core_branch_names), get_core_period_net(df_b_raw, dates[:10], core_branch_names), get_core_period_net(df_b_raw, dates[:45] if len(dates)>=45 else dates, core_branch_names), get_core_period_net(df_b_raw, dates[:60] if len(dates)>=60 else dates, core_branch_names)
        
        df_b_diff = process_branch_diff(df_b_raw, dates, firepower_threshold, period_days=15)
        df_b_diff_60 = process_branch_diff(df_b_raw, dates, firepower_threshold, period_days=60)
        
        df_daily_tracker, df_audit_smart = process_v30_daily_tracking(df_b_raw, tags, df_price, df_b_diff, dates, firepower_threshold, period_days=15)
        df_daily_tracker_60, _ = process_v30_daily_tracking(df_b_raw, tags, df_price, df_b_diff_60, dates, firepower_threshold, period_days=60)
        
        df_s_dyn = process_tdcc_dynamic(df_s_wide, df_price, parsed_dead_chip, dynamic_dict, s_val, chip_eng)

        df_margin = optimize_memory(process_margin(ds_dict.get("TaiwanStockMarginPurchaseShortSale", pd.DataFrame())))
        df_inst = optimize_memory(process_inst(ds_dict.get("TaiwanStockInstitutionalInvestorsBuySell", pd.DataFrame())))
        
        df_rev_raw = ds_dict.get("TaiwanStockMonthRevenue", pd.DataFrame())
        df_rev = pd.DataFrame()
        if not df_rev_raw.empty and 'revenue_year' in df_rev_raw.columns and 'revenue_month' in df_rev_raw.columns:
            df_rev_clean = df_rev_raw.dropna(subset=['revenue_year', 'revenue_month']).copy()
            df_rev_clean['營收月份'] = df_rev_clean['revenue_year'].astype(int).astype(str) + "-" + df_rev_clean['revenue_month'].astype(int).astype(str).str.zfill(2)
            df_rev = df_rev_clean.rename(columns={"revenue":"月營收(百萬元)"})[['營收月份','月營收(百萬元)']].tail(24)
            df_rev['月營收(百萬元)'] = (safe_to_num(df_rev['月營收(百萬元)'])/1000000).round().astype(int)
            df_rev = optimize_memory(df_rev.sort_values('營收月份', ascending=False))

        df_b_raw_60 = df_b_raw[df_b_raw['date'].isin(set(dates[:max_len]))]
        df_b_today = optimize_memory(process_branch_v25(df_b_raw_60, 1, dates, tags, df_p_raw, stickiness_threshold, max_len))
        df_b_prev1 = optimize_memory(process_branch_v25(df_b_raw_60, 1, dates[1:], tags, df_p_raw, stickiness_threshold, max_len))
        
        df_fut = optimize_memory(process_fut_inst(ds_dict.get("TaiwanFuturesInstitutionalInvestors", pd.DataFrame())))
        df_div = optimize_memory(process_div(ds_dict.get("TaiwanStockDividend", pd.DataFrame())))
        df_per = optimize_memory(process_per(ds_dict.get("TaiwanStockPER", pd.DataFrame())))
        df_disp = optimize_memory(process_disp(ds_dict.get("TaiwanStockDispositionSecuritiesPeriod", pd.DataFrame())))
        
        df_cbas_raw = ds_dict.get("TaiwanStockConvertibleBondDailyOverview", pd.DataFrame())
        df_cbas = optimize_memory(process_cbas(df_cbas_raw[df_cbas_raw['cb_id'].astype(str).str.replace(',', '', regex=False).str.startswith(user_stock_id)], curr_price, df_cb_info)) if not df_cbas_raw.empty and 'cb_id' in df_cbas_raw.columns else pd.DataFrame()
            
        market_cap_str = f"{(curr_price * current_total_shares) / 100000:,.2f} 億" if not df_price.empty and current_total_shares > 0 else "計算中..."
        company_info_text = f"【產業】 {industry} ｜ 【股本】 {capital_str} ｜ 【市值】 {market_cap_str} ｜ 【董監死籌碼】 {director_holding_str} ｜ 【20日均量】 {int(recent_20_vol):,} 張"
        
        st.subheader(f"{user_stock_id} {name} 全息戰報 (老手盤感升級版)")
        st.markdown(f"<div class='info-box'>{company_info_text}</div>", unsafe_allow_html=True)

        disp_warn = calculate_disposition_thresholds(df_price, df_day_trade, current_total_shares)
        bias = ((curr_price - pure_vwap) / pure_vwap * 100) if pure_vwap > 0 else 0
        vwap_str = f"{pure_vwap:,.2f}" if pure_vwap > 0 else "-"
        
        today_smart_net, today_short_trap, today_gap = df_daily_tracker.iloc.get('聰明錢淨流(張)', 0), df_daily_tracker.iloc.get('潛在賣壓(張)', 0), 0.0 if df_daily_tracker.empty else safe_to_num(df_daily_tracker.iloc.get('均價落差', 0))
        today_fp, today_diff_cnt = df_b_diff.iloc.get('買方火力(倍)', 1.0) if not df_b_diff.empty else 1.0, df_b_diff.iloc.get('買賣家數差', 0) if not df_b_diff.empty else 0

        custom_alerts =
        if today_smart_net >= dynamic_alert_threshold and dynamic_alert_threshold > 0: custom_alerts.append(f"【極端買擊】：今日聰明錢淨買超達 <b>{today_smart_net:,}</b> 張，突破警戒值")
        if today_smart_net <= -dynamic_alert_threshold and dynamic_alert_threshold > 0: custom_alerts.append(f"【極端拋售】：今日聰明錢淨賣超達 <b>{today_smart_net:,}</b> 張，突破警戒值")
        if pure_vwap > 0 and bias <= alert_bias_drop: custom_alerts.append(f"【跌破底線】：股價跌破大戶純淨防守線，乖離達 <b>{bias:.2f}%</b> (警戒值: {alert_bias_drop}%)，主力面臨套牢風險")

        if custom_alerts:
            alert_html = "<div style='background-color: #ffebee; border-left: 6px solid #d32f2f; padding: 15px; margin-bottom: 25px; border-radius: 4px;'><h4 style='color: #c62828;'>系統戰情紅色警報觸發</h4><ul>"
            for msg in custom_alerts: alert_html += f"<li>{msg}</li>"
            st.markdown(alert_html + "</ul></div>", unsafe_allow_html=True)

        if not df_ta_full.empty:
            st.markdown(f"<div class='section-title'>高階技術分析 (極緻緊湊版 - {ma_short}/{ma_mid}/{ma_long}極細均線)</div>", unsafe_allow_html=True)
            df_plot = pd.merge(df_price.head(kline_days).copy(), df_ta_full[['日期', f'MA{ma_short}', f'MA{ma_mid}(中線)', f'MA{ma_long}(長線)']].head(kline_days).copy(), on='日期', how='inner').sort_values('日期', ascending=True)
            df_plot['當沖總張數'] = pd.merge(df_plot, df_day_trade[['日期', '當沖總張數']], on='日期', how='left')['當沖總張數'].fillna(0) if not df_day_trade.empty else 0

            if not df_plot.empty:
                lr_data_json = "{}"
                if not df_lr_channel.empty:
                    df_plot = pd.merge(df_plot, df_lr_channel, on='日期', how='left')
                    df_plot_lr = df_plot.dropna(subset=).sort_values('日期', ascending=True)
                    lr_data = {"upper": [{"time": str(t), "value": float(v) if pd.notna(v) else 0.0} for t, v in zip(df_plot_lr['日期'], df_plot_lr)], "mid": [{"time": str(t), "value": float(v) if pd.notna(v) else 0.0} for t, v in zip(df_plot_lr['日期'], df_plot_lr)], "lower": [{"time": str(t), "value": float(v) if pd.notna(v) else 0.0} for t, v in zip(df_plot_lr['日期'], df_plot_lr)]}
                    lr_data_json = json.dumps(lr_data)

                time_series = df_plot['日期'].astype(str).tolist()
                kline_data = [{'time': t, 'open': float(o), 'high': float(h), 'low': float(l), 'close': float(c)} for t, o, h, l, c in zip(time_series, df_plot['開盤價(元)'], df_plot['最高價(元)'], df_plot['最低價(元)'], df_plot['收盤價(元)'])]
                total_vol_data =)]
                day_trade_vol_data = [{'time': t, 'value': float(dtv), 'color': '#FF9800'} for t, dtv in zip(time_series, df_plot['當沖總張數'])]
                ma_data = {"ma_short": [{'time': t, 'value': round(float(v), 2)} for t, v, is_valid in zip(time_series, df_plot[f'MA{ma_short}'], df_plot[f'MA{ma_short}'].notna()) if is_valid], "ma_mid": [{'time': t, 'value': round(float(v), 2)} for t, v, is_valid in zip(time_series, df_plot[f'MA{ma_mid}(中線)'], df_plot[f'MA{ma_mid}(中線)'].notna()) if is_valid], "ma_long": [{'time': t, 'value': round(float(v), 2)} for t, v, is_valid in zip(time_series, df_plot[f'MA{ma_long}(長線)'], df_plot[f'MA{ma_long}(長線)'].notna()) if is_valid]}

                html_template = """
                <!DOCTYPE html><html><head>
                <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
                <style>body { margin: 0; background: #fff; display: flex; flex-direction: column; height: 100vh; overflow: hidden;} #chart-main { flex: 3.2; position: relative; } #chart-vol { flex: 0.8; position: relative;}.legend { position: absolute; top: 4px; left: 8px; z-index: 10; font-size: 13px; pointer-events: none; background: rgba(255,255,255,0.7); padding: 2px 6px; border-radius: 4px; color: #333;}</style></head>
                <body><div id="chart-main"><div id="legend" class="legend"></div></div><div id="chart-vol"></div>
                <script>
                    const kData = KLINE_DATA, tVol = TOTAL_VOL, dtVol = DAYTRADE_VOL, ma = MA_DATA, lr = LR_DATA;
                    const mainChart = LightweightCharts.createChart(document.getElementById('chart-main'), { layout: { background: { color: '#ffffff' }, textColor: '#333' }, rightPriceScale: { autoScale: true }, timeScale: { visible: false } });
                    const volChart = LightweightCharts.createChart(document.getElementById('chart-vol'), { layout: { background: { color: '#ffffff' }, textColor: '#333' } });
                    const candleSeries = mainChart.addCandlestickSeries({ upColor: '#ffffff', borderUpColor: '#000', wickUpColor: '#000', downColor: '#000', borderDownColor: '#000', wickDownColor: '#000' });
                    candleSeries.setData(kData);
                    const lineOpt = { lineWidth: 1, crosshairMarkerVisible: false };
                    mainChart.addLineSeries({ color: '#ff9800',...lineOpt }).setData(ma.ma_short);
                    mainChart.addLineSeries({ color: '#2196f3',...lineOpt }).setData(ma.ma_mid);
                    mainChart.addLineSeries({ color: '#9c27b0',...lineOpt }).setData(ma.ma_long);
                    if (lr && lr.upper && lr.upper.length > 0) {
                        mainChart.addLineSeries({ color: 'rgba(30, 58, 138, 0.4)',...lineOpt }).setData(lr.upper);
                        mainChart.addLineSeries({ color: 'rgba(30, 58, 138, 0.6)', lineStyle: 2,...lineOpt }).setData(lr.mid);
                        mainChart.addLineSeries({ color: 'rgba(30, 58, 138, 0.4)',...lineOpt }).setData(lr.lower);
                    }
                    volChart.addHistogramSeries({ priceFormat: { type: 'volume' } }).setData(tVol);
                    volChart.addHistogramSeries({ priceFormat: { type: 'volume' } }).setData(dtVol);
                    mainChart.timeScale().subscribeVisibleLogicalRangeChange(r => { if(r!== null) volChart.timeScale().setVisibleLogicalRange(r); });
                </script></body></html>
                """
                components.html(html_template.replace("KLINE_DATA", json.dumps(kline_data)).replace("TOTAL_VOL", json.dumps(total_vol_data)).replace("DAYTRADE_VOL", json.dumps(day_trade_vol_data)).replace("MA_DATA", json.dumps(ma_data)).replace("LR_DATA", lr_data_json), height=600)

        st.markdown("<div class='category-title'>AI 全息籌碼深度診斷總結</div>", unsafe_allow_html=True)
        report_md = "<div class='ai-report-box'><h4>🧠 系統終極戰略推演與深度解析</h4><ul>"
        if disp_warn:
            if disp_warn.get('day_trade_warning'): report_md += "<li style='color:#d32f2f; font-weight:bold;'>⚠️ 【短線過熱警告】：近兩日當沖佔比逾60%，依據法規即將觸發注意股紅線，須防範流動性枯竭風險。</li>"
            if disp_warn.get('turnover_warning'): report_md += "<li style='color:#d32f2f; font-weight:bold;'>⚠️ 【高週轉率警告】：近5日週轉率極端過高(>10%)，已達投機標準，隨時可能進入處置分盤交易。</li>"
            if disp_warn.get('limit_6d') and curr_price > disp_warn['limit_6d']: report_md += "<li style='color:#d32f2f; font-weight:bold;'>⚠️ 【漲幅超限警告】：近6日累積漲幅達32%，觸發處置股警戒線，主力極可能被迫提早洗盤降溫。</li>"
        
        report_md += f"<li><b>一、 短線戰鬥多空定調 (今日籌碼真偽)：</b><br>{'聰明錢真實流入，且買賣家數差為負(籌碼高度集中)。' if today_smart_net > 100 and today_diff_cnt <= -10 else '聰明錢真實撤退，且買賣家數差為正(散戶瘋狂湧入)。' if today_smart_net < -100 and today_diff_cnt >= 10 else '短線籌碼呈現多空交戰，無明顯極端異常。'}</li>"
        report_md += f"<li><b>二、 核心防守價位與安全邊際確認：</b><br>系統已精算出的「純淨主力防守價」為 <b>{vwap_str} 元</b>。目前乖離 {bias:.1f}%。</li></ul>"
        report_md += f"<div class='ai-conclusion'><b>🚀 最終操作定調：沿均線觀察，嚴守停損停利紀律。</b></div></div>"
        st.markdown(report_md, unsafe_allow_html=True)

        st.markdown("---")
        actual_foot_days = footprint_days if len(dates) >= footprint_days else len(dates)
        display_dates = dates[:actual_foot_days]
        
        st.markdown("<div class='category-title'>01. 主力分點全息透視區 (依戰略天數排檔)</div>", unsafe_allow_html=True)
        with st.expander(f"【視覺系主菜】 {actual_foot_days}天主力戰鬥熱力圖 (Heatmap)", expanded=True):
            render_footprint_heatmap(df_b_raw, display_dates, dates[:actual_foot_days] if len(dates)>=actual_foot_days else dates, tags, footprint_rows, dynamic_noise_threshold)
            
        with st.expander(f"【戰略系海鮮】 {actual_foot_days}天大戶建倉成本區間分佈 (Volume Profile)", expanded=not is_right_side):
            render_volume_profile(df_b_raw, dates[:actual_foot_days] if len(dates)>=actual_foot_days else dates, footprint_rows)

        with st.expander(f"【甜點】 土洋聯合作戰比對 (近10日法人 vs 地方大戶角力)", expanded=is_right_side):
            render_institutional_vs_local(df_b_raw, df_inst, tags, top_n=4)

        stat_days = footprint_stat_days if len(dates) >= footprint_stat_days else len(dates)
        df_fb_main, df_fs_main = process_footprint(df_b_raw, display_dates, dates[:stat_days if stat_days > 0 else 1], tags, df_debug_tags, footprint_rows)
        with st.expander(f"【近 {stat_days} 日動向排行】 買賣超前 {footprint_rows} 大", expanded=True):
            render_clean_html_table(df_fb_main, f"買超前 {footprint_rows} 大")
            render_clean_html_table(df_fs_main, f"賣超前 {footprint_rows} 大")

        render_clean_html_table(df_daily_tracker, "02. 平日戰情追蹤矩陣 (近15日)")
        render_clean_html_table(df_s_dyn, "03. 一週集保籌碼雷達 (大戶存量與流量雙解碼)") 
        render_clean_html_table(df_inst, "04. 法人買賣超 (近10天)")
        render_clean_html_table(df_margin, "05. 散戶資券餘額 (近10天)")
        render_clean_html_table(df_day_trade, "06. 現股當沖明細 (近10天)")

        st.divider()
        st.info("請將下方所需資料複製後貼給 AI 進行深度分析或稽核。")
        with st.expander(f"給 AI 的實戰精華資料包 (CSV格式)", expanded=True):
            p1 = f"請依下面最新的盤後資料與系統兵推報告幫我深度分析 {user_stock_id} {name} 的量化籌碼。\n\n"
            p1 += f"{company_info_text}\n\n"
            p1 += f"【系統算出之純淨主力加權防守價 (Net VWAP)】: {vwap_str} 元\n"
            p1 += f"【核心分點控盤率 (相對於自由流通籌碼)】: {core_c_value}%\n\n"
            p1 += format_to_csv_string(df_daily_tracker, "平日戰情追蹤矩陣 (近15日)")
            p1 += format_to_csv_string(df_s_dyn.head(4) if not df_s_dyn.empty else df_s_dyn, "一週集保籌碼雷達 (近4週)")
            p1 += format_to_csv_string(df_inst.head(10) if not df_inst.empty else df_inst, "法人買賣超 (近10天)")
            p1 += format_to_csv_string(df_margin.head(10) if not df_margin.empty else df_margin, "散戶資券餘額 (近10天)")
            st.code(p1, language="text")

        st.success(f"系統升級完畢。已成功處理 {user_stock_id}。")
        gc.collect()
