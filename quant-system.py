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

# 關閉憑證警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 設定網頁標題與佈局
st.set_page_config(page_title="V34.2 終極全息量化系統 (純淨十字線版)", layout="wide")

# 內建 Token
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

# 注入全局 CSS
st.markdown("""
<style>
.table-responsive { overflow-x: auto; width: 100%; display: block; margin-bottom: 20px; }
table.dataframe { border-collapse: collapse; width: 100%; }
table.dataframe th, table.dataframe td { white-space: nowrap !important; text-align: center !important; padding: 8px 12px !important; }
table.dataframe th:first-child, table.dataframe td:first-child { position: sticky; left: 0; background-color: #f1f3f5; z-index: 1; border-right: 2px solid #dee2e6; }
.radar-table td:last-child { text-align: left !important; color: #ff4b4b; font-weight: bold; }
.daily-tracker td:last-child { text-align: left !important; color: #008080; font-weight: bold; }
.info-box { background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #ff4b4b; font-size: 16px;}
.dict-box { background-color: #fdf2f2; padding: 15px; border-radius: 10px; border-left: 5px solid #e03131; font-size: 14.5px; line-height: 1.7;}
.hawk-eye-box { background-color: #fff9db; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 6px solid #f59f00; font-size: 15px; line-height: 1.8;}
.hawk-alert { color: #d9480f; font-weight: bold; }
.hawk-safe { color: #2b8a3e; font-weight: bold; }
.hawk-title { font-size: 18px; font-weight: 900; color: #333; margin-bottom: 10px; border-bottom: 1px solid #ccc; padding-bottom: 5px;}
.section-title { margin-top: 35px; margin-bottom: 15px; color: #1e3a8a; border-bottom: 2px solid #1e3a8a; padding-bottom: 5px; font-size: 1.3rem !important; font-weight: 700 !important; }
.category-title { font-size: 1.6rem !important; font-weight: 900 !important; margin-top: 40px; color: #333; }
.loss-warning { color: #d9480f; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("📱 V34.2 終極全息量化系統 (純淨十字線版)")
st.caption("視覺優化：移除遮擋畫面的統整報價框，保留純淨的十字查價線供對齊使用。")

# UI 輸入區
col1, col2 = st.columns([1, 1])
with col1: 
    user_stock_id = st.text_input("個股代號", value="8027", placeholder="請輸入台股代號 (例: 2330)")
with col2: 
    dead_chip_input = st.text_input("死籌碼 %", placeholder="自動抓取董監事持股，也可自行輸入", help="留空將自動抓取。也可自行輸入比例數值")
run_btn = st.button("🚀 啟動 V34.2 視覺化運算引擎", use_container_width=True)

with st.expander("📖 【V34.2 實戰字典：破解主力的最高機密】", expanded=False):
    st.markdown("""
    <div class='dict-box'>
    <h4 style="color:#e03131; margin-top:0;">壹、戰情矩陣三維口訣 (看懂表 01)</h4>
    <ol>
        <li><b>看方向 (聰明錢淨流)</b>：正數代表波段大戶進場；負數代表撤退。</li>
        <li><b>看底氣 (均價落差)</b>：正數代表大戶賺錢，負數代表大戶賠錢(接刀)。</li>
        <li><b>看結構 (火力倍數)</b>：買方火力 > 1.5 倍代表大戶集中吃貨，高勝率。</li>
    </ol>
    <h4 style="color:#e03131;">貳、技術與籌碼雙劍合璧 (看 00 區塊 K線圖)</h4>
    <ul>
        <li><b>抄底黃金買點</b>：聰明錢連買 3 天 ＋ 買方火力 > 1.5 倍，且技術面剛好回踩 MA60 (季線乖離接近 0)。</li>
        <li><b>十字查價線</b>：滑鼠移入 K 線圖，系統會拉出純淨十字準星，方便垂直對齊成交量與時間軸。</li>
        <li><b>停損多殺多</b>：聰明錢大賣，且 MACD 出現死亡交叉並跌破季線。主力與技術派同時倒貨，嚴格停損。</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ==========================================
# 📌 工具與基本面情報抓取
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def get_stock_name(target_id):
    try:
        res = requests.get(f"https://tw.stock.yahoo.com/quote/{target_id}.TW", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if res.status_code == 200:
            match = re.search(r'<title>(.*?)\s*\(', res.text)
            return match.group(1).strip() if match else ""
    except: pass
    return ""

@st.cache_data(ttl=3600, show_spinner=False)
def get_company_profile(target_id):
    industry, address = "未知產業", "查無地址"
    try:
        fm_info = fetch_fm("TaiwanStockInfo", "2020-01-01")
        if not fm_info.empty and 'stock_id' in fm_info.columns:
            match_row = fm_info[fm_info['stock_id'] == str(target_id)]
            if not match_row.empty: industry = match_row['industry_category'].iloc[0]
    except: pass
    try:
        res = requests.get(f"https://tw.stock.yahoo.com/quote/{target_id}/profile", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if res.status_code == 200:
            text = re.sub(r'<[^>]+>', '|', res.text)
            match = re.search(r'公司地址\|+([^|]+)', text)
            if match: address = match.group(1).strip()
    except: pass
    return industry, address

def safe_get_fubon(url):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        if hasattr(ssl, 'OP_LEGACY_SERVER_CONNECT'): ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            return response.read().decode('big5', errors='ignore')
    except:
        try:
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, verify=False)
            if res.status_code == 200:
                res.encoding = 'big5'
                return res.text
        except: pass
    return ""

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fm(dataset, start_date, target_id=None, end_date=None):
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {"dataset": dataset, "start_date": start_date}
    if target_id: params["data_id"] = target_id
    if end_date: params["end_date"] = end_date
    try: 
        res = requests.get(url, params=params, headers={"Authorization": f"Bearer {FINMIND_TOKEN}"}, timeout=15)
        if res.status_code == 200:
            return pd.DataFrame(res.json().get("data", []))
    except: pass
    return pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fm_branch_fast_parallel(dates_list, target_id):
    if not dates_list: return pd.DataFrame()
    all_data = []
    def fetch_single(d):
        try: 
            res = requests.get("https://api.finmindtrade.com/api/v4/data", params={"dataset": "TaiwanStockTradingDailyReport", "data_id": target_id, "start_date": d, "end_date": d}, headers={"Authorization": f"Bearer {FINMIND_TOKEN}"}, timeout=15)
            if res.status_code == 200:
                return res.json().get("data", [])
        except: pass
        return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for r in executor.map(fetch_single, dates_list):
            if r: all_data.extend(r)
    return pd.DataFrame(all_data)

@st.cache_data(ttl=3600, show_spinner=False)
def scrape_block_trades(target_id, actual_dates):
    if not actual_dates: return pd.DataFrame(), []
    target_dates = actual_dates[:3] 
    block_data, debug_log = [], []
    def fetch_date(d):
        d_twse, d_tpex = d.replace("-", ""), f"{int(d.split('-')[0])-1911}/{d.split('-')[1]}/{d.split('-')[2]}"
        res_list, headers = [], {"User-Agent": "Mozilla/5.0"}
        try:
            res = requests.get(f"https://www.twse.com.tw/rwd/zh/block/BFIAUU?date={d_twse}&response=json", headers=headers, timeout=5, verify=False)
            if res.status_code == 200:
                j = res.json()
                if "data" in j and j["data"]:
                    for r in j["data"]:
                        if target_id in str(r): res_list.append([d, "TWSE", r])
        except: pass
        try:
            res = requests.get(f"https://www.tpex.org.tw/www/zh-tw/blockTrade/quote?date={d_tpex}&id=&response=json", headers=headers, timeout=5, verify=False)
            if res.status_code == 200:
                j = res.json()
                if "tables" in j and len(j["tables"])>0 and "data" in j["tables"][0]:
                    for r in j["tables"][0]["data"]:
                        if target_id in str(r): res_list.append([d, "TPEx", r])
        except: pass
        return res_list
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        for data in executor.map(fetch_date, target_dates):
            if data: block_data.extend(data)
    if not block_data: return pd.DataFrame(), list(set(debug_log))
    parsed = []
    for item in block_data:
        date, src, row = item
        nums = []
        for c in row:
            c_str = re.sub(r'<[^>]+>', '', str(c)).replace(',', '').strip()
            if c_str and ':' not in c_str:
                try: nums.append(float(c_str))
                except ValueError: pass
        nums.sort(reverse=True)
        if len(nums) >= 3:
            amt = nums[0] / 10000 if nums[0] > 100000 else nums[0]
            vol = nums[1] / 1000 if nums[1] > 1000 else nums[1]
            price = nums[2]
            t_type = next((re.sub(r'<[^>]+>', '', str(c)).strip() for c in row if any(x in str(c) for x in ["配對", "交易", "單一", "組合", "逐筆"])), "鉅額")
            parsed.append({"日期": date, "交易別": t_type, "成交量(張)": int(vol), "成交價(元)": round(price, 2), "成交金額(萬元)": int(amt)})
    return pd.DataFrame(parsed).sort_values("日期", ascending=False), list(set(debug_log))

@st.cache_data(ttl=3600, show_spinner=False)
def scrape_director_holding(target_id):
    headers = {"User-Agent": "Mozilla/5.0"}
    d_dict, static_val = {}, 0.0
    try:
        res = requests.get(f"https://goodinfo.tw/tw/StockDirectorSharehold.asp?STOCK_ID={target_id}", headers={"User-Agent": "Mozilla/5.0", "Cookie": "CLIENT_KEY=20260413;", "Referer": f"https://goodinfo.tw/tw/StockDetail.asp?STOCK_ID={target_id}"}, timeout=8)
        if res.status_code == 200:
            res.encoding = 'utf-8'
            for df in pd.read_html(StringIO(res.text)):
                if isinstance(df.columns, pd.MultiIndex): df.columns = ['_'.join(str(c) for c in col if 'Unnamed' not in str(c)).strip('_') for col in df.columns.values]
                else: df.columns = df.columns.astype(str)
                t_col = next((c for c in df.columns if '全體董監持股' in str(c) and '持股(%)' in str(c).replace(' ', '')), None)
                m_col = next((c for c in df.columns if '月別' in str(c)), None)
                if t_col and m_col:
                    latest = 0.0
                    for _, row in df.iterrows():
                        m, v = str(row[m_col]).replace('/', '-').strip(), str(row[t_col]).replace(',', '').strip()
                        if re.match(r'^\d{4}-\d{2}$', m) and v not in ['-', '', 'nan']:
                            try:
                                val = float(v)
                                if 0 < val < 100:
                                    d_dict[m] = val
                                    if latest == 0.0: latest = val
                            except: pass
                    if d_dict: return d_dict, latest, "Goodinfo", []
    except: pass
    return {}, 0.0, "失敗", []

def get_dead_chip_info(date_str, dead_chip_input, dynamic_dict, static_val, chip_engine):
    if dead_chip_input and str(dead_chip_input).strip() != "":
        try: return float(str(dead_chip_input).replace('%', '').strip()), "手動"
        except: pass
    m_key = str(date_str)[:7].replace('/', '-')
    if dynamic_dict and m_key in dynamic_dict: return dynamic_dict[m_key], "Goodinfo當月"
    if dynamic_dict: return list(dynamic_dict.values())[0], "Goodinfo最新"
    return (static_val, chip_engine) if static_val > 0 else (0.0, "-")

def extract_fubon_table(html_text, trigger, cols):
    start_idx = html_text.find(trigger)
    if start_idx == -1: return []
    fast_html = html_text[max(0, start_idx - 500) : start_idx + 35000]
    trs = re.compile(r'<tr[^>]*>([\s\S]*?)</tr>', re.IGNORECASE).findall(fast_html)
    td_pat = re.compile(r'<t[dh][^>]*>([\s\S]*?)</t[dh]>', re.IGNORECASE)
    out, is_t = [], False
    for tr in trs:
        tds = td_pat.findall(tr)
        if tds:
            row = [re.sub(r'<[^>]+>', '', td).replace('&nbsp;', '').replace(' ', '').replace('\r', '').replace('\n', '').strip() for td in tds]
            if trigger in "".join(row): is_t = True
            elif is_t and len(row) >= cols:
                if row[0] == "" or "註" in row[0]: is_t = False
                else: out.append(row[:cols])
    return out

def scrape_fubon_pledge(df_price_raw, target_id):
    all_data = []
    for i in range(3):
        html = safe_get_fubon(f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zc0/zc06_{target_id}_{i}.djhtm")
        if html:
            p = extract_fubon_table(html, "設質人身", 7)
            if p: all_data.extend(p)
    if not all_data: return pd.DataFrame(), pd.DataFrame()
    seen = set(); uniq = []
    for r in all_data:
        if "|".join(r) not in seen: seen.add("|".join(r)); uniq.append(r)
    df_all = pd.DataFrame(uniq, columns=["日期", "身份別", "姓名", "設質(張)", "解質(張)", "累積質設(張)", "質權人"])
    cy, cm = datetime.datetime.now().year, datetime.datetime.now().month
    py, pm = cy, 99
    p_dates = []
    for d_str in df_all['日期']:
        if len(d_str) == 5 and '/' in d_str: 
            m = int(d_str.split('/')[0])
            if pm == 99: py = cy - 1 if m > cm + 1 and cm < 3 else cy
            elif m > pm + 1: py -= 1
            pm = m
            p_dates.append(f"{py}-{d_str.replace('/', '-')}")
        elif len(d_str) >= 7 and '/' in d_str: 
            pts = d_str.split('/')
            py, pm = int(pts[0]) + 1911, int(pts[1])
            p_dates.append(f"{py}-{pts[1].strip()}-{pts[2].strip()}")
        else: p_dates.append(d_str)
    df_all['日期'] = p_dates
    for col in ["設質(張)", "解質(張)", "累積質設(張)"]: 
        df_all[col] = pd.to_numeric(df_all[col].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0).astype(int)
    
    price_dict = {pd.to_datetime(row['date']).strftime('%Y-%m-%d'): row['close'] for _, row in df_price_raw.iterrows()}
    p_prices, m_calls = [], []
    for _, row in df_all.iterrows():
        found_p, mc = "-", "-"
        if row['設質(張)'] > 0:
            try:
                td = pd.to_datetime(row['日期'])
                for i in range(20):
                    cd = (td - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
                    if cd in price_dict:
                        found_p = price_dict[cd]; mc = round(found_p * 0.78, 2); break
            except: pass
        p_prices.append(found_p); m_calls.append(mc)
    df_all['設質日收盤價'], df_all['強制賣出價(0.78)'] = p_prices, m_calls
    
    s_map = {}
    for _, r in df_all.iterrows():
        if r['姓名'] not in s_map: s_map[r['姓名']] = {"title": r['身份別'], "balance": r['累積質設(張)'], "p": "-", "mc": "-"}
        if s_map[r['姓名']]["p"] == "-" and r['設質(張)'] > 0:
            s_map[r['姓名']]["p"], s_map[r['姓名']]["mc"] = r['設質日收盤價'], r['強制賣出價(0.78)']
    s_rows = [{"身份別": d["title"], "姓名": n, "目前剩餘質設(張)": d["balance"], "最後設質收盤價(元)": d["p"], "估算斷頭價(0.78)": d["mc"]} for n, d in s_map.items() if d["balance"] > 0]
    return pd.DataFrame(s_rows), df_all

# ==========================================
# 📌 核心演算法
# ==========================================
def get_v27_intelligence(df_b_raw, df_p_raw):
    if df_b_raw.empty or df_p_raw.empty: return {}, pd.DataFrame()
    
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
    df['buy_shares'] = pd.to_numeric(df['buy'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    df['sell_shares'] = pd.to_numeric(df['sell'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    df['price_val'] = pd.to_numeric(df['price'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    
    df['buy_amt'] = df['buy_shares'] * df['price_val']
    df['sell_amt'] = df['sell_shares'] * df['price_val']
    
    tags, d_rows = {}, []
    for trader, g in df.groupby('securities_trader'):
        tb = round(g['buy_shares'].sum() / 1000)
        ts = round(g['sell_shares'].sum() / 1000)
        tv = tb + ts
        if tv == 0: continue
        dr = (min(tb, ts) * 2) / tv if tv > 0 else 0
        net = tb - ts
        nr = net / tb if tb > 0 else -1
        
        sum_buy_shares = g['buy_shares'].sum()
        sum_sell_shares = g['sell_shares'].sum()
        avg_b = g['buy_amt'].sum() / sum_buy_shares if sum_buy_shares > 0 else 0
        avg_s = g['sell_amt'].sum() / sum_sell_shares if sum_sell_shares > 0 else 0
        
        ld = g['date'].max()
        stats = price_stats.get(ld, {'pos': 0.5, 'strength': 0})
        pos, strn = stats['pos'], stats['strength']
        
        tag = "🔵 一般"
        if any(x in trader for x in ["台銀", "土銀", "彰銀", "第一", "兆豐", "華南", "合庫", "台企銀"]): tag = "🏦 [官股]"
        elif dr > 0.80:
            if nr < 0.05: tag = "🌪️ [純當沖客]"
            elif (strn > 0.01 and pos >= 0.7) or (pos == 1.0): tag = "🧱 [主動鎖碼]" 
            elif strn < -0.01 and pos < 0.3: tag = "🩹 [被動套牢]" 
            else: tag = "⚡ [隔日沖]"
        elif nr > 0.7: tag = "📈 [波段主]"
        elif tb > 500 and nr > 0.85: tag = "🧱 [真鎖碼]"
        
        tags[trader] = tag
        if tb > 100 or ts > 100:
            b_str = f"{round(avg_b, 2):,.2f}"
            if avg_b > latest_close and avg_b > 0 and net > 0:
                b_str = f"⚠️(虧) {b_str}"
                
            d_rows.append({
                "分點名稱": trader, "最終標籤": tag, "總買(張)": tb, "總賣(張)": ts, "淨留倉": int(net), 
                "買均價": b_str, "賣均價": round(avg_s, 2),
                "當沖率(%)": round(dr*100, 1), "均價強度(%)": round(strn*100, 2), "收盤位階": round(pos, 2)
            })
            
    return tags, pd.DataFrame(d_rows).sort_values('總買(張)', ascending=False)

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
            fn = df_f[df_f['tag'].str.contains("隔日沖|被套牢")] 
            f_vol = round(pd.to_numeric(fn['buy'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0).sum() / 1000)
            for _, fr in fn.iterrows():
                buy_vol = pd.to_numeric(str(fr['buy']).replace(',', '').strip(), errors='coerce')
                if buy_vol and buy_vol > 0: 
                    d_fri.append({"日期": d_str, "分點": fr['securities_trader'], "張數": round(buy_vol/1000)})
        
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
    
    df_radar = df[['日期', '收盤價(元)', '總人數變動率(%)', '原始大戶變動(%)', '隔日沖虛胖(%)', '純淨大戶變動(%)', '專家雷達診斷']].sort_values('日期', ascending=False)
    df_radar = df_radar[df_radar['專家雷達診斷'] != '⚪ 初始化']
    
    return df_radar, pd.DataFrame(d_math), pd.DataFrame(d_fri)

def process_branch_diff(df_raw, actual_dates):
    if df_raw.empty or not actual_dates: return pd.DataFrame()
    out = []
    df_raw_num = df_raw.copy()
    df_raw_num['buy'] = pd.to_numeric(df_raw_num['buy'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    df_raw_num['sell'] = pd.to_numeric(df_raw_num['sell'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    
    for d in actual_dates[:10]:
        df_d = df_raw_num[df_raw_num['date'] == d]
        if df_d.empty: continue
        
        buy_branches = df_d[df_d['buy'] > 0]
        sell_branches = df_d[df_d['sell'] > 0]
        buy_count = buy_branches['securities_trader'].nunique()
        sell_count = sell_branches['securities_trader'].nunique()
        diff_count = buy_count - sell_count
        active_count = df_d[(df_d['buy'] > 0) | (df_d['sell'] > 0)]['securities_trader'].nunique()
        concentration = ((sell_count - buy_count) / active_count * 100) if active_count > 0 else 0
        total_buy_vol = buy_branches['buy'].sum()
        total_sell_vol = sell_branches['sell'].sum()
        avg_buy_per_branch = total_buy_vol / buy_count if buy_count > 0 else 0
        avg_sell_per_branch = total_sell_vol / sell_count if sell_count > 0 else 0
        firepower = (avg_buy_per_branch / avg_sell_per_branch) if avg_sell_per_branch > 0 else (99.9 if avg_buy_per_branch > 0 else 1.0)
        
        diag = []
        if firepower > 1.5 and concentration > 5: diag.append("🔥 大戶火力壓制 (集中吃貨)")
        elif firepower < 0.7 and diff_count > 50: diag.append("💀 散戶螞蟻搬家 (主力倒貨)")
        elif active_count > 500 and firepower < 1.0: diag.append("⚠️ 籌碼極度發散 (熱門當沖雷區)")
        
        out.append({
            "日期": d, "活躍家數": active_count, "買賣家數差": diff_count, 
            "籌碼集中度(%)": round(concentration, 1), "買方火力(倍)": round(firepower, 2),
            "鷹眼診斷": " | ".join(diag) if diag else "🔵 中性換手"
        })
    return pd.DataFrame(out)

def process_v30_daily_tracking(df_branch_raw, intel_tags, df_price, df_branch_diff, actual_dates):
    if df_branch_raw.empty or len(actual_dates) < 5: return pd.DataFrame(), pd.DataFrame()
    out = []
    df_b = df_branch_raw.copy()
    df_b['bs'] = pd.to_numeric(df_b['buy'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    df_b['ss'] = pd.to_numeric(df_b['sell'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    df_b['pr'] = pd.to_numeric(df_b['price'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    df_b['tag'] = df_b['securities_trader'].map(intel_tags).fillna("🔵 一般")

    audit_smart_money = []

    for d in actual_dates[:5]:
        pr_row = df_price[df_price['日期'] == d]
        cp = pr_row['收盤價(元)'].iloc[0] if not pr_row.empty else 0
        sp = pr_row['漲跌(元)'].iloc[0] if not pr_row.empty else 0

        diff_row = df_branch_diff[df_branch_diff['日期'] == d]
        bsd = diff_row['買賣家數差'].iloc[0] if not diff_row.empty else 0
        firepower = diff_row['買方火力(倍)'].iloc[0] if not diff_row.empty and '買方火力(倍)' in diff_row.columns else 1.0

        day_b = df_b[df_b['date'] == d]
        smart_b = day_b[day_b['tag'].str.contains('波段主|真鎖碼|官股')]
        short_b = day_b[day_b['tag'].str.contains('隔日沖|套牢')]
        
        smart_grouped = smart_b.groupby(['securities_trader', 'tag'])[['bs', 'ss']].sum().reset_index()
        smart_grouped['net_vol'] = ((smart_grouped['bs'] - smart_grouped['ss']) / 1000).round().astype(int)
        
        short_grouped = short_b.groupby('securities_trader')[['bs', 'ss']].sum().reset_index()
        short_grouped['net_vol'] = ((short_grouped['bs'] - short_grouped['ss']) / 1000).round().astype(int)

        if d == actual_dates[0]:
            for _, r in smart_grouped.iterrows():
                if r['net_vol'] != 0:
                    audit_smart_money.append({"日期": d, "分點": r['securities_trader'], "標籤": r['tag'], "淨買超(張)": r['net_vol']})

        smart_net = smart_grouped['net_vol'].sum()
        short_trap = short_grouped['net_vol'].sum()

        smart_buy_amt = (smart_b['bs'] * smart_b['pr']).sum()
        smart_buy_vol = smart_b['bs'].sum()
        smart_avg_cost = smart_buy_amt / smart_buy_vol if smart_buy_vol > 0 else 0
        gap = cp - smart_avg_cost if smart_avg_cost > 0 else 0

        adv = []
        if smart_net > 50 and gap > 0: adv.append("🔥 主動鎖碼/強勢推升")
        elif smart_net > 50 and gap < 0: adv.append("🩹 大戶接刀/弱勢護盤")
        elif smart_net < -100 and sp > 0: adv.append("📉 拉高派發/聰明錢撤退")
        elif smart_net < -100 and sp <= 0: adv.append("💀 波段棄守/停損賣壓")

        if firepower > 1.5: adv.append("🟢 大戶火力壓制")
        elif firepower < 0.7: adv.append("⚠️ 散戶螞蟻搬家")

        out.append({
            "日期": d, "收盤價(元)": cp, "漲跌(元)": sp, "聰明錢淨流(張)": int(smart_net),
            "大戶買均價": round(smart_avg_cost, 2) if smart_avg_cost > 0 else "-",
            "均價落差": round(gap, 2) if smart_avg_cost > 0 else "-",
            "潛在賣壓(張)": int(short_trap), "買賣家數差": bsd, "單日微觀診斷": " | ".join(adv) if adv else "🔵 盤整/無明顯特徵"
        })
        
    audit_df = pd.DataFrame(audit_smart_money).sort_values('淨買超(張)', ascending=False) if audit_smart_money else pd.DataFrame()
    return pd.DataFrame(out), audit_df

def process_branch_v25(df_raw, period, actual_dates, intel_tags, df_price_raw):
    if df_raw.empty or df_price_raw.empty: return pd.DataFrame()
    
    latest_close = df_price_raw.sort_values('date', ascending=False)['close'].iloc[0]
    df = df_raw[df_raw['date'].isin(actual_dates[:period])].copy()
    df['buy_shares'] = pd.to_numeric(df['buy'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    df['sell_shares'] = pd.to_numeric(df['sell'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    df['price_val'] = pd.to_numeric(df['price'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    df['buy_amt'] = df['buy_shares'] * df['price_val']
    df['sell_amt'] = df['sell_shares'] * df['price_val']
    
    g = df.groupby('securities_trader').agg(bv_sum=('buy_shares', 'sum'), sv_sum=('sell_shares', 'sum'), ba_sum=('buy_amt', 'sum'), sa_sum=('sell_amt', 'sum')).reset_index()
    g['net_vol'] = round((g['bv_sum'] - g['sv_sum']) / 1000).astype(int)
    g['avg_b'] = (g['ba_sum'] / g['bv_sum'].replace(0, np.nan)).fillna(0)
    g['avg_s'] = (g['sa_sum'] / g['sv_sum'].replace(0, np.nan)).fillna(0)
    
    b = g[g['net_vol'] > 0].sort_values('net_vol', ascending=False).head(15).reset_index(drop=True)
    s = g[g['net_vol'] < 0].sort_values('net_vol', ascending=True).head(15).reset_index(drop=True)
    
    out, tv = [], round(g['bv_sum'].sum() / 1000) if g['bv_sum'].sum() > 0 else 1
    for i in range(15):
        r = {}
        if i < len(b): 
            b_str = f"{round(b.loc[i,'avg_b'], 2):,.2f}"
            if b.loc[i,'avg_b'] > latest_close and b.loc[i,'avg_b'] > 0 and b.loc[i,'net_vol'] > 0: b_str = f"⚠️(虧) {b_str}"
            r["買超分點"] = f"{intel_tags.get(b.loc[i,'securities_trader'],'🔵')} {b.loc[i,'securities_trader']}"
            r["買超(張)"] = int(b.loc[i,'net_vol'])
            r["買均價"] = b_str
            r["佔比"] = f"{(b.loc[i,'net_vol']/tv)*100:.1f}%" if tv > 0 else "-"
        else: 
            r["買超分點"], r["買超(張)"], r["買均價"], r["佔比"] = "-", 0, "-", "-"
            
        if i < len(s): 
            r["賣超分點"] = f"{intel_tags.get(s.loc[i,'securities_trader'],'🔵')} {s.loc[i,'securities_trader']}"
            r["賣超(張)"] = abs(int(s.loc[i,'net_vol']))
            r["賣均價"] = round(s.loc[i,'avg_s'], 2)
            r["佔比_"] = f"{(abs(s.loc[i,'net_vol'])/tv)*100:.1f}%" if tv > 0 else "-"
        else: 
            r["賣超分點"], r["賣超(張)"], r["賣均價"], r["佔比_"] = "-", 0, "-", "-"
        out.append(r)
    return pd.DataFrame(out)

def generate_ai_hawk_eye(df_daily, df_radar, df_fingerprint, df_diff):
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
            except Exception as e: alerts.append("<span>🔵 今日聰明錢數值解析中性。</span>")
        else: alerts.append("<span>🔵 今日大戶無明顯動作，成本線無法精算。</span>")

    if not df_diff.empty and len(df_diff) >= 1:
        alerts.append("<div class='hawk-title' style='margin-top:15px;'>2. 火力與籌碼結構剖析 (買賣家數差)</div>")
        latest_diff = df_diff.iloc[0]
        try:
            fp_val = float(str(latest_diff['買方火力(倍)']).replace(',', '').strip())
            fire_str = f"今日活躍券商共 <b>{latest_diff['活躍家數']} 家</b>，買方火力倍數為 <b>{fp_val} 倍</b>。"
            if fp_val > 1.5: alerts.append(f"<span class='hawk-safe'>🔥 【大戶火力壓制】{fire_str} 代表少數大戶正用絕對的資金優勢，掃光散戶螞蟻搬家的籌碼，這是極高勝率的集中吃貨訊號。</span>")
            elif fp_val < 0.7: alerts.append(f"<span class='hawk-alert'>💀 【散戶蜂擁接刀】{fire_str} 代表大戶在極少數分點大舉倒貨，而進場承接的都是資金極小的散戶。籌碼正在嚴重發散，屬於極度危險訊號。</span>")
            else: alerts.append(f"<span>🔵 【中性換手】{fire_str} 買賣雙方實力相當，屬於自然的市場換手階段。</span>")
        except: alerts.append(f"<span>🔵 【中性換手】今日活躍券商共 {latest_diff['活躍家數']} 家，籌碼發散程度一般。</span>")

    if not df_fingerprint.empty and len(df_fingerprint) >= 1:
        alerts.append("<div class='hawk-title' style='margin-top:15px;'>3. 主力分點微觀剖析 (前 15 大買超)</div>")
        top_15 = df_fingerprint.head(15)
        trapped = len(top_15[top_15['最終標籤'] == '🩹 [被動套牢]'])
        locked = len(top_15[top_15['最終標籤'] == '🧱 [主動鎖碼]'])
        day_traders = len(top_15[top_15['最終標籤'] == '🌪️ [純當沖客]'])
        if day_traders > 8: alerts.append(f"<span class='hawk-alert'>⚠️ 【賭場化警告】前 15 大買超分點中，高達 {day_traders} 家是極端當沖客。股價上漲多為虛火，缺乏長線實力買盤支撐。</span>")
        if trapped >= 2 and trapped > locked: alerts.append(f"<span class='hawk-alert'>⚠️ 【誘多套牢炸彈】前 15 大分點有 {trapped} 家處於『均價虧損』被迫留倉。請留意表格中標示 <span style='color:red;'>⚠️(虧)</span> 的主力，這些都是明日潛在的多殺多來源。</span>")
        elif locked >= 2 and locked > trapped: alerts.append(f"<span class='hawk-safe'>🔥 【主推鎖碼強勢】前 15 大分點有 {locked} 家處於『獲利強勢留倉』狀態，主力買均價極具防守優勢，具波段續攻潛力。</span>")
        elif trapped < 2 and locked < 2 and day_traders <= 8: alerts.append(f"<span>🔵 分點進出動機分散，無單一極端勢力控盤。</span>")

    if not df_radar.empty and len(df_radar) >= 1:
        latest_r = df_radar.iloc[0]
        try:
            o_chg = float(str(latest_r['原始大戶變動(%)']).replace(',', '').strip())
            f_fat = float(str(latest_r['隔日沖虛胖(%)']).replace(',', '').strip())
            p_chg = float(str(latest_r['純淨大戶變動(%)']).replace(',', '').strip())
            if o_chg > 0.5 and f_fat > 0.8 and p_chg <= 0.2:
                alerts.append("<div class='hawk-title' style='margin-top:15px;'>4. 週末集保雷達防護</div>")
                alerts.append("<span class='hawk-alert'>🚨 【集保騙局】週末公佈大戶持股看似增加，實則九成以上全是『隔日沖虛胖』，純淨大戶並未進場，請提防週一遭無情倒貨！</span>")
        except: pass
            
    if not alerts: alerts.append("<span>🔍 綜合火力與成本評估：目前籌碼結構中性，無極端操作訊號，請依紀律操作。</span>")
    return alerts

# ==========================================
# 📌 技術分析引擎 (10/60/240)
# ==========================================
def process_technical_analysis(df_price):
    if df_price.empty or len(df_price) < 30: return pd.DataFrame()
    df_ta = df_price.sort_values('日期', ascending=True).copy()
    df_ta['MA10'] = df_ta['收盤價(元)'].rolling(window=10).mean().round(2)
    df_ta['MA60(季線)'] = df_ta['收盤價(元)'].rolling(window=60).mean().round(2)
    df_ta['MA240(年線)'] = df_ta['收盤價(元)'].rolling(window=240).mean().round(2)
    df_ta['季線乖離(%)'] = ((df_ta['收盤價(元)'] - df_ta['MA60(季線)']) / df_ta['MA60(季線)'] * 100).round(2)
    
    delta = df_ta['收盤價(元)'].diff()
    gain, loss = delta.where(delta > 0, 0.0), -delta.where(delta < 0, 0.0)
    rs = gain.rolling(window=14, min_periods=1).mean() / loss.rolling(window=14, min_periods=1).mean().replace(0, np.nan)
    df_ta['RSI(14)'] = (100 - (100 / (1 + rs))).round(2).fillna(50)
    
    exp1, exp2 = df_ta['收盤價(元)'].ewm(span=12, adjust=False).mean(), df_ta['收盤價(元)'].ewm(span=26, adjust=False).mean()
    df_ta['MACD_DIF'] = (exp1 - exp2).round(2)
    df_ta['MACD_MACD(信號線)'] = df_ta['MACD_DIF'].ewm(span=9, adjust=False).mean().round(2)
    df_ta['MACD_OSC(柱狀圖)'] = (df_ta['MACD_DIF'] - df_ta['MACD_MACD(信號線)']).round(2)
    
    diag = []
    for i in range(len(df_ta)):
        adv = []
        if df_ta['收盤價(元)'].iloc[i] > df_ta['MA60(季線)'].iloc[i]: adv.append("🟢 站上季線")
        elif df_ta['收盤價(元)'].iloc[i] < df_ta['MA60(季線)'].iloc[i]: adv.append("🔴 跌破季線")
        if df_ta['RSI(14)'].iloc[i] > 80: adv.append("⚠️ 嚴重超買")
        elif df_ta['RSI(14)'].iloc[i] < 20: adv.append("🛡️ 嚴重超賣")
        if i > 0:
            if df_ta['MACD_OSC(柱狀圖)'].iloc[i] > 0 and df_ta['MACD_OSC(柱狀圖)'].iloc[i-1] <= 0: adv.append("🔥 MACD 黃金交叉")
            elif df_ta['MACD_OSC(柱狀圖)'].iloc[i] < 0 and df_ta['MACD_OSC(柱狀圖)'].iloc[i-1] >= 0: adv.append("💀 MACD 死亡交叉")
        diag.append(" | ".join(adv) if adv else "🔵 盤整")
        
    df_ta['技術面診斷'] = diag
    return df_ta.sort_values('日期', ascending=False)

# ⚠️ 【改版】：圖表引擎優化 (拔除統整報價視窗，保留十字查價線)
def plot_interactive_kline(df_price, df_ta):
    if df_price.empty or df_ta.empty: return None
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError:
        st.warning("⚠️ 系統缺少 plotly 套件，請在環境中安裝 pip install plotly 以顯示 K 線圖。")
        return None

    df_p = df_price[['日期', '開盤價(元)', '最高價(元)', '最低價(元)', '收盤價(元)', '成交量(張)']].head(180).copy()
    ta_cols = ['日期', 'MA10', 'MA60(季線)', 'MA240(年線)', 'MACD_DIF', 'MACD_MACD(信號線)', 'MACD_OSC(柱狀圖)', 'RSI(14)']
    df_t = df_ta[[c for c in ta_cols if c in df_ta.columns]].head(180).copy()
    
    df = pd.merge(df_p, df_t, on='日期', how='inner').sort_values('日期', ascending=True)
    df['日期'] = df['日期'].astype(str)
    
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.15, 0.15, 0.2], subplot_titles=("K線與長線均線 (180天)", "成交量(張)", "MACD (12,26,9)", "RSI (14)"))

    fig.add_trace(go.Candlestick(x=df['日期'], open=df['開盤價(元)'], high=df['最高價(元)'], low=df['最低價(元)'], close=df['收盤價(元)'], name='K線', increasing_line_color='#ef5350', decreasing_line_color='#26a69a'), row=1, col=1)
    if 'MA10' in df.columns: fig.add_trace(go.Scatter(x=df['日期'], y=df['MA10'], mode='lines', name='MA10', line=dict(color='#ffa726', width=1.5)), row=1, col=1)
    if 'MA60(季線)' in df.columns: fig.add_trace(go.Scatter(x=df['日期'], y=df['MA60(季線)'], mode='lines', name='MA60(季)', line=dict(color='#29b6f6', width=2)), row=1, col=1)
    if 'MA240(年線)' in df.columns: fig.add_trace(go.Scatter(x=df['日期'], y=df['MA240(年線)'], mode='lines', name='MA240(年)', line=dict(color='#ab47bc', width=2.5)), row=1, col=1)
    
    colors = ['#ef5350' if row['收盤價(元)'] >= row['開盤價(元)'] else '#26a69a' for i, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df['日期'], y=df['成交量(張)'], marker_color=colors, name='成交量'), row=2, col=1)

    if 'MACD_OSC(柱狀圖)' in df.columns:
        macd_colors = ['#ef5350' if val > 0 else '#26a69a' for val in df['MACD_OSC(柱狀圖)']]
        fig.add_trace(go.Bar(x=df['日期'], y=df['MACD_OSC(柱狀圖)'], marker_color=macd_colors, name='MACD柱狀圖'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['日期'], y=df['MACD_DIF'], mode='lines', name='DIF', line=dict(color='#42a5f5', width=1.5)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['日期'], y=df['MACD_MACD(信號線)'], mode='lines', name='MACD信號', line=dict(color='#ffa726', width=1.5)), row=3, col=1)

    if 'RSI(14)' in df.columns:
        fig.add_trace(go.Scatter(x=df['日期'], y=df['RSI(14)'], mode='lines', name='RSI(14)', line=dict(color='#ab47bc', width=1.5)), row=4, col=1)
        fig.add_hline(y=80, line_dash="dash", line_color="#ef5350", line_width=1, row=4, col=1)
        fig.add_hline(y=20, line_dash="dash", line_color="#26a69a", line_width=1, row=4, col=1)

    # ⚠️ 【關鍵修改】：hovermode='closest' 移除統整方塊，恢復預設清爽顯示
    fig.update_layout(
        height=850, 
        margin=dict(l=30, r=30, t=40, b=30),
        xaxis_rangeslider_visible=False,
        plot_bgcolor='#f8f9fa',
        paper_bgcolor='white',
        showlegend=False,
        hovermode='closest' # 移除 x unified，不遮擋 K 線
    )
    
    # ⚠️ 保留十字查價線設定
    fig.update_xaxes(
        type='category', showgrid=True, gridwidth=1, gridcolor='#e0e0e0', tickangle=45,
        showspikes=True, spikemode='across', spikethickness=1, spikedash='dot', spikecolor='#9e9e9e', spikesnap='cursor'
    )
    fig.update_yaxes(
        showgrid=True, gridwidth=1, gridcolor='#e0e0e0',
        showspikes=True, spikemode='across', spikethickness=1, spikedash='dot', spikecolor='#9e9e9e', spikesnap='cursor'
    )
    return fig

# ==========================================
# 📌 資料處理與排版 
# ==========================================
def process_price(df):
    if df.empty: return pd.DataFrame()
    df_out = df.copy()
    df_out['Trading_Volume'] = (pd.to_numeric(df_out['Trading_Volume'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0) / 1000).round().astype(int)
    df_out = df_out.rename(columns={"date":"日期","Trading_Volume":"成交量(張)","close":"收盤價(元)","spread":"漲跌(元)","open":"開盤價(元)","max":"最高價(元)","min":"最低價(元)"})
    df_out["斷頭價(0.78)"] = (df_out["收盤價(元)"] * 0.78).round(2)
    return df_out[['日期','成交量(張)','開盤價(元)','最高價(元)','最低價(元)','收盤價(元)','漲跌(元)','斷頭價(0.78)']].sort_values('日期', ascending=False)

def clean_level_by_math(x):
    s = str(x).replace(',', '').replace(' ', '')
    if s in ["17", "17.0", "合計", "總計"]: return "合計"
    nums = re.findall(r'\d+', s)
    if not nums: return s
    if len(nums) == 1 and int(nums[0]) <= 15:
        m = {1: "1-999股", 2: "1-5張", 3: "5-10張", 4: "10-15張", 5: "15-20張", 6: "20-30張", 7: "30-40張", 8: "40-50張", 9: "50-100張", 10: "100-200張", 11: "200-400張", 12: "400-600張", 13: "600-800張", 14: "800-1000張", 15: "1000張以上"}
        return m.get(int(nums[0]), s)
    up = int(nums[-1])
    if up <= 999: return "1-999股"
    elif up <= 5000: return "1-5張"
    elif up <= 10000: return "5-10張"
    elif up <= 15000: return "10-15張"
    elif up <= 20000: return "15-20張"
    elif up <= 30000: return "20-30張"
    elif up <= 40000: return "30-40張"
    elif up <= 50000: return "40-50張"
    elif up <= 100000: return "50-100張"
    elif up <= 200000: return "100-200張"
    elif up <= 400000: return "200-400張"
    elif up <= 600000: return "400-600張"
    elif up <= 800000: return "600-800張"
    elif up <= 1000000: return "800-1000張" 
    else: return "1000張以上" 

def process_tdcc(df):
    if df.empty: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df = df[~df['HoldingSharesLevel'].astype(str).str.contains('差異數')].copy()
    df['LevelClean'] = df['HoldingSharesLevel'].apply(clean_level_by_math)
    df['unit'] = (pd.to_numeric(df.get('unit', 0).astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0) / 1000).round().astype(int)
    df['people'] = pd.to_numeric(df['people'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0).astype(int)
    
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
        df_w[f"{l}_張數"] = p_u[l]
        df_w[f"{l}_人數"] = p_p[l]
        df_w[f"{l}_比例(%)"] = (p_u[l] / df_t['總張數'] * 100).fillna(0).round(2)
        
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
            v_num = pd.to_numeric(df_out[col].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
            df_out[col.replace('股數', '張數')] = (v_num / 1000).round().astype(int)
            df_out = df_out.drop(columns=[col])
    cols = ['日期'] + [c for c in df_out.columns if '張數' in c or '率' in c]
    return df_out[cols].tail(10).sort_values('日期', ascending=False)

def process_margin(df):
    if df.empty: return pd.DataFrame()
    for c in ["MarginPurchaseBuy", "MarginPurchaseSell", "MarginPurchaseCashRepayment", "MarginPurchaseTodayBalance", "MarginPurchaseYesterdayBalance", "ShortSaleBuy", "ShortSaleSell", "ShortSaleCashRepayment", "ShortSaleTodayBalance", "OffsetLoanAndShort", "ShortSaleYesterdayBalance"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0).round().astype(int)
    df = df.rename(columns={"date":"日期", "MarginPurchaseBuy":"融資買進(萬元)", "MarginPurchaseSell":"融資賣出(萬元)", "MarginPurchaseCashRepayment":"融資現償(萬元)", "MarginPurchaseTodayBalance":"融資餘額(萬元)", "ShortSaleBuy":"融券買進(張)", "ShortSaleSell":"融券賣出(張)", "ShortSaleTodayBalance":"融券餘額(張)", "OffsetLoanAndShort":"資券相抵(張)"})
    if '融資餘額(萬元)' in df.columns and 'MarginPurchaseYesterdayBalance' in df.columns:
        df['融資增減(萬元)'] = df['融資餘額(萬元)'] - df['MarginPurchaseYesterdayBalance']
    if '融券餘額(張)' in df.columns and 'ShortSaleYesterdayBalance' in df.columns:
        df['融券增減(張)'] = df['融券餘額(張)'] - df['ShortSaleYesterdayBalance']
    cols = [c for c in ['日期','融資買進(萬元)','融資賣出(萬元)','融資現償(萬元)','融資餘額(萬元)','融資增減(萬元)','融券買進(張)','融券賣出(張)','融券餘額(張)','融券增減(張)','資券相抵(張)'] if c in df.columns]
    return df[cols].tail(10).sort_values('日期', ascending=False)

def process_inst(df):
    if df.empty: return pd.DataFrame()
    pdf = df.pivot_table(index='date', columns='name', values=['buy', 'sell'], fill_value=0).reset_index()
    pdf.columns = ['_'.join(c).strip('_') for c in pdf.columns.values]
    out = pd.DataFrame({'日期': pdf['date']})
    f_b = pd.to_numeric(pdf.get('buy_Foreign_Investor',0).astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    f_s = pd.to_numeric(pdf.get('sell_Foreign_Investor',0).astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    out['外資買賣超(張)'] = ((f_b - f_s) / 1000).round().astype(int)
    i_b = pd.to_numeric(pdf.get('buy_Investment_Trust',0).astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    i_s = pd.to_numeric(pdf.get('sell_Investment_Trust',0).astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    out['投信買賣超(張)'] = ((i_b - i_s) / 1000).round().astype(int)
    ds_b = pd.to_numeric(pdf.get('buy_Dealer_self',0).astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    ds_s = pd.to_numeric(pdf.get('sell_Dealer_self',0).astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    out['自營商(自行)買賣超'] = ((ds_b - ds_s) / 1000).round().astype(int)
    dh_b = pd.to_numeric(pdf.get('buy_Dealer_Hedging',0).astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    dh_s = pd.to_numeric(pdf.get('sell_Dealer_Hedging',0).astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    out['自營商(避險)買賣超'] = ((dh_b - dh_s) / 1000).round().astype(int)
    out['三大法人買賣超(張)'] = out['外資買賣超(張)'] + out['投信買賣超(張)'] + out['自營商(自行)買賣超'] + out['自營商(避險)買賣超']
    return out.tail(10).sort_values('日期', ascending=False)

def process_fut_inst(df):
    if df.empty: return pd.DataFrame()
    df['net'] = pd.to_numeric(df['long_open_interest_balance_volume'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0) - pd.to_numeric(df['short_open_interest_balance_volume'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    pdf = df.pivot_table(index='date', columns='institutional_investors', values='net', fill_value=0).reset_index()
    pdf.columns.name = None
    for col in ['Foreign_Investor', 'Investment_Trust', 'Dealer']:
        if col not in pdf.columns: pdf[col] = 0
    return pdf.rename(columns={'date': '日期', 'Foreign_Investor': '外資多空(口)', 'Investment_Trust': '投信多空(口)', 'Dealer': '自營多空(口)'}).tail(10).sort_values('日期', ascending=False)

def process_per(df):
    if df.empty: return pd.DataFrame()
    df_out = df.copy().rename(columns={"date":"日期","dividend_yield":"殖利率(%)","PER":"本益比(倍)","PBR":"淨值比(倍)"})
    for col in ["殖利率(%)", "本益比(倍)", "淨值比(倍)"]: 
        if col in df_out.columns: df_out[col] = pd.to_numeric(df_out[col].astype(str).str.replace(',', '').str.strip(), errors='coerce').round(2)
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
        year_num = pd.to_numeric(df_out['股利年份'].astype(str).str.replace(',', '').str.replace('年', '').str.strip(), errors='coerce')
        recent = sorted(year_num.dropna().unique(), reverse=True)[:5]
        return df_out[year_num.isin(recent)][cols].sort_values('公告日期', ascending=False)
    return df_out[cols].sort_values('公告日期', ascending=False).head(10)

def process_cbas(df):
    if df.empty: return pd.DataFrame()
    df_out = df.rename(columns={"date": "日期", "cb_id": "可轉債代號", "cb_name": "可轉債名稱", "ConversionPrice": "轉換價(元)", "PriceOfUnderlyingStock": "標的股價(元)", "OutstandingAmount": "未償還餘額", "CouponRate": "票面利率(%)"})
    cols = [c for c in ["日期", "可轉債代號", "可轉債名稱", "轉換價(元)", "標的股價(元)", "未償還餘額", "票面利率(%)"] if c in df_out.columns]
    return df_out[cols]

def show_table(title, df, custom_class=""):
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
    if df is None or df.empty: 
        st.warning("此區塊查無數據或無發行紀錄")
    else:
        def fmt_auto(x):
            if pd.isna(x): return "-"
            s = str(x).strip()
            if s in ["-", ""]: return "-"
            if "⚠️(虧)" in s:
                v_str = s.replace("⚠️(虧)", "").strip()
                try:
                    v = float(v_str.replace(',', '').replace('%', ''))
                    return f"<span class='loss-warning'>⚠️(虧) {f'{v:,.2f}' if '.' in v_str else f'{int(v):,}'}</span>"
                except: return f"<span class='loss-warning'>{s}</span>"
            is_pct = "%" in s
            try:
                v = float(s.replace(',', '').replace('%', ''))
                return f"{v:,.2f}" + ("%" if is_pct else "") if '.' in s or is_pct else f"{int(v):,}"
            except: return str(x)
            
        f_dict = {c: fmt_auto for c in df.columns}
        left_cols = [c for c in df.columns if any(kw in str(c) for kw in ['日期', '公告日期', '分點', '名稱', '姓名', '身份別', '質權人', '交易別', '診斷', '判定', '門檻', '條件', '措施', '契約', '代號', '來源', '標籤', '單日微觀診斷', '專家雷達診斷', '鷹眼診斷', '技術面診斷'])]
        right_cols = [c for c in df.columns if c not in left_cols]
        styler = df.style.format(f_dict).set_properties(**{'text-align': 'right !important'}, subset=right_cols)
        if left_cols: styler = styler.set_properties(**{'text-align': 'left !important'}, subset=left_cols)
        try: styler = styler.hide(axis="index")
        except: styler = styler.hide_index()
        html = styler.set_table_styles([dict(selector='th', props=[('text-align', 'center !important')]), dict(selector='table', props=[('width', '100%')])]).to_html()
        html = html.replace('&lt;span class=&#x27;loss-warning&#x27;&gt;', "<span class='loss-warning'>").replace('&lt;/span&gt;', "</span>")
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
    if not user_stock_id.strip():
        st.warning("⚠️ 請先在上方輸入股票代號！")
        st.stop()

    with st.spinner(f"正在啟動 V34.2 視覺化淨化引擎..."):
        name = get_stock_name(user_stock_id)
        if not name:
            st.error(f"⚠️ 查無股票代號 {user_stock_id} 的基本資料。"); st.stop()
            
        df_p_raw = fetch_fm("TaiwanStockPrice", (datetime.date.today() - datetime.timedelta(days=1095)).strftime("%Y-%m-%d"), user_stock_id)
        if df_p_raw.empty: 
            st.error("⚠️ 查無歷史股價資料。"); st.stop()
        
        dates = sorted(df_p_raw['date'].unique().tolist(), reverse=True)
        d_60 = dates[59] if len(dates) >= 60 else dates[-1]
        
        df_price = process_price(df_p_raw)
        df_ta_full = process_technical_analysis(df_price)
        
        ta_display_cols = ['日期', '收盤價(元)', 'MA10', 'MA60(季線)', 'MA240(年線)', '季線乖離(%)', 'RSI(14)', 'MACD_OSC(柱狀圖)', '技術面診斷']
        df_ta_display = df_ta_full[ta_display_cols].copy() if not df_ta_full.empty and all(c in df_ta_full.columns for c in ta_display_cols) else pd.DataFrame()
        
        dynamic_dict, s_val, chip_eng, _ = scrape_director_holding(user_stock_id)
        df_b_raw = fetch_fm_branch_fast_parallel(dates[:60], user_stock_id)
        tags, df_debug_tags = get_v27_intelligence(df_b_raw, df_p_raw)
        df_b_diff = process_branch_diff(df_b_raw, dates)
        df_daily_tracker, df_audit_smart = process_v30_daily_tracking(df_b_raw, tags, df_price, df_b_diff, dates)
        df_s_raw = fetch_fm("TaiwanStockHoldingSharesPer", d_60, user_stock_id)
        df_s_wide, df_s_unit, df_s_ppl = process_tdcc(df_s_raw)
        df_s_dyn = process_tdcc_dynamic(df_s_wide, df_price, dead_chip_input, dynamic_dict, s_val, chip_eng)
        df_v27_radar, df_debug_math, _ = process_v27_ultimate_radar(df_s_wide, dead_chip_input, dynamic_dict, s_val, df_price, df_b_raw, tags)

        df_twse, _ = scrape_block_trades(user_stock_id, dates)
        df_margin = process_margin(fetch_fm("TaiwanStockMarginPurchaseShortSale", d_60, user_stock_id))
        df_day_trade = process_day_trading(fetch_fm("TaiwanStockDayTrading", d_60, user_stock_id))
        df_inst = process_inst(fetch_fm("TaiwanStockInstitutionalInvestorsBuySell", d_60, user_stock_id))
        
        df_rev_raw = fetch_fm("TaiwanStockMonthRevenue", "2022-01-01", user_stock_id)
        df_rev = pd.DataFrame()
        if not df_rev_raw.empty:
            df_rev_raw['營收月份'] = df_rev_raw['revenue_year'].astype(str) + "-" + df_rev_raw['revenue_month'].astype(str).str.zfill(2)
            df_rev = df_rev_raw.rename(columns={"revenue":"月營收(百萬元)"})[['營收月份','月營收(百萬元)']].tail(24)
            df_rev['月營收(百萬元)'] = (pd.to_numeric(df_rev['月營收(百萬元)'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)/1000000).round().astype(int)
            df_rev = df_rev.sort_values('營收月份', ascending=False)

        df_b_today = process_branch_v25(df_b_raw, 1, dates, tags, df_p_raw)
        df_b_prev1 = process_branch_v25(df_b_raw, 1, dates[1:], tags, df_p_raw)
        df_b_3 = process_branch_v25(df_b_raw, 3, dates, tags, df_p_raw)
        df_b_10 = process_branch_v25(df_b_raw, 10, dates, tags, df_p_raw)
        df_b_20 = process_branch_v25(df_b_raw, 20, dates, tags, df_p_raw)
        df_b_30 = process_branch_v25(df_b_raw, 30, dates, tags, df_p_raw)
        df_b_60 = process_branch_v25(df_b_raw, 60, dates, tags, df_p_raw)

        df_gov = pd.DataFrame()
        if not df_b_today.empty: df_gov = df_b_today[df_b_today.astype(str).apply(lambda x: x.str.contains('|'.join(["台銀", "土銀", "彰銀", "第一", "兆豐", "華南", "合庫", "台企銀"]))).any(axis=1)]
        df_p_sum, df_p_det = scrape_fubon_pledge(df_p_raw, user_stock_id)
        df_fut = process_fut_inst(fetch_fm("TaiwanFuturesInstitutionalInvestors", d_60, "TX"))
        df_div = process_div(fetch_fm("TaiwanStockDividend", "2015-01-01", user_stock_id))
        df_per = process_per(fetch_fm("TaiwanStockPER", d_60, user_stock_id))
        df_disp = process_disp(fetch_fm("TaiwanStockDispositionSecuritiesPeriod", (datetime.date.today()-datetime.timedelta(days=180)).strftime("%Y-%m-%d"), user_stock_id))
        df_cbas_raw = fetch_fm("TaiwanStockConvertibleBondDailyOverview", dates[0])
        df_cbas = process_cbas(df_cbas_raw[df_cbas_raw['cb_id'].astype(str).str.startswith(user_stock_id)]) if not df_cbas_raw.empty else pd.DataFrame()

        market_cap_str = "計算中..."
        industry, address = get_company_profile(user_stock_id)
        if not df_price.empty and not df_s_wide.empty:
            market_cap_str = f"{(df_price['收盤價(元)'].iloc[0] * df_s_wide['總張數'].iloc[0]) / 100000:,.2f} 億"
        company_info_text = f"🏢 **【產業】** {industry} ｜ 💰 **【市值】** {market_cap_str} ｜ 📍 **【公司地址】** {address}"

        st.subheader(f"📊 {user_stock_id} {name} 全息戰報 (V34.2 純淨十字線版)")
        st.markdown(f"<div class='info-box'>{company_info_text}</div>", unsafe_allow_html=True)
        
        hawk_alerts = generate_ai_hawk_eye(df_daily_tracker, df_v27_radar, df_debug_tags, df_b_diff)
        hawk_html_display = "<div class='hawk-eye-box'>"
        hawk_csv_text = "▼▼▼ 系統 AI 鷹眼深度診斷報告 ▼▼▼\n"
        for alert in hawk_alerts: 
            hawk_html_display += f"{alert}<br>"
            clean_text = re.sub(r'<[^>]+>', '', alert).replace('&nbsp;', ' ')
            if "1." in clean_text or "2." in clean_text or "3." in clean_text or "4." in clean_text: hawk_csv_text += f"\n[{clean_text}]\n"
            else: hawk_csv_text += f"- {clean_text}\n"
        hawk_html_display += "</div>"
        st.markdown(hawk_html_display, unsafe_allow_html=True)

        st.markdown("<div class='category-title'>📈 00. 技術面與大局觀</div>", unsafe_allow_html=True)
        if not df_ta_display.empty:
            show_table("00-1. 技術分析指標 (近10天)", df_ta_display.head(10))
            st.markdown("<div class='section-title'>📈 00-2. 互動式 K 線與技術指標圖 (近180日)</div>", unsafe_allow_html=True)
            fig_kline = plot_interactive_kline(df_price, df_ta_full)
            if fig_kline: st.plotly_chart(fig_kline, use_container_width=True)

        st.markdown("<div class='category-title'>📊 核心戰情追蹤</div>", unsafe_allow_html=True)
        show_table("01. 平日戰情追蹤矩陣 (結合大戶買均價與落差)", df_daily_tracker, "daily-tracker")
        show_table("02. 專家診斷雷達 (週末除水版)", df_v27_radar.head(8), "radar-table")
        show_table("03. 雙軸活大戶鎖碼判定表 (C-Value)", df_s_dyn.head(8))
        show_table("04. 收盤價量 (近10天)", df_price.head(10))

        st.markdown("<div class='category-title'>🕵️‍♂️ 主力分點指紋與動向</div>", unsafe_allow_html=True)
        show_table("05. 主力分點指紋圖鑑 (紅色標示為目前套牢)", df_debug_tags.head(30))
        show_table(f"06. 主力分點 - 今日 ({dates[0]})", df_b_today)
        show_table(f"07. 主力分點 - 近60日", df_b_60)
        
        with st.expander("📂 點此展開過渡期分點 (前一日、近3日~近30日)", expanded=False):
            show_table(f"07-1. 主力分點 - 前一日 ({dates[1] if len(dates)>1 else '無'})", df_b_prev1)
            show_table("07-2. 主力分點 - 近3日", df_b_3)
            show_table("07-3. 主力分點 - 近10日", df_b_10)
            show_table("07-4. 主力分點 - 近20日", df_b_20)
            show_table("07-5. 主力分點 - 近30日", df_b_30)

        st.markdown("<div class='category-title'>🏦 法人與資券變化</div>", unsafe_allow_html=True)
        show_table("08. 法人買賣超 (近10天)", df_inst)
        show_table("09. 散戶資券餘額 (近10天)", df_margin)
        show_table("10. 現股當沖明細 (近10天)", df_day_trade)
        show_table("11. 八大官股進出 (今日)", df_gov)
        show_table("12. 買賣家數差明細 (結合火力倍數)", df_b_diff)
        show_table("13. 台指期貨三大法人未平倉 (大盤)", df_fut)

        st.markdown("<div class='category-title'>📈 基本面與進階籌碼數據</div>", unsafe_allow_html=True)
        show_table("14. 集保分級 - 張數表 (近8週)", df_s_unit)
        show_table("15. 集保分級 - 人數表 (近8週)", df_s_ppl)
        show_table("16. 月營收 (百萬元) (近24個月)", df_rev)
        show_table("17. 董監大股東質設總覽", df_p_sum)
        show_table("18. 董監大股東質設明細", df_p_det)
        show_table("19. 鉅額交易明細 (近3日)", df_twse)
        show_table("20. 歷年股利 (近5年)", df_div)
        show_table("21. 本益比、淨值比與殖利率", df_per)
        show_table("22. 處置有價證券狀態", df_disp)
        show_table("23. CBAS 可轉債數據", df_cbas)

        st.divider()
        st.info("請將下方所需資料複製後貼給 Gemini 進行深度分析或稽核。")
        
        with st.expander(f"📋 給 Gemini 的 V34.2 實戰精華資料包 (CSV格式)", expanded=True):
            p1 = f"請依下面最新的盤後資料與系統鷹眼報告幫我深度分析 {user_stock_id} {name} 的量化籌碼，必須以我給的資料優先使用。\n\n"
            p1 += f"{company_info_text}\n\n"
            p1 += hawk_csv_text + "\n"
            p1 += format_to_csv_string(df_ta_display.head(10), "00-1. 技術分析指標 (近10天)")
            p1 += format_to_csv_string(df_daily_tracker, "01. 平日戰情追蹤矩陣 (近5日)")
            p1 += format_to_csv_string(df_v27_radar.head(4), "02. 專家診斷雷達 (近4週)")
            p1 += format_to_csv_string(df_s_dyn.head(4), "03. 雙軸活大戶鎖碼判定表 (近4週)")
            p1 += format_to_csv_string(df_b_today, f"06. 主力分點 - 今日 ({dates[0]})")
            p1 += format_to_csv_string(df_b_60, "07. 主力分點 - 近60日")
            p1 += format_to_csv_string(df_inst.head(10), "08. 法人買賣超 (近10天)")
            p1 += format_to_csv_string(df_margin.head(10), "09. 散戶資券餘額 (近10天)")
            p1 += format_to_csv_string(df_day_trade.head(10), "10. 現股當沖明細 (近10天)")
            if not df_gov.empty: p1 += format_to_csv_string(df_gov, "11. 八大官股進出 (今日)")
            p1 += format_to_csv_string(df_b_diff.head(10), "12. 買賣家數差明細 (近10天)")
            if not df_fut.empty: p1 += format_to_csv_string(df_fut.head(10), "13. 台指期貨三大法人未平倉 (大盤)")
            p1 += format_to_csv_string(df_rev.head(12), "16. 月營收 (百萬元) (近12個月)")
            if not df_p_sum.empty: p1 += format_to_csv_string(df_p_sum, "17. 董監大股東質設總覽")
            if not df_twse.empty: p1 += format_to_csv_string(df_twse, "19. 鉅額交易明細 (近3日)")
            if not df_div.empty: p1 += format_to_csv_string(df_div.head(5), "20. 歷年股利 (近5年)")
            if not df_disp.empty: p1 += format_to_csv_string(df_disp, "22. 處置有價證券狀態")
            if not df_cbas.empty: p1 += format_to_csv_string(df_cbas, "23. CBAS 可轉債數據")
            st.code(p1, language="text")

        with st.expander(f"🔎 給 Gemini 的 V34.2 稽核與驗算資料包 (CSV格式)", expanded=False):
            p2 = f"請幫我驗證 {user_stock_id} {name} 以下 CSV 數據的數學邏輯正確性：\n\n"
            p2 += format_to_csv_string(df_debug_tags.head(30), "稽核A：前30大分點指紋數據")
            p2 += format_to_csv_string(df_debug_math, "稽核B：除水還原數學驗算表")
            p2 += format_to_csv_string(df_audit_smart, f"稽核C：今日({dates[0]})聰明錢淨流成分表 (應絕對吻合表01之總和)")
            
            df_audit_fire = df_b_raw[df_b_raw['date'] == dates[0]].copy()
            df_audit_fire['buy'] = pd.to_numeric(df_audit_fire['buy'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
            df_audit_fire['sell'] = pd.to_numeric(df_audit_fire['sell'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
            df_audit_fire = df_audit_fire.rename(columns={'securities_trader': '分點', 'buy': '買進(股)', 'sell': '賣出(股)', 'price': '成交價'})
            p2 += format_to_csv_string(df_audit_fire[['分點', '買進(股)', '賣出(股)', '成交價']], f"稽核D：今日({dates[0]})全台分點進出原始表 (用以驗算活躍家數與火力倍數)")
            st.code(p2, language="text")
