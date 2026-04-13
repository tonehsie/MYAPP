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
st.set_page_config(page_title="V26.7 終極全息量化系統", layout="wide")

# 內建 Token
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

# 注入全局 CSS
st.markdown("""
<style>
table.dataframe th, table.dataframe td { white-space: nowrap !important; text-align: center !important; }
.radar-table td:last-child { text-align: left !important; color: #ff4b4b; font-weight: bold; }
.daily-tracker td:last-child { text-align: left !important; color: #008080; font-weight: bold; }
.debug-header { color: #f63366; font-weight: bold; }
.info-box { background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #ff4b4b; font-size: 16px;}
.dict-box { background-color: #e8f4f8; padding: 15px; border-radius: 10px; border-left: 5px solid #008080; font-size: 14px; line-height: 1.6;}
</style>
""", unsafe_allow_html=True)

st.title("🤖 交易員實戰手冊：V26.7 全息量化除水系統")
st.caption("核心升級：欄位語意白話文優化，內建實戰名詞字典，去除解讀障礙。")

# 內建字典 (展開式)
with st.expander("📖 【必讀】V26.7 獨家數據欄位與實戰名詞解釋", expanded=False):
    st.markdown("""
    <div class='dict-box'>
    <b>▼ 0. 平日戰情追蹤矩陣 (週一至週四的每日金流)</b><br>
    <ul>
        <li><b>波段/官股淨流(張)</b>：代表長線大戶 (📈波段主、🧱真鎖碼、🏦官股) 今天的真實買賣超。正數是吃貨，負數是偷跑。</li>
        <li><b>隔日沖潛在賣壓(張)</b>：代表極短線投機客 (⚡隔日沖) 買進且留倉到明天的張數。數字越大，明天開盤的下殺風險越高。</li>
        <li><b>買賣家數差</b>：當日「買進券商家數 - 賣出券商家數」。負數代表籌碼流向少數人 (大戶集中)；正數代表籌碼發散 (散戶接刀)。</li>
    </ul>
    <b>▼ 1-1. 雙軸活大戶鎖碼判定表 (長線存量)</b><br>
    <ul>
        <li><b>死籌碼(%)</b>：公司董監事及大股東質押的持股比例，通常鎖在金庫裡，不會在市場上流通。</li>
        <li><b>純淨活大戶C-Value(%)</b>：扣除死籌碼後，市場上真正流通的股票中，有多少 % 被 1000 張以上大戶鎖住。大於 30% 為高度鎖碼，大於 50% 為絕對控盤。</li>
    </ul>
    <b>▼ 1-2. 專家診斷雷達 (週末除水版) (每週動能)</b><br>
    <ul>
        <li><b>原始大戶變動(%)</b>：集保中心週末公佈的 1000 張以上大戶持股增減比例 (表面數據)。</li>
        <li><b>隔日沖虛胖(%)</b>：系統抓出週五當天進場的「隔日沖」大戶買超量，佔總股本的比例。這些是下週一就會砸掉的假籌碼。</li>
        <li><b>純淨大戶變動(%)</b>：(原始變動 - 隔日沖虛胖)。這是扒開假象後，長線大戶這個禮拜真正的進出比例。</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

# UI 輸入區
col1, col2 = st.columns([1, 1])
with col1: user_stock_id = st.text_input("個股代號", value="8027")
with col2: dead_chip_input = st.text_input("死籌碼 %", placeholder="留空自動計算")
run_btn = st.button("🚀 啟動 V26.7 引擎：擷取地緣情報與全息雷達", use_container_width=True)
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
def scrape_block_trades(target_id, actual_dates):
    if not actual_dates: return pd.DataFrame(), []
    target_dates = actual_dates[:3] 
    block_data, debug_log = [], []
    def fetch_date(d):
        d_twse, d_tpex = d.replace("-", ""), f"{int(d.split('-')[0])-1911}/{d.split('-')[1]}/{d.split('-')[2]}"
        res_list, headers = [], {"User-Agent": "Mozilla/5.0"}
        try:
            j = requests.get(f"https://www.twse.com.tw/rwd/zh/block/BFIAUU?date={d_twse}&response=json", headers=headers, timeout=5, verify=False).json()
            if "data" in j and j["data"]:
                for r in j["data"]:
                    if target_id in str(r): res_list.append([d, "TWSE", r])
        except: pass
        try:
            j = requests.get(f"https://www.tpex.org.tw/www/zh-tw/blockTrade/quote?date={d_tpex}&id=&response=json", headers=headers, timeout=5, verify=False).json()
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
        nums = [float(re.sub(r'<[^>]+>', '', str(c)).replace(',', '').strip()) for c in row if re.sub(r'<[^>]+>', '', str(c)).replace(',', '').strip() and ':' not in str(c)]
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
    try:
        html = safe_get_fubon(f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zck/zck_{target_id}.djhtm")
        if html:
            table_match = re.search(r'姓名/法人名稱(.*?)</table>', html, re.IGNORECASE | re.DOTALL)
            if table_match:
                e_dict = {}
                for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', table_match.group(1), re.IGNORECASE | re.DOTALL):
                    tds = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.IGNORECASE | re.DOTALL)
                    if len(tds) >= 4:
                        title, name, ratio_str = re.sub(r'<[^>]+>', '', tds[0]).strip(), re.sub(r'<[^>]+>', '', tds[1]).strip(), re.sub(r'<[^>]+>', '', tds[3]).replace('%', '').strip()
                        if ('董' in title or '監' in title) and '辭' not in title and '職稱' not in title:
                            try: e_dict[name.split('-')[0].strip()] = max(e_dict.get(name.split('-')[0].strip(), 0), float(ratio_str))
                            except: pass
                if 0 < sum(e_dict.values()) < 100: return {}, round(sum(e_dict.values()), 2), "富邦精算", []
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
# 📌 模組一：V26.7 指紋識別與除水雷達
# ==========================================
def get_v25_broker_intelligence(df_raw):
    if df_raw.empty: return {}, pd.DataFrame()
    df = df_raw.copy()
    df['date'] = pd.to_datetime(df['date'])
    df['b_vol'] = (pd.to_numeric(df['buy'], errors='coerce').fillna(0) / 1000).astype(int)
    df['s_vol'] = (pd.to_numeric(df['sell'], errors='coerce').fillna(0) / 1000).astype(int)
    tags, d_rows = {}, []
    for trader, g in df.sort_values(['securities_trader', 'date']).groupby('securities_trader'):
        tb, ts = g['b_vol'].sum(), g['s_vol'].sum()
        tv = tb + ts
        dr = (min(tb, ts) * 2) / tv if tv > 0 else 0
        g['net'] = g['b_vol'] - g['s_vol']
        buy_days = g[g['net'] > 50]
        f_dump, h_tot = 0, buy_days['net'].sum()
        for _, r in buy_days.iterrows():
            fut = g[(g['date'] > r['date']) & (g['date'] <= r['date'] + pd.Timedelta(days=3)) & (g['net'] < 0)]
            if not fut.empty: f_dump += abs(fut['net'].sum())
        fr = f_dump / h_tot if h_tot > 0 else 0
        loy = (tb - ts) / tb if tb > 0 else 0
        
        tag = "🔵 一般"
        if any(x in trader for x in ["台銀", "土銀", "彰銀", "第一", "兆豐", "華南", "合庫", "台企銀"]): tag = "🏦 [官股]"
        elif dr > 0.85 and tv > 1000: tag = "🌪️ [當沖客]"
        elif fr > 0.70 and h_tot > 200: tag = "⚡ [隔日沖]"
        elif g['date'].nunique() >= 12 and loy > 0.7: tag = "📈 [波段主]"
        elif tb > 1000 and loy > 0.85: tag = "🧱 [真鎖碼]"
        tags[trader] = tag
        if tb > 100 or ts > 100: d_rows.append({"分點名稱": trader, "最終標籤": tag, "總買(張)": tb, "總賣(張)": ts, "淨留倉": int(h_tot), "當沖率": round(dr*100, 1), "隔日賣出率": round(fr*100, 1)})
    return tags, pd.DataFrame(d_rows).sort_values('總買(張)', ascending=False)

def get_smart_threshold(price, capital_bn, dead_float):
    if pd.isna(price) or price <= 0: return 1000 
    rt = max((max(3000, capital_bn * 500) * 10000) / (price * 1000), (capital_bn * 10000) * (max(0.1, 0.5 * (100 - dead_float) / 100) / 100))
    al = min([100, 200, 400, 600, 800, 1000], key=lambda x: abs(x - rt))
    return min(al, 400) if price < 30 else al

def process_v25_ultimate_radar(df_wide, dead_chip_input, dynamic_dict, static_val, df_price, df_branch_raw, intel_tags):
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
            fn = df_f[df_f['tag'] == "⚡ [隔日沖]"]
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
    # 【語意優化】：將變數名稱改為白話文
    df['純淨大戶變動(%)'], df['隔日沖虛胖(%)'], df['V26.7_雷達診斷'] = ddf['純淨變動'], ddf['雜訊'], ddf['診斷']
    return df[['日期', '收盤價(元)', '總人數變動率(%)', '原始大戶變動(%)', '純淨大戶變動(%)', '隔日沖虛胖(%)', 'V26.7_雷達診斷']].sort_values('日期', ascending=False), pd.DataFrame(d_math), pd.DataFrame(d_fri)

# ==========================================
# 📌 模組二：V26.7 平日戰情追蹤矩陣 (語意優化版)
# ==========================================
def process_v26_daily_tracking(df_branch_raw, intel_tags, df_price, df_branch_diff, actual_dates):
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
            nn = df_d[df_d['tag'].str.contains('隔日沖')]['net_vol'].sum()
        adv = []
        if sn > 50 and bsd < 0: adv.append("🟢 主力吃貨/籌碼集中")
        elif sn < -100: adv.append("🔴 波段大戶撤退")
        if nn > 300: adv.append("⚠️ 短線隔日沖進駐")
        if bsd > 100: adv.append("📉 散戶進場接刀")
        # 【語意優化】：修改欄位名稱為實戰語言
        out.append({"日期": d, "收盤價(元)": cp, "漲跌(元)": sp, "波段/官股淨流入(張)": int(sn), "隔日沖潛在賣壓(張)": int(nn), "買賣家數差": bsd, "單日微觀診斷": " | ".join(adv) if adv else "無明顯特徵"})
    return pd.DataFrame(out)

# ==========================================
# 📌 資料處理與排版 (數學自算比例版維持不變)
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
        # 【語意優化】
        out.append({"日期": row['日期'], "收盤價(元)": p, "股本(億)": round(cap, 2), "大戶精算門檻": f"系統判定 ({int(ct)}張)", "大戶原持股(%)": round(lp, 2), "死籌碼(%)": f"{float(cur_dead):.2f}% ({cl})" if cur_dead > 0 else "-", "純淨活大戶C_Value(%)": cd, "實戰判定": st})
    return pd.DataFrame(out)

def process_branch_v25(df_raw, period, actual_dates, intel_tags):
    if df_raw.empty: return pd.DataFrame()
    df = df_raw[df_raw['date'].isin(actual_dates[:period])].copy()
    df['bv'], df['sv'] = (df['buy'] / 1000).astype(int), (df['sell'] / 1000).astype(int)
    g = df.groupby('securities_trader')[['bv', 'sv']].sum().reset_index()
    g['net'] = g['bv'] - g['sv']
    b = g[g['net'] > 0].sort_values('net', ascending=False).head(15).reset_index(drop=True)
    s = g[g['net'] < 0].sort_values('net', ascending=True).head(15).reset_index(drop=True)
    out, tv = [], g['bv'].sum() if g['bv'].sum() > 0 else 1
    for i in range(15):
        r = {}
        if i < len(b): r["買超分點"] = f"{intel_tags.get(b.loc[i,'securities_trader'],'🔵')} {b.loc[i,'securities_trader']}"; r["買超(張)"] = int(b.loc[i,'net']); r["佔比"] = f"{(b.loc[i,'net']/tv)*100:.1f}%"
        else: r["買超分點"] = "-"; r["買超(張)"] = 0; r["佔比"] = "-"
        if i < len(s): r["賣超分點"] = f"{intel_tags.get(s.loc[i,'securities_trader'],'🔵')} {s.loc[i,'securities_trader']}"; r["賣超(張)"] = abs(int(s.loc[i,'net'])); r["佔比_"] = f"{(abs(s.loc[i,'net'])/tv)*100:.1f}%"
        else: r["賣超分點"] = "-"; r["賣超(張)"] = 0; r["佔比_"] = "-"
        out.append(r)
    return pd.DataFrame(out)

def process_branch_diff(df_raw, actual_dates):
    if df_raw.empty or not actual_dates: return pd.DataFrame()
    out = []
    for d in actual_dates[:10]:
        df_d = df_raw[df_raw['date'] == d]
        if df_d.empty: continue
        out.append({"日期": d, "買進家數": df_d[df_d['buy'] > 0]['securities_trader'].nunique(), "賣出家數": df_d[df_d['sell'] > 0]['securities_trader'].nunique(), "買賣家數差": df_d[df_d['buy'] > 0]['securities_trader'].nunique() - df_d[df_d['sell'] > 0]['securities_trader'].nunique()})
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
            p_dates.append(f"{py}-{pts[1]}-{pts[2]}")
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
        if col in df_out.columns: df_out[col.replace('股數', '張數')] = (pd.to_numeric(df_out[col], errors='coerce').fillna(0) / 1000).round().astype(int); df_out = df_out.drop(columns=[col])
    return df_out[['日期'] + [c for c in df_out.columns if '張數' in c or '率' in c]].tail(10).sort_values('日期', ascending=False)

def process_margin(df):
    if df.empty: return pd.DataFrame()
    for c in ["MarginPurchaseBuy", "MarginPurchaseSell", "MarginPurchaseCashRepayment", "MarginPurchaseTodayBalance", "MarginPurchaseYesterdayBalance", "ShortSaleBuy", "ShortSaleSell", "ShortSaleCashRepayment", "ShortSaleTodayBalance", "OffsetLoanAndShort", "ShortSaleYesterdayBalance"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).round().astype(int)
    df = df.rename(columns={"date":"日期", "MarginPurchaseBuy":"融資買進(萬元)", "MarginPurchaseSell":"融資賣出(萬元)", "MarginPurchaseCashRepayment":"融資現償(萬元)", "MarginPurchaseTodayBalance":"融資餘額(萬元)", "ShortSaleBuy":"融券買進(張)", "ShortSaleSell":"融券賣出(張)", "ShortSaleTodayBalance":"融券餘額(張)", "OffsetLoanAndShort":"資券相抵(張)"})
    df['融資增減(萬元)'] = df['融資餘額(萬元)'] - df.get('MarginPurchaseYesterdayBalance', 0)
    df['融券增減(張)'] = df['融券餘額(張)'] - df.get('ShortSaleYesterdayBalance', 0)
    return df[['日期','融資買進(萬元)','融資賣出(萬元)','融資現償(萬元)','融資餘額(萬元)','融資增減(萬元)','融券買進(張)','融券賣出(張)','融券餘額(張)','融券增減(張)','資券相抵(張)']].tail(10).sort_values('日期', ascending=False)

def process_inst(df):
    if df.empty: return pd.DataFrame()
    pdf = df.pivot_table(index='date', columns='name', values=['buy', 'sell'], fill_value=0).reset_index()
    pdf.columns = ['_'.join(c).strip('_') for c in pdf.columns.values]
    out = pd.DataFrame({'日期': pdf['date']})
    f_b = pd.to_numeric(pdf.get('buy_Foreign_Investor',0), errors='coerce').fillna(0) + pd.to_numeric(pdf.get('buy_Foreign_Dealer_Self',0), errors='coerce').fillna(0)
    f_s = pd.to_numeric(pdf.get('sell_Foreign_Investor',0), errors='coerce').fillna(0) + pd.to_numeric(pdf.get('sell_Foreign_Dealer_Self',0), errors='coerce').fillna(0)
    out['外資買賣超(張)'] = ((f_b - f_s) / 1000).round().astype(int)
    i_b = pd.to_numeric(pdf.get('buy_Investment_Trust',0), errors='coerce').fillna(0); i_s = pd.to_numeric(pdf.get('sell_Investment_Trust',0), errors='coerce').fillna(0)
    out['投信買賣超(張)'] = ((i_b - i_s) / 1000).round().astype(int)
    d_b = pd.to_numeric(pdf.get('buy_Dealer_self',0), errors='coerce').fillna(0) + pd.to_numeric(pdf.get('buy_Dealer_Hedging',0), errors='coerce').fillna(0)
    d_s = pd.to_numeric(pdf.get('sell_Dealer_self',0), errors='coerce').fillna(0) + pd.to_numeric(pdf.get('sell_Dealer_Hedging',0), errors='coerce').fillna(0)
    out['自營買賣超(張)'] = ((d_b - d_s) / 1000).round().astype(int)
    out['三大法人買賣超(張)'] = out['外資買賣超(張)'] + out['投信買賣超(張)'] + out['自營買賣超(張)']
    return out.tail(10).sort_values('日期', ascending=False)

def process_fut_inst(df):
    if df.empty: return pd.DataFrame()
    df['net'] = pd.to_numeric(df['long_open_interest_balance_volume'], errors='coerce').fillna(0) - pd.to_numeric(df['short_open_interest_balance_volume'], errors='coerce').fillna(0)
    pdf = df.pivot_table(index='date', columns='institutional_investors', values='net', fill_value=0).reset_index()
    pdf.columns.name = None
    for col in ['Foreign_Investor', 'Investment_Trust', 'Dealer']:
        if col not in pdf.columns: pdf[col] = 0
    return pdf.rename(columns={'date': '日期', 'Foreign_Investor': '外資多空(口)', 'Investment_Trust': '投信多空(口)', 'Dealer': '自營多空(口)'}).tail(10).sort_values('日期', ascending=False)

def process_per(df):
    if df.empty: return pd.DataFrame()
    df_out = df.copy().rename(columns={"date":"日期","dividend_yield":"殖利率(%)","PER":"本益比(倍)","PBR":"淨值比(倍)"})
    for col in ["殖利率(%)", "本益比(倍)", "淨值比(倍)"]: df_out[col] = pd.to_numeric(df_out[col], errors='coerce').round(2)
    return df_out[['日期', '本益比(倍)', '淨值比(倍)', '殖利率(%)']].tail(10).sort_values('日期', ascending=False)

def process_disp(df):
    if df.empty: return pd.DataFrame()
    df_out = df.copy().rename(columns={"date":"公告日期","disposition_cnt":"處置次數","condition":"處置條件","measure":"處置措施","period_start":"處置起日","period_end":"處置迄日"})
    return df_out[['公告日期', '處置次數', '處置起日', '處置迄日', '處置條件', '處置措施']].tail(5).sort_values('公告日期', ascending=False)

def process_div(df):
    if df.empty: return pd.DataFrame()
    df_out = df.rename(columns={"date": "公告日期", "year": "股利年份", "StockEarningsDistribution": "盈餘配股(元)", "StockStatutorySurplus": "公積配股(元)", "CashEarningsDistribution": "盈餘配息(元)", "CashStatutorySurplus": "公積配息(元)"})
    cols = [c for c in ["公告日期", "股利年份", "盈餘配息(元)", "公積配息(元)", "盈餘配股(元)", "公積配股(元)"] if c in df_out.columns]
    if '股利年份' in df_out.columns:
        df_out['股利年份'] = pd.to_numeric(df_out['股利年份'], errors='coerce')
        recent = sorted(df_out['股利年份'].dropna().unique(), reverse=True)[:5]
        return df_out[df_out['股利年份'].isin(recent)][cols].sort_values(['公告日期'], ascending=[False])
    return df_out[cols].sort_values('公告日期', ascending=False).head(10)

def process_cbas(df):
    if df.empty: return pd.DataFrame()
    df_out = df.rename(columns={"date": "日期", "cb_id": "可轉債代號", "cb_name": "可轉債名稱", "ConversionPrice": "轉換價(元)", "PriceOfUnderlyingStock": "標的股價(元)", "OutstandingAmount": "未償還餘額", "CouponRate": "票面利率(%)"})
    cols = [c for c in ["日期", "可轉債代號", "可轉債名稱", "轉換價(元)", "標的股價(元)", "未償還餘額", "票面利率(%)"] if c in df_out.columns]
    return df_out[cols]

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
        left_cols = [c for c in df.columns if any(kw in str(c) for kw in ['日期', '分點', '名稱', '姓名', '身份別', '質權人', '交易別', '診斷', '判定', '門檻', '條件', '措施', '契約', '代號', '來源', '標籤', '單日微觀診斷'])]
        right_cols = [c for c in df.columns if c not in left_cols]
        styler = df.style.format(f_dict).set_properties(**{'text-align': 'right !important'}, subset=right_cols)
        if left_cols: styler = styler.set_properties(**{'text-align': 'left !important'}, subset=left_cols)
        try: styler = styler.hide(axis="index")
        except: styler = styler.hide_index()
        html = styler.set_table_styles([dict(selector='th', props=[('text-align', 'center !important')]), dict(selector='table', props=[('width', '100%')])]).to_html()
        if custom_class: html = html.replace('<table', f'<table class="{custom_class}"')
        st.markdown(html, unsafe_allow_html=True)

def format_to_csv_string(df, title):
    header = f"▼▼▼ {title} ▼▼▼\n"
    if df is None or df.empty: return header + "此區塊查無最新數據或無發行紀錄\n"
    return header + df.to_csv(index=False) + "\n"

# ==========================================
# 📌 執行主引擎
# ==========================================
if run_btn:
    with st.spinner(f"正在執行 V26.7 全息除水引擎 (語意與字典優化版)..."):
        name = get_stock_name(user_stock_id)
        df_p_raw = fetch_fm("TaiwanStockPrice", (datetime.date.today() - datetime.timedelta(days=1095)).strftime("%Y-%m-%d"), user_stock_id)
        if df_p_raw.empty: st.error("查無股價"); st.stop()
        
        dates = sorted(df_p_raw['date'].unique().tolist(), reverse=True)
        d_60 = dates[59] if len(dates) >= 60 else dates[-1]
        df_price = process_price(df_p_raw)
        dynamic_dict, s_val, chip_eng, _ = scrape_director_holding(user_stock_id)
        
        df_b_raw = fetch_fm_branch_fast_parallel(dates[:60], user_stock_id)
        tags, df_debug_tags = get_v25_broker_intelligence(df_b_raw)
        df_b_diff = process_branch_diff(df_b_raw, dates)
        
        df_s_raw = fetch_fm("TaiwanStockHoldingSharesPer", d_60, user_stock_id)
        df_s_wide, df_s_unit, df_s_ppl = process_tdcc(df_s_raw)
        df_s_dyn = process_tdcc_dynamic(df_s_wide, df_price, dead_chip_input, dynamic_dict, s_val, chip_eng)
        df_v26_radar, df_debug_math, df_debug_friday = process_v25_ultimate_radar(df_s_wide, dead_chip_input, dynamic_dict, s_val, df_price, df_b_raw, tags)
        df_daily_tracker = process_v26_daily_tracking(df_b_raw, tags, df_price, df_b_diff, dates)

        df_twse, _ = scrape_block_trades(user_stock_id, dates)
        df_margin = process_margin(fetch_fm("TaiwanStockMarginPurchaseShortSale", d_60, user_stock_id))
        df_day_trade = process_day_trading(fetch_fm("TaiwanStockDayTrading", d_60, user_stock_id))
        df_inst = process_inst(fetch_fm("TaiwanStockInstitutionalInvestorsBuySell", d_60, user_stock_id))
        
        df_rev_raw = fetch_fm("TaiwanStockMonthRevenue", "2022-01-01", user_stock_id)
        df_rev = pd.DataFrame()
        if not df_rev_raw.empty:
            df_rev_raw['營收月份'] = df_rev_raw['revenue_year'].astype(str) + "-" + df_rev_raw['revenue_month'].astype(str).str.zfill(2)
            df_rev = df_rev_raw.rename(columns={"revenue":"月營收(百萬元)"})[['營收月份','月營收(百萬元)']].tail(24)
            df_rev['月營收(百萬元)'] = (df_rev['月營收(百萬元)']/1000000).round().astype(int)
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

        # 【精算市值】
        market_cap_str = "計算中..."
        industry, address = get_company_profile(user_stock_id)
        if not df_price.empty and not df_s_wide.empty:
            market_cap_str = f"{(df_price['收盤價(元)'].iloc[0] * df_s_wide['總張數'].iloc[0]) / 100000:,.2f} 億"
        company_info_text = f"🏢 **【產業】** {industry} ｜ 💰 **【市值】** {market_cap_str} ｜ 📍 **【公司地址 (地緣核對)】** {address}"

        # --- 頁面呈現 ---
        st.subheader(f"📊 {user_stock_id} {name} V26.7 全息戰報")
        st.markdown(f"<div class='info-box'>{company_info_text}</div>", unsafe_allow_html=True)
        show_table("⚡ 0. 平日戰情追蹤矩陣 (週一至週四核心代理指標)", df_daily_tracker, "daily-tracker")
        show_table("1-1. 雙軸活大戶鎖碼判定表 (C-Value) (近8週)", df_s_dyn)
        show_table("1-2. V26.7 專家診斷雷達 (週末除水版) (近8週)", df_v26_radar, "radar-table")
        show_table("2-1. 集保分級 - 張數表 (近8週)", df_s_unit)
        show_table("2-2. 集保分級 - 人數表 (近8週)", df_s_ppl)
        if df_twse.empty: st.markdown("#### 3. 鉅額交易明細 (近3日)"); st.warning("無鉅額交易")
        else: show_table("3. 鉅額交易明細 (近3日)", df_twse)
        show_table("4. 散戶資券餘額 (近10天)", df_margin)
        show_table("5. 現股當沖明細 (近10天)", df_day_trade)
        show_table("6. 法人買賣超 (近10天)", df_inst)
        show_table("7. 收盤價量 (近10天)", df_price.head(10))
        show_table("8. 月營收 (百萬元) (近24個月)", df_rev)
        show_table(f"9-1. 主力分點 - 今日 ({dates[0]}) [指紋辨識]", df_b_today)
        show_table(f"9-2. 主力分點 - 前一日 ({dates[1] if len(dates)>1 else '無'}) [指紋辨識]", df_b_prev1)
        show_table("9-3. 主力分點 - 近3日 [指紋辨識]", df_b_3)
        show_table("9-4. 主力分點 - 近10日 [指紋辨識]", df_b_10)
        show_table("9-5. 主力分點 - 近20日 [指紋辨識]", df_b_20)
        show_table("9-6. 主力分點 - 近30日 [指紋辨識]", df_b_30)
        show_table("9-7. 主力分點 - 近60日 [指紋辨識]", df_b_60)
        show_table("10. 八大官股進出 (今日)", df_gov)
        show_table("11. 買賣家數差明細 (近10天)", df_b_diff)
        st.markdown("#### 12. 董監大股東質設明細")
        if df_p_det.empty: st.warning("此區塊查無數據")
        else:
            if not df_p_sum.empty: st.markdown(df_p_sum.to_html(index=False, border=1), unsafe_allow_html=True)
            st.markdown(df_p_det.to_html(index=False, border=1), unsafe_allow_html=True)
        show_table("13. 台指期貨三大法人未平倉 (大盤) (近10天)", df_fut)
        show_table("14. 歷年股利 (近5年)", df_div)
        show_table("15. 本益比、淨值比與殖利率 (近10天)", df_per)
        show_table("16. 處置有價證券狀態", df_disp)
        show_table("17. CBAS 可轉債數據", df_cbas)

        st.divider()
        with st.expander("🛠️ 【開發者專用】V26.7 演算法稽核中心", expanded=False):
            st.markdown("<h5 class='debug-header'>1. 分點指紋圖鑑</h5>", unsafe_allow_html=True)
            st.dataframe(df_debug_tags)
            st.markdown("<h5 class='debug-header'>2. 除水驗算公式</h5>", unsafe_allow_html=True)
            st.dataframe(df_debug_math)

        st.divider()
        with st.expander("📋 【點擊展開：給 Gemini 的 V26.7 量化分析與稽核資料包 (CSV格式)】", expanded=True):
            p = f"請分析標的: {user_stock_id} {name} (V26.7 量化籌碼)\n"
            p += f"{company_info_text}\n\n"
            p += format_to_csv_string(df_daily_tracker, "0. 平日戰情追蹤矩陣 (近5日)")
            p += format_to_csv_string(df_s_dyn.head(8), "1-1. 雙軸活大戶鎖碼判定表 (C-Value)")
            p += format_to_csv_string(df_v26_radar.head(8), "1-2. V26.7 專家診斷雷達 (週末除水版)")
            p += format_to_csv_string(df_twse, "3. 鉅額交易明細 (近3日)")
            p += format_to_csv_string(df_margin, "4. 散戶資券餘額 (近10天)")
            p += format_to_csv_string(df_inst, "6. 法人買賣超 (近10天)")
            p += format_to_csv_string(df_price.head(10), "7. 收盤價量 (近10天)")
            p += format_to_csv_string(df_b_today, f"9-1. 主力分點 - 今日 ({dates[0]})")
            p += format_to_csv_string(df_b_60, "9-7. 主力分點 - 近60日")
            p += "\n\n【稽核專區 - 供 AI 驗算邏輯正確性】\n"
            p += format_to_csv_string(df_debug_tags.head(30), "稽核A：前30大分點指紋數據")
            p += format_to_csv_string(df_debug_math, "稽核B：除水還原數學驗算表")
            p += "\n請幫我結合『V26.7 名詞定義』與上列數據，給出最新的實戰操作建議。"
            st.code(p, language="text")
