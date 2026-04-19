import streamlit as st
import requests
import pandas as pd
import numpy as np
import datetime
import re
import concurrent.futures
import urllib.request
import ssl
import urllib3
from io import StringIO
from plotly.subplots import make_subplots
import plotly.graph_objects as go

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="全息量化系統 (V50.05版)", layout="wide", initial_sidebar_state="expanded")
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

GITHUB_MANUAL_URL = "https://raw.githubusercontent.com/tonehsie/stock/refs/heads/main/README.md"

CSS = """
<style>
.table-container { overflow: auto; max-height: 480px; width: 100%; margin-bottom: 25px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.table-container table { width: 100% !important; border-collapse: separate !important; border-spacing: 0; font-size: 15px !important; font-family: sans-serif; background-color: #fff; }
.table-container th, .table-container td { white-space: nowrap !important; padding: 10px 12px !important; border-bottom: 1px solid #dee2e6; border-right: 1px solid #dee2e6; vertical-align: middle; }
.table-container th { border-top: 1px solid #dee2e6; word-break: keep-all !important; text-align: center !important; background-color: #f1f3f5 !important; color: #333 !important; font-weight: 700 !important; line-height: 1.4; position: sticky; top: 0; z-index: 3; }
.table-container th:first-child, .table-container td:first-child { position: sticky; left: 0; background-color: #f8f9fa; z-index: 4; font-weight: bold; text-align: center !important; border-left: 1px solid #dee2e6; }
.table-container thead th:first-child { z-index: 5; }

.text-left { text-align: left !important; }
.text-right { text-align: right !important; font-variant-numeric: tabular-nums; }
.loss-warning { color: #d9480f; font-weight: bold; }
.highlight-red { color: #d32f2f; font-weight: bold; }
.highlight-green { color: #2e7d32; font-weight: bold; }
.info-box { background-color: #f8f9fa; padding: 15px 20px; border-radius: 8px; margin-bottom: 25px; border-left: 6px solid #1e3a8a; font-size: 1.1rem; font-weight: bold; color: #1e3a8a; }
.section-title { margin-top: 35px; margin-bottom: 15px; color: #1e3a8a; border-bottom: 2px solid #1e3a8a; padding-bottom: 5px; font-size: 1.3rem !important; font-weight: 700 !important; }
.category-title { font-size: 1.6rem !important; font-weight: 900 !important; margin-top: 40px; color: #333; }
.stTabs [data-baseweb='tab-list'] { gap: 10px; }
.stTabs [data-baseweb='tab'] { height: 50px; white-space: pre-wrap; background-color: #f8f9fa; border-radius: 4px 4px 0 0; padding: 10px 20px; font-weight: bold; }
.stTabs [aria-selected='true'] { background-color: #e3f2fd !important; color: #1e3a8a !important; border-bottom: 3px solid #1e3a8a !important; }
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
        return "⚠️ 無法載入說明書，請確認 GitHub Raw 網址是否正確。"
    except Exception as e: return f"⚠️ 說明書載入失敗: {e}"

@st.cache_data(ttl=300, show_spinner=False)
def get_api_usage(token):
    try:
        r = requests.get(f"https://api.web.finmindtrade.com/v2/user_info?token={token}", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data.get("user_count", 0), data.get("api_request_limit", 0)
    except: pass
    return None, None

st.sidebar.header("🎛️ 戰術參數控制面板")
kline_days = st.sidebar.slider("K線顯示天數 (圖表景深)", 30, 600, 270, 10)
lookback_days = st.sidebar.selectbox("長線籌碼回溯天數 (全局黏著度分母)", [20, 60, 90, 120], index=1)
stickiness_threshold = st.sidebar.slider("主力黏著度門檻 (%)", 10.0, 80.0, 50.0, 5.0)
footprint_days = st.sidebar.slider("足跡明細追蹤天數 (顯示範圍)", 3, 60, 20, 1)
footprint_rows = st.sidebar.slider("足跡矩陣顯示筆數 (多空各 N 名)", 5, 50, 15, 5)
firepower_threshold = st.sidebar.slider("買方火力倍數門檻", 1.0, 5.0, 1.5, 0.1)
st.sidebar.divider()
st.sidebar.markdown("### 🧠 淨化籌碼引擎")
filter_day_trade = st.sidebar.checkbox("剔除散戶與隔日沖，計算「純淨加權均價」", value=True)
st.sidebar.divider()
ma_short = st.sidebar.number_input("短均線 (天)", min_value=1, max_value=20, value=10)
ma_mid = st.sidebar.number_input("中均線/防守線 (天)", min_value=20, max_value=100, value=60)
ma_long = st.sidebar.number_input("長均線 (天)", min_value=100, max_value=300, value=240)

st.title("📱 全息量化系統 (V50.05 數學核心零死角版)")
user_count, api_limit = get_api_usage(FINMIND_TOKEN)
usage_text = f" | 🔑 FinMind 額度: {user_count} / {api_limit}" if user_count is not None else ""
st.caption(f"🚀 V50.05 終極數學重構：修復分點抹零漏洞、阻斷雷達時序污染、剔除零價均價坍塌。{usage_text}")

with st.expander("📖 點此閱讀【全息量化系統】四大核心模組終極實戰說明書", expanded=False):
    manual_text = fetch_github_manual(GITHUB_MANUAL_URL)
    st.markdown(manual_text, unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])
with col1: 
    user_stock_id = st.text_input("個股代號", value="2330")
with col2: 
    dead_chip_input = st.text_input("死籌碼 % (董監事或董監事+大股東持股，留空自動抓)")
run_btn = st.button("🚀 啟動 V50.05 決策引擎", use_container_width=True, key="run_engine")

def safe_to_num(series, fill_val=0):
    if pd.api.types.is_numeric_dtype(series): return series.fillna(fill_val)
    return pd.to_numeric(series.astype(str).str.replace(',', '', regex=False).str.replace('%', '', regex=False).str.strip(), errors='coerce').fillna(fill_val)

@st.cache_data(ttl=3600, show_spinner=False)
def get_stock_name_v46(tid):
    try:
        r = requests.get(f"https://tw.stock.yahoo.com/quote/{tid}.TW", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code == 200:
            m = re.search(r'<title>(.*?)\s*\(', r.text)
            return m.group(1).strip() if m else ""
    except: pass
    return ""

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_finmind_v46(ds, sd, tid=None, ed=None):
    url = "https://api.finmindtrade.com/api/v4/data"
    p = {"dataset": ds, "start_date": sd}
    if tid: p["data_id"] = tid
    if ed: p["end_date"] = ed
    try: 
        r = requests.get(url, params=p, headers={"Authorization": f"Bearer {FINMIND_TOKEN}"}, timeout=15)
        if r.status_code == 200: return pd.DataFrame(r.json().get("data", []))
    except: pass
    return pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_branch_data_v46(dl, tid):
    if not dl: return pd.DataFrame()
    all_d = []
    with requests.Session() as session:
        session.headers.update({"Authorization": f"Bearer {FINMIND_TOKEN}"})
        def fs(d):
            try: 
                r = session.get("https://api.finmindtrade.com/api/v4/data", params={"dataset": "TaiwanStockTradingDailyReport", "data_id": tid, "start_date": d, "end_date": d}, timeout=15)
                if r.status_code == 200: return r.json().get("data", [])
            except: pass
            return []
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
            for r in ex.map(fs, dl):
                if r: all_d.extend(r)
    df = pd.DataFrame(all_d)
    if not df.empty:
        for c in ['buy', 'sell', 'price']:
            if c in df.columns: 
                df[c] = safe_to_num(df[c])
            else:
                df[c] = 0.0
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def scrape_block_v46(tid, ad):
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
                if r.status_code == 200 and "data" in r.json():
                    for ro in r.json().get("data", []):
                        if tid in str(ro): rl.append([d, "TWSE", ro])
            except: pass
            try:
                r = session.get(f"https://www.tpex.org.tw/www/zh-tw/blockTrade/quote?date={dtp}&id=&response=json", timeout=5, verify=False)
                if r.status_code == 200 and "tables" in r.json() and r.json()["tables"]:
                    for ro in r.json()["tables"][0].get("data", []):
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
def scrape_director_v46(tid):
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
        f = fetch_finmind_v46("TaiwanStockInfo", "2020-01-01")
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

def get_v47_intelligence(df_b_raw, df_p_raw, stick_thresh, global_days, dates_list):
    if df_b_raw.empty or df_p_raw.empty: return {}, pd.DataFrame()
    
    actual_global_days = df_b_raw['date'].nunique()
    if actual_global_days == 0: actual_global_days = 1

    df_p = df_p_raw.copy()
    df_p['date'] = pd.to_datetime(df_p['date'])
    df_p['avg_price'] = (df_p['close'] + df_p['max'] + df_p['min']) / 3
    range_diff = df_p['max'] - df_p['min']
    df_p['pos'] = np.where(range_diff == 0, 0.5, (df_p['close'] - df_p['min']) / range_diff.replace(0, 1))
    price_stats = df_p.set_index('date')[['pos']].to_dict('index')
    latest_close = df_p.sort_values('date', ascending=False)['close'].iloc[0] if not df_p.empty else 0

    df = df_b_raw.copy()
    df['date_dt'] = pd.to_datetime(df['date'])
    df['buy_amt'] = df['buy'] * df['price']
    df['sell_amt'] = df['sell'] * df['price']
    df['net_shares'] = df['buy'] - df['sell']

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

    tags, d_rows = {}, []
    gov_list = ["台銀", "土銀", "彰銀", "第一", "兆豐", "華南", "合庫", "台企銀"]

    for trader, g in df.groupby('securities_trader'):
        tb_shares = g['buy'].sum()
        ts_shares = g['sell'].sum()
        tv_shares = tb_shares + ts_shares
        
        if tv_shares == 0: continue

        active_days = g['date_dt'].nunique()
        stickiness = (active_days / actual_global_days) * 100
        
        net_t_shares = tb_shares - ts_shares
        if net_t_shares > 0:
            hoard_ratio = (net_t_shares / tb_shares * 100) if tb_shares > 0 else 0
        else:
            hoard_ratio = (abs(net_t_shares) / ts_shares * 100) if ts_shares > 0 else 0

        tb, ts = round(tb_shares / 1000), round(ts_shares / 1000)

        valid_buys = g[g['price'] > 0]
        valid_b_shares = valid_buys['buy'].sum()
        avg_b = (valid_buys['buy'] * valid_buys['price']).sum() / valid_b_shares if valid_b_shares > 0 else 0
        
        valid_sells = g[g['price'] > 0]
        valid_s_shares = valid_sells['sell'].sum()
        avg_s = (valid_sells['sell'] * valid_sells['price']).sum() / valid_s_shares if valid_s_shares > 0 else 0

        ld = pd.to_datetime(g['date']).max()
        pos = price_stats.get(ld, {'pos': 0.5})['pos']

        v60 = stats.loc[trader, 'net_60d'] if trader in stats.index else 0
        v20 = stats.loc[trader, 'net_20d'] if trader in stats.index else 0
        v5  = stats.loc[trader, 'net_5d'] if trader in stats.index else 0

        if any(x in trader for x in gov_list): tag = "🏦 [影子官股]"
        elif -200 <= v60 <= 200 and -200 <= v20 <= 200 and v5 >= 300: tag = "⚠️ [隔日沖大戶]"
        elif v60 >= 300 and v20 >= 100 and v5 <= -100: tag = "💀 [大戶出貨]"
        elif v60 >= 200 and v20 >= 100 and v5 >= 50: tag = "🔥 [長駐波段主]"
        elif v60 <= -200 and v20 <= -100 and v5 <= -100: tag = "📉 [趨勢空方]"
        elif v60 <= -100 and v5 >= 200: tag = "🩹 [被套牢]"
        elif stickiness >= stick_thresh: tag = "🥷 [潛伏造市者]"
        elif stickiness < 10.0 and abs(v5) > 50: tag = "🏃 [游擊過客]"
        else: tag = "🔵 一般/游擊"

        tags[trader] = tag
        b_str = f"{round(avg_b, 2):,.2f}"
        if avg_b > latest_close and avg_b > 0 and (tb-ts) > 0: b_str = f"⚠️(虧) {b_str}"

        d_rows.append({
            "分點名稱": trader, "最終標籤": tag,
            "近60日淨買(張)": int(v60), "近20日淨買(張)": int(v20), "近5日淨買(張)": int(v5),
            "黏著度(%)": round(stickiness, 1), "囤出貨率(%)": round(hoard_ratio, 1),
            "總買(張)": tb, "總賣(張)": ts, "淨留倉": int(tb - ts),
            "買均價": b_str, "賣均價": round(avg_s, 2) if avg_s > 0 else "-", "收盤位階": round(pos, 2)
        })
    return tags, pd.DataFrame(d_rows).sort_values('近60日淨買(張)', ascending=False)

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
    df['tag'] = df['securities_trader'].map(tags).fillna("🔵 一般/游擊")
    
    if is_filter_active: 
        valid_df = df[~df['tag'].str.contains("隔日沖|游擊|空方", na=False)]
    else: 
        valid_df = df

    if valid_df.empty: return 0.0, 0, 0, 0.0, []
    
    def calc_broker(x):
        b_v = x['buy'].sum()
        s_v = x['sell'].sum()
        valid_b = x[x['price'] > 0]
        b_a = (valid_b['buy'] * valid_b['price']).sum()
        valid_b_v = valid_b['buy'].sum()
        return pd.Series({'buy_vol': b_v, 'sell_vol': s_v, 'buy_amt': b_a, 'valid_buy_vol': valid_b_v})
        
    broker_stats = valid_df.groupby('securities_trader').apply(calc_broker)
    broker_stats['net_vol'] = broker_stats['buy_vol'] - broker_stats['sell_vol']
    
    top_buyers = broker_stats[broker_stats['net_vol'] > 0].sort_values('net_vol', ascending=False).head(dynamic_n)
    
    if top_buyers.empty: return 0.0, 0, 0, 0.0, []
    
    core_branch_names = top_buyers.index.tolist()
    
    top_buyers['avg_buy_price'] = (top_buyers['buy_amt'] / top_buyers['valid_buy_vol'].replace(0, np.nan)).fillna(0)
    total_net_vol = top_buyers['net_vol'].sum()
    
    vwap = round((top_buyers['avg_buy_price'] * top_buyers['net_vol']).sum() / total_net_vol, 2) if total_net_vol > 0 else 0.0
    net_accum = int(total_net_vol / 1000)
    active_buyers = len(top_buyers)
    
    c_value = 0.0
    if total_lots > 0:
        safe_dead_ratio = max(0.0, min(99.9, float(dead_chip_ratio)))
        free_float_ratio = (100.0 - safe_dead_ratio) / 100.0
        free_float_lots = total_lots * free_float_ratio
        if free_float_lots > 0:
            c_value = round((net_accum / free_float_lots) * 100, 2)

    return vwap, net_accum, active_buyers, c_value, core_branch_names

def get_core_period_net(df_raw, rank_dates, core_names):
    if df_raw.empty or not rank_dates or not core_names: return 0
    df_rank = df_raw[df_raw['date'].isin(rank_dates)].copy()
    df_rank = df_rank[df_rank['securities_trader'].isin(core_names)]
    # V50.05 數學重構：先在股數的絕對維度進行無損總和，最後才四捨五入轉換成張
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
                "標籤": intel_tags.get(trader, "🔵 一般"),
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
    
    # V50.05 數學重構：單日/多日榜單也必須套用 0 元防護，避免 API 缺漏污染排行均價
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
            if b.loc[i,'avg_b'] > latest_close and b.loc[i,'avg_b'] > 0 and b.loc[i,'net'] > 0: b_str = f"⚠️(虧) {b_str}"
            raw_tag = intel_tags.get(b.loc[i,'securities_trader'],'🔵 一般')
            attr = "🏃 短線" if any(x in raw_tag for x in ["隔日沖", "游擊"]) else "⚓ 中長線" if any(x in raw_tag for x in ["長駐", "潛伏", "官股"]) else "⚖️ 波段"
            r["買超分點"] = b.loc[i,'securities_trader']
            r["買_標籤"] = raw_tag
            r["買_週期"] = attr
            r["買超(張)"] = int(b.loc[i,'net'])
            r["買均價"] = b_str
            r["佔比"] = f"{(b.loc[i,'net']/tv)*100:.1f}%" if tv > 0 else "-"
        else: r["買超分點"], r["買_標籤"], r["買_週期"], r["買超(張)"], r["買均價"], r["佔比"] = "-", "-", "-", 0, "-", "-"
        
        if i < len(s): 
            raw_tag_s = intel_tags.get(s.loc[i,'securities_trader'],'🔵 一般')
            attr_s = "🏃 短線" if any(x in raw_tag_s for x in ["隔日沖", "游擊"]) else "⚓ 中長線" if any(x in raw_tag_s for x in ["長駐", "潛伏", "官股"]) else "⚖️ 波段"
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

def calculate_dynamic_large_holder_pct(row, threshold):
    levels_dict = {
        100: '100-200張_比例(%)',
        200: '200-400張_比例(%)',
        400: '400-600張_比例(%)',
        600: '600-800張_比例(%)',
        800: '800-1000張_比例(%)',
        1000: '1000張以上_比例(%)'
    }
    total = 0.0
    for k, v in levels_dict.items():
        if k >= threshold and v in row:
            val = pd.to_numeric(row.get(v, 0), errors='coerce')
            if pd.notna(val): total += val
    return total

def process_v27_ultimate_radar(df_wide, dead_chip_input, dynamic_dict, static_val, df_price, df_branch_raw, intel_tags):
    if df_wide.empty or len(df_wide) < 2: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df = df_wide.sort_values('日期', ascending=True).copy()
    df['dt_end'] = pd.to_datetime(df['日期'])
    if not df_price.empty:
        df_p = df_price.copy(); df_p['dt'] = pd.to_datetime(df_p['日期'])
        df_p = df_p.sort_values('dt'); df_p['ma20'] = df_p['收盤價(元)'].rolling(20, min_periods=1).mean()
        df = pd.merge_asof(df.sort_values('dt_end'), df_p[['dt', '收盤價(元)', 'ma20']], left_on='dt_end', right_on='dt', direction='backward')
    else: df['收盤價(元)'], df['ma20'] = 0, 0
        
    df['總人數變率(%)'] = (df['總人數(人)'].pct_change() * 100).round(2)
    
    out, d_math, d_fri = [], [], []
    prev_large_pct = None
    
    for i, row in df.iterrows():
        d_str = row['日期']
        p = row.get('收盤價(元)', 0)
        total_lots = row.get('總張數', 0)
        
        if pd.isna(p) or p <= 0 or total_lots <= 0: 
            out.append({"日期": d_str, "大戶原持股(%)": 0, "原始大戶變動(%)": 0, "純淨變動": 0, "雜訊": 0, "診斷": "⚪ 初始化/數據不全"})
            # V50.05 數學防呆：遇到無效日絕對不可覆寫前值，確保 WoW 變動序列的剛性！
            continue
            
        cur_dead, _ = get_dead_chip_info(d_str, dead_chip_input, dynamic_dict, static_val, "")
        safe_dead_ratio = max(0.0, min(99.9, cur_dead))
        ct = get_smart_threshold(p, total_lots, safe_dead_ratio)
        
        current_large_pct = calculate_dynamic_large_holder_pct(row, ct)
        
        if prev_large_pct is None:
            raw_chg = 0.0
            p_chg = 0.0
            f_impact = 0.0
            adv = ["⚪ 初始化 (基準建立)"]
        else:
            raw_chg = round(current_large_pct - prev_large_pct, 2)
            valid_trading_dates = df_branch_raw[df_branch_raw['date'] <= d_str]['date'].unique()
            f_vol_exact = 0
            
            if len(valid_trading_dates) > 0:
                last_trading_date = max(valid_trading_dates)
                df_f = df_branch_raw[df_branch_raw['date'] == last_trading_date].copy()
                
                if not df_f.empty:
                    df_f_grouped = df_f.groupby('securities_trader')[['buy', 'sell']].sum().reset_index()
                    df_f_grouped['tag'] = df_f_grouped['securities_trader'].map(intel_tags).fillna("")
                    fn = df_f_grouped[df_f_grouped['tag'].str.contains("隔日沖|被套牢|游擊過客", na=False)].copy()
                    fn['net_buy_exact'] = (fn['buy'] - fn['sell']) / 1000
                    
                    fake_branches = fn[fn['net_buy_exact'] >= ct]
                    f_vol_exact = fake_branches['net_buy_exact'].sum()
                    
                    for _, fr in fake_branches.iterrows():
                        d_fri.append({"日期": d_str, "分點": fr['securities_trader'], "張數": round(fr['net_buy_exact'])})
                        
            f_impact = (f_vol_exact / max(1, total_lots)) * 100 
            p_chg = round(raw_chg - f_impact, 2)
            d_math.append({"日期": d_str, "原始變動": raw_chg, "隔日沖干擾": round(f_impact, 2), "純淨變動": p_chg})
            
            lev = 100 / (100 - safe_dead_ratio) if safe_dead_ratio > 0 else 1
            adv = []
            if row['總人數變率(%)'] > 2.0 and p_chg < 0: adv.append(f"💀 [逃命] 散戶增{row['總人數變率(%)']}%，大戶實質倒貨{abs(p_chg)}%")
            else:
                if p_chg * lev > 2.5 and row['收盤價(元)'] > row['ma20']: adv.append(f"🚀 [真軋空] 站上月線且大戶純淨買超{round(p_chg*lev, 2)}%")
                elif p_chg > 0.4 and row['收盤價(元)'] < row['ma20']: adv.append(f"🧱 [底位建倉] 跌破月線但主力吃貨{p_chg}%")
                elif p_chg < -1.0: adv.append(f"📉 [主力撤退] 大戶實質流出{abs(p_chg)}%")
                if f_impact > 1.2: adv.append(f"⚡ [隔日沖陷阱] 虛胖買盤潛藏{round(f_impact, 2)}%倒貨危機")
                
        prev_large_pct = current_large_pct
        out.append({"日期": d_str, "大戶原持股(%)": round(current_large_pct, 2), "原始大戶變動(%)": raw_chg, "純淨變動": p_chg, "雜訊": round(f_impact, 2), "診斷": " | ".join(adv) if adv else "🔵 盤整"})
        
    ddf = pd.DataFrame(out)
    df = pd.merge(df, ddf, on='日期', how='left')
    
    df['專家雷達診斷'] = df['診斷']
    df['純淨大戶變動(%)'] = df['純淨變動']
    df['隔日沖虛胖(%)'] = df['雜訊']
    
    res_df = df[['日期', '收盤價(元)', '大戶原持股(%)', '總人數變率(%)', '原始大戶變動(%)', '隔日沖虛胖(%)', '純淨大戶變動(%)', '專家雷達診斷']].sort_values('日期', ascending=False)
    res_df = res_df[~res_df['專家雷達診斷'].str.contains('初始化', na=False)]
    
    return res_df, pd.DataFrame(d_math), pd.DataFrame(d_fri)

def process_branch_diff(df_raw, actual_dates, fire_thresh, period_days=10):
    if df_raw.empty or not actual_dates: return pd.DataFrame()
    out = []
    df_raw_num = df_raw[['date', 'securities_trader', 'buy', 'sell']].copy()
    for d in actual_dates[:period_days]:
        df_d = df_raw_num[df_raw_num['date'] == d]
        if df_d.empty: continue
        buy_branches, sell_branches = df_d[df_d['buy'] > 0], df_d[df_d['sell'] > 0]
        buy_count, sell_count = buy_branches['securities_trader'].nunique(), sell_branches['securities_trader'].nunique()
        diff_count = buy_count - sell_count
        active_count = df_d[(df_d['buy'] > 0) | (df_d['sell'] > 0)]['securities_trader'].nunique()
        concentration = ((sell_count - buy_count) / active_count * 100) if active_count > 0 else 0
        total_buy_vol, total_sell_vol = buy_branches['buy'].sum(), sell_branches['sell'].sum()
        avg_b = total_buy_vol / buy_count if buy_count > 0 else 0
        avg_s = total_sell_vol / sell_count if sell_count > 0 else 0
        firepower = (avg_b / avg_s) if avg_s > 0 else (99.9 if avg_b > 0 else 1.0)
        diag = []
        if firepower >= fire_thresh and concentration > 5: diag.append(f"🔥 大戶火力壓制 ({fire_thresh}倍↑)")
        elif firepower < 0.7 and diff_count > 50: diag.append("💀 散戶螞蟻搬家 (主力倒貨)")
        elif active_count > 500 and firepower < 1.0: diag.append("⚠️ 籌碼極度發散 (熱門當沖雷區)")
        out.append({"日期": d, "活躍家數": active_count, "買賣家數差": diff_count, "籌碼集中度(%)": round(concentration, 1), "買方火力(倍)": round(firepower, 2), "鷹眼診斷": " | ".join(diag) if diag else "🔵 中性換手"})
    return pd.DataFrame(out)

def process_v30_daily_tracking(df_branch_raw, intel_tags, df_price, df_branch_diff, actual_dates, fire_thresh, period_days=5):
    if df_branch_raw.empty or len(actual_dates) < period_days: return pd.DataFrame(), pd.DataFrame()
    out, audit_smart_money = [], []
    df_b = df_branch_raw[['date', 'securities_trader', 'buy', 'sell', 'price']].copy()
    df_b = df_b.rename(columns={'buy': 'bs', 'sell': 'ss', 'price': 'pr'})
    df_b['tag'] = df_b['securities_trader'].map(intel_tags).fillna("🔵 一般")
    
    for d in actual_dates[:period_days]:
        pr_row = df_price[df_price['日期'] == d]
        cp = pr_row['收盤價(元)'].iloc[0] if not pr_row.empty else 0
        op = pr_row['開盤價(元)'].iloc[0] if not pr_row.empty else 0
        hp = pr_row['最高價(元)'].iloc[0] if not pr_row.empty else 0
        lp = pr_row['最低價(元)'].iloc[0] if not pr_row.empty else 0
        sp = pr_row['漲跌(元)'].iloc[0] if not pr_row.empty else 0
        
        diff_row = df_branch_diff[df_branch_diff['日期'] == d]
        bsd = diff_row['買賣家數差'].iloc[0] if not diff_row.empty else 0
        firepower = diff_row['買方火力(倍)'].iloc[0] if not diff_row.empty and '買方火力(倍)' in diff_row.columns else 1.0
        active_cnt = diff_row['活躍家數'].iloc[0] if not diff_row.empty and '活躍家數' in diff_row.columns else 0
        concentration = diff_row['籌碼集中度(%)'].iloc[0] if not diff_row.empty and '籌碼集中度(%)' in diff_row.columns else 0
        eye_diag = diff_row['鷹眼診斷'].iloc[0] if not diff_row.empty and '鷹眼診斷' in diff_row.columns else ""

        day_b = df_b[df_b['date'] == d]
        
        smart_b = day_b[day_b['tag'].str.contains('波段主|官股|潛伏造市者|大戶出貨', na=False)].copy()
        smart_b['valid_bs'] = np.where(smart_b['pr'] > 0, smart_b['bs'], 0)
        smart_b['amt'] = smart_b['valid_bs'] * smart_b['pr']
        
        smart_grouped = smart_b.groupby(['securities_trader', 'tag']).agg(bs=('bs','sum'), ss=('ss','sum'), valid_bs=('valid_bs','sum'), amt=('amt','sum')).reset_index()
        smart_grouped['net_vol'] = ((smart_grouped['bs'] - smart_grouped['ss']) / 1000).round().astype(int)
        
        short_b = day_b[day_b['tag'].str.contains('隔日沖大戶|被套牢|游擊過客', na=False)].copy()
        short_grouped = short_b.groupby('securities_trader')[['bs', 'ss']].sum().reset_index()
        short_grouped['net_vol'] = ((short_grouped['bs'] - short_grouped['ss']) / 1000).round().astype(int)
        
        if d == actual_dates[0]:
            for _, r in smart_grouped.iterrows():
                if r['net_vol'] != 0: audit_smart_money.append({"日期": d, "分點": r['securities_trader'], "標籤": r['tag'], "淨買超(張)": r['net_vol']})
        
        smart_net = smart_grouped['net_vol'].sum()
        short_trap = short_grouped['net_vol'].sum()
        
        s_ret = smart_grouped[smart_grouped['bs'] > smart_grouped['ss']].copy()
        if not s_ret.empty:
            s_ret['avg_p'] = (s_ret['amt'] / s_ret['valid_bs'].replace(0, np.nan)).fillna(0)
            s_ret['net_shares'] = s_ret['bs'] - s_ret['ss']
            total_n = s_ret['net_shares'].sum()
            smart_avg_cost = (s_ret['avg_p'] * s_ret['net_shares']).sum() / total_n if total_n > 0 else 0
        else:
            smart_avg_cost = 0
            
        gap = cp - smart_avg_cost if smart_avg_cost > 0 and cp > 0 else 0
        
        adv = []
        if cp <= 0: adv.append("⏸️ 股價無紀錄/暫停交易")
        else:
            day_range = hp - lp
            lower_shadow = min(cp, op) - lp
            if day_range > 0 and (lower_shadow / day_range) > 0.5 and smart_net > 0: adv.append("🛡️ 探底洗盤成功，主力護盤")
            if smart_net > 50 and gap > 0: adv.append("🔥 主動鎖碼/強勢推升")
            elif smart_net > 50 and gap < 0: adv.append("🩹 大戶接刀/弱勢護盤")
            elif smart_net < -100 and sp > 0: adv.append("📉 拉高派發/撤退")
            elif smart_net < -100 and sp <= 0: adv.append("💀 波段棄守/多殺多")
            
        if eye_diag and eye_diag != "🔵 中性換手": adv.append(eye_diag)
        elif not adv: adv.append("🔵 盤整/無明顯特徵")

        out.append({
            "日期": d, "收盤價(元)": cp if cp > 0 else "-", "漲跌(元)": sp if cp > 0 else "-", "聰明錢淨流(張)": int(smart_net), 
            "大戶淨加權均價": round(smart_avg_cost, 2) if smart_avg_cost > 0 else "-", 
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

def process_price(df):
    if df.empty: return pd.DataFrame()
    df_out = df.copy()
    
    if 'Trading_Volume' in df_out.columns: df_out['成交量(張)'] = (safe_to_num(df_out['Trading_Volume']) / 1000).round().astype(int)
    elif 'Trading_volume' in df_out.columns: df_out['成交量(張)'] = (safe_to_num(df_out['Trading_volume']) / 1000).round().astype(int)
    else: df_out['成交量(張)'] = 0
        
    df_out = df_out.rename(columns={"date":"日期","close":"收盤價(元)","spread":"漲跌(元)","open":"開盤價(元)","max":"最高價(元)","min":"最低價(元)"})
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]
    
    df_out["斷頭價(0.78)"] = (df_out["收盤價(元)"] * 0.78).round(2)
    cols_to_keep = ['日期','成交量(張)','開盤價(元)','最高價(元)','最低價(元)','收盤價(元)','漲跌(元)','斷頭價(0.78)']
    cols_to_keep = [c for c in cols_to_keep if c in df_out.columns]
    return df_out[cols_to_keep].sort_values('日期', ascending=False)

def process_technical_analysis(df_price, s_ma, m_ma, l_ma):
    if df_price.empty or len(df_price) < 30: return pd.DataFrame()
    df_ta = df_price.sort_values('日期', ascending=True).copy()
    df_ta[f'MA{s_ma}'] = df_ta['收盤價(元)'].rolling(window=s_ma, min_periods=1).mean().round(2)
    df_ta[f'MA{m_ma}'] = df_ta['收盤價(元)'].rolling(window=m_ma, min_periods=1).mean().round(2)
    df_ta[f'MA{l_ma}'] = df_ta['收盤價(元)'].rolling(window=l_ma, min_periods=1).mean().round(2)
    
    df_ta['中線乖離(%)'] = ((df_ta['收盤價(元)'] - df_ta[f'MA{m_ma}']) / df_ta[f'MA{m_ma}'].replace(0, np.nan) * 100).round(2)
    
    cond_up = df_ta['收盤價(元)'] > df_ta[f'MA{m_ma}']
    cond_down = df_ta['收盤價(元)'] < df_ta[f'MA{m_ma}']
    df_ta['技術面診斷'] = np.where(cond_up, "🟢 站上中線防守", np.where(cond_down, "🔴 跌破中線防守", "🔵 盤整"))
    df_ta.rename(columns={f'MA{m_ma}': f'MA{m_ma}(中線)', f'MA{l_ma}': f'MA{l_ma}(長線)'}, inplace=True)
    return df_ta.sort_values('日期', ascending=False)

def process_tdcc(df):
    if df.empty: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df = df[~df['HoldingSharesLevel'].astype(str).str.contains('差異數')].copy()
    df['LevelClean'] = df['HoldingSharesLevel'].apply(clean_level_by_math)
    df['unit'] = (safe_to_num(df.get('unit', 0)) / 1000).round().astype(int)
    df['people'] = safe_to_num(df['people']).astype(int)
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
    for l in lvls: 
        df_w[f"{l}_張數"], df_w[f"{l}_人數"], df_w[f"{l}_比例(%)"] = p_u[l], p_p[l], (p_u[l] / df_t['總張數'].replace(0, np.nan) * 100).fillna(0).round(2)
    df_w = df_w.rename(columns={'date': '日期'}).sort_values('日期', ascending=False)
    df_unit = pd.merge(df_t[['date', '總張數']], p_u[['date']+lvls], on='date').rename(columns={'date': '日期'}).sort_values('日期', ascending=False)
    df_ppl = pd.merge(df_t[['date', '總人數(人)']], p_p[['date']+lvls], on='date').rename(columns={'date': '日期'}).sort_values('日期', ascending=False)
    return df_w, df_unit, df_ppl

def process_tdcc_dynamic(df_share_wide, df_price, dead_chip_input, dynamic_dict, static_val, chip_engine):
    if df_share_wide.empty or df_price.empty: return pd.DataFrame()
    df_s, df_p = df_share_wide.copy(), df_price.copy()
    df_s['dt'], df_p['dt'] = pd.to_datetime(df_s['日期']), pd.to_datetime(df_p['日期'])
    df_m = pd.merge_asof(df_s.sort_values('dt'), df_p.sort_values('dt')[['dt', '收盤價(元)']], on='dt', direction='backward').sort_values('dt', ascending=False)
    out = []
    for _, row in df_m.iterrows():
        p = row.get('收盤價(元)', 0)
        if pd.isna(p) or p <= 0: continue
        cur_dead, cl = get_dead_chip_info(row['日期'], dead_chip_input, dynamic_dict, static_val, chip_engine)
        total_lots = row.get('總張數', 0)
        cap = total_lots / 10000
        safe_dead_ratio = max(0.0, min(99.9, cur_dead))
        ct = get_smart_threshold(p, total_lots, safe_dead_ratio)
        
        lp = calculate_dynamic_large_holder_pct(row, ct)
        
        cd, st_val = "-", "無董監事持股數據"
        if 0 < safe_dead_ratio < 100:
            cv = max(0, (lp - safe_dead_ratio) / (100.0 - safe_dead_ratio))
            st_val = "🔴 絕對控盤" if cv >= 0.5 else "🟡 高度鎖碼" if cv >= 0.3 else "🔵 初步集結" if cv >= 0.15 else "⚪ 籌碼渙散"
            cd = round(cv * 100, 2)
        out.append({"日期": row['日期'], "收盤價(元)": p, "股本(億)": round(cap, 2), "大戶精算門檻": f"系統判定 ({int(ct)}張)", "大戶原持股(%)": round(lp, 2), "董監死籌碼(%)": f"{float(safe_dead_ratio):.2f}% ({cl})" if safe_dead_ratio > 0 else "-", "純淨活大戶C_Value(%)": cd, "實戰判定": st_val})
    return pd.DataFrame(out)

def process_day_trading(df):
    if df.empty: return pd.DataFrame()
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
    if df.empty: return pd.DataFrame()
    for c in ["MarginPurchaseBuy", "MarginPurchaseSell", "MarginPurchaseCashRepayment", "MarginPurchaseTodayBalance", "MarginPurchaseYesterdayBalance", "ShortSaleBuy", "ShortSaleSell", "ShortSaleCashRepayment", "ShortSaleTodayBalance", "OffsetLoanAndShort", "ShortSaleYesterdayBalance"]:
        if c in df.columns: df[c] = safe_to_num(df[c]).round().astype(int)
    df = df.rename(columns={"date":"日期", "MarginPurchaseBuy":"融資買進(張)", "MarginPurchaseSell":"融資賣出(張)", "MarginPurchaseCashRepayment":"融資現償(張)", "MarginPurchaseTodayBalance":"融資餘額(張)", "ShortSaleBuy":"融券買進(張)", "ShortSaleSell":"融券賣出(張)", "ShortSaleTodayBalance":"融券餘額(張)", "OffsetLoanAndShort":"資券相抵(張)"})
    df = df.loc[:, ~df.columns.duplicated()]
    for c in ["融資買進(張)", "融資賣出(張)", "融資現償(張)", "融資餘額(張)", "融券買進(張)", "融券賣出(張)", "融券餘額(張)", "資券相抵(張)"]:
        if c in df.columns:
            df[c] = (safe_to_num(df[c]) / 1000).round().astype(int)
    if '融資餘額(張)' in df.columns and 'MarginPurchaseYesterdayBalance' in df.columns:
        prev_margin = (safe_to_num(df['MarginPurchaseYesterdayBalance']) / 1000).round().astype(int)
        df['融資增減(張)'] = df['融資餘額(張)'] - prev_margin
    if '融券餘額(張)' in df.columns and 'ShortSaleYesterdayBalance' in df.columns:
        prev_short = (safe_to_num(df['ShortSaleYesterdayBalance']) / 1000).round().astype(int)
        df['融券增減(張)'] = df['融券餘額(張)'] - prev_short
    cols = [c for c in ['日期','融資買進(張)','融資賣出(張)','融資現償(張)','融資餘額(張)','融資增減(張)','融券買進(張)','融券賣出(張)','融券餘額(張)','融券增減(張)','資券相抵(張)'] if c in df.columns]
    return df[cols].tail(10).sort_values('日期', ascending=False)

def process_inst(df):
    if df.empty: return pd.DataFrame()
    pdf = df.pivot_table(index='date', columns='name', values=['buy', 'sell'], fill_value=0).reset_index()
    pdf.columns = ['_'.join(c).strip('_') for c in pdf.columns.values]
    out = pd.DataFrame({'日期': pdf['date']})
    f_b = safe_to_num(pdf.get('buy_Foreign_Investor',0))
    f_s = safe_to_num(pdf.get('sell_Foreign_Investor',0))
    out['外資買賣超(張)'] = ((f_b - f_s) / 1000).round().astype(int)
    i_b = safe_to_num(pdf.get('buy_Investment_Trust',0))
    i_s = safe_to_num(pdf.get('sell_Investment_Trust',0))
    out['投信買賣超(張)'] = ((i_b - i_s) / 1000).round().astype(int)
    ds_b = safe_to_num(pdf.get('buy_Dealer_self',0))
    ds_s = safe_to_num(pdf.get('sell_Dealer_self',0))
    out['自營商(自行)買賣超'] = ((ds_b - ds_s) / 1000).round().astype(int)
    dh_b = safe_to_num(pdf.get('buy_Dealer_Hedging',0))
    dh_s = safe_to_num(pdf.get('sell_Dealer_Hedging',0))
    out['自營商(避險)買賣超'] = ((dh_b - dh_s) / 1000).round().astype(int)
    out['三大法人買賣超(張)'] = out['外資買賣超(張)'] + out['投信買賣超(張)'] + out['自營商(自行)買賣超'] + out['自營商(避險)買賣超']
    return out.tail(10).sort_values('日期', ascending=False)

def process_fut_inst(df):
    if df.empty: return pd.DataFrame()
    df['net'] = safe_to_num(df['long_open_interest_balance_volume']) - safe_to_num(df['short_open_interest_balance_volume'])
    pdf = df.pivot_table(index='date', columns='institutional_investors', values='net', fill_value=0).reset_index()
    pdf.columns.name = None
    for col in ['Foreign_Investor', 'Investment_Trust', 'Dealer']:
        if col not in pdf.columns: pdf[col] = 0
    return pdf.rename(columns={'date': '日期', 'Foreign_Investor': '外資多空(口)', 'Investment_Trust': '投信多空(口)', 'Dealer': '自營多空(口)'}).tail(10).sort_values('日期', ascending=False)

def process_per(df):
    if df.empty: return pd.DataFrame()
    df_out = df.copy().rename(columns={"date":"日期","dividend_yield":"殖利率(%)","PER":"本益比(倍)","PBR":"淨值比(倍)"})
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]
    for col in ["殖利率(%)", "本益比(倍)", "淨值比(倍)"]: 
        if col in df_out.columns: df_out[col] = safe_to_num(df_out[col]).round(2)
    cols = [c for c in ['日期', '本益比(倍)', '淨值比(倍)', '殖利率(%)'] if c in df_out.columns]
    return df_out[cols].tail(10).sort_values('日期', ascending=False)

def process_disp(df):
    if df.empty: return pd.DataFrame()
    df_out = df.copy().rename(columns={"date":"公告日期","disposition_cnt":"處置次數","condition":"處置條件","measure":"處置措施","period_start":"處置起日","period_end":"處置迄日"})
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]
    cols = [c for c in ['公告日期', '處置次數', '處置起日', '處置迄日', '處置條件', '處置措施'] if c in df_out.columns]
    return df_out[cols].tail(5).sort_values('公告日期', ascending=False)

def process_div(df):
    if df.empty: return pd.DataFrame()
    df_out = df.rename(columns={"date": "公告日期", "year": "股利年份", "StockEarningsDistribution": "盈餘配股(元)", "StockStatutorySurplus": "公積配股(元)", "CashEarningsDistribution": "盈餘配息(元)", "CashStatutorySurplus": "公積配息(元)"})
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]
    cols = [c for c in ["公告日期", "股利年份", "盈餘配息(元)", "公積配息(元)", "盈餘配股(元)", "公積配股(元)"] if c in df_out.columns]
    if '股利年份' in df_out.columns:
        year_num = safe_to_num(df_out['股利年份'].astype(str).str.replace('年', '').str.strip(), fill_val=np.nan)
        recent = sorted(year_num.dropna().unique(), reverse=True)[:5]
        return df_out[year_num.isin(recent)][cols].sort_values('公告日期', ascending=False)
    return df_out[cols].sort_values('公告日期', ascending=False).head(10)

def process_cbas(df, current_stock_price, df_cb_info=None):
    if df.empty: return pd.DataFrame()
    df_out = df.copy().rename(columns={"date": "日期", "cb_id": "可轉債代號", "cb_name": "可轉債名稱", "conversion_price": "轉換價(元)", "ConversionPrice": "轉換價(元)", "underlying_stock_price": "標的股價(元)", "PriceOfUnderlyingStock": "標的股價(元)", "outstanding_amount": "未償還餘額", "OutstandingAmount": "未償還餘額", "outstanding_balance": "未償還餘額", "close": "CB收盤價", "closing_price": "CB收盤價", "conversion_premium_rate": "溢價率(%)", "premium_rate": "溢價率(%)", "PremiumRate": "溢價率(%)", "theoretical_value": "轉換價值", "TheoreticalValue": "轉換價值"})
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]
    
    if "可轉債代號" in df_out.columns: df_out['可轉債代號'] = df_out['可轉債代號'].astype(str).str.replace(',', '', regex=False).str.replace('.0', '', regex=False).str.strip()
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
            df_cb_info_clean['可轉債代號'] = df_cb_info_clean['可轉債代號'].astype(str).str.replace(',', '', regex=False).str.replace('.0', '', regex=False).str.strip()
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

def generate_ai_hawk_eye(df_daily, df_radar, df_fingerprint, df_diff, fire_thresh):
    alerts = []
    if not df_daily.empty and len(df_daily) >= 1:
        today_d = df_daily.iloc[0]
        alerts.append("#### 1. 矩陣金流剖析 (聰明錢與成本底牌)")
        flow_str = f"今日聰明錢淨流入 **{today_d['聰明錢淨流(張)']} 張**。"
        if today_d['均價落差'] != "-":
            try:
                gap_val = float(str(today_d['均價落差']).replace(',', '').strip())
                chg_val = float(str(today_d['漲跌(元)']).replace(',', '').strip()) if today_d['漲跌(元)'] not in ["-", ""] else 0.0
                if gap_val > 0 and today_d['聰明錢淨流(張)'] > 0: alerts.append(f"> 🟢 **【主動鎖碼】** {flow_str} 大戶買進均價低於收盤價 (落差 +{gap_val})。主力具備強勢推升意願。")
                elif gap_val < 0 and today_d['聰明錢淨流(張)'] > 0: alerts.append(f"> 🔴 **【接刀套牢】** {flow_str} 大戶買進均價高於收盤價 (落差 {gap_val})。主力護盤已被套牢，易引發停損賣壓！")
                elif today_d['聰明錢淨流(張)'] < -100 and chg_val > 0: alerts.append(f"> 🔴 **【拉高派發】** 今日股價收紅，聰明錢卻趁機撤退 **{today_d['聰明錢淨流(張)']} 張**。主力逢高倒貨，追高風險大。")
                elif today_d['聰明錢淨流(張)'] < -100: alerts.append(f"> 💀 **【波段棄守】** 股價走弱且聰明錢大舉撤退 **{today_d['聰明錢淨流(張)']} 張**。長線防守線可能崩潰。")
                else: alerts.append("> ⚪ 今日聰明錢無明顯極端進出，大戶成本線持平。")
            except: alerts.append("> ⚪ 今日聰明錢數值解析中性。")
        else: alerts.append("> ⚪ 今日大戶無明顯動作，成本線無法精算。")
    return alerts

def render_clean_html_table(df, title=""):
    if df is None or df.empty:
        if title: st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
        st.warning("此區塊查無數據。")
        return

    text_keywords = ['日期', '分點', '標籤', '週期', '名稱', '姓名', '身份別', '條件', '措施', '診斷', '代號']
    
    html = ""
    if title: html += f"<div class='section-title'>{title}</div>"
    html += "<div class='table-container'><table>"
    
    html += "<thead><tr>"
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
                if "⚠️(虧)" in s:
                    clean_num = s.replace("⚠️(虧)", "").strip()
                    display_val = f"<span class='loss-warning'>⚠️(虧) {clean_num}</span>"
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
# 📌 執行主引擎
# ==========================================
if run_btn:
    if not user_stock_id.strip(): 
        st.warning("⚠️ 請先在上方輸入股票代號！")
        st.stop()

    with st.spinner(f"正在啟動 V50.05 決策引擎 (雙向卷軸渲染中)..."):
        name = get_stock_name_v46(user_stock_id)
        if not name: 
            st.error(f"⚠️ 查無股票代號 {user_stock_id} 的基本資料。")
            st.stop()
            
        industry, address = get_company_profile(user_stock_id)
            
        df_p_raw = fetch_finmind_v46("TaiwanStockPrice", (datetime.date.today() - datetime.timedelta(days=1095)).strftime("%Y-%m-%d"), user_stock_id)
        if df_p_raw.empty: 
            st.error("⚠️ 查無歷史股價資料。")
            st.stop()
        
        dates = sorted(df_p_raw['date'].unique().tolist(), reverse=True)
        if not dates: st.stop()
            
        max_len = lookback_days if len(dates) >= lookback_days else len(dates)
        if max_len == 0: max_len = 1
        d_end = dates[max_len-1]
        
        df_price = process_price(df_p_raw)
        curr_price = df_price['收盤價(元)'].iloc[0] if not df_price.empty else 0
        df_ta_full = process_technical_analysis(df_price, ma_short, ma_mid, ma_long)
        
        dynamic_dict, s_val, chip_eng, _ = scrape_director_v46(user_stock_id)
        df_b_raw = fetch_branch_data_v46(dates[:max_len], user_stock_id)
        
        if df_b_raw.empty:
            st.error(f"⚠️ 查無 {user_stock_id} 的分點進出資料，可能為暫停交易或 API 狀態異常，請稍後再試。")
            st.stop()
            
        tags, df_debug_tags = get_v47_intelligence(df_b_raw, df_p_raw, stickiness_threshold, max_len, dates)
        
        df_s_raw = fetch_finmind_v46("TaiwanStockHoldingSharesPer", d_end, user_stock_id)
        df_s_wide, df_s_unit, df_s_ppl = process_tdcc(df_s_raw)
        current_total_shares = df_s_wide['總張數'].iloc[0] if not df_s_wide.empty else 0
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
                display_cols = ['日期', '收盤價(元)', '純淨活大戶C_Value(%)', '純淨大戶變動(%)', '總人數變率(%)', '大戶精算門檻', '隔日沖虛胖(%)', '終極籌碼診斷']
                df_combined_display = df_combined_radar[[c for c in display_cols if c in df_combined_radar.columns]].sort_values('日期', ascending=False).head(8)

        df_twse, _ = scrape_block_v46(user_stock_id, dates)
        df_margin = process_margin(fetch_finmind_v46("TaiwanStockMarginPurchaseShortSale", d_end, user_stock_id))
        df_day_trade = process_day_trading(fetch_finmind_v46("TaiwanStockDayTrading", d_end, user_stock_id))
        df_inst = process_inst(fetch_finmind_v46("TaiwanStockInstitutionalInvestorsBuySell", d_end, user_stock_id))
        
        df_rev_raw = fetch_finmind_v46("TaiwanStockMonthRevenue", "2022-01-01", user_stock_id)
        df_rev = pd.DataFrame()
        if not df_rev_raw.empty:
            df_rev_raw['營收月份'] = df_rev_raw['revenue_year'].astype(str) + "-" + df_rev_raw['revenue_month'].astype(str).str.zfill(2)
            df_rev = df_rev_raw.rename(columns={"revenue":"月營收(百萬元)"})[['營收月份','月營收(百萬元)']].tail(24)
            df_rev['月營收(百萬元)'] = (safe_to_num(df_rev['月營收(百萬元)'])/1000000).round().astype(int)
            df_rev = df_rev.sort_values('營收月份', ascending=False)

        df_b_today = process_branch_v25(df_b_raw, 1, dates, tags, df_p_raw, stickiness_threshold, max_len)
        df_b_prev1 = process_branch_v25(df_b_raw, 1, dates[1:], tags, df_p_raw, stickiness_threshold, max_len)
        df_b_3 = process_branch_v25(df_b_raw, 3, dates, tags, df_p_raw, stickiness_threshold, max_len)
        df_b_10 = process_branch_v25(df_b_raw, 10, dates, tags, df_p_raw, stickiness_threshold, max_len)
        df_b_60 = process_branch_v25(df_b_raw, max_len, dates, tags, df_p_raw, stickiness_threshold, max_len)

        df_gov = pd.DataFrame()
        if not df_b_today.empty: df_gov = df_b_today[df_b_today.astype(str).apply(lambda x: x.str.contains('|'.join(["台銀", "土銀", "彰銀", "第一", "兆豐", "華南", "合庫", "台企銀"]))).any(axis=1)]
        df_p_sum, df_p_det = scrape_fubon_pledge(df_p_raw, user_stock_id)
        df_fut = process_fut_inst(fetch_finmind_v46("TaiwanFuturesInstitutionalInvestors", d_end, "TX"))
        df_div = process_div(fetch_finmind_v46("TaiwanStockDividend", "2015-01-01", user_stock_id))
        df_per = process_per(fetch_finmind_v46("TaiwanStockPER", d_end, user_stock_id))
        df_disp = process_disp(fetch_finmind_v46("TaiwanStockDispositionSecuritiesPeriod", (datetime.date.today()-datetime.timedelta(days=180)).strftime("%Y-%m-%d"), user_stock_id))
        
        df_cbas_raw = fetch_finmind_v46("TaiwanStockConvertibleBondDailyOverview", dates[0])
        df_cb_info_list = []
        if not df_cbas_raw.empty and 'cb_id' in df_cbas_raw.columns:
            cb_mask = df_cbas_raw['cb_id'].astype(str).str.replace(',', '', regex=False).str.startswith(user_stock_id)
            target_cbs = df_cbas_raw[cb_mask]['cb_id'].astype(str).str.replace(',', '', regex=False).str.replace('.0', '', regex=False).str.strip().unique()
            for cid in target_cbs:
                info_df = fetch_finmind_v46("TaiwanStockConvertibleBondInfo", "2000-01-01", tid=cid)
                if not info_df.empty: df_cb_info_list.append(info_df)
            df_cb_info = pd.concat(df_cb_info_list, ignore_index=True) if df_cb_info_list else pd.DataFrame()
            df_cbas = process_cbas(df_cbas_raw[cb_mask], curr_price, df_cb_info)
        else:
            df_cbas = pd.DataFrame()
        
        market_cap_str = "計算中..."
        if not df_price.empty and current_total_shares > 0: market_cap_str = f"{(curr_price * current_total_shares) / 100000:,.2f} 億"
            
        company_info_text = f"🏢 **【產業】** {industry} &nbsp;｜&nbsp; 💰 **【市值】** {market_cap_str} &nbsp;｜&nbsp; 📍 **【公司地址】** {address} &nbsp;｜&nbsp; 🔒 **【董監死籌碼】** {director_holding_str}"
        
        st.subheader(f"📊 {user_stock_id} {name} 全息戰報 (V50.05版)")
        st.markdown(f"<div class='info-box'>{company_info_text}</div>", unsafe_allow_html=True)

        st.markdown("<div class='category-title'>🤖 AI 跨週期共振研判與診斷</div>", unsafe_allow_html=True)
            
        bias = ((curr_price - pure_vwap) / pure_vwap * 100) if pure_vwap > 0 else 0
        
        phase_title, phase_desc = "⚪ 籌碼中性 (自然換手)", "缺乏明顯波段主力介入，目前盤勢由一般市場力量主導，建議觀望技術面表態。"
        if pure_vwap > 0:
            if curr_price >= pure_vwap:
                if bias <= 10.0:
                    phase_title = "🟢 主力吃貨中 (安全建倉區)"
                    phase_desc = f"最新收盤價 ({curr_price}元) 貼近主力成本，乖離率僅 **{bias:.1f}%**。主力正在安全邊際內默默吸籌，下檔具備鐵板支撐，是風險報酬比極佳的潛伏期。"
                elif 10.0 < bias <= 50.0:
                    phase_title = "🔥 趨勢推升 (波段多頭起漲)"
                    phase_desc = f"股價穩定脫離成本區 (乖離率 **{bias:.1f}%**)，波段主力已點火發動攻勢。若伴隨大戶持續淨買超，顯示推升意願強烈，可抱緊順勢操作。"
                else:
                    phase_title = "⚠️ 嚴重過熱 (乖離破表)"
                    phase_desc = f"股價已呈極端噴出，乖離率高達 **{bias:.1f}%**，進入台股高危險過熱區。主力帳面獲利極大，隨時可能無情收割。若見聰明錢流出，請嚴格執行停利！"
            else:
                if bias >= -15.0:
                    phase_title = "🩹 主力防守戰 (跌破邊緣)"
                    phase_desc = f"股價跌破主力成本 (乖離 **{bias:.1f}%**)。主力帳面出現虧損，請密切觀察近期是否主動買超護盤，若跌破 -15% 則防線將徹底崩潰。"
                elif bias >= -30.0:
                    phase_title = "💀 主力套牢 / 棄守多殺多"
                    phase_desc = f"股價深度跌破防守價 (乖離 **{bias:.1f}%**)。波段主力已被嚴重套牢或直接停損棄守，極易引發多殺多恐慌賣壓，建議立刻避開。"
                else:
                    phase_title = "🩸 嚴重超跌 (乖離極大)"
                    phase_desc = f"股價崩跌遠低於主力成本 (乖離 **{bias:.1f}%**)。恐慌性拋售已達極致，籌碼徹底洗牌，隨時可能出現報復性死貓反彈。"

        trend_icon, trend_title, trend_desc = "⚪", "數據不足", "等待更多交易日資料累積。"
        if pure_vwap == 0: pass
        elif bias < -5.0:
            if net_60 > 0 and net_10 <= 0 and net_3 <= 0:
                trend_icon, trend_title = "📉", "防線破裂 (主力套牢/停損)"
                trend_desc = f"股價深度破線 (乖離 {bias:.1f}%)。長線大戶慘遭套牢，且中短線已出現轉賣停損跡象，極易引發多殺多，請勿摸底接刀。"
            elif net_60 <= 0 and net_10 <= 0 and net_3 <= 0:
                trend_icon, trend_title = "💀", "兵敗如山 (全面大逃殺)"
                trend_desc = "股價嚴重破線且短中長線主力全面大舉倒貨。籌碼與技術面雙雙潰敗，嚴禁摸底接刀。"
            elif net_3 > 0:
                trend_icon, trend_title = "🩹", "破線抵抗 (弱勢反彈)"
                trend_desc = "股價雖跌破主力成本，但近3日有特定買盤進場試圖抵抗。需觀察是否能強勢站回防守價，否則視為死貓反彈。"
            else:
                trend_icon, trend_title = "⚠️", "弱勢探底 (支撐失效)"
                trend_desc = "股價持續在主力成本之下弱勢運行，買盤退縮，防線實質失效，風險極高。"
        elif bias >= -5.0 and bias <= 10.0:
            if net_60 > 0 and net_10 > 0 and net_3 > 0:
                trend_icon, trend_title = "🟢", "三期共振 (完美吃貨)"
                trend_desc = f"股價貼近防守價 (乖離 {bias:.1f}%)，且短中長線主力全面站在買方！籌碼極度安定，是最具安全邊際的潛伏建倉期。"
            elif net_60 > 0 and (net_10 <= 0 or net_3 <= 0):
                trend_icon, trend_title = "🧱", "洗盤震盪 (回測支撐)"
                trend_desc = "長線底單穩固，但中短線出現調節賣壓。目前股價在防守價附近測試支撐，若能守穩則洗盤後仍有高點。"
            elif net_60 <= 0 and net_3 > 0:
                trend_icon, trend_title = "🚀", "谷底翻揚 (新血點火)"
                trend_desc = "長線雖無囤貨，但近期有新血主力進場強勢點火，股價試圖築底反轉，可輕倉跟隨短線動能。"
            else:
                trend_icon, trend_title = "⏳", "籌碼渙散 (方向不明)"
                trend_desc = "股價處於盤整區，但中長線主力並未積極建倉，走勢陷入隨機無序震盪，建議觀望。"
        else:
            if net_60 > 0 and net_10 > 0 and net_3 > 0:
                trend_icon, trend_title = "🔥", "趨勢推升 (強勢鎖碼)"
                trend_desc = f"股價強勢脫離成本區 (乖離 {bias:.1f}%)，且短中長線主力持續追價買進！趨勢極強，持股可抱緊順勢操作。"
            elif net_3 <= 0 and net_10 > 0:
                trend_icon, trend_title = "⚠️", "漲多調節 (高檔震盪)"
                trend_desc = "股價已大幅拉開利潤空間，近3日短線出現獲利了結賣壓。提防高檔震盪，不宜過度追高。"
            elif net_10 <= 0 and net_3 <= 0:
                trend_icon, trend_title = "🚨", "高檔派發 (主力出貨)"
                trend_desc = "股價處於高位，但中短線主力已開始連續大舉撤退！這是明確的高檔出貨訊號，請嚴格執行停利！"
            else:
                trend_icon, trend_title = "⚡", "高檔換手 (多空交戰)"
                trend_desc = "股價高檔噴出後震盪，多空分點激烈交戰中。一旦跌破短線均線支撐，極易引發獲利了結賣壓。"

        if bias > 50.0:
            bias_color, bias_desc = "#d32f2f", "⚠️ 嚴重過熱 (>50%)"
        elif bias > 10.0:
            bias_color, bias_desc = "#f59f00", "🔥 波段推升"
        elif bias >= 0.0:
            bias_color, bias_desc = "#2e7d32", "✅ 安全建倉區"
        elif bias >= -15.0:
            bias_color, bias_desc = "#f59f00", "🩹 跌破防守價"
        elif bias >= -30.0:
            bias_color, bias_desc = "#d32f2f", "💀 停損多殺多"
        else:
            bias_color, bias_desc = "#9c27b0", "🩸 嚴重超跌 (<-30%)"
        
        net3_color = "#d32f2f" if net_3 > 0 else "#2e7d32" if net_3 < 0 else "#333"
        net10_color = "#d32f2f" if net_10 > 0 else "#2e7d32" if net_10 < 0 else "#333"
        net60_color = "#d32f2f" if net_60 > 0 else "#2e7d32" if net_60 < 0 else "#333"
        
        c_color = "#d32f2f" if core_c_value >= 5.0 else "#f59f00" if core_c_value >= 2.0 else "#333"

        st.markdown(f"#### 🎯 【階段判定】: {phase_title}")
        st.markdown(f"> {phase_desc}")
        st.markdown("<br>", unsafe_allow_html=True)
                
        adv_html = f"""
        <div style='display:flex; gap:15px; flex-wrap:wrap; background-color:#ffffff; padding:20px; border-radius:8px; border:1px solid #e9ecef; margin-bottom:15px;'>
            <div style='flex:1; min-width:140px; border-right: 1px solid #eee; display: flex; flex-direction: column; justify-content: center;'>
                <span style='font-size:0.95rem; color:#666;'>🛡️ 淨留倉加權防守價 (Net VWAP)</span>
                <span style='font-size:1.5rem; font-weight:bold; color:#1e3a8a;'>{pure_vwap} 元</span>
                <span style='font-size:0.85rem; color:#888; margin-top:5px;'>前 {dynamic_n} 大核心 ({radar_reason})</span>
            </div>
            <div style='flex:1; min-width:140px; border-right: 1px solid #eee; display: flex; flex-direction: column; justify-content: center;'>
                <span style='font-size:0.95rem; color:#666;'>📏 主力成本乖離率</span>
                <span style='font-size:1.5rem; font-weight:bold; color:{bias_color};'>{bias:.1f}%</span>
                <span style='font-size:0.85rem; color:{bias_color}; margin-top:5px;'>{bias_desc}</span>
            </div>
            <div style='flex:1.2; min-width:180px; border-right: 1px solid #eee; display: flex; flex-direction: column; justify-content: center;'>
                <span style='font-size:0.95rem; color:#666;'>📊 核心前 {dynamic_n} 大 (實篩 {active_main_branches} 家) 多空淨留倉</span>
                <div style='font-size:0.95rem; margin-top:3px; line-height: 1.5;'>
                    近 &nbsp;3 日：<span style='color:{net3_color}; font-weight:bold;'>{net_3:+,} 張</span><br>
                    近 10 日：<span style='color:{net10_color}; font-weight:bold;'>{net_10:+,} 張</span><br>
                    近 60 日：<span style='color:{net60_color}; font-weight:bold;'>{net_60:+,} 張</span>
                </div>
                <div style='margin-top:8px; padding-top:8px; border-top:1px dashed #ccc; font-size:0.9rem; color:#444;'>
                    🎯 真實鎖碼率(C_Value): <span style='color:{c_color}; font-weight:900; font-size:1.1rem;'>{core_c_value}%</span>
                </div>
            </div>
            <div style='flex:1.5; min-width:200px; display: flex; flex-direction: column; justify-content: center;'>
                <span style='font-size:0.95rem; color:#666;'>📈 籌碼動向綜合診斷</span>
                <span style='font-size:1.3rem; font-weight:bold; color:#333; margin-top:3px;'>{trend_icon} {trend_title}</span>
                <span style='font-size:0.9rem; color:#555; margin-top:5px; line-height:1.4;'>{trend_desc}</span>
            </div>
        </div>
        """
        st.markdown(adv_html, unsafe_allow_html=True)
        
        st.caption(f"💡 備註：所有數據皆已透過 AI 自動 **{'過濾隔日沖' if filter_day_trade else '包含所有分點'}**。加權防守價已排除高頻刷量誤差。C_Value 為主力吸納自由流通活籌碼之百分比。")
        st.markdown("---")
        
        hawk_alerts = generate_ai_hawk_eye(df_daily_tracker, df_combined_display, pd.DataFrame(), df_b_diff, firepower_threshold)
        st.markdown("### 🦅 AI 鷹眼深度診斷報告")
        hawk_csv_text = "▼▼▼ 系統 AI 鷹眼深度診斷報告 ▼▼▼\n"
        for alert in hawk_alerts: 
            st.markdown(alert)
            clean_text = alert.replace('**', '').replace('> ', '').replace('🟢', '').replace('🔴', '').replace('💀', '').replace('⚠️', '').replace('⚪', '').strip()
            hawk_csv_text += f"{clean_text}\n"

        if not df_ta_full.empty:
            st.markdown(f"<div class='section-title'>📈 極簡純淨 K 線與成交量 (自訂 {kline_days} 日)</div>", unsafe_allow_html=True)
            df_plot = df_price.head(kline_days).copy()
            df_t_plot = df_ta_full[['日期', f'MA{ma_short}', f'MA{ma_mid}(中線)', f'MA{ma_long}(長線)']].head(kline_days).copy()
            df_plot = pd.merge(df_plot, df_t_plot, on='日期', how='inner').sort_values('日期', ascending=True)
            
            if not df_plot.empty:
                df_plot['日期'] = df_plot['日期'].astype(str)
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.75, 0.25])
                
                fig.add_trace(go.Scatter(x=df_plot['日期'], y=df_plot['收盤價(元)'], mode='markers', marker=dict(color='rgba(0,0,0,0)', size=2), hoverinfo='none', showlegend=False), row=1, col=1)
                fig.add_trace(go.Candlestick(x=df_plot['日期'], open=df_plot['開盤價(元)'], high=df_plot['最高價(元)'], low=df_plot['最低價(元)'], close=df_plot['收盤價(元)'], name='K線', increasing_line_color='#d32f2f', increasing_fillcolor='#d32f2f', decreasing_line_color='#2e7d32', decreasing_fillcolor='#2e7d32', whiskerwidth=0, hoverinfo='skip'), row=1, col=1)
                
                if f'MA{ma_short}' in df_plot.columns: fig.add_trace(go.Scatter(x=df_plot['日期'], y=df_plot[f'MA{ma_short}'], mode='lines', name=f'MA{ma_short}', line=dict(color='#ffa726', width=1.5), hoverinfo='skip'), row=1, col=1)
                if f'MA{ma_mid}(中線)' in df_plot.columns: fig.add_trace(go.Scatter(x=df_plot['日期'], y=df_plot[f'MA{ma_mid}(中線)'], mode='lines', name=f'MA{ma_mid}', line=dict(color='#29b6f6', width=2), hoverinfo='skip'), row=1, col=1)
                if f'MA{ma_long}(長線)' in df_plot.columns: fig.add_trace(go.Scatter(x=df_plot['日期'], y=df_plot[f'MA{ma_long}(長線)'], mode='lines', name=f'MA{ma_long}', line=dict(color='#ab47bc', width=2.5), hoverinfo='skip'), row=1, col=1)
                
                vol_colors = ['#d32f2f' if row['收盤價(元)'] >= row['開盤價(元)'] else '#2e7d32' for _, row in df_plot.iterrows()]
                fig.add_trace(go.Bar(x=df_plot['日期'], y=df_plot['成交量(張)'], marker_color=vol_colors, showlegend=False, name="成交量", hoverinfo='skip'), row=2, col=1)
                
                fig.update_layout(height=650, margin=dict(l=30, r=30, t=20, b=20), xaxis_rangeslider_visible=False, plot_bgcolor='white', paper_bgcolor='white', hovermode='x unified', showlegend=False)
                fig.update_xaxes(showgrid=False, zeroline=False, type='category', row=1, col=1)
                fig.update_yaxes(showgrid=True, gridcolor='#f0f0f0', zeroline=False, row=1, col=1)
                fig.update_xaxes(showgrid=False, zeroline=False, tickangle=45, type='category', row=2, col=1)
                fig.update_yaxes(showgrid=False, zeroline=False, row=2, col=1)
                
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        actual_foot_days = footprint_days if len(dates) >= footprint_days else len(dates)
        display_dates = dates[:actual_foot_days]
        
        st.markdown("<div class='category-title'>🕵️‍♂️ 主力分點全息透視區 (全維度折疊展開)</div>", unsafe_allow_html=True)
        st.info("💡 所有分點足跡與明細已集中於此，點擊展開即可查看。表格支援上下左右雙向滑動，直向顯示約 10 行以維持版面整潔。")
        
        df_fb_3, df_fs_3 = process_footprint(df_b_raw, display_dates, dates[:3], tags, df_debug_tags, dynamic_n)
        with st.expander(f"🔥 【近 3 日急單動向】 買賣超前 {dynamic_n} 大 (顯示 {actual_foot_days} 日足跡)"):
            render_clean_html_table(df_fb_3, f"🔥 【近 3 日急單動向】 近 3 日買超前 {dynamic_n} 大 (顯示 {actual_foot_days} 日足跡)")
            render_clean_html_table(df_fs_3, f"🔥 【近 3 日急單動向】 近 3 日賣超前 {dynamic_n} 大 (顯示 {actual_foot_days} 日足跡)")
            
        df_fb_10, df_fs_10 = process_footprint(df_b_raw, display_dates, dates[:10], tags, df_debug_tags, dynamic_n)
        with st.expander(f"📈 【近 10 日波段動向】 買賣超前 {dynamic_n} 大 (顯示 {actual_foot_days} 日足跡)"):
            render_clean_html_table(df_fb_10, f"📈 【近 10 日波段動向】 近 10 日買超前 {dynamic_n} 大 (顯示 {actual_foot_days} 日足跡)")
            render_clean_html_table(df_fs_10, f"📈 【近 10 日波段動向】 近 10 日賣超前 {dynamic_n} 大 (顯示 {actual_foot_days} 日足跡)")
            
        df_fb_60, df_fs_60 = process_footprint(df_b_raw, display_dates, dates[:60], tags, df_debug_tags, dynamic_n)
        with st.expander(f"⚓ 【近 60 日長線動向】 買賣超前 {dynamic_n} 大 (顯示 {actual_foot_days} 日足跡)"):
            render_clean_html_table(df_fb_60, f"⚓ 【近 60 日長線動向】 近 60 日買超前 {dynamic_n} 大 (顯示 {actual_foot_days} 日足跡)")
            render_clean_html_table(df_fs_60, f"⚓ 【近 60 日長線動向】 近 60 日賣超前 {dynamic_n} 大 (顯示 {actual_foot_days} 日足跡)")

        with st.expander(f"04. 主力分點 - 今日 ({dates[0]})"):
            render_clean_html_table(df_b_today)
        with st.expander(f"05. 主力分點 - 前一日"):
            render_clean_html_table(df_b_prev1)
        with st.expander("06. 點此展開過渡期分點 (近3日 / 10日 / 60日總和)"):
            render_clean_html_table(df_b_3, "主力分點 - 近 3 日")
            render_clean_html_table(df_b_10, "主力分點 - 近 10 日")
            render_clean_html_table(df_b_60, f"主力分點 - 近 {max_len} 日")
        with st.expander("07. 主力分點圖鑑 (三維動態檢驗)"):
            render_clean_html_table(df_debug_tags)

        st.markdown("<div class='category-title'>📊 核心戰情追蹤</div>", unsafe_allow_html=True)
        render_clean_html_table(df_daily_tracker, "01. 平日戰情追蹤矩陣 (合併家數差與火力)")
        render_clean_html_table(df_combined_display, "02. 一週集保籌碼雷達 (大戶存量與流量雙解碼)") 

        st.markdown("<div class='category-title'>🏦 法人與資券變化</div>", unsafe_allow_html=True)
        render_clean_html_table(df_gov, "08. 影子官股進出 (今日)")
        render_clean_html_table(df_inst, "09. 法人買賣超 (近10天)")
        render_clean_html_table(df_margin, "10. 散戶資券餘額 (近10天)")
        render_clean_html_table(df_day_trade, "11. 現股當沖明細 (近10天)")

        st.markdown("<div class='category-title'>📈 基本面與進階籌碼數據</div>", unsafe_allow_html=True)
        render_clean_html_table(df_rev, "13. 月營收 (百萬元) (近24個月)")
        with st.expander("📂 14. 點此展開集保分級表 (近8週)", expanded=False):
            render_clean_html_table(df_s_unit, "14-1. 集保分級 - 張數表")
            render_clean_html_table(df_s_ppl, "14-2. 集保分級 - 人數表")
            
        render_clean_html_table(df_per, "19. 本益比、淨值比與殖利率")
        render_clean_html_table(df_disp, "20. 處置有價證券狀態")
        render_clean_html_table(df_cbas, "21. CBAS 可轉債數據")

        st.divider()
        st.info("請將下方所需資料複製後貼給 Gemini 進行深度分析或稽核。")
        with st.expander(f"📋 給 Gemini 的 V50.05 實戰精華資料包 (CSV格式)", expanded=True):
            p1 = f"請依下面最新的盤後資料與系統鷹眼報告幫我深度分析 {user_stock_id} {name} 的量化籌碼，必須以我給的資料優先使用。\n\n"
            p1 += f"{company_info_text}\n\n"
            p1 += hawk_csv_text + "\n"
            p1 += f"【系統算出之純淨主力加權防守價 (Net VWAP)】: {pure_vwap} 元\n"
            p1 += f"【主力活籌碼真實鎖碼率 (C_Value)】: {core_c_value}%\n\n"
            p1 += f"【核心主力3日淨留倉】: {net_3} 張\n"
            p1 += f"【核心主力10日淨留倉】: {net_10} 張\n"
            p1 += f"【核心主力60日淨留倉】: {net_60} 張\n\n"
            
            p1 += format_to_csv_string(df_daily_tracker, "01. 平日戰情追蹤矩陣 (近5日)")
            p1 += format_to_csv_string(df_combined_display.head(4) if not df_combined_display.empty else df_combined_display, "02. 一週集保籌碼雷達 (近4週)")
            p1 += format_to_csv_string(df_inst.head(10) if not df_inst.empty else df_inst, "09. 法人買賣超 (近10天)")
            p1 += format_to_csv_string(df_margin.head(10) if not df_margin.empty else df_margin, "10. 散戶資券餘額 (近10天)")
            p1 += format_to_csv_string(df_day_trade.head(10) if not df_day_trade.empty else df_day_trade, "11. 現股當沖明細 (近10天)")
            p1 += format_to_csv_string(df_fut.head(10) if not df_fut.empty else df_fut, "12. 台指期貨三大法人未平倉 (大盤)")
            p1 += format_to_csv_string(df_rev.head(12) if not df_rev.empty else df_rev, "13. 月營收 (百萬元) (近12個月)")
            p1 += format_to_csv_string(df_p_sum, "15. 董監大股東質設總覽")
            p1 += format_to_csv_string(df_twse, "17. 鉅額交易明細 (近3日)")
            p1 += format_to_csv_string(df_per.head(10) if not df_per.empty else df_per, "19. 本益比、淨值比與殖利率")
            p1 += format_to_csv_string(df_disp, "20. 處置有價證券狀態")
            p1 += format_to_csv_string(df_cbas, "21. CBAS 可轉債數據")
            st.code(p1, language="text")

        st.divider()
        st.markdown("<div class='category-title'>🔍 系統底層數據 Raw Data Dump 驗證區 (CSV 格式 / 60天)</div>", unsafe_allow_html=True)
        with st.expander("點此展開系統原始擷取數據 (供驗證 00, 01 等模組計算邏輯)", expanded=False):
            st.info("💡 這裡傾印了供你人工/AI 稽核技術面與主力戰情所需的近 60 天核心基礎資料。")
            dump_text = "請協助驗證以下底層 Raw Data 邏輯是否正確：\n\n"
            
            df_price_dump = df_price.head(60).copy() if not df_price.empty else pd.DataFrame()
            dump_text += format_to_csv_string(df_price_dump, "Raw 00: 股價與成交量原始數據 (近 60 天)")
            dump_text += format_to_csv_string(df_b_diff_60, "Raw 01-A: 活躍券商與買賣家數差數據 (近 60 天)")
            dump_text += format_to_csv_string(df_daily_tracker_60, "Raw 01-B: 主力戰場追蹤矩陣 (近 60 天)")
            
            df_tdcc_dump = df_s_wide.head(10).copy() if not df_s_wide.empty else pd.DataFrame()
            dump_text += format_to_csv_string(df_tdcc_dump, "Raw 02: 集保股權分散表原始數據 (近 10 週)")
            
            st.code(dump_text, language="text")
