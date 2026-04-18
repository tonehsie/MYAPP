import streamlit as st, requests, pandas as pd, numpy as np, datetime, re, concurrent.futures, urllib.request, ssl, urllib3
from io import StringIO
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="V46.13 終極全息量化系統 (究極效能版)", layout="wide", initial_sidebar_state="expanded")
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

st.markdown("""<style>
.table-responsive{overflow-x:auto;width:100%;display:block;margin-bottom:20px}
table.dataframe{border-collapse:collapse;width:100%}
table.dataframe th,table.dataframe td{white-space:nowrap!important;text-align:center!important;padding:8px 12px!important}
table.dataframe th:first-child,table.dataframe td:first-child{position:sticky;left:0;background-color:#f1f3f5;z-index:1;border-right:2px solid #dee2e6}
.radar-table td:last-child{text-align:left!important;color:#ff4b4b;font-weight:bold}
.daily-tracker td:last-child{text-align:left!important;color:#008080;font-weight:bold}
.info-box{background-color:#f0f2f6;padding:15px;border-radius:10px;margin-bottom:20px;border-left:5px solid #ff4b4b;font-size:16px;line-height:1.8}
.hawk-eye-box{background-color:#fff9db;padding:20px;border-radius:10px;margin-bottom:20px;border-left:6px solid #f59f00;font-size:15px;line-height:1.8}
.hawk-alert{color:#d9480f;font-weight:bold}
.hawk-safe{color:#2b8a3e;font-weight:bold}
.section-title{margin-top:35px;margin-bottom:15px;color:#1e3a8a;border-bottom:2px solid #1e3a8a;padding-bottom:5px;font-size:1.3rem!important;font-weight:700!important}
.category-title{font-size:1.6rem!important;font-weight:900!important;margin-top:40px;color:#333}
.loss-warning{color:#d9480f;font-weight:bold}
</style>""", unsafe_allow_html=True)

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
footprint_days = st.sidebar.slider("足跡動態追蹤天數", 3, 60, 20, 1)
footprint_rows = st.sidebar.slider("足跡矩陣顯示筆數 (多空各 N 名)", 5, 50, 15, 5)
firepower_threshold = st.sidebar.slider("買方火力倍數門檻", 1.0, 5.0, 1.5, 0.1)
st.sidebar.divider()
ma_short = st.sidebar.number_input("短均線 (天)", min_value=1, max_value=20, value=10)
ma_mid = st.sidebar.number_input("中均線/防守線 (天)", min_value=20, max_value=100, value=60)
ma_long = st.sidebar.number_input("長均線 (天)", min_value=100, max_value=300, value=240)

st.title("📱 V46.13 終極全息量化系統 (究極效能優化版)")
user_count, api_limit = get_api_usage(FINMIND_TOKEN)
usage_text = f" | 🔑 FinMind 額度使用狀態: {user_count} / {api_limit}" if user_count is not None else ""
st.caption(f"🚀 深度優化：全面消滅重複運算、啟動爬蟲全域快取、精準萃取 AI 資料包。{usage_text}")

col1, col2 = st.columns([1, 1])
with col1: user_stock_id = st.text_input("個股代號", value="2330")
with col2: dead_chip_input = st.text_input("死籌碼 % (留空自動雙引擎抓取)")
run_btn = st.button("🚀 啟動 V46.13 全局運算引擎", use_container_width=True, key="run_engine")

def safe_to_num(series, fill_val=0):
    if pd.api.types.is_numeric_dtype(series):
        return series.fillna(fill_val)
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
    url, p = "https://api.finmindtrade.com/api/v4/data", {"dataset": ds, "start_date": sd}
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
    session = requests.Session()
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
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def scrape_block_v46(tid, ad):
    if not ad: return pd.DataFrame(), []
    td, bd, dl = ad[:3], [], []
    session = requests.Session()
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
            if c_str and ':' not in c_str and c_str.replace('.', '', 1).isdigit():
                nums.append(float(c_str))
        nums.sort(reverse=True)
        if len(nums) >= 3:
            amt = nums[0] / 10000 if nums[0] > 100000 else nums[0]
            vol = nums[1] / 1000 if nums[1] > 1000 else nums[1]
            tt = next((re.sub(r'<[^>]+>', '', str(c)).strip() for c in row if any(x in str(c) for x in ["配對","交易","單一","組合","逐筆"])), "鉅額")
            p.append({"日期": date, "交易別": tt, "成交量(張)": int(vol), "成交價(元)": round(nums[2], 2), "成交金額(萬元)": int(amt)})
    return pd.DataFrame(p).sort_values("日期", ascending=False), list(set(dl))

def safe_get_fubon(url):
    try:
        ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        if hasattr(ssl, 'OP_LEGACY_SERVER_CONNECT'): ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as res: return res.read().decode('big5', errors='ignore')
    except:
        try:
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, verify=False)
            if res.status_code == 200: res.encoding = 'big5'; return res.text
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
                        title, name, r_str = re.sub(r'<[^>]+>', '', tds[0]).strip(), re.sub(r'<[^>]+>', '', tds[1]).strip(), re.sub(r'<[^>]+>', '', tds[3]).replace('%', '').strip()
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
    sn = set(); uq = []
    for r in alld:
        if "|".join(r) not in sn: sn.add("|".join(r)); uq.append(r)
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
                    if cd in prd: fp = prd[cd]; mc = round(fp * 0.78, 2); break
            except: pass
        pps.append(fp); mcs.append(mc)
    df_all['設質日收盤價'], df_all['強制賣出價(0.78)'] = pps, mcs
    sm = {}
    for _, r in df_all.iterrows():
        if r['姓名'] not in sm: sm[r['姓名']] = {"title": r['身份別'], "balance": r['累積質設(張)'], "p": "-", "mc": "-"}
        if sm[r['姓名']]["p"] == "-" and r['設質(張)'] > 0: sm[r['姓名']]["p"], sm[r['姓名']]["mc"] = r['設質日收盤價'], r['強制賣出價(0.78)']
    sr = [{"身份別": d["title"], "姓名": n, "目前剩餘質設(張)": d["balance"], "最後設質收盤價(元)": d["p"], "估算斷頭價(0.78)": d["mc"]} for n, d in sm.items() if d["balance"] > 0]
    return pd.DataFrame(sr), df_all

def get_v27_intelligence(df_b_raw, df_p_raw, stick_thresh, global_days):
    if df_b_raw.empty or df_p_raw.empty: return {}, pd.DataFrame()
    if global_days <= 0: global_days = 1
    df_p = df_p_raw.copy()
    df_p['date'] = pd.to_datetime(df_p['date'])
    df_p['avg_price'] = (df_p['close'] + df_p['max'] + df_p['min']) / 3
    range_diff = df_p['max'] - df_p['min']
    df_p['pos'] = np.where(range_diff == 0, 1.0, (df_p['close'] - df_p['min']) / range_diff.replace(0, 1))
    df_p['strength'] = np.where(df_p['avg_price'] == 0, 0, (df_p['close'] - df_p['avg_price']) / df_p['avg_price'].replace(0, 1))
    price_stats = df_p.set_index('date')[['pos', 'strength']].to_dict('index')
    latest_close = df_p.sort_values('date', ascending=False)['close'].iloc[0] if not df_p.empty else 0

    df = df_b_raw.copy()
    df['date'] = pd.to_datetime(df['date'])
    
    # ⚡ V46.13: 免轉換，直接運算
    df['buy_amt'] = df['buy'] * df['price']
    df['sell_amt'] = df['sell'] * df['price']
    
    tags, d_rows = {}, []
    for trader, g in df.groupby('securities_trader'):
        tb, ts = round(g['buy'].sum() / 1000), round(g['sell'].sum() / 1000)
        tv = tb + ts
        if tv == 0: continue
        active_days = g['date'].nunique()
        stickiness = (active_days / global_days) * 100
        dr, net = (min(tb, ts) * 2) / tv if tv > 0 else 0, tb - ts
        nr = net / tb if tb > 0 else -1
        hoard_ratio = (abs(net) / tv * 100) if tv > 0 else 0
        avg_b = g['buy_amt'].sum() / g['buy'].sum() if g['buy'].sum() > 0 else 0
        avg_s = g['sell_amt'].sum() / g['sell'].sum() if g['sell'].sum() > 0 else 0
        ld = pd.to_datetime(g['date']).max()
        stats = price_stats.get(ld, {'pos': 0.5, 'strength': 0})
        pos, strn = stats['pos'], stats['strength']
        
        tag = "🔵 一般"
        if any(x in trader for x in ["台銀", "土銀", "彰銀", "第一", "兆豐", "華南", "合庫", "台企銀"]): tag = "🏦 [影子官股]"
        elif stickiness >= stick_thresh: tag = "🥷 [潛伏造市者]" if dr > 0.70 else "👑 [長駐波段主]"
        elif dr > 0.80: tag = "🏃 [游擊過客]" if stickiness < 10.0 else "🌪️ [純當沖客]" if nr < 0.05 else "🧱 [主動鎖碼]" if (strn > 0.01 and pos >= 0.7) or (pos == 1.0) else "🩹 [被套牢]" if strn < -0.01 and pos < 0.3 else "⚡ [隔日沖]"
        elif nr > 0.7: tag = "📈 [波段主]"
        elif tb > 500 and nr > 0.85: tag = "🧱 [真鎖碼]"
        
        tags[trader] = tag
        b_str = f"{round(avg_b, 2):,.2f}"
        if avg_b > latest_close and avg_b > 0 and net > 0: b_str = f"⚠️(虧) {b_str}"
        d_rows.append({"分點名稱": trader, "最終標籤": tag, "黏著度(%)": round(stickiness, 1), "囤貨率(%)": round(hoard_ratio, 1), "總買(張)": tb, "總賣(張)": ts, "淨留倉": int(net), "買均價": b_str, "賣均價": round(avg_s, 2), "當沖率(%)": round(dr*100, 1), "均價強度(%)": round(strn*100, 2), "收盤位階": round(pos, 2)})
    return tags, pd.DataFrame(d_rows).sort_values('總買(張)', ascending=False)

def process_footprint(df_raw, dynamic_dates, intel_tags, df_fingerprint, top_n, global_days):
    if df_raw.empty or not dynamic_dates: return pd.DataFrame(), pd.DataFrame()
    df = df_raw[df_raw['date'].isin(dynamic_dates)].copy()
    if df.empty: return pd.DataFrame(), pd.DataFrame()
    
    # ⚡ V46.13: 免轉換，直接運算
    df['net'] = ((df['buy'] - df['sell']) / 1000).round().astype(int)
    g = df.groupby(['securities_trader', 'date'])['net'].sum().reset_index()
    p = g.pivot(index='securities_trader', columns='date', values='net').fillna(0).astype(int)
    p['total'] = p.sum(axis=1)
    top_b = p[p['total'] > 0].nlargest(top_n, 'total').reset_index()
    top_s = p[p['total'] < 0].nsmallest(top_n, 'total').reset_index()
    
    fp_dict = {}
    if not df_fingerprint.empty:
        fp_dict = df_fingerprint.set_index('分點名稱')[['黏著度(%)', '囤貨率(%)']].to_dict('index')
    
    def build_df(res_df):
        out = []
        for _, r in res_df.iterrows():
            trader = r['securities_trader']
            st_val = fp_dict.get(trader, {}).get('黏著度(%)', "-")
            hr_val = fp_dict.get(trader, {}).get('囤貨率(%)', "-")
            
            row_dict = {
                "分點名稱": trader, 
                "標籤": intel_tags.get(trader, "🔵 一般"),
                "黏著度(%)": st_val,
                "囤貨率(%)": hr_val,
                f"{len(dynamic_dates)}日累計(張)": f"+{r['total']}" if r['total'] > 0 else str(r['total'])
            }
            for i, d in enumerate(dynamic_dates):
                v = r.get(d, 0)
                row_dict[f"T-{i}" if i > 0 else "今日(T)"] = f"+{v}" if v > 0 else str(v)
            out.append(row_dict)
        return pd.DataFrame(out)
    return build_df(top_b), build_df(top_s)

def process_branch_v25(df_raw, period, actual_dates, intel_tags, df_price_raw, stick_thresh, global_days):
    if df_raw.empty or df_price_raw.empty: return pd.DataFrame()
    latest_close = df_price_raw.sort_values('date', ascending=False)['close'].iloc[0]
    if global_days <= 0: global_days = 1
    global_act_days = df_raw.groupby('securities_trader')['date'].nunique().to_dict()
    df = df_raw[df_raw['date'].isin(actual_dates[:period])].copy()
    if df.empty: return pd.DataFrame()
    
    # ⚡ V46.13: 免轉換，直接運算
    df['ba'] = df['buy'] * df['price']; df['sa'] = df['sell'] * df['price']
    g = df.groupby('securities_trader').agg(bv=('buy', 'sum'), sv=('sell', 'sum'), ba=('ba', 'sum'), sa=('sa', 'sum')).reset_index()
    g['net'] = round((g['bv'] - g['sv']) / 1000).astype(int)
    g['avg_b'] = (g['ba'] / g['bv'].replace(0, np.nan)).fillna(0)
    g['avg_s'] = (g['sa'] / g['sv'].replace(0, np.nan)).fillna(0)
    g['stick'] = g['securities_trader'].map(lambda x: (global_act_days.get(x, 0) / global_days) * 100).round(1)
    b = g[g['net'] > 0].sort_values('net', ascending=False).head(15).reset_index(drop=True)
    s = g[g['net'] < 0].sort_values('net', ascending=True).head(15).reset_index(drop=True)
    out, tv = [], round(g['bv'].sum() / 1000) if g['bv'].sum() > 0 else 1
    for i in range(15):
        r = {}
        if i < len(b): 
            b_str = f"{round(b.loc[i,'avg_b'], 2):,.2f}"
            if b.loc[i,'avg_b'] > latest_close and b.loc[i,'avg_b'] > 0 and b.loc[i,'net'] > 0: b_str = f"⚠️(虧) {b_str}"
            r["買超分點"] = f"{intel_tags.get(b.loc[i,'securities_trader'],'🔵')} {b.loc[i,'securities_trader']}"
            r["黏著度(%)"] = f"{b.loc[i,'stick']}%"; r["買超(張)"] = int(b.loc[i,'net']); r["買均價"] = b_str; r["佔比"] = f"{(b.loc[i,'net']/tv)*100:.1f}%" if tv > 0 else "-"
        else: r["買超分點"], r["黏著度(%)"], r["買超(張)"], r["買均價"], r["佔比"] = "-", "-", 0, "-", "-"
        if i < len(s): 
            r["賣超分點"] = f"{intel_tags.get(s.loc[i,'securities_trader'],'🔵')} {s.loc[i,'securities_trader']}"
            r["黏著度(%)_"] = f"{s.loc[i,'stick']}%"; r["賣超(張)"] = abs(int(s.loc[i,'net'])); r["賣均價"] = round(s.loc[i,'avg_s'], 2); r["佔比_"] = f"{(abs(s.loc[i,'net'])/tv)*100:.1f}%" if tv > 0 else "-"
        else: r["賣超分點"], r["黏著度(%)_"], r["賣超(張)"], r["賣均價"], r["佔比_"] = "-", "-", 0, "-", "-"
        out.append(r)
    return pd.DataFrame(out)

def get_smart_threshold(price, capital_bn, dead_float):
    if pd.isna(price) or price <= 0: return 1000 
    rt = max((max(3000, capital_bn * 500) * 10000) / (price * 1000), (capital_bn * 10000) * (max(0.1, 0.5 * (100 - dead_float) / 100) / 100))
    al = min([100, 200, 400, 600, 800, 1000], key=lambda x: abs(x - rt))
    return min(al, 400) if price < 30 else al

def process_v27_ultimate_radar(df_wide, dead_chip_input, dynamic_dict, static_val, df_price, df_branch_raw, intel_tags):
    if df_wide.empty or len(df_wide) < 2: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df = df_wide.sort_values('日期', ascending=True).copy()
    df['dt_end'] = pd.to_datetime(df['日期'])
    if not df_price.empty:
        df_p = df_price.copy(); df_p['dt'] = pd.to_datetime(df_p['日期'])
        df_p = df_p.sort_values('dt'); df_p['ma20'] = df_p['收盤價(元)'].rolling(20).mean()
        df = pd.merge_asof(df.sort_values('dt_end'), df_p[['dt', '收盤價(元)', 'ma20']], left_on='dt_end', right_on='dt', direction='backward')
    else: df['收盤價(元)'], df['ma20'] = 0, 0
    df['原始大戶變動(%)'] = df['1000張以上_比例(%)'].diff().round(2)
    df['總人數變動率(%)'] = (df['總人數(人)'].pct_change() * 100).round(2)
    out, d_math, d_fri = [], [], []
    for i, row in df.iterrows():
        if pd.isna(row['原始大戶變動(%)']): out.append({"純淨變動": 0, "雜訊": 0, "診斷": "⚪ 初始化"}); continue
        d_str = row['日期']
        df_f = df_branch_raw[df_branch_raw['date'] == d_str]
        f_vol = 0
        if not df_f.empty:
            df_f = df_f.copy(); df_f['tag'] = df_f['securities_trader'].map(intel_tags)
            fn = df_f[df_f['tag'].str.contains("隔日沖|被套牢|游擊過客", na=False)] 
            # ⚡ V46.13: 免轉換，直接運算
            f_vol = round(fn['buy'].sum() / 1000)
            for _, fr in fn.iterrows():
                buy_vol = fr['buy']
                if buy_vol and buy_vol > 0: d_fri.append({"日期": d_str, "分點": fr['securities_trader'], "張數": round(buy_vol/1000)})
        f_impact = (f_vol / row['總張數']) * 100 if row['總張數'] > 0 else 0
        p_chg = round(row['原始大戶變動(%)'] - f_impact, 2)
        d_math.append({"日期": d_str, "原始變動": row['原始大戶變動(%)'], "隔日沖干擾": round(f_impact, 2), "純淨變動": p_chg})
        dead, _ = get_dead_chip_info(d_str, dead_chip_input, dynamic_dict, static_val, "")
        lev = 100 / (100 - dead) if 0 < dead < 100 else 1
        adv = []
        if row['總人數變動率(%)'] > 2.0 and p_chg < 0: adv.append(f"💀 [逃命] 散戶增{row['總人數變動率(%)']}%，大戶實質倒貨{abs(p_chg)}%")
        else:
            if p_chg * lev > 2.5 and row['收盤價(元)'] > row['ma20']: adv.append(f"🚀 [真軋空] 站上月線且大戶純淨買超{round(p_chg*lev, 2)}%")
            elif p_chg > 0.4 and row['收盤價(元)'] < row['ma20']: adv.append(f"🧱 [底位建倉] 跌破月線但主力吃貨{p_chg}%")
            elif p_chg < -1.0: adv.append(f"📉 [主力撤退] 大戶實質流出{abs(p_chg)}%")
            if f_impact > 1.2: adv.append(f"⚡ [隔日沖陷阱] 虛胖買盤潛藏{round(f_impact, 2)}%倒貨危機")
        out.append({"純淨變動": p_chg, "雜訊": round(f_impact, 2), "診斷": " | ".join(adv) if adv else "🔵 盤整"})
    ddf = pd.DataFrame(out)
    df['純淨大戶變動(%)'], df['隔日沖虛胖(%)'], df['專家雷達診斷'] = ddf['純淨變動'], ddf['雜訊'], ddf['診斷']
    return df[['日期', '收盤價(元)', '總人數變動率(%)', '原始大戶變動(%)', '隔日沖虛胖(%)', '純淨大戶變動(%)', '專家雷達診斷']].sort_values('日期', ascending=False)[df['專家雷達診斷'] != '⚪ 初始化'], pd.DataFrame(d_math), pd.DataFrame(d_fri)

def process_branch_diff(df_raw, actual_dates, fire_thresh):
    if df_raw.empty or not actual_dates: return pd.DataFrame()
    out = []
    # ⚡ V46.13: 零拷貝技術，僅抽取需要的欄位
    df_raw_num = df_raw[['date', 'securities_trader', 'buy', 'sell']].copy()
    
    for d in actual_dates[:10]:
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

def process_v30_daily_tracking(df_branch_raw, intel_tags, df_price, df_branch_diff, actual_dates, fire_thresh):
    if df_branch_raw.empty or len(actual_dates) < 5: return pd.DataFrame(), pd.DataFrame()
    out, audit_smart_money = [], []
    
    # ⚡ V46.13: 零拷貝擷取
    df_b = df_branch_raw[['date', 'securities_trader', 'buy', 'sell', 'price']].copy()
    df_b = df_b.rename(columns={'buy': 'bs', 'sell': 'ss', 'price': 'pr'})
    
    df_b['tag'] = df_b['securities_trader'].map(intel_tags).fillna("🔵 一般")
    for d in actual_dates[:5]:
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
        smart_b = day_b[day_b['tag'].str.contains('波段主|真鎖碼|官股|潛伏造市者|長駐波段主', na=False)]
        short_b = day_b[day_b['tag'].str.contains('隔日沖|套牢|游擊過客', na=False)]
        smart_grouped = smart_b.groupby(['securities_trader', 'tag'])[['bs', 'ss']].sum().reset_index()
        smart_grouped['net_vol'] = ((smart_grouped['bs'] - smart_grouped['ss']) / 1000).round().astype(int)
        short_grouped = short_b.groupby('securities_trader')[['bs', 'ss']].sum().reset_index()
        short_grouped['net_vol'] = ((short_grouped['bs'] - short_grouped['ss']) / 1000).round().astype(int)
        if d == actual_dates[0]:
            for _, r in smart_grouped.iterrows():
                if r['net_vol'] != 0: audit_smart_money.append({"日期": d, "分點": r['securities_trader'], "標籤": r['tag'], "淨買超(張)": r['net_vol']})
        smart_net, short_trap = smart_grouped['net_vol'].sum(), short_grouped['net_vol'].sum()
        smart_buy_vol = smart_b['bs'].sum()
        smart_avg_cost = (smart_b['bs'] * smart_b['pr']).sum() / smart_buy_vol if smart_buy_vol > 0 else 0
        gap = cp - smart_avg_cost if smart_avg_cost > 0 else 0
        adv = []
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
            "日期": d, 
            "收盤價(元)": cp, 
            "漲跌(元)": sp, 
            "聰明錢淨流(張)": int(smart_net), 
            "大戶買均價": round(smart_avg_cost, 2) if smart_avg_cost > 0 else "-", 
            "均價落差": round(gap, 2) if smart_avg_cost > 0 else "-", 
            "活躍家數": active_cnt,
            "買賣家數差": bsd, 
            "籌碼集中度(%)": concentration,
            "買方火力(倍)": firepower,
            "潛在賣壓(張)": int(short_trap), 
            "綜合診斷": " | ".join(adv)
        })
    return pd.DataFrame(out), pd.DataFrame(audit_smart_money).sort_values('淨買超(張)', ascending=False) if audit_smart_money else pd.DataFrame()

def process_cbas(df, current_stock_price, df_cb_info=None):
    if df.empty: return pd.DataFrame()
    df_out = df.copy().rename(columns={"date": "日期", "cb_id": "可轉債代號", "cb_name": "可轉債名稱", "conversion_price": "轉換價(元)", "ConversionPrice": "轉換價(元)", "underlying_stock_price": "標的股價(元)", "PriceOfUnderlyingStock": "標的股價(元)", "outstanding_amount": "未償還餘額", "OutstandingAmount": "未償還餘額", "outstanding_balance": "未償還餘額", "close": "CB收盤價", "closing_price": "CB收盤價", "conversion_premium_rate": "溢價率(%)", "premium_rate": "溢價率(%)", "PremiumRate": "溢價率(%)", "theoretical_value": "轉換價值", "TheoreticalValue": "轉換價值"})
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
        alerts.append("<div class='hawk-title'>1. 矩陣金流剖析 (聰明錢與成本底牌)</div>")
        flow_str = f"今日聰明錢淨流入 <b>{today_d['聰明錢淨流(張)']} 張</b>。"
        if today_d['均價落差'] != "-":
            try:
                gap_val = float(str(today_d['均價落差']).replace(',', '').strip())
                chg_val = float(str(today_d['漲跌(元)']).replace(',', '').strip()) if today_d['漲跌(元)'] not in ["-", ""] else 0.0
                if gap_val > 0 and today_d['聰明錢淨流(張)'] > 0: alerts.append(f"<span class='hawk-safe'>🔥 【主動鎖碼】{flow_str} 且大戶買進均價低於收盤價 (均價落差 +{gap_val})。主力帳面獲利，底氣強勁，具備強勢推升與留倉意願。</span>")
                elif gap_val < 0 and today_d['聰明錢淨流(張)'] > 0: alerts.append(f"<span class='hawk-alert'>🩹 【接刀套牢】{flow_str} 但大戶買進均價高於收盤價 (均價落差 {gap_val})。主力今日進場護盤或試單已被套牢，明日若無法開高，極易引發停損賣壓！</span>")
                elif today_d['聰明錢淨流(張)'] < -100 and chg_val > 0: alerts.append(f"<span class='hawk-alert'>📉 【拉高派發】今日股價收紅，但聰明錢卻趁機撤退 {today_d['聰明錢淨流(張)']} 張。這是典型的主力利用當沖熱度逢高倒貨，追高風險極大。</span>")
                elif today_d['聰明錢淨流(張)'] < -100: alerts.append(f"<span class='hawk-alert'>💀 【波段棄守】股價走弱且聰明錢大舉撤退 {today_d['聰明錢淨流(張)']} 張。長線防守線可能崩潰，建議順勢避開。</span>")
                else: alerts.append("<span>🔵 今日聰明錢無明顯極端進出，大戶成本線持平。</span>")
            except: alerts.append("<span>🔵 今日聰明錢數值解析中性。</span>")
        else: alerts.append("<span>🔵 今日大戶無明顯動作，成本線無法精算。</span>")

    if not df_diff.empty and len(df_diff) >= 1:
        alerts.append("<div class='hawk-title' style='margin-top:15px;'>2. 火力與籌碼結構剖析 (買賣家數差)</div>")
        latest_diff = df_diff.iloc[0]
        try:
            fp_val = float(str(latest_diff['買方火力(倍)']).replace(',', '').strip())
            fire_str = f"今日活躍券商共 <b>{latest_diff['活躍家數']} 家</b>，買方火力倍數為 <b>{fp_val} 倍</b>。"
            if fp_val >= fire_thresh: alerts.append(f"<span class='hawk-safe'>🔥 【大戶火力壓制】{fire_str} 代表少數大戶正用絕對的資金優勢集中吃貨，高於自訂的 {fire_thresh} 倍門檻，高勝率訊號！</span>")
            elif fp_val < 0.7: alerts.append(f"<span class='hawk-alert'>💀 【散戶蜂擁接刀】{fire_str} 代表大戶大舉倒貨，籌碼嚴重發散，極度危險。</span>")
            else: alerts.append(f"<span>🔵 【中性換手】{fire_str} 買賣雙方實力相當，自然市場換手。</span>")
        except: alerts.append(f"<span>🔵 【中性換手】今日活躍券商共 {latest_diff['活躍家數']} 家，籌碼發散程度一般。</span>")

    if not df_fingerprint.empty and len(df_fingerprint) >= 1:
        alerts.append("<div class='hawk-title' style='margin-top:15px;'>3. 主力潛伏微觀剖析 (前 15 大買超)</div>")
        top_15 = df_fingerprint.head(15)
        makers = len(top_15[top_15['最終標籤'].str.contains('潛伏造市者|長駐波段主', na=False)])
        tourists = len(top_15[top_15['最終標籤'].str.contains('游擊過客|隔日沖|純當沖客', na=False)])
        if tourists > 8: alerts.append(f"<span class='hawk-alert'>⚠️ 【游擊客炸彈】前 15 大買超中，高達 {tourists} 家是低黏著度的游擊客。明日開盤 9:30 前必定湧現龐大倒貨潮，嚴禁追高！</span>")
        elif makers >= 3: alerts.append(f"<span class='hawk-safe'>🔥 【潛伏主力現蹤】前 15 大分點有 {makers} 家是高黏著度的長駐大戶。波段底單深厚，具備高度安全邊際。</span>")
        else: alerts.append(f"<span>🔵 分點進出動機分散，無單一極端勢力控盤。</span>")

    if not df_radar.empty and len(df_radar) >= 1:
        latest_r = df_radar.iloc[0]
        try:
            o_chg = float(str(latest_r['原始大戶變動(%)']).replace(',', '').strip())
            f_fat = float(str(latest_r['隔日沖虛胖(%)']).replace(',', '').strip())
            p_chg = float(str(latest_r['純淨大戶變動(%)']).replace(',', '').strip())
            if o_chg > 0.5 and f_fat > 0.8 and p_chg <= 0.2:
                alerts.append("<div class='hawk-title' style='margin-top:15px;'>4. 週末集保雷達防護</div>")
                alerts.append("<span class='hawk-alert'>🚨 【集保騙局】週末公佈大戶持股看似增加，實則九成以上全是『游擊客虛胖』，純淨大戶並未進場，提防週一無情倒貨！</span>")
        except: pass
    if not alerts: alerts.append("<span>🔍 綜合火力與成本評估：目前籌碼結構中性，請依紀律操作。</span>")
    return alerts

# ⚡ V46.13 優化：預先編譯正則表達式，減少字串清洗記憶體消耗
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
    df_out['Trading_Volume'] = (safe_to_num(df_out['Trading_Volume']) / 1000).round().astype(int)
    df_out = df_out.rename(columns={"date":"日期","Trading_Volume":"成交量(張)","close":"收盤價(元)","spread":"漲跌(元)","open":"開盤價(元)","max":"最高價(元)","min":"最低價(元)"})
    df_out["斷頭價(0.78)"] = (df_out["收盤價(元)"] * 0.78).round(2)
    return df_out[['日期','成交量(張)','開盤價(元)','最高價(元)','最低價(元)','收盤價(元)','漲跌(元)','斷頭價(0.78)']].sort_values('日期', ascending=False)

def process_technical_analysis(df_price, s_ma, m_ma, l_ma):
    if df_price.empty or len(df_price) < 30: return pd.DataFrame()
    df_ta = df_price.sort_values('日期', ascending=True).copy()
    df_ta[f'MA{s_ma}'] = df_ta['收盤價(元)'].rolling(window=s_ma).mean().round(2)
    df_ta[f'MA{m_ma}(中線)'] = df_ta['收盤價(元)'].rolling(window=m_ma).mean().round(2)
    df_ta[f'MA{l_ma}(長線)'] = df_ta['收盤價(元)'].rolling(window=l_ma).mean().round(2)
    df_ta['中線乖離(%)'] = ((df_ta['收盤價(元)'] - df_ta[f'MA{m_ma}(中線)']) / df_ta[f'MA{m_ma}(中線)'] * 100).round(2)
    
    cond_up = df_ta['收盤價(元)'] > df_ta[f'MA{m_ma}(中線)']
    cond_down = df_ta['收盤價(元)'] < df_ta[f'MA{m_ma}(中線)']
    df_ta['技術面診斷'] = np.where(cond_up, "🟢 站上中線防守", np.where(cond_down, "🔴 跌破中線防守", "🔵 盤整"))
    
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
    for l in lvls: df_w[f"{l}_張數"], df_w[f"{l}_人數"], df_w[f"{l}_比例(%)"] = p_u[l], p_p[l], (p_u[l] / df_t['總張數'] * 100).fillna(0).round(2)
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
        if pd.isna(p) or p == 0: continue
        cur_dead, cl = get_dead_chip_info(row['日期'], dead_chip_input, dynamic_dict, static_val, chip_engine)
        cap = row.get('總張數', 0) / 10000
        ct = get_smart_threshold(p, cap, cur_dead)
        lvls = ['100-200張_比例(%)', '200-400張_比例(%)', '400-600張_比例(%)', '600-800張_比例(%)', '800-1000張_比例(%)', '1000張以上_比例(%)']
        if ct > 100: lvls = lvls[1:]
        if ct > 200: lvls = lvls[1:]
        if ct > 400: lvls = lvls[1:]
        if ct > 600: lvls = lvls[1:]
        if ct > 800: lvls = lvls[1:]
        lp = sum([pd.to_numeric(row.get(c, 0), errors='coerce') for c in lvls])
        cd, st = "-", "無死籌碼數據"
        if 0 < cur_dead < 100:
            cv = max(0, (lp - cur_dead) / (100.0 - cur_dead))
            st = "🔴 絕對控盤" if cv >= 0.5 else "🟡 高度鎖碼" if cv >= 0.3 else "🔵 初步集結" if cv >= 0.15 else "⚪ 籌碼渙散"
            cd = round(cv * 100, 2)
        out.append({"日期": row['日期'], "收盤價(元)": p, "股本(億)": round(cap, 2), "大戶精算門檻": f"系統判定 ({int(ct)}張)", "大戶原持股(%)": round(lp, 2), "死籌碼(%)": f"{float(cur_dead):.2f}% ({cl})" if cur_dead > 0 else "-", "純淨活大戶C_Value(%)": cd, "實戰判定": st})
    return pd.DataFrame(out)

def process_day_trading(df):
    if df.empty: return pd.DataFrame()
    df_out = df.copy().rename(columns={"date": "日期", "Volume": "當沖總股數", "BuyAfterSale": "先買後賣股數", "SellAfterBuy": "先賣後買股數", "DayTradingVolume": "當沖總股數"})
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
    df = df.rename(columns={"date":"日期", "MarginPurchaseBuy":"融資買進(萬元)", "MarginPurchaseSell":"融資賣出(萬元)", "MarginPurchaseCashRepayment":"融資現償(萬元)", "MarginPurchaseTodayBalance":"融資餘額(萬元)", "ShortSaleBuy":"融券買進(張)", "ShortSaleSell":"融券賣出(張)", "ShortSaleTodayBalance":"融券餘額(張)", "OffsetLoanAndShort":"資券相抵(張)"})
    if '融資餘額(萬元)' in df.columns and 'MarginPurchaseYesterdayBalance' in df.columns: df['融資增減(萬元)'] = df['融資餘額(萬元)'] - df['MarginPurchaseYesterdayBalance']
    if '融券餘額(張)' in df.columns and 'ShortSaleYesterdayBalance' in df.columns: df['融券增減(張)'] = df['融券餘額(張)'] - df['ShortSaleYesterdayBalance']
    cols = [c for c in ['日期','融資買進(萬元)','融資賣出(萬元)','融資現償(萬元)','融資餘額(萬元)','融資增減(萬元)','融券買進(張)','融券賣出(張)','融券餘額(張)','融券增減(張)','資券相抵(張)'] if c in df.columns]
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
    for col in ["殖利率(%)", "本益比(倍)", "淨值比(倍)"]: 
        if col in df_out.columns: df_out[col] = safe_to_num(df_out[col]).round(2)
    cols = [c for c in ['日期', '本益比(倍)', '淨值比(倍)', '殖利率(%)'] if c in df_out.columns]
    return df_out[cols].tail(10).sort_values('日期', ascending=False)

def process_disp(df):
    if df.empty: return pd.DataFrame()
    df_out = df.copy().rename(columns={"date":"公告日期","disposition_cnt":"處置次數","condition":"處置條件","measure":"處置措施","period_start":"處置起日","period_end":"處置迄日"})
    cols = [c for c in ['公告日期', '處置次數', '處置起日', '處置迄日', '處置條件', '處置措施'] if c in df_out.columns]
    return df_out[cols].tail(5).sort_values('公告日期', ascending=False)

def process_div(df):
    if df.empty: return pd.DataFrame()
    df_out = df.rename(columns={"date": "公告日期", "year": "股利年份", "StockEarningsDistribution": "盈餘配股(元)", "StockStatutorySurplus": "公積配股(元)", "CashEarningsDistribution": "盈餘配息(元)", "CashStatutorySurplus": "公積配息(元)"})
    cols = [c for c in ["公告日期", "股利年份", "盈餘配息(元)", "公積配息(元)", "盈餘配股(元)", "公積配股(元)"] if c in df_out.columns]
    if '股利年份' in df_out.columns:
        year_num = safe_to_num(df_out['股利年份'].astype(str).str.replace('年', '').str.strip(), fill_val=np.nan)
        recent = sorted(year_num.dropna().unique(), reverse=True)[:5]
        return df_out[year_num.isin(recent)][cols].sort_values('公告日期', ascending=False)
    return df_out[cols].sort_values('公告日期', ascending=False).head(10)

def show_table(title, df, custom_class=""):
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
    if df is None or df.empty: 
        st.warning("此區塊查無數據或無發行紀錄")
    else:
        def fmt_auto(x, col_name=""):
            if pd.isna(x): return "-"
            s = str(x).strip()
            if s in ["-", ""]: return "-"
            if s.startswith("+"): return f"<span style='color:#d9480f; font-weight:bold;'>{s}</span>"
            if "⚠️(虧)" in s:
                v_str = s.replace("⚠️(虧)", "").strip()
                try: return f"<span class='loss-warning'>⚠️(虧) {float(v_str.replace(',','').replace('%','')):,.2f}</span>"
                except: return f"<span class='loss-warning'>{s}</span>"
            if any(kw in col_name for kw in ["代號", "年份", "次數"]): return s
            is_pct = "%" in s
            try:
                c_val = float(s.replace(",", "").replace("%", ""))
                fmt_v = f"{c_val:,.2f}" if "." in s or is_pct else f"{int(c_val):,}"
                return f"{fmt_v}%" if is_pct else fmt_v
            except: return str(x)
            
        f_dict = {c: lambda x, col=c: fmt_auto(x, col) for c in df.columns}
        left_cols = [c for c in df.columns if any(kw in str(c) for kw in ['日期', '公告日期', '分點', '名稱', '姓名', '身份別', '質權人', '交易別', '診斷', '判定', '門檻', '條件', '措施', '契約', '代號', '來源', '標籤', '囤貨率(%)', '單日微觀診斷', '專家雷達診斷', '鷹眼診斷', '技術面診斷', '綜合診斷', '終極籌碼診斷'])]
        right_cols = [c for c in df.columns if c not in left_cols]
        styler = df.style.format(f_dict).set_properties(**{'text-align': 'right !important'}, subset=right_cols)
        if left_cols: styler = styler.set_properties(**{'text-align': 'left !important'}, subset=left_cols)
        try: styler = styler.hide(axis="index")
        except: styler = styler.hide_index()
        html = styler.set_table_styles([dict(selector='th', props=[('text-align', 'center !important')]), dict(selector='table', props=[('width', '100%')])]).to_html()
        html = html.replace('&lt;', '<').replace('&gt;', '>').replace('&#x27;', "'").replace('&quot;', '"')
        if custom_class: html = html.replace('<table', f'<table class="{custom_class}"')
        st.markdown(f'<div class="table-responsive">{html}</div>', unsafe_allow_html=True)

def format_to_csv_string(df, title):
    header = f"▼▼▼ {title} ▼▼▼\n"
    if df is None or df.empty: return header + "此區塊查無數據或無發行紀錄\n"
    return header + df.to_csv(index=False) + "\n"

# ==========================================
# 📌 執行主引擎
# ==========================================
if run_btn:
    if not user_stock_id.strip(): st.warning("⚠️ 請先在上方輸入股票代號！"); st.stop()

    with st.spinner(f"正在啟動 V46.13 究極效能引擎 (全域快取與零拷貝技術啟動)..."):
        name = get_stock_name_v46(user_stock_id)
        if not name: st.error(f"⚠️ 查無股票代號 {user_stock_id} 的基本資料。"); st.stop()
            
        df_p_raw = fetch_finmind_v46("TaiwanStockPrice", (datetime.date.today() - datetime.timedelta(days=1095)).strftime("%Y-%m-%d"), user_stock_id)
        if df_p_raw.empty: st.error("⚠️ 查無歷史股價資料。"); st.stop()
        
        dates = sorted(df_p_raw['date'].unique().tolist(), reverse=True)
        if not dates: st.error("⚠️ 無法取得有效交易日期，請確認 API 連線狀態。"); st.stop()
            
        max_len = lookback_days if len(dates) >= lookback_days else len(dates)
        if max_len == 0: max_len = 1
        d_end = dates[max_len-1]
        
        df_price = process_price(df_p_raw)
        df_ta_full = process_technical_analysis(df_price, ma_short, ma_mid, ma_long)
        
        dynamic_dict, s_val, chip_eng, _ = scrape_director_v46(user_stock_id)
        
        df_b_raw = fetch_branch_data_v46(dates[:max_len], user_stock_id)
        
        tags, df_debug_tags = get_v27_intelligence(df_b_raw, df_p_raw, stickiness_threshold, max_len)
        
        df_b_diff = process_branch_diff(df_b_raw, dates, firepower_threshold)
        df_daily_tracker, df_audit_smart = process_v30_daily_tracking(df_b_raw, tags, df_price, df_b_diff, dates, firepower_threshold)
        df_s_raw = fetch_finmind_v46("TaiwanStockHoldingSharesPer", d_end, user_stock_id)
        df_s_wide, df_s_unit, df_s_ppl = process_tdcc(df_s_raw)
        df_s_dyn = process_tdcc_dynamic(df_s_wide, df_price, dead_chip_input, dynamic_dict, s_val, chip_eng)
        df_v27_radar, df_debug_math, _ = process_v27_ultimate_radar(df_s_wide, dead_chip_input, dynamic_dict, s_val, df_price, df_b_raw, tags)

        df_combined_display = pd.DataFrame()
        if not df_v27_radar.empty and not df_s_dyn.empty:
            df_combined_radar = pd.merge(df_s_dyn, df_v27_radar, on=['日期', '收盤價(元)'], how='inner')
            if not df_combined_radar.empty:
                df_combined_radar['終極籌碼診斷'] = df_combined_radar['實戰判定'].astype(str) + " | " + df_combined_radar['專家雷達診斷'].astype(str)
                display_cols = ['日期', '收盤價(元)', '純淨活大戶C_Value(%)', '純淨大戶變動(%)', '總人數變動率(%)', '大戶精算門檻', '隔日沖虛胖(%)', '終極籌碼診斷']
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

        actual_foot_days = footprint_days if len(dates) >= footprint_days else len(dates)
        df_footprint_buy, df_footprint_sell = process_footprint(df_b_raw, dates[:actual_foot_days], tags, df_debug_tags, footprint_rows, max_len)

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
        curr_stock_p = df_price['收盤價(元)'].iloc[0] if not df_price.empty else 0
        df_cb_info_list = []
        if not df_cbas_raw.empty and 'cb_id' in df_cbas_raw.columns:
            cb_mask = df_cbas_raw['cb_id'].astype(str).str.replace(',', '', regex=False).str.startswith(user_stock_id)
            target_cbs = df_cbas_raw[cb_mask]['cb_id'].astype(str).str.replace(',', '', regex=False).str.replace('.0', '', regex=False).str.strip().unique()
            for cid in target_cbs:
                info_df = fetch_finmind_v46("TaiwanStockConvertibleBondInfo", "2000-01-01", tid=cid)
                if not info_df.empty: df_cb_info_list.append(info_df)
            df_cb_info = pd.concat(df_cb_info_list, ignore_index=True) if df_cb_info_list else pd.DataFrame()
            df_cbas = process_cbas(df_cbas_raw[cb_mask], curr_stock_p, df_cb_info)
        else:
            df_cbas = pd.DataFrame()

        defense_line = "無明顯防守區"
        if not df_debug_tags.empty:
            main_forces = df_debug_tags[df_debug_tags['最終標籤'].str.contains('潛伏造市者|長駐波段主')]
            if not main_forces.empty:
                total_v, total_c = 0, 0.0
                for _, r in main_forces.iterrows():
                    v = r['總買(張)']
                    c_str = str(r['買均價']).replace('⚠️(虧)', '').replace(',', '').strip()
                    try:
                        c = float(c_str)
                        total_v += v
                        total_c += v * c
                    except: pass
                if total_v > 0:
                    vwap = round(total_c / total_v, 2)
                    curr_p = df_price['收盤價(元)'].iloc[0] if not df_price.empty else 0
                    status = "🟢 守穩防線" if curr_p >= vwap else "🔴 跌破防線"
                    defense_line = f"{vwap} 元 ({status})"

        market_cap_str = "計算中..."
        industry, address = get_company_profile(user_stock_id)
        if not df_price.empty and not df_s_wide.empty:
            market_cap_str = f"{(df_price['收盤價(元)'].iloc[0] * df_s_wide['總張數'].iloc[0]) / 100000:,.2f} 億"
        
        company_info_text = f"🏢 **【產業】** {industry} ｜ 💰 **【市值】** {market_cap_str} ｜ 📍 **【公司地址】** {address}"
        
        st.subheader(f"📊 {user_stock_id} {name} 全息戰報 (V46.13 究極效能優化版)")
        st.markdown(f"<div class='info-box'>{company_info_text}<br>🏆 <b>【潛伏主力綜合防守線】</b>：{defense_line}</div>", unsafe_allow_html=True)
        
        hawk_alerts = generate_ai_hawk_eye(df_daily_tracker, df_v27_radar, df_debug_tags, df_b_diff, firepower_threshold)
        hawk_html_display = "<div class='hawk-eye-box'>"
        hawk_csv_text = "▼▼▼ 系統 AI 鷹眼深度診斷報告 ▼▼▼\n"
        for alert in hawk_alerts: 
            hawk_html_display += f"{alert}<br>"
            clean_text = re.sub(r'<[^>]+>', '', alert).replace('&nbsp;', ' ')
            if "1." in clean_text or "2." in clean_text or "3." in clean_text or "4." in clean_text: hawk_csv_text += f"\n[{clean_text}]\n"
            else: hawk_csv_text += f"- {clean_text}\n"
        hawk_html_display += "</div>"
        st.markdown(hawk_html_display, unsafe_allow_html=True)

        st.markdown("<div class='category-title'>📈 00. 職業極簡技術大局觀</div>", unsafe_allow_html=True)
        if not df_ta_full.empty:
            st.markdown(f"<div class='section-title'>📈 00. 極簡純淨 K 線與成交量 (自訂 {kline_days} 日)</div>", unsafe_allow_html=True)
            
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            df_p_plot = df_price[['日期', '開盤價(元)', '最高價(元)', '最低價(元)', '收盤價(元)', '成交量(張)']].head(kline_days).copy()
            df_t_plot = df_ta_full[['日期', f'MA{ma_short}', f'MA{ma_mid}(中線)', f'MA{ma_long}(長線)']].head(kline_days).copy()
            df_plot = pd.merge(df_p_plot, df_t_plot, on='日期', how='inner').sort_values('日期', ascending=True)
            
            if not df_plot.empty:
                df_plot['日期'] = df_plot['日期'].astype(str)
                fig_kline = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
                fig_kline.add_trace(go.Candlestick(x=df_plot['日期'], open=df_plot['開盤價(元)'], high=df_plot['最高價(元)'], low=df_plot['最低價(元)'], close=df_plot['收盤價(元)'], name='K線', increasing_line_color='#ef5350', decreasing_line_color='#26a69a'), row=1, col=1)
                if f'MA{ma_short}' in df_plot.columns: fig_kline.add_trace(go.Scatter(x=df_plot['日期'], y=df_plot[f'MA{ma_short}'], mode='lines', name=f'MA{ma_short}', line=dict(color='#ffa726', width=1.5)), row=1, col=1)
                if f'MA{ma_mid}(中線)' in df_plot.columns: fig_kline.add_trace(go.Scatter(x=df_plot['日期'], y=df_plot[f'MA{ma_mid}(中線)'], mode='lines', name=f'MA{ma_mid}', line=dict(color='#29b6f6', width=2)), row=1, col=1)
                if f'MA{ma_long}(長線)' in df_plot.columns: fig_kline.add_trace(go.Scatter(x=df_plot['日期'], y=df_plot[f'MA{ma_long}(長線)'], mode='lines', name=f'MA{ma_long}', line=dict(color='#ab47bc', width=2.5)), row=1, col=1)
                colors = ['#ef5350' if row['收盤價(元)'] >= row['開盤價(元)'] else '#26a69a' for i, row in df_plot.iterrows()]
                fig_kline.add_trace(go.Bar(x=df_plot['日期'], y=df_plot['成交量(張)'], marker_color=colors, name='成交量'), row=2, col=1)
                fig_kline.update_traces(hoverinfo='none', hovertemplate='') 
                fig_kline.update_layout(height=600, margin=dict(l=30, r=30, t=20, b=30), xaxis_rangeslider_visible=False, plot_bgcolor='white', paper_bgcolor='white', showlegend=True, legend=dict(orientation="h", yanchor="top", y=1.02, xanchor="left", x=0.01), hovermode='x')
                fig_kline.update_xaxes(type='category', showgrid=False, zeroline=False, tickangle=45, showspikes=True, spikemode='across', spikethickness=1, spikedash='dot', spikecolor='#333333', spikesnap='cursor')
                fig_kline.update_yaxes(showgrid=False, zeroline=False, showspikes=True, spikemode='across', spikethickness=1, spikedash='dot', spikecolor='#333333', spikesnap='cursor')
                st.plotly_chart(fig_kline, use_container_width=True)
            else:
                st.warning("⚠️ 查無 K 線歷史資料可供繪製圖表。")

        st.markdown("<div class='category-title'>📊 核心戰情追蹤</div>", unsafe_allow_html=True)
        show_table("01. 平日戰情追蹤矩陣 (合併家數差與火力)", df_daily_tracker, "daily-tracker")
        show_table("02. 終極集保籌碼雷達 (大戶存量與流量雙解碼)", df_combined_display, "radar-table")

        st.markdown("<div class='category-title'>🕵️‍♂️ 主力分點指紋與動向</div>", unsafe_allow_html=True)
        show_table(f"03A. 近 {actual_foot_days} 日主力足跡動態矩陣 (多單前{footprint_rows}大)", df_footprint_buy)
        show_table(f"03B. 近 {actual_foot_days} 日主力足跡動態矩陣 (空單前{footprint_rows}大)", df_footprint_sell)
        
        show_table(f"04. 主力分點 - 今日 ({dates[0]})", df_b_today)
        show_table(f"05. 主力分點 - 前一日 ({dates[1] if len(dates)>1 else '無'})", df_b_prev1)
        
        with st.expander(f"📂 06. 點此展開過渡期分點 (近3日~近 {max_len} 日總和)", expanded=False):
            show_table("06-1. 主力分點 - 近3日", df_b_3)
            show_table("06-2. 主力分點 - 近10日", df_b_10)
            show_table(f"06-3. 主力分點 - 近 {max_len} 日總和", df_b_60)

        with st.expander(f"📂 07. 點此展開主力分點指紋圖鑑 (紅色標示為目前套牢)", expanded=False):
            show_table("主力分點指紋圖鑑", df_debug_tags.head(30))

        st.markdown("<div class='category-title'>🏦 法人與資券變化</div>", unsafe_allow_html=True)
        show_table("08. 影子官股進出 (今日)", df_gov)
        show_table("09. 法人買賣超 (近10天)", df_inst)
        show_table("10. 散戶資券餘額 (近10天)", df_margin)
        show_table("11. 現股當沖明細 (近10天)", df_day_trade)
        show_table("12. 台指期貨三大法人未平倉 (大盤)", df_fut)

        st.markdown("<div class='category-title'>📈 基本面與進階籌碼數據</div>", unsafe_allow_html=True)
        show_table("13. 月營收 (百萬元) (近24個月)", df_rev)
        
        with st.expander("📂 14. 點此展開集保分級表 (近8週)", expanded=False):
            show_table("14-1. 集保分級 - 張數表", df_s_unit)
            show_table("14-2. 集保分級 - 人數表", df_s_ppl)

        show_table("15. 董監大股東質設總覽", df_p_sum)
        show_table("16. 董監大股東質設明細", df_p_det)
        show_table("17. 鉅額交易明細 (近3日)", df_twse)
        show_table("18. 歷年股利 (近5年)", df_div)
        show_table("19. 本益比、淨值比與殖利率", df_per)
        show_table("20. 處置有價證券狀態", df_disp)
        show_table("21. CBAS 可轉債數據 (未償還比例與套利雷達精算)", df_cbas)

        st.divider()
        st.info("請將下方所需資料複製後貼給 Gemini 進行深度分析或稽核。")
        
        with st.expander(f"📋 給 Gemini 的 V46.13 實戰精華資料包 (CSV格式)", expanded=True):
            p1 = f"請依下面最新的盤後資料與系統鷹眼報告幫我深度分析 {user_stock_id} {name} 的量化籌碼，必須以我給的資料優先使用。\n\n"
            p1 += f"{company_info_text}\n\n"
            p1 += hawk_csv_text + "\n"
            p1 += f"【潛伏主力防線】: {defense_line}\n\n"
            
            p1 += format_to_csv_string(df_daily_tracker, "01. 平日戰情追蹤矩陣 (近5日)")
            p1 += format_to_csv_string(df_combined_display.head(4) if not df_combined_display.empty else df_combined_display, "02. 終極集保籌碼雷達 (近4週)")
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
