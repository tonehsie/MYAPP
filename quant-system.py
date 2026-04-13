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
st.set_page_config(page_title="V27.6 終極全息量化系統 (鷹眼破局版)", layout="wide")

# 內建 Token
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

# 注入全局 CSS (新增鷹眼警示框樣式)
st.markdown("""
<style>
.table-responsive { overflow-x: auto; width: 100%; display: block; margin-bottom: 20px; }
table.dataframe th, table.dataframe td { white-space: nowrap !important; text-align: center !important; padding: 8px 12px !important; }
.radar-table td:last-child { text-align: left !important; color: #ff4b4b; font-weight: bold; }
.daily-tracker td:last-child { text-align: left !important; color: #008080; font-weight: bold; }
.debug-header { color: #f63366; font-weight: bold; }
.info-box { background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #ff4b4b; font-size: 16px;}
.dict-box { background-color: #fdf2f2; padding: 15px; border-radius: 10px; border-left: 5px solid #e03131; font-size: 14px; line-height: 1.6;}
.hawk-eye-box { background-color: #fff9db; padding: 15px; border-radius: 10px; margin-bottom: 20px; border-left: 6px solid #f59f00; font-size: 16px; line-height: 1.8;}
.hawk-alert { color: #d9480f; font-weight: bold; }
.hawk-safe { color: #2b8a3e; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🤖 交易員實戰手冊：V27.6 全息量化除水系統")
st.caption("核心升級：導入『AI 鷹眼破局引擎』，自動偵測主力越沖越高、誘多套牢與週末集保騙局。")

# UI 輸入區
col1, col2 = st.columns([1, 1])
with col1: 
    user_stock_id = st.text_input("個股代號", value="8027", placeholder="請輸入台股代號 (例: 2330)")
with col2: 
    dead_chip_input = st.text_input("死籌碼 %", placeholder="自動抓取董監事持股比例，也可自行輸入", help="留空將自動抓取。您也可自行輸入比例（涵蓋董監事＋大股東持股）")
run_btn = st.button("🚀 啟動 V27.6 完整引擎", use_container_width=True)
st.divider()

# ==========================================
# 📌 工具與基本面情報抓取
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def get_stock_name(target_id):
    try:
        res = requests.get(f"https://tw.stock.yahoo.com/quote/{target_id}.TW", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        match = re.search(r'<title>(.*?)\s*\(', res.text)
        return match.group(1).strip() if match else ""
    except: return ""

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
            res.encoding = 'big5'
            return res.text
        except: return ""

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fm(dataset, start_date, target_id=None, end_date=None):
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {"dataset": dataset, "start_date": start_date}
    if target_id: params["data_id"] = target_id
    if end_date: params["end_date"] = end_date
    try: return pd.DataFrame(requests.get(url, params=params, headers={"Authorization": f"Bearer {FINMIND_TOKEN}"}, timeout=15).json().get("data", []))
    except: return pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fm_branch_fast_parallel(dates_list, target_id):
    if not dates_list: return pd.DataFrame()
    all_data = []
    def fetch_single(d):
        try: return requests.get("https://api.finmindtrade.com/api/v4/data", params={"dataset": "TaiwanStockTradingDailyReport", "data_id": target_id, "start_date": d, "end_date": d}, headers={"Authorization": f"Bearer {FINMIND_TOKEN}"}, timeout=15).json().get("data", [])
        except: return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for r in executor.map(fetch_single, dates_list):
            if r: all_data.extend(r)
    return pd.DataFrame(all_data)

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
# 📌 V27.6 指紋辨識 (結合 VWAP 與開收高低)
# ==========================================
def get_v27_intelligence(df_b_raw, df_p_raw):
    if df_b_raw.empty or df_p_raw.empty: return {}, pd.DataFrame()
    
    df_p = df_p_raw.copy()
    df_p['date'] = pd.to_datetime(df_p['date'])
    df_p['avg_price'] = (df_p['close'] + df_p['max'] + df_p['min']) / 3
    df_p['pos'] = (df_p['close'] - df_p['min']) / (df_p['max'] - df_p['min']).replace(0, 1)
    df_p['strength'] = (df_p['close'] - df_p['avg_price']) / df_p['avg_price']
    price_stats = df_p.set_index('date')[['pos', 'strength']].to_dict('index')

    df = df_b_raw.copy()
    df['date'] = pd.to_datetime(df['date'])
    df['bv'] = (pd.to_numeric(df['buy'], errors='coerce').fillna(0) / 1000).astype(int)
    df['sv'] = (pd.to_numeric(df['sell'], errors='coerce').fillna(0) / 1000).astype(int)
    
    tags, d_rows = {}, []
    for trader, g in df.groupby('securities_trader'):
        tb, ts = g['bv'].sum(), g['sv'].sum()
        tv = tb + ts
        if tv == 0: continue
        dr = (min(tb, ts) * 2) / tv
        net = tb - ts
        nr = net / tb if tb > 0 else -1
        
        ld = g['date'].max()
        stats = price_stats.get(ld, {'pos': 0.5, 'strength': 0})
        pos, strn = stats['pos'], stats['strength']
        
        tag = "🔵 一般"
        if any(x in trader for x in ["台銀", "土銀", "彰銀", "第一", "兆豐", "華南", "合庫", "台企銀"]): tag = "🏦 [官股]"
        elif dr > 0.80:
            if nr < 0.05: tag = "🌪️ [純當沖客]"
            elif strn > 0.01 and pos > 0.7: tag = "🧱 [主動鎖碼]" 
            elif strn < -0.01 and pos < 0.3: tag = "🩹 [被動套牢]" 
            else: tag = "⚡ [隔日沖]"
        elif nr > 0.7: tag = "📈 [波段主]"
        elif tb > 500 and nr > 0.85: tag = "🧱 [真鎖碼]"
        
        tags[trader] = tag
        if tb > 100 or ts > 100:
            d_rows.append({
                "分點名稱": trader, "最終標籤": tag, "總買(張)": tb, "總賣(張)": ts, "淨留倉": int(net), 
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
            fn = df_f[df_f['tag'].str.contains("隔日沖|主動鎖碼|被套牢")] 
            f_vol = fn['buy'].sum() / 1000
            for _, fr in fn.iterrows():
                if fr['buy'] > 0: d_fri.append({"日期": d_str, "分點": fr['securities_trader'], "張數": int(fr['buy']/1000)})
        
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
    df['純淨大戶變動(%)'], df['隔日沖虛胖(%)'], df['V27.6_雷達診斷'] = ddf['純淨變動'], ddf['雜訊'], ddf['診斷']
    
    df_radar = df[['日期', '收盤價(元)', '總人數變動率(%)', '原始大戶變動(%)', '隔日沖虛胖(%)', '純淨大戶變動(%)', 'V27.6_雷達診斷']].sort_values('日期', ascending=False)
    df_radar = df_radar[df_radar['V27.6_雷達診斷'] != '⚪ 初始化']
    
    return df_radar, pd.DataFrame(d_math), pd.DataFrame(d_fri)

# ==========================================
# 📌 模組二：V27.6 平日戰情追蹤矩陣
# ==========================================
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
            df_d['net_vol'] = (df_d['buy'] - df_d['sell']) / 1000
            sn = df_d[df_d['tag'].str.contains('波段主|真鎖碼|官股')]['net_vol'].sum()
            nn = df_d[df_d['tag'].str.contains('隔日沖|鎖碼|套牢')]['net_vol'].sum()
        adv = []
        if sn > 50 and bsd < 0: adv.append("🟢 主力吃貨/籌碼集中")
        elif sn < -100: adv.append("🔴 波段大戶撤退")
        if nn > 300: adv.append("⚠️ 短線潛在賣壓進駐")
        if bsd > 100: adv.append("📉 散戶進場接刀")
        out.append({"日期": d, "收盤價(元)": cp, "漲跌(元)": sp, "波段/官股淨流入(張)": int(sn), "隔日沖潛在賣壓(張)": int(nn), "買賣家數差": bsd, "單日微觀診斷": " | ".join(adv) if adv else "無明顯特徵"})
    return pd.DataFrame(out)

# ==========================================
# 📌 數據清洗與基礎整理
# ==========================================
def process_price(df):
    if df.empty: return pd.DataFrame()
    df_out = df.copy()
    df_out['Trading_Volume'] = (pd.to_numeric(df_out['Trading_Volume'], errors='coerce').fillna(0) / 1000).round().astype(int)
    df_out = df_out.rename(columns={"date":"日期","Trading_Volume":"成交量(張)","close":"收盤價(元)","spread":"漲跌(元)","open":"開盤價(元)","max":"最高價(元)","min":"最低價(元)"})
    df_out["斷頭價(0.78)"] = (df_out["收盤價(元)"] * 0.78).round(2)
    return df_out[['日期','成交量(張)','開盤價(元)','最高價(元)','最低價(元)','收盤價(元)','漲跌(元)','斷頭價(0.78)']].sort_values('日期', ascending=False)

def clean_level_by_math(x):
    s = str(x).replace(',', '').replace(' ', '')
    if s in ["17", "17.0", "合計", "總計"]: return "合計"
    nums = re.findall(r'\d+', s)
    if not nums: return s
    up = int(nums[-1])
    if up <= 999: return "1-999股"
    elif up <= 5000: return "1-5張"
    elif up <= 10000: return "5-10張"
    elif up <= 50000: return "10-50張" # 簡化合併中型
    elif up <= 100000: return "50-100張"
    elif up <= 400000: return "100-400張"
    elif up <= 1000000: return "400-1000張"
    else: return "1000張以上" 

def process_tdcc(df):
    if df.empty: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df = df[~df['HoldingSharesLevel'].astype(str).str.contains('差異數')]
    df['LevelClean'] = df['HoldingSharesLevel'].apply(clean_level_by_math)
    df['unit'] = (pd.to_numeric(df.get('unit', 0), errors='coerce').fillna(0) / 1000).round().astype(int)
    df['people'] = pd.to_numeric(df['people'], errors='coerce').fillna(0).astype(int)
    
    dates = sorted(df['date'].unique(), reverse=True)[:15]
    df = df[df['date'].isin(dates)]
    df_levels = df[~df['LevelClean'].str.contains('合計|總計')]
    if df_levels.empty: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    p_u = df_levels.pivot_table(index='date', columns='LevelClean', values='unit', aggfunc='sum').reset_index().fillna(0)
    p_p = df_levels.pivot_table(index='date', columns='LevelClean', values='people', aggfunc='sum').reset_index().fillna(0)
    
    lvls = ['1-999股', '1-5張', '5-10張', '10-50張', '50-100張', '100-400張', '400-1000張', '1000張以上']
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
        
        lp = pd.to_numeric(row.get('1000張以上_比例(%)', 0), errors='coerce')
        cd, st = "-", "無死籌碼數據"
        if 0 < cur_dead < 100:
            cv = max(0, (lp - cur_dead) / (100.0 - cur_dead))
            st = "🔴 絕對控盤" if cv >= 0.5 else "🟡 高度鎖碼" if cv >= 0.3 else "🔵 初步集結" if cv >= 0.15 else "⚪ 籌碼渙散"
            cd = round(cv * 100, 2)
        out.append({"日期": row['日期'], "收盤價(元)": p, "大戶原持股(%)": round(lp, 2), "死籌碼(%)": f"{float(cur_dead):.2f}% ({cl})" if cur_dead > 0 else "-", "純淨活大戶C_Value(%)": cd, "實戰判定": st})
    return pd.DataFrame(out)

def process_branch_diff(df_raw, actual_dates):
    if df_raw.empty or not actual_dates: return pd.DataFrame()
    out = []
    for d in actual_dates[:10]:
        df_d = df_raw[df_raw['date'] == d]
        if df_d.empty: continue
        out.append({"日期": d, "買進家數": df_d[df_d['buy'] > 0]['securities_trader'].nunique(), "賣出家數": df_d[df_d['sell'] > 0]['securities_trader'].nunique(), "買賣家數差": df_d[df_d['buy'] > 0]['securities_trader'].nunique() - df_d[df_d['sell'] > 0]['securities_trader'].nunique()})
    return pd.DataFrame(out)

def process_margin(df):
    if df.empty: return pd.DataFrame()
    for c in ["MarginPurchaseBuy", "MarginPurchaseSell", "MarginPurchaseCashRepayment", "MarginPurchaseTodayBalance", "MarginPurchaseYesterdayBalance", "ShortSaleBuy", "ShortSaleSell", "ShortSaleCashRepayment", "ShortSaleTodayBalance", "OffsetLoanAndShort", "ShortSaleYesterdayBalance"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).round().astype(int)
    df = df.rename(columns={"date":"日期", "MarginPurchaseTodayBalance":"融資餘額(萬元)", "ShortSaleTodayBalance":"融券餘額(張)"})
    df['融資增減(萬元)'] = df['融資餘額(萬元)'] - df.get('MarginPurchaseYesterdayBalance', 0)
    return df[['日期','融資餘額(萬元)','融資增減(萬元)','融券餘額(張)']].tail(10).sort_values('日期', ascending=False)

def process_inst(df):
    if df.empty: return pd.DataFrame()
    pdf = df.pivot_table(index='date', columns='name', values=['buy', 'sell'], fill_value=0).reset_index()
    pdf.columns = ['_'.join(c).strip('_') for c in pdf.columns.values]
    out = pd.DataFrame({'日期': pdf['date']})
    f_b = pd.to_numeric(pdf.get('buy_Foreign_Investor',0), errors='coerce').fillna(0)
    f_s = pd.to_numeric(pdf.get('sell_Foreign_Investor',0), errors='coerce').fillna(0)
    out['外資買賣超(張)'] = ((f_b - f_s) / 1000).round().astype(int)
    
    ds_b = pd.to_numeric(pdf.get('buy_Dealer_self',0), errors='coerce').fillna(0)
    ds_s = pd.to_numeric(pdf.get('sell_Dealer_self',0), errors='coerce').fillna(0)
    out['自營商(自行)買賣超'] = ((ds_b - ds_s) / 1000).round().astype(int)
    
    out['重點法人合計(張)'] = out['外資買賣超(張)'] + out['自營商(自行)買賣超']
    return out.tail(10).sort_values('日期', ascending=False)

# ⚠️ 【全新模組：V27.6 AI 鷹眼破局引擎邏輯】
def generate_ai_hawk_eye(df_daily, df_radar, df_fingerprint):
    alerts = []
    
    # 1. 偵測「虛假熱度」與主力撤退 (看近一日)
    if not df_daily.empty:
        today_d = df_daily.iloc[0]
        if today_d['波段/官股淨流入(張)'] < -100 and today_d['買賣家數差'] > 50:
            alerts.append("<span class='hawk-alert'>🚨 【假突破/虛假熱度】股價高檔爆量，但「聰明錢」單日大撤退，且買賣家數發散，散戶正在接刀！</span>")
        elif today_d['波段/官股淨流入(張)'] > 200 and today_d['買賣家數差'] < 0:
            alerts.append("<span class='hawk-safe'>🛡️ 【真實推升】波段大戶與官股真金白銀吃貨，且籌碼集中，非當沖客虛火。</span>")

    # 2. 偵測「誘多套牢」與「主動鎖碼」 (看前 15 大分點狀態)
    if not df_fingerprint.empty:
        top_15 = df_fingerprint.head(15)
        trapped = len(top_15[top_15['最終標籤'] == '🩹 [被動套牢]'])
        locked = len(top_15[top_15['最終標籤'] == '🧱 [主動鎖碼]'])
        
        if trapped >= 2 and trapped > locked:
            alerts.append(f"<span class='hawk-alert'>⚠️ 【誘多套牢】前 15 大分點有 {trapped} 家處於『均價虧損』的被迫留倉狀態，明日開盤極易引發多殺多賣壓。</span>")
        elif locked >= 2 and locked > trapped:
            alerts.append(f"<span class='hawk-safe'>🔥 【主動鎖碼】前 15 大分點有 {locked} 家處於『獲利強勢留倉』狀態，主力買均價極具優勢，具波段續攻潛力。</span>")

    # 3. 偵測「週末集保騙局」 (看最新一週雷達)
    if not df_radar.empty:
        latest_r = df_radar.iloc[0]
        if latest_r['原始大戶變動(%)'] > 0.5 and latest_r['隔日沖虛胖(%)'] > 0.8 and latest_r['純淨大戶變動(%)'] <= 0.2:
            alerts.append("<span class='hawk-alert'>🚨 【集保騙局】週末公佈大戶持股增加，實則九成以上全是『隔日沖虛胖』，純淨大戶根本沒買，小心週一遭倒貨！</span>")
            
    if not alerts:
        alerts.append("<span>🔍 目前籌碼結構中性，無極端操作訊號，請依紀律操作。</span>")
        
    return alerts

def show_table(title, df, custom_class=""):
    st.markdown(f"#### {title}")
    if df is None or df.empty: st.warning("此區塊查無數據或無發行紀錄")
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
        left_cols = [c for c in df.columns if any(kw in str(c) for kw in ['日期', '分點', '名稱', '標籤', '診斷'])]
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
    if df is None or df.empty: return header + "此區塊查無數據\n"
    return header + df.to_csv(index=False) + "\n"

# ==========================================
# 📌 執行主引擎
# ==========================================
if run_btn:
    if not user_stock_id.strip():
        st.warning("⚠️ 請先在上方輸入股票代號！")
        st.stop()

    with st.spinner(f"正在執行 V27.6 終極全息引擎 (鷹眼自動破局運算中)..."):
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
        
        # 核心 V27 處理
        df_b_raw = fetch_fm_branch_fast_parallel(dates[:60], user_stock_id)
        tags, df_debug_tags = get_v27_intelligence(df_b_raw, df_p_raw)
        df_b_diff = process_branch_diff(df_b_raw, dates)
        
        df_s_raw = fetch_fm("TaiwanStockHoldingSharesPer", d_60, user_stock_id)
        df_s_wide, df_s_unit, df_s_ppl = process_tdcc(df_s_raw)
        df_s_dyn = process_tdcc_dynamic(df_s_wide, df_price, dead_chip_input, dynamic_dict, s_val, chip_eng)
        df_v27_radar, df_debug_math, _ = process_v27_ultimate_radar(df_s_wide, dead_chip_input, dynamic_dict, s_val, df_price, df_b_raw, tags)
        df_daily_tracker = process_v27_daily_tracking(df_b_raw, tags, df_price, df_b_diff, dates)

        df_margin = process_margin(fetch_fm("TaiwanStockMarginPurchaseShortSale", d_60, user_stock_id))
        df_inst = process_inst(fetch_fm("TaiwanStockInstitutionalInvestorsBuySell", d_60, user_stock_id))

        market_cap_str = "計算中..."
        industry, address = get_company_profile(user_stock_id)
        if not df_price.empty and not df_s_wide.empty:
            market_cap_str = f"{(df_price['收盤價(元)'].iloc[0] * df_s_wide['總張數'].iloc[0]) / 100000:,.2f} 億"
        company_info_text = f"🏢 **【產業】** {industry} ｜ 💰 **【市值】** {market_cap_str} ｜ 📍 **【公司地址 (地緣核對)】** {address}"

        # --- 頁面呈現 ---
        st.subheader(f"📊 {user_stock_id} {name} V27.6 全息戰報")
        st.markdown(f"<div class='info-box'>{company_info_text}</div>", unsafe_allow_html=True)
        
        # ⚠️ 【全新區塊：V27.6 AI 鷹眼破局引擎顯示區】
        hawk_alerts = generate_ai_hawk_eye(df_daily_tracker, df_v27_radar, df_debug_tags)
        hawk_html = "<div class='hawk-eye-box'><b>👁️‍🗨️ V27.6 AI 鷹眼自動破局診斷：</b><br>"
        for alert in hawk_alerts: hawk_html += f"► {alert}<br>"
        hawk_html += "</div>"
        st.markdown(hawk_html, unsafe_allow_html=True)

        show_table("⚡ 0. 平日戰情追蹤矩陣", df_daily_tracker, "daily-tracker")
        show_table("1-1. 雙軸活大戶鎖碼判定表 (C-Value)", df_s_dyn.head(8))
        show_table("1-2. V27.6 專家診斷雷達 (週末除水版)", df_v27_radar.head(8), "radar-table")
        show_table("9. 主力分點指紋圖鑑 (核心30大)", df_debug_tags.head(30))

        st.divider()

        # ⚠️ 【AI 精華區】
        with st.expander(f"📋 【點擊展開：給 Gemini 的 V27.6 實戰精華資料包】", expanded=True):
            p1 = f"請依下面最新的盤後資料幫我分析 {user_stock_id} {name} 的量化籌碼，必須以我給的資料優先使用。\n\n"
            p1 += f"{company_info_text}\n\n"
            p1 += format_to_csv_string(df_daily_tracker, "0. 平日戰情追蹤矩陣 (近5日)")
            p1 += format_to_csv_string(df_v27_radar.head(4), "1-2. V27.6 專家診斷雷達 (近4週)")
            p1 += format_to_csv_string(df_margin.head(5), "4. 散戶資券餘額 (近5天)")
            p1 += format_to_csv_string(df_inst.head(5), "6. 法人買賣超 (近5天)")
            p1 += format_to_csv_string(df_debug_tags.head(30), "9. 主力分點指紋圖鑑 (核心30大)")
            st.code(p1, language="text")
