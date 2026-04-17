import streamlit as st, requests, pandas as pd, numpy as np, datetime, re, concurrent.futures, urllib.request, ssl, urllib3
from io import StringIO
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="V47.2 終極全息量化系統 (銅牆鐵壁版)", layout="wide", initial_sidebar_state="expanded")
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

st.title("📱 V47.2 終極全息量化系統 (銅牆鐵壁版)")
st.caption("🚀 深度優化：全面導入防禦性編程 (Defensive Programming)，徹底根絕 API 欄位缺失或大小寫錯誤造成的系統崩潰。")

col1, col2 = st.columns([1, 1])
with col1: user_stock_id = st.text_input("個股代號", value="8027")
with col2: dead_chip_input = st.text_input("死籌碼 % (留空自動雙引擎抓取)")
run_btn = st.button("🚀 啟動 V47.2 全局運算引擎", use_container_width=True, key="run_engine")

# ⚡ V47.2 絕對安全的數值轉換引擎
def safe_to_num(series, fill_val=0):
    if series is None: return fill_val
    if not isinstance(series, pd.Series): series = pd.Series(series)
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
            r = session.get("https://api.finmindtrade.com/api/v4/data", params={"dataset": "TaiwanStockTradingDailyReport", "data_id": tid, "start_date": d, "end_date": d}, timeout=10)
            if r.status_code == 200: return r.json().get("data", [])
        except: pass
        return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
        for r in ex.map(fs, dl):
            if r: all_d.extend(r)
    return pd.DataFrame(all_d)

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
        df_all[c] = safe_to_num(df_all.get(c, 0)).astype(int)
        
    prd = {pd.to_datetime(r['date']).strftime('%Y-%m-%d'): r['close'] for _, r in df_pr.iterrows()} if 'date' in df_pr.columns and 'close' in df_pr.columns else {}
    pps, mcs = [], []
    for _, r in df_all.iterrows():
        fp, mc = "-", "-"
        if r.get('設質(張)', 0) > 0:
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
        if sm[r['姓名']]["p"] == "-" and r.get('設質(張)', 0) > 0: sm[r['姓名']]["p"], sm[r['姓名']]["mc"] = r['設質日收盤價'], r['強制賣出價(0.78)']
    sr = [{"身份別": d["title"], "姓名": n, "目前剩餘質設(張)": d["balance"], "最後設質收盤價(元)": d["p"], "估算斷頭價(0.78)": d["mc"]} for n, d in sm.items() if d["balance"] > 0]
    return pd.DataFrame(sr), df_all

def get_v27_intelligence(df_b_raw, df_p_raw, stick_thresh, global_days):
    if df_b_raw.empty or df_p_raw.empty or 'date' not in df_p_raw.columns or 'date' not in df_b_raw.columns: 
        return {}, pd.DataFrame()
    if global_days <= 0: global_days = 1
    df_p = df_p_raw.copy()
    df_p['date'] = pd.to_datetime(df_p['date'], errors='coerce')
    
    # ⚡ V47.2：全部使用寬容取值機制
    df_p['close'] = safe_to_num(df_p.get('close', 0))
    df_p['max'] = safe_to_num(df_p.get('max', 0))
    df_p['min'] = safe_to_num(df_p.get('min', 0))
    
    df_p['avg_price'] = (df_p['close'] + df_p['max'] + df_p['min']) / 3
    range_diff = df_p['max'] - df_p['min']
    df_p['pos'] = np.where(range_diff == 0, 1.0, (df_p['close'] - df_p['min']) / np.where(range_diff==0, 1, range_diff))
    df_p['strength'] = np.where(df_p['avg_price'] == 0, 0, (df_p['close'] - df_p['avg_price']) / np.where(df_p['avg_price']==0, 1, df_p['avg_price']))
    price_stats = df_p.set_index('date')[['pos', 'strength']].to_dict('index')
    latest_close = df_p.sort_values('date', ascending=False)['close'].iloc[0] if not df_p.empty else 0

    df = df_b_raw.copy()
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['buy_shares'] = safe_to_num(df.get('buy', 0))
    df['sell_shares'] = safe_to_num(df.get('sell', 0))
    df['price_val'] = safe_to_num(df.get('price', 0))
    df['buy_amt'] = df['buy_shares'] * df['price_val']
    df['sell_amt'] = df['sell_shares'] * df['price_val']
    
    tags, d_rows = {}, []
    if 'securities_trader' not in df.columns: return tags, pd.DataFrame()
    
    for trader, g in df.groupby('securities_trader'):
        tb, ts = round(g['buy_shares'].sum() / 1000), round(g['sell_shares'].sum() / 1000)
        tv = tb + ts
        if tv == 0: continue
        active_days = g['date'].nunique()
        stickiness = (active_days / global_days) * 100
        dr, net = (min(tb, ts) * 2) / tv if tv > 0 else 0, tb - ts
        nr = net / tb if tb > 0 else -1
        hoard_ratio = (abs(net) / tv * 100) if tv > 0 else 0
        avg_b = g['buy_amt'].sum() / g['buy_shares'].sum() if g['buy_shares'].sum() > 0 else 0
        avg_s = g['sell_amt'].sum() / g['sell_shares'].sum() if g['sell_shares'].sum() > 0 else 0
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
    if df_raw.empty or not dynamic_dates or 'date' not in df_raw.columns or 'securities_trader' not in df_raw.columns: 
        return pd.DataFrame(), pd.DataFrame()
    df = df_raw[df_raw['date'].isin(dynamic_dates)].copy()
    if df.empty: return pd.DataFrame(), pd.DataFrame()
    
    df['buy'] = safe_to_num(df.get('buy', 0))
    df['sell'] = safe_to_num(df.get('sell', 0))
    
    df['net'] = ((df['buy'] - df['sell']) / 1000).round().astype(int)
    g = df.groupby(['securities_trader', 'date'])['net'].sum().reset_index()
    p = g.pivot(index='securities_trader', columns='date', values='net').fillna(0).astype(int)
    p['total'] = p.sum(axis=1)
    top_b = p[p['total'] > 0].nlargest(top_n, 'total').reset_index()
    top_s = p[p['total'] < 0].nsmallest(top_n, 'total').reset_index()
    
    fp_dict = {}
    if not df_fingerprint.empty and '分點名稱' in df_fingerprint.columns:
        fp_dict = df_fingerprint.set_index('分點名稱')[['黏著度(%)', '囤貨率(%)']].to_dict('index')
    
    def build_df(res_df):
        out = []
        for _, r in res_df.iterrows():
            trader = r.get('securities_trader', '')
            st_val = fp_dict.get(trader, {}).get('黏著度(%)', "-")
            hr_val = fp_dict.get(trader, {}).get('囤貨率(%)', "-")
            
            row_dict = {
                "分點名稱": trader, 
                "標籤": intel_tags.get(trader, "🔵 一般"),
                "黏著度(%)": st_val,
                "囤貨率(%)": hr_val,
                f"{len(dynamic_dates)}日累計(張)": f"+{r.get('total',0)}" if r.get('total',0) > 0 else str(r.get('total',0))
            }
            for i, d in enumerate(dynamic_dates):
                v = r.get(d, 0)
                row_dict[f"T-{i}" if i > 0 else "今日(T)"] = f"+{v}" if v > 0 else str(v)
            out.append(row_dict)
        return pd.DataFrame(out)
    return build_df(top_b), build_df(top_s)

def process_branch_v25(df_raw, period, actual_dates, intel_tags, df_price_raw, stick_thresh, global_days):
    if df_raw.empty or df_price_raw.empty or 'date' not in df_raw.columns or 'close' not in df_price_raw.columns: 
        return pd.DataFrame()
    latest_close = df_price_raw.sort_values('date', ascending=False)['close'].iloc[0]
    if global_days <= 0: global_days = 1
    global_act_days = df_raw.groupby('securities_trader')['date'].nunique().to_dict() if 'securities_trader' in df_raw.columns else {}
    df = df_raw[df_raw['date'].isin(actual_dates[:period])].copy()
    if df.empty or 'securities_trader' not in df.columns: return pd.DataFrame()
    
    df['buy'] = safe_to_num(df.get('buy', 0))
    df['sell'] = safe_to_num(df.get('sell', 0))
    df['price'] = safe_to_num(df.get('price', 0))
    
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
    if df_wide.empty or len(df_wide) < 2 or '日期' not in df_wide.columns: 
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df = df_wide.sort_values('日期', ascending=True).copy()
    df['dt_end'] = pd.to_datetime(df['日期'], errors='coerce')
    if not df_price.empty and '日期' in df_price.columns and '收盤價(元)' in df_price.columns:
        df_p = df_price.copy()
        df_p['dt'] = pd.to_datetime(df_p['日期'], errors='coerce')
        df_p = df_p.sort_values('dt'); df_p['ma20'] = df_p['收盤價(元)'].rolling(20).mean()
        df = pd.merge_asof(df.sort_values('dt_end'), df_p[['dt', '收盤價(元)', 'ma20']], left_on='dt_end', right_on='dt', direction='backward')
    else: df['收盤價(元)'], df['ma20'] = 0, 0
    
    col_1000 = '1000張以上_比例(%)' if '1000張以上_比例(%)' in df.columns else None
    if col_1000: df['原始大戶變動(%)'] = df[col_1000].diff().round(2)
    else: df['原始大戶變動(%)'] = 0
    
    if '總人數(人)' in df.columns: df['總人數變動率(%)'] = (df['總人數(人)'].pct_change() * 100).round(2)
    else: df['總人數變動率(%)'] = 0

    out, d_math, d_fri = [], [], []
    branch_groups = df_branch_raw.groupby('date') if not df_branch_raw.empty and 'date' in df_branch_raw.columns else None
    
    for i, row in df.iterrows():
        if pd.isna(row.get('原始大戶變動(%)', np.nan)): out.append({"純淨變動": 0, "雜訊": 0, "診斷": "⚪ 初始化"}); continue
        d_str = row['日期']
        df_f = branch_groups.get_group(d_str).copy() if branch_groups is not None and d_str in branch_groups.groups else pd.DataFrame()
        f_vol = 0
        if not df_f.empty and 'securities_trader' in df_f.columns:
            df_f['tag'] = df_f['securities_trader'].map(intel_tags)
            fn = df_f[df_f['tag'].str.contains("隔日沖|被套牢|游擊過客", na=False)] 
            f_vol = round(safe_to_num(fn.get('buy', 0)).sum() / 1000)
            for _, fr in fn.iterrows():
                buy_vol = pd.to_numeric(str(fr.get('buy', 0)).replace(',', '').strip(), errors='coerce')
                if buy_vol and buy_vol > 0: d_fri.append({"日期": d_str, "分點": fr.get('securities_trader', ''), "張數": round(buy_vol/1000)})
        f_impact = (f_vol / row['總張數']) * 100 if row.get('總張數', 0) > 0 else 0
        p_chg = round(row.get('原始大戶變動(%)', 0) - f_impact, 2)
        d_math.append({"日期": d_str, "原始變動": row.get('原始大戶變動(%)', 0), "隔日沖干擾": round(f_impact, 2), "純淨變動": p_chg})
        dead, _ = get_dead_chip_info(d_str, dead_chip_input, dynamic_dict, static_val, "")
        lev = 100 / (100 - dead) if 0 < dead < 100 else 1
        adv = []
        if row.get('總人數變動率(%)', 0) > 2.0 and p_chg < 0: adv.append(f"💀 [逃命] 散戶增{row.get('總人數變動率(%)',0)}%，大戶實質倒貨{abs(p_chg)}%")
        else:
            if p_chg * lev > 2.5 and row.get('收盤價(元)', 0) > row.get('ma20', 0): adv.append(f"🚀 [真軋空] 站上月線且大戶純淨買超{round(p_chg*lev, 2)}%")
            elif p_chg > 0.4 and row.get('收盤價(元)', 0) < row.get('ma20', 0): adv.append(f"🧱 [底位建倉] 跌破月線但主力吃貨{p_chg}%")
            elif p_chg < -1.0: adv.append(f"📉 [主力撤退] 大戶實質流出{abs(p_chg)}%")
            if f_impact > 1.2: adv.append(f"⚡ [隔日沖陷阱] 虛胖買盤潛藏{round(f_impact, 2)}%倒貨危機")
        out.append({"純淨變動": p_chg, "雜訊": round(f_impact, 2), "診斷": " | ".join(adv) if adv else "🔵 盤整"})
    ddf = pd.DataFrame(out)
    if not ddf.empty:
        df['純淨大戶變動(%)'], df['隔日沖虛胖(%)'], df['專家雷達診斷'] = ddf.get('純淨變動',0), ddf.get('雜訊',0), ddf.get('診斷',"")
        cols_to_rtn = ['日期', '收盤價(元)', '總人數變動率(%)', '原始大戶變動(%)', '隔日沖虛胖(%)', '純淨大戶變動(%)', '專家雷達診斷']
        safe_cols = [c for c in cols_to_rtn if c in df.columns]
        return df[safe_cols].sort_values('日期', ascending=False)[df['專家雷達診斷'] != '⚪ 初始化'], pd.DataFrame(d_math), pd.DataFrame(d_fri)
