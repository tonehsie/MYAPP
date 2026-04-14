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
st.set_page_config(page_title="V29.3 終極全息量化系統 (主力成本透視版)", layout="wide")

# 內建 Token
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

# 注入全局 CSS
st.markdown("""
<style>
.table-responsive { overflow-x: auto; width: 100%; display: block; margin-bottom: 20px; }
table.dataframe { border-collapse: collapse; width: 100%; }
table.dataframe th, table.dataframe td { white-space: nowrap !important; text-align: center !important; padding: 8px 12px !important; }

/* 凍結第一欄，手機左右滑動時標題不會跑掉 */
table.dataframe th:first-child, table.dataframe td:first-child {
    position: sticky;
    left: 0;
    background-color: #f1f3f5;
    z-index: 1;
    border-right: 2px solid #dee2e6;
}

.radar-table td:last-child { text-align: left !important; color: #ff4b4b; font-weight: bold; }
.daily-tracker td:last-child { text-align: left !important; color: #008080; font-weight: bold; }
.debug-header { color: #f63366; font-weight: bold; }
.info-box { background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #ff4b4b; font-size: 16px;}
.dict-box { background-color: #fdf2f2; padding: 15px; border-radius: 10px; border-left: 5px solid #e03131; font-size: 14px; line-height: 1.6;}
.hawk-eye-box { background-color: #fff9db; padding: 15px; border-radius: 10px; margin-bottom: 20px; border-left: 6px solid #f59f00; font-size: 16px; line-height: 1.8;}
.hawk-alert { color: #d9480f; font-weight: bold; }
.hawk-safe { color: #2b8a3e; font-weight: bold; }

/* 統一所有標題的文字大小、粗細與顏色 */
.section-title { 
    font-size: 1.3rem !important; 
    font-weight: 700 !important; 
    margin-top: 35px; 
    margin-bottom: 15px; 
    color: #1e3a8a; 
    border-bottom: 2px solid #1e3a8a; 
    padding-bottom: 5px; 
}
.category-title {
    font-size: 1.6rem !important;
    font-weight: 900 !important;
    margin-top: 40px;
    color: #333;
}
</style>
""", unsafe_allow_html=True)

st.title("📱 V29.3 終極全息量化系統")
st.caption("火力升級：導入加權成本精算引擎，全線分點表單新增「買賣均價」，精準鎖定主力防守線。")

# UI 輸入區
col1, col2 = st.columns([1, 1])
with col1: 
    user_stock_id = st.text_input("個股代號", value="1815", placeholder="請輸入台股代號 (例: 2330)")
with col2: 
    dead_chip_input = st.text_input("死籌碼 %", placeholder="自動抓取董監事持股，也可自行輸入", help="留空將自動抓取。也可自行輸入比例數值")
run_btn = st.button("🚀 啟動 V29.3 主力成本透視引擎", use_container_width=True)

# 內建字典
with st.expander("📖 忘記名詞意思？點我查看【V29 實戰字典】", expanded=False):
    st.markdown("""
    <div class='dict-box'>
    <b>▼ 新增：成本防守線</b><br>
    <ul>
        <li><b>買賣均價</b>：利用 (總成交金額 ÷ 總成交股數) 精算而出的絕對成本。當股價跌至大戶的「買均價」時，極易形成強力支撐。</li>
    </ul>
    <b>▼ 均價信心標籤 (盤中動能)</b><br>
    <ul>
        <li><b>🧱 [主動鎖碼]</b>：大戶買進且收盤價 > 全天均價。帳面獲利且強勢控盤。</li>
        <li><b>🩹 [被動套牢]</b>：大戶留倉但收盤價 < 全天均價。大戶買貴被套，易有停損賣壓。</li>
        <li><b>🚀 [尾盤偷襲]</b>：收盤價突然大幅拉開與全天均價的距離。</li>
        <li><b>🌪️ [純當沖客]</b>：買賣極度對稱，不參與明日戰局。</li>
    </ul>
    <b>▼ 籌碼核心名詞</b><br>
    <ul>
        <li><b>隔日沖潛在賣壓(張)</b>：極短線投機客買進且留倉到明天的張數。</li>
        <li><b>純淨活大戶C-Value(%)</b>：扣除死籌碼後，流通股票中被大戶鎖住的比例。</li>
        <li><b>純淨大戶變動(%)</b>：(原始變動 - 隔日沖虛胖)。扒開假象後，長線大戶一週真正的進出比例。</li>
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
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            return response.read().decode('big5', errors='ignore')
    except Exception:
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

# ==========================================
# 📌 V29.3 指紋辨識 (新增買賣均價成本引擎)
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

    df = df_b_raw.copy()
    df['date'] = pd.to_datetime(df['date'])
    
    # 數值強制脫水
    df['buy_shares'] = pd.to_numeric(df['buy'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    df['sell_shares'] = pd.to_numeric(df['sell'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    df['price_val'] = pd.to_numeric(df['price'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    
    # 計算單筆總金額 (用來算加權平均)
    df['buy_amt'] = df['buy_shares'] * df['price_val']
    df['sell_amt'] = df['sell_shares'] * df['price_val']
    df['bv'] = (df['buy_shares'] / 1000).astype(int)
    df['sv'] = (df['sell_shares'] / 1000).astype(int)
    
    tags, d_rows = {}, []
    for trader, g in df.groupby('securities_trader'):
        tb = g['bv'].sum()
        ts = g['sv'].sum()
        tv = tb + ts
        if tv == 0: continue
        dr = (min(tb, ts) * 2) / tv
        net = tb - ts
        nr = net / tb if tb > 0 else -1
        
        # ⚠️ 【新增加權均價精算】
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
            d_rows.append({
                "分點名稱": trader, "最終標籤": tag, "總買(張)": tb, "總賣(張)": ts, "淨留倉": int(net), 
                "買均價": round(avg_b, 2), "賣均價": round(avg_s, 2),
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
            f_vol = pd.to_numeric(fn['buy'].astype(str).str.replace(',', ''), errors='coerce').fillna(0).sum() / 1000
            for _, fr in fn.iterrows():
                buy_vol = pd.to_numeric(str(fr['buy']).replace(',', ''), errors='coerce')
                if buy_vol and buy_vol > 0: 
                    d_fri.append({"日期": d_str, "分點": fr['securities_trader'], "張數": int(buy_vol/1000)})
        
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
    df['純淨大戶變動(%)'], df['隔日沖虛胖(%)'], df['V29.3_雷達診斷'] = ddf['純淨變動'], ddf['雜訊'], ddf['診斷']
    
    df_radar = df[['日期', '收盤價(元)', '總人數變動率(%)', '原始大戶變動(%)', '隔日沖虛胖(%)', '純淨大戶變動(%)', 'V29.3_雷達診斷']].sort_values('日期', ascending=False)
    df_radar = df_radar[df_radar['V29.3_雷達診斷'] != '⚪ 初始化']
    
    return df_radar, pd.DataFrame(d_math), pd.DataFrame(d_fri)

def process_v27_daily_tracking(df_branch_raw, intel_tags, df_price, df_branch_diff, actual_dates):
    if df_branch_raw.empty or len(actual_dates) < 5: return pd.DataFrame()
    out = []
    for d in actual_dates[:5]:
        pr = df_price[df_price['日期'] == d]
        cp = pr['收盤價(元)'].iloc[0] if not pr.empty else 0
        sp = pr['漲跌(元)'].iloc[0] if not pr.empty else 0
        diff = df_branch_diff[df_branch_diff['日期'] == d]
        bsd = diff['買賣家數差'].iloc[0] if not diff.empty else 0
        df_d = df_branch_raw[df_branch_raw['date'] == d]
        sn, nn = 0, 0
        if not df_d.empty:
            df_d = df_d.copy(); df_d['tag'] = df_d['securities_trader'].map(intel_tags).fillna("🔵 一般")
            df_d['net_vol'] = (pd.to_numeric(df_d['buy'].astype(str).str.replace(',', ''), errors='coerce').fillna(0) - pd.to_numeric(df_d['sell'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)) / 1000
            sn = df_d[df_d['tag'].str.contains('波段主|真鎖碼|官股')]['net_vol'].sum()
            nn = df_d[df_d['tag'].str.contains('隔日沖|套牢')]['net_vol'].sum()
        adv = []
        if sn > 50 and bsd < 0: adv.append("🟢 主力吃貨/籌碼集中")
        elif sn < -100: adv.append("🔴 波段大戶撤退")
        if nn > 300: adv.append("⚠️ 短線潛在賣壓進駐")
        if bsd > 100: adv.append("📉 散戶進場接刀")
        out.append({"日期": d, "收盤價(元)": cp, "漲跌(元)": sp, "波段/官股淨流入(張)": int(sn), "隔日沖潛在賣壓(張)": int(nn), "買賣家數差": bsd, "單日微觀診斷": " | ".join(adv) if adv else "無明顯特徵"})
    return pd.DataFrame(out)

def generate_ai_hawk_eye(df_daily, df_radar, df_fingerprint):
    alerts = []
    if not df_daily.empty and len(df_daily) >= 1:
        today_d = df_daily.iloc[0]
        if today_d['波段/官股淨流入(張)'] < -100 and today_d['買賣家數差'] > 50:
            alerts.append("<span class='hawk-alert'>🚨 【假突破/虛假熱度】股價高檔爆量，但「聰明錢」單日大撤退，且買賣家數發散，散戶正在接刀！</span>")
        elif today_d['波段/官股淨流入(張)'] > 200 and today_d['買賣家數差'] < 0:
            alerts.append("<span class='hawk-safe'>🛡️ 【真實推升】波段大戶與官股真金白銀吃貨，且籌碼集中，非當沖客虛火。</span>")

    if not df_fingerprint.empty and len(df_fingerprint) >= 1:
        top_15 = df_fingerprint.head(15)
        trapped = len(top_15[top_15['最終標籤'] == '🩹 [被動套牢]'])
        locked = len(top_15[top_15['最終標籤'] == '🧱 [主動鎖碼]'])
        if trapped >= 2 and trapped > locked:
            alerts.append(f"<span class='hawk-alert'>⚠️ 【誘多套牢】前 15 大分點有 {trapped} 家處於『均價虧損』被迫留倉，明日易引發多殺多賣壓。</span>")
        elif locked >= 2 and locked > trapped:
            alerts.append(f"<span class='hawk-safe'>🔥 【主動鎖碼】前 15 大分點有 {locked} 家處於『獲利強勢留倉』狀態，主力買均價極具優勢，具波段續攻潛力。</span>")

    if not df_radar.empty and len(df_radar) >= 1:
        latest_r = df_radar.iloc[0]
        if latest_r['原始大戶變動(%)'] > 0.5 and latest_r['隔日沖虛胖(%)'] > 0.8 and latest_r['純淨大戶變動(%)'] <= 0.2:
            alerts.append("<span class='hawk-alert'>🚨 【集保騙局】週末公佈大戶持股增加，實則九成以上全是『隔日沖虛胖』，純淨大戶根本沒買，小心週一遭倒貨！</span>")
            
    if not alerts:
        alerts.append("<span>🔍 目前籌碼結構中性，無極端操作訊號，請依紀律操作。</span>")
    return alerts

# ==========================================
# 📌 資料處理與排版 
# ==========================================
def process_price(df):
    if df.empty: return pd.DataFrame()
    df_out = df.copy()
    df_out['Trading_Volume'] = (pd.to_numeric(df_out['Trading_Volume'].astype(str).str.replace(',', ''), errors='coerce').fillna(0) / 1000).round().astype(int)
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
    df['unit'] = (pd.to_numeric(df.get('unit', 0).astype(str).str.replace(',', ''), errors='coerce').fillna(0) / 1000).round().astype(int)
    df['people'] = pd.to_numeric(df['people'].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
    
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

# ⚠️ 【V29.3 新增買賣均價顯示於每日分點排行】
def process_branch_v25(df_raw, period, actual_dates, intel_tags):
    if df_raw.empty: return pd.DataFrame()
    df = df_raw[df_raw['date'].isin(actual_dates[:period])].copy()
    
    df['buy_shares'] = pd.to_numeric(df['buy'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    df['sell_shares'] = pd.to_numeric(df['sell'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    df['price_val'] = pd.to_numeric(df['price'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    
    df['buy_amt'] = df['buy_shares'] * df['price_val']
    df['sell_amt'] = df['sell_shares'] * df['price_val']
    df['bv'] = (df['buy_shares'] / 1000).astype(int)
    df['sv'] = (df['sell_shares'] / 1000).astype(int)
    
    g = df.groupby('securities_trader').agg(
        bv=('bv', 'sum'), sv=('sv', 'sum'),
        buy_shares=('buy_shares', 'sum'), sell_shares=('sell_shares', 'sum'),
        buy_amt=('buy_amt', 'sum'), sell_amt=('sell_amt', 'sum')
    ).reset_index()
    
    g['net'] = g['bv'] - g['sv']
    g['avg_b'] = np.where(g['buy_shares'] > 0, g['buy_amt'] / g['buy_shares'], 0)
    g['avg_s'] = np.where(g['sell_shares'] > 0, g['sell_amt'] / g['sell_shares'], 0)
    
    b = g[g['net'] > 0].sort_values('net', ascending=False).head(15).reset_index(drop=True)
    s = g[g['net'] < 0].sort_values('net', ascending=True).head(15).reset_index(drop=True)
    
    out, tv = [], g['bv'].sum() if g['bv'].sum() > 0 else 1
    for i in range(15):
        r = {}
        if i < len(b): 
            r["買超分點"] = f"{intel_tags.get(b.loc[i,'securities_trader'],'🔵')} {b.loc[i,'securities_trader']}"
            r["買超(張)"] = int(b.loc[i,'net'])
            r["買均價"] = round(b.loc[i,'avg_b'], 2)
            r["佔比"] = f"{(b.loc[i,'net']/tv)*100:.1f}%"
        else: 
            r["買超分點"] = "-"; r["買超(張)"] = 0; r["買均價"] = "-"; r["佔比"] = "-"
            
        if i < len(s): 
            r["賣超分點"] = f"{intel_tags.get(s.loc[i,'securities_trader'],'🔵')} {s.loc[i,'securities_trader']}"
            r["賣超(張)"] = abs(int(s.loc[i,'net']))
            r["賣均價"] = round(s.loc[i,'avg_s'], 2)
            r["佔比_"] = f"{(abs(s.loc[i,'net'])/tv)*100:.1f}%"
        else: 
            r["賣超分點"] = "-"; r["賣超(張)"] = 0; r["賣均價"] = "-"; r["佔比_"] = "-"
        out.append(r)
    return pd.DataFrame(out)

def process_branch_diff(df_raw, actual_dates):
    if df_raw.empty or not actual_dates: return pd.DataFrame()
    out = []
    df_raw_num = df_raw.copy()
    df_raw_num['buy'] = pd.to_numeric(df_raw_num['buy'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    df_raw_num['sell'] = pd.to_numeric(df_raw_num['sell'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    
    for d in actual_dates[:10]:
        df_d = df_raw_num[df_raw_num['date'] == d]
        if df_d.empty: continue
        out.append({
            "日期": d, 
            "買進家數": df_d[df_d['buy'] > 0]['securities_trader'].nunique(), 
            "賣出家數": df_d[df_d['sell'] > 0]['securities_trader'].nunique(), 
            "買賣家數差": df_d[df_d['buy'] > 0]['securities_trader'].nunique() - df_d[df_d['sell'] > 0]['securities_trader'].nunique()
        })
    return pd.DataFrame(out)

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
    for col in ["設質(張)", "解質(張)", "累積質設(張)"]: df_all[col] = pd.to_numeric(df_all[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
    
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

def process_day_trading(df):
    if df.empty: return pd.DataFrame()
    df_out = df.copy().rename(columns={"date": "日期", "Volume": "當沖總股數", "BuyAfterSale": "先買後賣股數", "SellAfterBuy": "先賣後買股數", "DayTradingVolume": "當沖總股數"})
    for col in ["當沖總股數", "先買後賣股數", "先賣後買股數"]:
        if col in df_out.columns: df_out[col.replace('股數', '張數')] = (pd.to_numeric(df_out[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0) / 1000).round().astype(int); df_out = df_out.drop(columns=[col])
    cols = ['日期'] + [c for c in df_out.columns if '張數' in c or '率' in c]
    return df_out[cols].tail(10).sort_values('日期', ascending=False)

def process_margin(df):
    if df.empty: return pd.DataFrame()
    for c in ["MarginPurchaseBuy", "MarginPurchaseSell", "MarginPurchaseCashRepayment", "MarginPurchaseTodayBalance", "MarginPurchaseYesterdayBalance", "ShortSaleBuy", "ShortSaleSell", "ShortSaleCashRepayment", "ShortSaleTodayBalance", "OffsetLoanAndShort", "ShortSaleYesterdayBalance"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', ''), errors='coerce').fillna(0).round().astype(int)
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
    f_b = pd.to_numeric(pdf.get('buy_Foreign_Investor',0).astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    f_s = pd.to_numeric(pdf.get('sell_Foreign_Investor',0).astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    out['外資買賣超(張)'] = ((f_b - f_s) / 1000).round().astype(int)
    
    i_b = pd.to_numeric(pdf.get('buy_Investment_Trust',0).astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    i_s = pd.to_numeric(pdf.get('sell_Investment_Trust',0).astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    out['投信買賣超(張)'] = ((i_b - i_s) / 1000).round().astype(int)
    
    ds_b = pd.to_numeric(pdf.get('buy_Dealer_self',0).astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    ds_s = pd.to_numeric(pdf.get('sell_Dealer_self',0).astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    out['自營商(自行)買賣超'] = ((ds_b - ds_s) / 1000).round().astype(int)
    
    dh_b = pd.to_numeric(pdf.get('buy_Dealer_Hedging',0).astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    dh_s = pd.to_numeric(pdf.get('sell_Dealer_Hedging',0).astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    out['自營商(避險)買賣超'] = ((dh_b - dh_s) / 1000).round().astype(int)
    
    out['三大法人買賣超(張)'] = out['外資買賣超(張)'] + out['投信買賣超(張)'] + out['自營商(自行)買賣超'] + out['自營商(避險)買賣超']
    return out.tail(10).sort_values('日期', ascending=False)

def process_fut_inst(df):
    if df.empty: return pd.DataFrame()
    df['net'] = pd.to_numeric(df['long_open_interest_balance_volume'].astype(str).str.replace(',', ''), errors='coerce').fillna(0) - pd.to_numeric(df['short_open_interest_balance_volume'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    pdf = df.pivot_table(index='date', columns='institutional_investors', values='net', fill_value=0).reset_index()
    pdf.columns.name = None
    for col in ['Foreign_Investor', 'Investment_Trust', 'Dealer']:
        if col not in pdf.columns: pdf[col] = 0
    return pdf.rename(columns={'date': '日期', 'Foreign_Investor': '外資多空(口)', 'Investment_Trust': '投信多空(口)', 'Dealer': '自營多空(口)'}).tail(10).sort_values('日期', ascending=False)

def process_per(df):
    if df.empty: return pd.DataFrame()
    df_out = df.copy().rename(columns={"date":"日期","dividend_yield":"殖利率(%)","PER":"本益比(倍)","PBR":"淨值比(倍)"})
    for col in ["殖利率(%)", "本益比(倍)", "淨值比(倍)"]: 
        if col in df_out.columns:
            df_out[col] = pd.to_numeric(df_out[col].astype(str).str.replace(',', ''), errors='coerce').round(2)
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
            is_pct = "%" in s
            try:
                v = float(s.replace(',', '').replace('%', ''))
                return f"{v:,.2f}" + ("%" if is_pct else "") if '.' in s or is_pct else f"{int(v):,}"
            except: return str(x)
        f_dict = {c: fmt_auto for c in df.columns}
        left_cols = [c for c in df.columns if any(kw in str(c) for kw in ['日期', '公告日期', '分點', '名稱', '姓名', '身份別', '質權人', '交易別', '診斷', '判定', '門檻', '條件', '措施', '契約', '代號', '來源', '標籤', '單日微觀診斷', 'V29.3_雷達診斷'])]
        right_cols = [c for c in df.columns if c not in left_cols]
        styler = df.style.format(f_dict).set_properties(**{'text-align': 'right !important'}, subset=right_cols)
        if left_cols: styler = styler.set_properties(**{'text-align': 'left !important'}, subset=left_cols)
        try: styler = styler.hide(axis="index")
        except: styler = styler.hide_index()
        html = styler.set_table_styles([dict(selector='th', props=[('text-align', 'center !important')]), dict(selector='table', props=[('width', '100%')])]).to_html()
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

    with st.spinner(f"正在啟動 V29.3 終極引擎 (主力成本加權計算中)..."):
        name = get_stock_name(user_stock_id)
        if not name:
            st.error(f"⚠️ 查無股票代號 {user_stock_id} 的基本資料。"); st.stop()
            
        df_p_raw = fetch_fm("TaiwanStockPrice", (datetime.date.today() - datetime.timedelta(days=1095)).strftime("%Y-%m-%d"), user_stock_id)
        if df_p_raw.empty: 
            st.error("⚠️ 查無歷史股價資料。"); st.stop()
        
        dates = sorted(df_p_raw['date'].unique().tolist(), reverse=True)
        d_60 = dates[59] if len(dates) >= 60 else dates[-1]
        df_price = process_price(df_p_raw)
        dynamic_dict, s_val, chip_eng, _ = scrape_director_holding(user_stock_id)
        
        df_b_raw = fetch_fm_branch_fast_parallel(dates[:60], user_stock_id)
        tags, df_debug_tags = get_v27_intelligence(df_b_raw, df_p_raw)
        df_b_diff = process_branch_diff(df_b_raw, dates)
        
        df_s_raw = fetch_fm("TaiwanStockHoldingSharesPer", d_60, user_stock_id)
        df_s_wide, df_s_unit, df_s_ppl = process_tdcc(df_s_raw)
        df_s_dyn = process_tdcc_dynamic(df_s_wide, df_price, dead_chip_input, dynamic_dict, s_val, chip_eng)
        df_v27_radar, df_debug_math, _ = process_v27_ultimate_radar(df_s_wide, dead_chip_input, dynamic_dict, s_val, df_price, df_b_raw, tags)
        df_daily_tracker = process_v27_daily_tracking(df_b_raw, tags, df_price, df_b_diff, dates)

        df_twse, _ = scrape_block_trades(user_stock_id, dates)
        df_margin = process_margin(fetch_fm("TaiwanStockMarginPurchaseShortSale", d_60, user_stock_id))
        df_day_trade = process_day_trading(fetch_fm("TaiwanStockDayTrading", d_60, user_stock_id))
        df_inst = process_inst(fetch_fm("TaiwanStockInstitutionalInvestorsBuySell", d_60, user_stock_id))
        
        df_rev_raw = fetch_fm("TaiwanStockMonthRevenue", "2022-01-01", user_stock_id)
        df_rev = pd.DataFrame()
        if not df_rev_raw.empty:
            df_rev_raw['營收月份'] = df_rev_raw['revenue_year'].astype(str) + "-" + df_rev_raw['revenue_month'].astype(str).str.zfill(2)
            df_rev = df_rev_raw.rename(columns={"revenue":"月營收(百萬元)"})[['營收月份','月營收(百萬元)']].tail(24)
            df_rev['月營收(百萬元)'] = (pd.to_numeric(df_rev['月營收(百萬元)'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)/1000000).round().astype(int)
            df_rev = df_rev.sort_values('營收月份', ascending=False)

        df_b_today = process_branch_v25(df_b_raw, 1, dates, tags)
        df_b_prev1 = process_branch_v25(df_b_raw, 1, dates[1:], tags)
        df_b_3 = process_branch_v25(df_b_raw, 3, dates, tags)
        df_b_10 = process_branch_v25(df_b_raw, 10, dates, tags)
        df_b_20 = process_branch_v25(df_b_raw, 20, dates, tags)
        df_b_30 = process_branch_v25(df_b_raw, 30, dates, tags)
        df_b_60 = process_branch_v25(df_b_raw, 60, dates, tags)

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

        # ==========================================
        # ⚠️ 頁面呈現
        # ==========================================
        st.subheader(f"📊 {user_stock_id} {name} 全息戰報 (V29.3 主力成本透視版)")
        st.markdown(f"<div class='info-box'>{company_info_text}</div>", unsafe_allow_html=True)
        
        hawk_alerts = generate_ai_hawk_eye(df_daily_tracker, df_v27_radar, df_debug_tags)
        hawk_html = "<div class='hawk-eye-box'><b>👁️‍🗨️ AI 鷹眼自動破局診斷：</b><br>"
        for alert in hawk_alerts: hawk_html += f"► {alert}<br>"
        hawk_html += "</div>"
        st.markdown(hawk_html, unsafe_allow_html=True)

        st.markdown("<div class='category-title'>📊 核心戰情追蹤</div>", unsafe_allow_html=True)
        show_table("01. 平日戰情追蹤矩陣 (核心代理指標)", df_daily_tracker, "daily-tracker")
        show_table("02. 專家診斷雷達 (週末除水版)", df_v27_radar.head(8), "radar-table")
        show_table("03. 雙軸活大戶鎖碼判定表 (C-Value)", df_s_dyn.head(8))
        show_table("04. 收盤價量 (近10天)", df_price.head(10))

        st.markdown("<div class='category-title'>🕵️‍♂️ 主力分點指紋與動向</div>", unsafe_allow_html=True)
        show_table("05. 主力分點指紋圖鑑 (盤中動能辨識)", df_debug_tags.head(30))
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
        show_table("12. 買賣家數差明細 (近10天)", df_b_diff)
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
        
        with st.expander(f"📋 給 Gemini 的 V29.3 實戰精華資料包 (CSV格式)", expanded=True):
            p1 = f"請依下面最新的盤後資料幫我分析 {user_stock_id} {name} 的量化籌碼，必須以我給的資料優先使用。\n\n"
            p1 += f"{company_info_text}\n\n"
            p1 += format_to_csv_string(df_daily_tracker, "01. 平日戰情追蹤矩陣 (近5日)")
            p1 += format_to_csv_string(df_v27_radar.head(4), "02. 專家診斷雷達 (近4週)")
            p1 += format_to_csv_string(df_s_dyn.head(4), "03. 雙軸活大戶鎖碼判定表 (近4週)")
            p1 += format_to_csv_string(df_debug_tags.head(30), "05. 主力分點指紋圖鑑 (核心30大)")
            p1 += format_to_csv_string(df_b_today, f"06. 主力分點 - 今日 ({dates[0]})")
            p1 += format_to_csv_string(df_b_60, "07. 主力分點 - 近60日")
            p1 += format_to_csv_string(df_inst.head(5), "08. 法人買賣超 (近5天)")
            p1 += format_to_csv_string(df_margin.head(5), "09. 散戶資券餘額 (近5天)")
            if not df_p_det.empty: p1 += format_to_csv_string(df_p_det, "18. 董監大股東質設明細")
            if not df_cbas.empty: p1 += format_to_csv_string(df_cbas, "23. CBAS 可轉債數據")
            st.code(p1, language="text")

        with st.expander(f"🔎 給 Gemini 的 V29.3 稽核與驗算資料包 (CSV格式)", expanded=False):
            p2 = f"請幫我驗證 {user_stock_id} {name} 以下 CSV 數據的數學邏輯正確性：\n\n"
            p2 += format_to_csv_string(df_debug_tags.head(30), "稽核A：前30大分點指紋數據")
            p2 += format_to_csv_string(df_debug_math, "稽核B：除水還原數學驗算表")
            st.code(p2, language="text")
