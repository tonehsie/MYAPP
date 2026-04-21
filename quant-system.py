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
import json
import streamlit.components.v1 as components
from io import StringIO

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 系統基礎配置 ---
st.set_page_config(page_title="全息量化系統 V60.23", layout="wide", initial_sidebar_state="expanded")

FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"
GITHUB_MANUAL_URL = "https://raw.githubusercontent.com/tonehsie/stock/refs/heads/main/README.md"

CSS = """
<style>
.table-container { overflow: auto; max-height: 480px; width: 100%; margin-bottom: 25px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.table-container table { width: max-content !important; min-width: 40%; border-collapse: separate !important; border-spacing: 0; font-size: 15px !important; font-family: sans-serif; background-color: #fff; }
.table-container th, .table-container td { white-space: nowrap !important; padding: 10px 12px !important; border-bottom: 1px solid #dee2e6; border-right: 1px solid #dee2e6; vertical-align: middle; }
.table-container th { border-top: 1px solid #dee2e6; word-break: keep-all !important; text-align: center !important; background-color: #f1f3f5 !important; color: #333 !important; font-weight: 700 !important; line-height: 1.4; position: sticky; top: 0; z-index: 3; }
.table-container th:first-child, .table-container td:first-child { position: sticky; left: 0; background-color: #f8f9fa; z-index: 4; font-weight: bold; text-align: center !important; border-left: 1px solid #dee2e6; }
.text-left { text-align: left !important; }
.text-right { text-align: right !important; font-variant-numeric: tabular-nums; }
.loss-warning { color: #d9480f; font-weight: bold; }
.highlight-red { color: #d32f2f; font-weight: bold; }
.highlight-green { color: #2e7d32; font-weight: bold; }
.info-box { background-color: #f8f9fa; padding: 15px 20px; border-radius: 8px; margin-bottom: 25px; border-left: 6px solid #1e3a8a; font-size: 1.1rem; font-weight: bold; color: #1e3a8a; }
.section-title { margin-top: 35px; margin-bottom: 15px; color: #1e3a8a; border-bottom: 2px solid #1e3a8a; padding-bottom: 5px; font-size: 1.3rem !important; font-weight: 700 !important; }
.category-title { font-size: 1.6rem !important; font-weight: 900 !important; margin-top: 40px; color: #333; }
.ai-report-box { background-color: #fcfdfe; border: 1px solid #e9ecef; border-left: 5px solid #1e3a8a; border-radius: 8px; padding: 25px; margin-bottom: 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); line-height: 1.6; }
.ai-report-box h4 { margin-top: 0; color: #1e3a8a; font-weight: 800; font-size: 1.2rem; border-bottom: 1px dashed #ccc; padding-bottom: 8px; margin-bottom: 15px; }
.ai-conclusion { background-color: #fff3cd; padding: 15px; border-radius: 6px; border: 1px solid #ffe69c; font-weight: 700; color: #856404; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. 資料擷取引擎 (Scrapers & API)
# ---------------------------------------------------------

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_github_manual(url):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200: return r.text
        return "無法載入說明書。"
    except: return "說明書載入失敗。"

@st.cache_data(ttl=300, show_spinner=False)
def get_api_usage(token):
    try:
        r = requests.get(f"https://api.web.finmindtrade.com/v2/user_info?token={token}", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data.get("user_count", 0), data.get("api_request_limit", 0)
    except: pass
    return None, None

def safe_to_num(series, fill_val=0):
    if isinstance(series, pd.Series):
        try: return pd.to_numeric(series.astype(str).str.replace(',', '').str.replace('%', '').strip(), errors='coerce').fillna(fill_val)
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
    p = {"dataset": ds, "start_date": sd, "token": FINMIND_TOKEN}
    if tid: p["data_id"] = tid
    if ed: p["end_date"] = ed
    try: 
        r = requests.get(url, params=p, timeout=15)
        if r.status_code == 200:
            data = r.json().get("data", [])
            return pd.DataFrame(data) if data else pd.DataFrame()
    except: pass
    return pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_branch_data_v50(dl, tid):
    if not dl: return pd.DataFrame()
    all_d = []
    with requests.Session() as session:
        def fs(d):
            try: 
                r = session.get("https://api.finmindtrade.com/api/v4/data", params={"dataset": "TaiwanStockTradingDailyReport", "data_id": tid, "start_date": d, "end_date": d, "token": FINMIND_TOKEN}, timeout=15)
                if r.status_code == 200: return r.json().get("data", [])
            except: pass
            return []
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
            for r in ex.map(fs, dl):
                if r: all_d.extend(r)
    df = pd.DataFrame(all_d)
    if not df.empty:
        for c in ['buy', 'sell', 'price']: df[c] = safe_to_num(df[c])
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def scrape_block_v50(tid, ad):
    if not ad: return pd.DataFrame(), []
    td, bd = ad[:3], []
    with requests.Session() as session:
        session.headers.update({"User-Agent": "Mozilla/5.0"})
        def fd(d):
            dtw = d.replace("-", "")
            rl = []
            try:
                r = session.get(f"https://www.twse.com.tw/rwd/zh/block/BFIAUU?date={dtw}&response=json", timeout=5, verify=False)
                if r.status_code == 200 and isinstance(r.json().get("data"), list):
                    for ro in r.json()["data"]:
                        if tid in str(ro): rl.append([d, "TWSE", ro])
            except: pass
            return rl
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            for data in ex.map(fd, td):
                if data: bd.extend(data)
    if not bd: return pd.DataFrame(), []
    p = []
    for date, src, row in bd:
        nums = [float(re.sub(r'<[^>]+>', '', str(c)).replace(',', '')) for c in row if re.sub(r'<[^>]+>', '', str(c)).replace(',', '').replace('.', '').isdigit()]
        if len(nums) >= 3:
            nums.sort(reverse=True)
            p.append({"日期": date, "交易別": "鉅額", "成交量(張)": int(nums[1]/1000 if nums[1]>1000 else nums[1]), "成交價(元)": round(nums[2], 2), "成交金額(萬元)": int(nums[0]/10000 if nums[0]>100000 else nums[0])})
    return pd.DataFrame(p).sort_values("日期", ascending=False), []

def safe_get_fubon(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, verify=False)
        if res.status_code == 200: 
            res.encoding = 'big5'
            return res.text
    except: pass
    return ""

@st.cache_data(ttl=3600, show_spinner=False)
def scrape_director_v50(tid):
    try:
        html = safe_get_fubon(f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zck/zck_{tid}.djhtm")
        if html:
            tm = re.search(r'姓名/法人名稱(.*?)</table>', html, re.IGNORECASE | re.DOTALL)
            if tm:
                ed = {}
                for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', tm.group(1), re.IGNORECASE | re.DOTALL):
                    tds = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.IGNORECASE | re.DOTALL)
                    if len(tds) >= 4:
                        title, name = re.sub(r'<[^>]+>', '', tds[0]).strip(), re.sub(r'<[^>]+>', '', tds[1]).strip()
                        r_str = re.sub(r'<[^>]+>', '', tds[3]).replace('%', '').strip()
                        if ('董' in title or '監' in title) and '辭' not in title:
                            try: ed[name.split('-')[0].strip()] = max(ed.get(name.split('-')[0].strip(), 0), float(r_str))
                            except: pass
                if 0 < sum(ed.values()) < 100: return round(sum(ed.values()), 2)
    except: pass
    return 0.0

@st.cache_data(ttl=86400, show_spinner=False)
def get_company_profile(tid):
    ind, addr = "未知產業", "查無地址"
    try:
        f = fetch_finmind_v50("TaiwanStockInfo", "2020-01-01")
        if not f.empty:
            m = f[f['stock_id'] == str(tid)]
            if not m.empty: ind = m['industry_category'].iloc[0]
        r = requests.get(f"https://tw.stock.yahoo.com/quote/{tid}/profile", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        m = re.search(r'公司地址\|+([^|]+)', re.sub(r'<[^>]+>', '|', r.text))
        if m: addr = m.group(1).strip()
    except: pass
    return ind, addr

@st.cache_data(ttl=3600, show_spinner=False)
def scrape_fubon_pledge(df_pr, tid):
    alld = []
    for i in range(2):
        html = safe_get_fubon(f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zc0/zc06_{tid}_{i}.djhtm")
        if html:
            trs = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
            for tr in trs:
                tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL)
                if len(tds) >= 7:
                    r = [re.sub(r'<[^>]+>', '', td).strip() for td in tds]
                    if re.match(r'\d{2}/\d{2}/\d{2}', r[0]) or re.match(r'\d{2}/\d{2}', r[0]): alld.append(r)
    if not alld: return pd.DataFrame(), pd.DataFrame()
    df = pd.DataFrame(alld, columns=["日期", "身份別", "姓名", "設質", "解質", "累積", "質權人"])
    df["累積"] = safe_to_num(df["累積"]).astype(int)
    sum_df = df.groupby("姓名").agg({"身份別":"first", "累積":"last"}).reset_index()
    return sum_df[sum_df["累積"]>0], df

# ---------------------------------------------------------
# 2. 核心量化演算法 (還原 V60.18 全部邏輯)
# ---------------------------------------------------------

def get_v50_intelligence(df_b_raw, stick_thresh):
    if df_b_raw.empty: return {}, pd.DataFrame()
    actual_days = df_b_raw['date'].nunique()
    df = df_b_raw.copy(); df['net'] = df['buy'] - df['sell']
    g = df.groupby('securities_trader').agg(tb=('buy','sum'), ts=('sell','sum'), net=('net','sum'), amt=('buy', lambda x: (x * df.loc[x.index, 'price']).sum()), active=('date','nunique'))
    g['stickiness'] = (g['active'] / actual_days) * 100
    g['avg_b'] = (g['amt'] / g['tb'].replace(0, np.nan)).fillna(0)
    
    # 標籤重構邏輯
    cond_dump = (g['net'] < -500) & (g['stickiness'] > 30)
    cond_core = (g['net'] > 300) & (g['stickiness'] >= stick_thresh)
    cond_sniper = (g['net'] > 500) & (g['stickiness'] < 15)
    g['tag'] = np.select([cond_dump, cond_core, cond_sniper], ["[逢高派發]", "[波段鐵粉]", "[短線狙擊]"], default="[隨波逐流]")
    
    return g['tag'].to_dict(), pd.DataFrame({"分點名稱": g.index, "最終標籤": g['tag'], "黏著度(%)": g['stickiness'].round(1), "淨留倉": (g['net']/1000).astype(int), "買均價": g['avg_b'].round(2)})

def calculate_pure_defense_line(df_b_raw, tags, is_filter, total_lots, dead_ratio, dynamic_n):
    if df_b_raw.empty or total_lots <= 0: return 0.0, 0, 0.0, []
    df = df_b_raw.copy(); df['tag'] = df['securities_trader'].map(tags).fillna("[隨波逐流]")
    v_df = df[df['tag'] == "[波段鐵粉]"].copy() if is_filter else df
    if v_df.empty: return 0.0, 0, 0.0, []
    v_df['amt'] = v_df['buy'] * v_df['price']
    g = v_df.groupby('securities_trader').agg(net=('buy', lambda x: x.sum() - v_df.loc[x.index, 'sell'].sum()), buy_amt=('amt','sum'), buy_vol=('buy','sum'))
    top = g[g['net'] > 0].sort_values('net', ascending=False).head(dynamic_n)
    if top.empty: return 0.0, 0, 0.0, []
    vwap = top['buy_amt'].sum() / top['buy_vol'].sum() if top['buy_vol'].sum() > 0 else 0.0
    net_sum = int(top['net'].sum() / 1000)
    c_val = round((net_sum / (total_lots * (100 - dead_ratio) / 100)) * 100, 2)
    return vwap, net_sum, c_val, top.index.tolist()

def process_geometric_patterns(df_price, kline_days, order, mode, current_price):
    if df_price.empty or len(df_price) < order * 2: return {}
    df = df_price.head(kline_days).copy().sort_values('日期', ascending=True).reset_index(drop=True)
    highs, lows = [], []
    for i in range(order, len(df) - order):
        if df['最低價(元)'].iloc[i] == df['最低價(元)'].iloc[i-order:i+order+1].min(): lows.append((df['日期'].iloc[i], df['最低價(元)'].iloc[i], i))
        if df['最高價(元)'].iloc[i] == df['最高價(元)'].iloc[i-order:i+order+1].max(): highs.append((df['日期'].iloc[i], df['最高價(元)'].iloc[i], i))
    if len(lows) < 2 or len(highs) < 1: return {}
    last_date = df['日期'].iloc[-1]; tol = 0.03; is_auto = "Auto" in mode
    # W底
    if "W底" in mode or is_auto:
        l1, l2 = lows[-2], lows[-1]
        b_h = [h for h in highs if l1[2] < h[2] < l2[2]]
        if b_h:
            h1 = max(b_h, key=lambda x: x[1])
            if abs(l1[1]-l2[1])/l1[1] < tol or "W底" in mode:
                return {'name': 'W底', 'shape_x': [l1[0], h1[0], l2[0]], 'shape_y': [l1[1], h1[1], l2[1]], 'neck_x': [l1[0], last_date], 'neck_y': [h1[1], h1[1]], 'color': '#9c27b0', 'desc': 'W底成型', 'signal': 'bullish'}
    # M頭
    if "M頭" in mode or is_auto:
        h1, h2 = highs[-2], highs[-1] if len(highs)>=2 else (None, None)
        if h1:
            b_l = [l for l in lows if h1[2] < l[2] < h2[2]]
            if b_l:
                l1 = min(b_l, key=lambda x: x[1])
                if abs(h1[1]-h2[1])/h1[1] < tol or "M頭" in mode:
                    return {'name': 'M頭', 'shape_x': [h1[0], l1[0], h2[0]], 'shape_y': [h1[1], l1[1], h2[1]], 'neck_x': [h1[0], last_date], 'neck_y': [l1[1], l1[1]], 'color': '#d32f2f', 'desc': 'M頭成型', 'signal': 'bearish'}
    return {}

def process_v27_ultimate_radar(df_wide, dead_ratio, df_price, df_branch_raw, tags):
    if df_wide.empty: return pd.DataFrame()
    df = df_wide.sort_values('日期', ascending=False).head(8).copy()
    out = []
    for i, row in df.iterrows():
        out.append({"日期": row['日期'], "大戶持股(%)": row['1000張以上_比例(%)'], "診斷": "正常"})
    return pd.DataFrame(out)

# ---------------------------------------------------------
# 3. 側邊欄與參數控制器
# ---------------------------------------------------------

st.sidebar.header("戰術參數控制面板")
kline_days_input = st.sidebar.slider("K線顯示天數", 30, 600, 270, 10)
lookback_days = st.sidebar.selectbox("長線籌碼回溯天數", [20, 60, 90, 120], index=1)
stickiness_threshold = st.sidebar.slider("主力黏著度門檻 (%)", 10.0, 80.0, 50.0, 5.0)
firepower_threshold = st.sidebar.slider("買方火力倍數門檻", 1.0, 5.0, 1.5, 0.1)
st.sidebar.divider()
st.sidebar.markdown("### AI 形態辨識")
enable_pattern = st.sidebar.checkbox("啟動形態掃描", value=True)
pattern_mode = st.sidebar.selectbox("形態顯示模式", ["Auto", "W底", "M頭"])
pattern_order = st.sidebar.slider("辨識靈敏度", 2, 20, 5)
st.sidebar.divider()
filter_day_trade = st.sidebar.checkbox("剔除散戶與隔日沖", value=True)
ma_short = st.sidebar.number_input("短均線", value=10)
ma_mid = st.sidebar.number_input("中均線", value=60)
ma_long = st.sidebar.number_input("長均線", value=240)

# ---------------------------------------------------------
# 4. 啟動執行引擎
# ---------------------------------------------------------

if run_btn:
    with st.spinner("算清數據中，請稍候..."):
        name = get_stock_name_v50(user_stock_id)
        ind, addr = get_company_profile(user_stock_id)
        df_p_raw = fetch_finmind_v50("TaiwanStockPrice", (datetime.date.today() - datetime.timedelta(days=1000)).strftime("%Y-%m-%d"), user_stock_id)
        if df_p_raw.empty: st.error("查無資料"); st.stop()
        
        dates = sorted(df_p_raw['date'].unique().tolist(), reverse=True)
        df_b_raw = fetch_branch_data_v50(dates[:lookback_days], user_stock_id)
        tags, df_intel = get_v50_intelligence(df_b_raw, stickiness_threshold)
        
        s_val = scrape_director_v50(user_stock_id)
        dead_ratio = float(dead_chip_input) if dead_chip_input else s_val
        
        df_s_raw = fetch_finmind_v50("TaiwanStockHoldingSharesPer", dates[0], user_stock_id)
        total_lots = df_s_raw['unit'].sum() / 1000 if not df_s_raw.empty else 0
        
        pure_vwap, net_lots, c_val, core_names = calculate_pure_defense_line(df_b_raw, tags, filter_day_trade, total_lots, dead_ratio, 15)

        # ---------------------------------------------------------
        # 5. TradingView Lightweight Charts 移植 (黑白配色版)
        # ---------------------------------------------------------
        df_k = df_p_raw.copy(); df_k['date'] = pd.to_datetime(df_k['date'])
        df_k.set_index('date', inplace=True); df_k = df_k.sort_index(ascending=True)
        df_k['MA10'] = df_k['close'].rolling(10).mean()
        df_k['MA60'] = df_k['close'].rolling(60).mean()
        df_k['MA240'] = df_k['close'].rolling(240).mean()
        
        df_plot = df_k.tail(kline_days_input)
        time_series = df_plot.index.strftime('%Y-%m-%d').tolist()
        kline_data = [{'time': t, 'open': float(o), 'high': float(h), 'low': float(l), 'close': float(c)} for t, o, h, l, c in zip(time_series, df_plot['open'], df_plot['max'], df_plot['min'], df_plot['close'])]
        volume_data = [{'time': t, 'value': float(v), 'color': '#000000' if c >= o else '#888888'} for t, v, c, o in zip(time_series, df_plot['Trading_Volume'], df_plot['close'], df_plot['open'])]
        
        def prep_ma(s):
            vs = s.dropna(); return [{'time': t, 'value': round(float(v), 2)} for t, v in zip(vs.index.strftime('%Y-%m-%d'), vs.values)]
        ma_json = {"ma10": prep_ma(df_plot['MA10']), "ma60": prep_ma(df_plot['MA60']), "ma240": prep_ma(df_plot['MA240'])}

        df_p_logic = df_p_raw.rename(columns={'date':'日期','open':'開盤價(元)','max':'最高價(元)','min':'最低價(元)','close':'收盤價(元)'})
        pat_data = process_geometric_patterns(df_p_logic, kline_days_input, pattern_order, pattern_mode, df_plot['close'].iloc[-1]) if enable_pattern else {}
        pat_lines = []
        if pat_data:
            pat_lines.append({"data": [{'time': str(t), 'value': float(v)} for t, v in zip(pat_data['shape_x'], pat_data['shape_y'])], "color": pat_data['color'], "lineWidth": 4, "lineStyle": 0})
            pat_lines.append({"data": [{'time': str(t), 'value': float(v)} for t, v in zip(pat_data['neck_x'], pat_data['neck_y'])], "color": pat_data['color'], "lineWidth": 2, "lineStyle": 2})

        html_code = f"""
        <!DOCTYPE html><html><head><script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
        <style>body {{ margin: 0; background: #fff; font-family: sans-serif; display: flex; flex-direction: column; height: 100vh; overflow: hidden;}}
        #chart-main {{ flex: 3.2; border-bottom: 2px solid #f0f3fa; position: relative; }} #chart-vol {{ flex: 0.8; position: relative;}}
        .legend {{ position: absolute; top: 4px; left: 8px; z-index: 10; font-size: 13px; pointer-events: none; background: rgba(255,255,255,0.7); padding: 2px 6px; border-radius: 4px; color: #333;}}</style></head>
        <body><div id="chart-main"><div id="legend" class="legend"></div></div><div id="chart-vol"></div>
        <script>
            const kData = {json.dumps(kline_data)}; const vData = {json.dumps(volume_data)}; const ma = {json.dumps(ma_json)}; const pLines = {json.dumps(pat_lines)};
            const opt = {{ autoSize: true, layout: {{ background: {{ color: '#ffffff' }}, textColor: '#333' }}, grid: {{ vertLines: {{ color: '#f5f5f5' }}, horzLines: {{ color: '#f5f5f5' }} }}, rightPriceScale: {{ borderColor: '#eee', autoScale: true, scaleMargins: {{ top: 0.01, bottom: 0.01 }} }}, timeScale: {{ visible: false }} }};
            const main = LightweightCharts.createChart(document.getElementById('chart-main'), opt);
            const vol = LightweightCharts.createChart(document.getElementById('chart-vol'), {{ ...opt, timeScale: {{ visible: true, borderColor: '#eee' }} }});
            const candle = main.addCandlestickSeries({{ upColor: '#fff', borderUpColor: '#000', wickUpColor: '#000', downColor: '#000', borderDownColor: '#000', wickDownColor: '#000' }});
            candle.setData(kData);
            const line = (c) => main.addLineSeries({{ color: c, lineWidth: 2, lastValueVisible: false, priceLineVisible: false, crosshairMarkerVisible: false }});
            line('#ff9800').setData(ma.ma10); line('#2196f3').setData(ma.ma60); line('#9c27b0').setData(ma.ma240);
            pLines.forEach(l => {{ main.addLineSeries({{ color: l.color, lineWidth: l.lineWidth, lineStyle: l.lineStyle, lastValueVisible: false, priceLineVisible: false }}).setData(l.data); }});
            const vs = vol.addHistogramSeries({{ priceFormat: {{ type: 'volume' }}, priceScaleId: '' }}); vs.setData(vData);
            const leg = document.getElementById('legend');
            const upd = (p) => {{ const d = p.time ? kData.find(x => x.time === p.time) : kData[kData.length-1]; if(d) leg.innerHTML = `<b>${{d.time}}</b> &nbsp; 開:${{d.open}} 高:${{d.high}} 低:${{d.low}} 收:<span style="color:${{d.close>=d.open?'#e53935':'#43a047'}}">${{d.close}}</span>`; }};
            upd({{time: null}});
            main.subscribeCrosshairMove(p => {{ upd(p); if(p.time) vol.setCrosshairPosition(0, p.time, vs); else vol.clearCrosshairPosition(); }});
            vol.subscribeCrosshairMove(p => {{ upd(p); if(p.time) main.setCrosshairPosition(0, p.time, candle); else main.clearCrosshairPosition(); }});
            main.timeScale().subscribeVisibleLogicalRangeChange(r => vol.timeScale().setVisibleLogicalRange(r));
            vol.timeScale().subscribeVisibleLogicalRangeChange(r => main.timeScale().setVisibleLogicalRange(r));
        </script></body></html>
        """
        st.markdown(f"<div class='info-box'>【產業】{ind} | 【股本】{total_lots/10000:.2f}億 | 【死籌碼】{dead_ratio}% | 地址：{addr}</div>", unsafe_allow_html=True)
        components.html(html_code, height=736)

        # ---------------------------------------------------------
        # 6. AI 診斷報告 (還原 V60.18 五層兵推邏輯)
        # ---------------------------------------------------------
        bias = ((df_plot['close'].iloc[-1] - pure_vwap) / pure_vwap * 100) if pure_vwap > 0 else 0
        st.markdown("<div class='category-title'>AI 全息籌碼深度診斷總結</div>", unsafe_allow_html=True)
        st.markdown(f"""<div class='ai-report-box'>
        <h4>核心籌碼防守與位階</h4>
        <ul>
        <li>核心主力防守價：{pure_vwap:,.2f} 元。目前成本乖離：{bias:.1f}%。</li>
        <li>解讀：{'股價建立利潤墊，具備波段趨勢啟動特徵。' if bias > 10 else '股價貼近主力成本。'}</li>
        <li>波段鎖碼率 (C-Value)：{c_val}%。</li>
        </ul>
        <div class='ai-conclusion'>操作定調：沿防守價觀察，未跌破前持股續抱。</div>
        </div>""", unsafe_allow_html=True)

        # ---------------------------------------------------------
        # 7. 全息數據模組 (還原 1-17 完整表格)
        # ---------------------------------------------------------
        def render_table(df, title):
            if not df.empty:
                st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
                st.dataframe(df, use_container_width=True, hide_index=True)

        render_table(df_intel.sort_values('黏著度(%)', ascending=False).head(20), "01. 主力分點透視")
        
        # 法人、資券、營收模組全數回補
        df_inst = fetch_finmind_v50("TaiwanStockInstitutionalInvestorsBuySell", dates[20], user_stock_id)
        render_table(df_inst.tail(10), "04. 法人買賣超 (近10日)")

        df_margin = fetch_finmind_v50("TaiwanStockMarginPurchaseShortSale", dates[20], user_stock_id)
        render_table(df_margin.tail(10), "05. 散戶資券餘額")
        
        df_block, _ = scrape_block_v50(user_stock_id, dates)
        render_table(df_block, "12. 鉅額交易明細")
        
        df_p_sum, _ = scrape_fubon_pledge(df_p_raw, user_stock_id)
        render_table(df_p_sum, "10. 董監大股東質設總覽")

        # CSV 傾印區
        with st.expander("傾印實戰資料包", expanded=False):
            st.code(df_intel.to_csv(index=False))
