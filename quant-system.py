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
st.set_page_config(page_title="V25.2 終極全息量化系統", layout="wide")

# 內建 Token
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

# 注入全局 CSS
st.markdown("""
<style>
table.dataframe th, table.dataframe td { white-space: nowrap !important; text-align: center !important; }
.radar-table td:last-child { text-align: left !important; color: #ff4b4b; font-weight: bold; }
.debug-header { color: #f63366; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🤖 交易員實戰手冊：V25.2 全息量化除水系統")
st.caption("核心功能：指紋識別、數據除水、技術位階、CSV 稽核資料包")

# UI 輸入區
col1, col2 = st.columns([1, 1])
with col1:
    user_stock_id = st.text_input("個股代號", value="8027")
with col2:
    dead_chip_input = st.text_input("死籌碼 %", placeholder="留空自動計算")

run_btn = st.button("🚀 啟動 V25.2 引擎：擷取資料並產生稽核包", use_container_width=True)

st.divider()

# ==========================================
# 工具函式
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def get_stock_name(target_id):
    try:
        res = requests.get(f"https://tw.stock.yahoo.com/quote/{target_id}.TW", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        match = re.search(r'<title>(.*?)\s*\(', res.text)
        return match.group(1).strip() if match else ""
    except: return ""

def safe_get_fubon(url):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        if hasattr(ssl, 'OP_LEGACY_SERVER_CONNECT'):
            ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            return response.read().decode('big5', errors='ignore')
    except: return ""

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fm(dataset, start_date, target_id=None, end_date=None):
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {"dataset": dataset, "start_date": start_date}
    if target_id: params["data_id"] = target_id
    if end_date: params["end_date"] = end_date
    headers = {"Authorization": f"Bearer {FINMIND_TOKEN}"}
    try:
        res = requests.get(url, params=params, headers=headers, timeout=15).json()
        return pd.DataFrame(res.get("data", []))
    except: return pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def scrape_director_holding(target_id):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        url_good = f"https://goodinfo.tw/tw/StockDirectorSharehold.asp?STOCK_ID={target_id}"
        h = headers.copy(); h["Referer"] = f"https://goodinfo.tw/tw/StockDetail.asp?STOCK_ID={target_id}"; h["Cookie"] = "CLIENT_KEY=20260412;" 
        res = requests.get(url_good, headers=h, timeout=8)
        if res.status_code == 200:
            res.encoding = 'utf-8'
            dfs = pd.read_html(StringIO(res.text))
            for df in dfs:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = ['_'.join(str(c) for c in col if 'Unnamed' not in str(c)).strip('_') for col in df.columns.values]
                else: df.columns = df.columns.astype(str)
                target_col = next((c for c in df.columns if '全體董監持股' in str(c) and '持股(%)' in str(c)), None)
                month_col = next((c for c in df.columns if '月別' in str(c)), None)
                if target_col and month_col:
                    d_dict = {}
                    for _, row in df.iterrows():
                        m, v = str(row[month_col]).strip(), str(row[target_col]).strip()
                        if re.match(r'^\d{4}-\d{2}$', m) and v not in ['-', '', 'nan']:
                            d_dict[m] = float(v)
                    if d_dict: return d_dict, list(d_dict.values())[0], "Goodinfo", []
    except: pass
    return {}, 0.0, "失敗", []

def get_dead_chip_info(date_str, dead_chip_input, dynamic_dict, static_val, chip_engine):
    if dead_chip_input and str(dead_chip_input).strip() != "":
        try: return float(str(dead_chip_input).replace('%', '').strip()), "手動"
        except: pass
    month_key = str(date_str)[:7].replace('/', '-')
    if dynamic_dict and month_key in dynamic_dict: return dynamic_dict[month_key], "Goodinfo當月"
    if dynamic_dict: return list(dynamic_dict.values())[0], "Goodinfo最新"
    return (static_val, chip_engine) if static_val > 0 else (0.0, "-")

# ==========================================
# 📌 V25.2 指紋識別模組 (強化嚴格分類)
# ==========================================
def get_v25_broker_intelligence(df_raw):
    if df_raw.empty: return {}, pd.DataFrame()
    df = df_raw.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['securities_trader', 'date'])
    df['b_vol'] = (pd.to_numeric(df['buy'], errors='coerce').fillna(0) / 1000).astype(int)
    df['s_vol'] = (pd.to_numeric(df['sell'], errors='coerce').fillna(0) / 1000).astype(int)
    
    tags, debug_rows = {}, []
    govs = ["台銀", "土銀", "彰銀", "第一", "兆豐", "華南", "合庫", "台企銀"]
    
    for trader, group in df.groupby('securities_trader'):
        t_buy, t_sell = group['b_vol'].sum(), group['s_vol'].sum()
        days = group['date'].nunique()
        total_v = t_buy + t_sell
        day_ratio = (min(t_buy, t_sell) * 2) / total_v if total_v > 0 else 0
        
        group['net_day'] = group['b_vol'] - group['s_vol']
        buy_days = group[group['net_day'] > 50]
        flipper_dump, hold_total = 0, buy_days['net_day'].sum()
        
        for idx, row in buy_days.iterrows():
            future = group[(group['date'] > row['date']) & (group['date'] <= row['date'] + pd.Timedelta(days=3)) & (group['net_day'] < 0)]
            if not future.empty: flipper_dump += abs(future['net_day'].sum())
                
        flip_rate = flipper_dump / hold_total if hold_total > 0 else 0
        loyalty = (t_buy - t_sell) / t_buy if t_buy > 0 else 0
        
        tag = "🔵 一般"
        if any(g in trader for g in govs): tag = "🏦 [官股]"
        elif day_ratio > 0.85 and total_v > 1000: tag = "🌪️ [當沖客]"
        elif flip_rate > 0.70 and hold_total > 200: tag = "⚡ [隔日沖]"
        elif days >= 12 and loyalty > 0.7: tag = "📈 [波段主]"
        elif t_buy > 1000 and loyalty > 0.85: tag = "🧱 [真鎖碼]"
        
        tags[trader] = tag
        if t_buy > 100 or t_sell > 100:
            debug_rows.append({"分點名稱": trader, "最終標籤": tag, "總買(張)": t_buy, "總賣(張)": t_sell, "淨留倉": int(hold_total), "當沖率": round(day_ratio*100, 1), "隔日賣出率": round(flip_rate*100, 1)})
            
    return tags, pd.DataFrame(debug_rows).sort_values('總買(張)', ascending=False)

# ==========================================
# 📌 V25.2 除水雷達與 CSV 驗算模組
# ==========================================
def process_v25_ultimate_radar(df_wide, dead_chip_input, dynamic_dict, static_val, df_price, df_branch_raw, intel_tags):
    if df_wide.empty or len(df_wide) < 2: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    df = df_wide.sort_values('日期', ascending=True).copy()
    df['dt_end'] = pd.to_datetime(df['日期'])
    df_p = df_price.copy()
    if not df_p.empty:
        df_p['dt'] = pd.to_datetime(df_p['日期'])
        df_p_s = df_p.sort_values('dt')
        df_p_s['ma20'] = df_p_s['收盤價(元)'].rolling(20).mean()
        df = pd.merge_asof(df.sort_values('dt_end'), df_p_s[['dt', '收盤價(元)', 'ma20']], left_on='dt_end', right_on='dt', direction='backward')
        
    df['1000張變動(%)'] = df['1000張以上_比例(%)'].diff().round(2)
    df['總人數變動率(%)'] = (df['總人數(人)'].pct_change() * 100).round(2)
    df['作戰區變動(%)'] = (df['200-400張_比例(%)']+df['400-600張_比例(%)']+df['600-800張_比例(%)']).diff().round(2)
    
    out_diag, debug_math, debug_friday = [], [], []
    for i, row in df.iterrows():
        if pd.isna(row['1000張變動(%)']):
            out_diag.append({"真實變動": 0, "雜訊": 0, "診斷": "⚪ 初始化"}); continue
        
        d_str = row['日期']
        df_f = df_branch_raw[df_branch_raw['date'] == d_str]
        f_vol = 0
        if not df_f.empty:
            df_f = df_f.copy(); df_f['tag'] = df_f['securities_trader'].map(intel_tags)
            f_noise = df_f[df_f['tag'] == "⚡ [隔日沖]"]
            f_vol = f_noise['buy'].sum() / 1000
            for _, fr in f_noise.iterrows():
                if fr['buy'] > 0: debug_friday.append({"日期": d_str, "分點": fr['securities_trader'], "張數": int(fr['buy']/1000)})
        
        f_impact = (f_vol / row['總張數']) * 100 if row['總張數'] > 0 else 0
        pure_chg = round(row['1000張變動(%)'] - f_impact, 2)
        debug_math.append({"日期": d_str, "原始變動": row['1000張變動(%)'], "隔日沖干擾": round(f_impact, 2), "純淨變動": pure_chg})
        
        dead, _ = get_dead_chip_info(d_str, dead_chip_input, dynamic_dict, static_val, "")
        lev = 100 / (100 - dead) if 0 < dead < 100 else 1
        max_i = max(abs(pure_chg * lev), abs(row['作戰區變動(%)'] * lev))
        
        advice = []
        if row['總人數變動率(%)'] > 2.0 and pure_change < 0: advice.append("💀 [逃命]")
        else:
            if pure_chg * lev > 2.5 and row['收盤價(元)'] > row['ma20']: advice.append("🚀 [真·軋空]")
            elif pure_chg > 0.4 and row['收盤價(元)'] < row['ma20']: advice.append("🧱 [底位建倉]")
            if f_impact > 1.2: advice.append(f"⚡ [隔日沖陷阱]")
        
        out_diag.append({"真實變動": pure_chg, "雜訊": round(f_impact, 2), "診斷": " | ".join(advice) if advice else "🔵 盤整"})

    diag_df = pd.DataFrame(out_diag)
    df['真實大戶變動(%)'], df['隔日沖雜訊(%)'], df['V25.2_專家診斷'] = diag_df['真實變動'], diag_df['雜訊'], diag_df['診斷']
    return df[['日期', '收盤價(元)', '總人數變動率(%)', '1000張變動(%)', '真實大戶變動(%)', '隔日沖雜訊(%)', 'V25.2_專家診斷']].sort_values('日期', ascending=False), pd.DataFrame(debug_math), pd.DataFrame(debug_friday)

# ==========================================
# 其他處理函式 (與原版相同)
# ==========================================
def process_price(df):
    if df.empty: return pd.DataFrame()
    df_out = df.copy()
    df_out['Trading_Volume'] = (pd.to_numeric(df_out['Trading_Volume'], errors='coerce').fillna(0) / 1000).round().astype(int)
    df_out = df_out.rename(columns={"date":"日期","Trading_Volume":"成交量(張)","close":"收盤價(元)","spread":"漲跌(元)"})
    return df_out[['日期','成交量(張)','收盤價(元)','漲跌(元)']].sort_values('日期', ascending=False)

def process_tdcc(df):
    if df.empty: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df = df[~df['HoldingSharesLevel'].astype(str).str.contains('差異數')]
    df['unit'] = (pd.to_numeric(df.get('unit', 0), errors='coerce').fillna(0) / 1000).round().astype(int)
    p_unit = df.pivot_table(index='date', columns='HoldingSharesLevel', values='unit', aggfunc='first').fillna(0)
    p_ppl = df.pivot_table(index='date', columns='HoldingSharesLevel', values='people', aggfunc='first').fillna(0)
    p_pct = df.pivot_table(index='date', columns='HoldingSharesLevel', values='percent', aggfunc='first').fillna(0)
    
    res = pd.DataFrame({'日期': p_unit.index})
    res['總張數'] = p_unit.sum(axis=1).values
    res['總人數(人)'] = p_ppl.sum(axis=1).values
    res['1000張以上_比例(%)'] = p_pct.iloc[:, -1].values
    res['200-400張_比例(%)'] = p_pct.iloc[:, 10].values
    res['400-600張_比例(%)'] = p_pct.iloc[:, 11].values
    res['600-800張_比例(%)'] = p_pct.iloc[:, 12].values
    res['200-400張_人數'] = p_ppl.iloc[:, 10].values
    res['200-400張_張數'] = p_unit.iloc[:, 10].values
    return res.sort_values('日期', ascending=False), p_unit, p_ppl

def process_branch_v25(df_raw, period, actual_dates, intel_tags):
    if df_raw.empty: return pd.DataFrame()
    df = df_raw[df_raw['date'].isin(actual_dates[:period])].copy()
    df['bv'] = (df['buy'] / 1000).astype(int); df['sv'] = (df['sell'] / 1000).astype(int)
    g = df.groupby('securities_trader')[['bv', 'sv']].sum().reset_index()
    g['net'] = g['bv'] - g['sv']
    b = g[g['net'] > 0].sort_values('net', ascending=False).head(15).reset_index(drop=True)
    s = g[g['net'] < 0].sort_values('net', ascending=True).head(15).reset_index(drop=True)
    out = []
    for i in range(15):
        row = {}
        if i < len(b): row["買超分點"] = f"{intel_tags.get(b.loc[i,'securities_trader'],'🔵')} {b.loc[i,'securities_trader']}"; row["買超(張)"] = int(b.loc[i,'net'])
        else: row["買超分點"] = "-"; row["買超(張)"] = 0
        if i < len(s): row["賣超分點"] = f"{intel_tags.get(s.loc[i,'securities_trader'],'🔵')} {s.loc[i,'securities_trader']}"; row["賣超(張)"] = abs(int(s.loc[i,'net']))
        else: row["賣超分點"] = "-"; row["賣超(張)"] = 0
        out.append(row)
    return pd.DataFrame(out)

# ==========================================
# 📌 執行引擎
# ==========================================
if run_btn:
    with st.spinner(f"正在執行 V25.2 除水引擎..."):
        name = get_stock_name(user_stock_id)
        df_p_raw = fetch_fm("TaiwanStockPrice", "2023-01-01", user_stock_id)
        if df_p_raw.empty: st.error("查無股價"); st.stop()
        
        dates = sorted(df_p_raw['date'].unique().tolist(), reverse=True)
        df_price = process_price(df_p_raw)
        dynamic_dict, s_val, chip_eng, _ = scrape_director_holding(user_stock_id)
        
        # 抓 60 天分點
        df_b_raw = fetch_fm_branch_fast_parallel(dates[:60], user_stock_id)
        tags, df_debug_tags = get_v25_broker_intelligence(df_b_raw)
        
        # 集保與雷達
        df_s_raw = fetch_fm("TaiwanStockHoldingSharesPer", dates[60], user_stock_id)
        df_s_wide, _, _ = process_tdcc(df_s_raw)
        df_v25_radar, df_debug_math, df_debug_friday = process_v25_ultimate_radar(df_s_wide, dead_chip_input, dynamic_dict, s_val, df_price, df_b_raw, tags)

        # 頁面呈現
        st.subheader(f"📊 {user_stock_id} {name} V25.2 全息戰報")
        st.markdown("#### ▼▼▼ 1. V25.2 專家診斷雷達 (除水版) ▼▼▼")
        st.table(df_v25_radar.head(8))
        
        st.markdown("#### ▼▼▼ 2. 主力分點 - 近60日 (指紋標記) ▼▼▼")
        st.table(process_branch_v25(df_b_raw, 60, dates, tags))

        # 稽核中心
        with st.expander("🛠️ 【開發者專用】V25.2 演算法稽核中心", expanded=True):
            st.markdown("<h5 class='debug-header'>1. 分點指紋圖鑑 (CSV)</h5>", unsafe_allow_html=True)
            st.dataframe(df_debug_tags)
            st.markdown("<h5 class='debug-header'>2. 除水驗算公式 (CSV)</h5>", unsafe_allow_html=True)
            st.dataframe(df_debug_math)

        # AI 戰報生成 (加入 CSV 驗算包)
        st.divider()
        with st.expander("📋 【點擊展開：給 Gemini 的 V25.2 量化分析與稽核資料包】", expanded=True):
            p = f"分析標的: {user_stock_id} {name} (V25.2)\n"
            p += f"▼▼▼ V25.2 診斷雷達 ▼▼▼\n{df_v25_radar.head(8).to_csv(index=False)}\n"
            p += f"▼▼▼ [稽核] 分點指紋原始數據 (CSV) ▼▼▼\n{df_debug_tags.to_csv(index=False)}\n"
            p += f"▼▼▼ [稽核] 除水還原數學驗算表 (CSV) ▼▼▼\n{df_debug_math.to_csv(index=False)}\n"
            p += f"▼▼▼ [稽核] 週五隔日沖攔截清單 (CSV) ▼▼▼\n{df_debug_friday.to_csv(index=False) if not df_debug_friday.empty else '無隔日沖'}\n"
            p += "\n請幫我驗證以上 CSV 數據的邏輯正確性，並給出多空操作評分。"
            st.code(p, language="text")

# 補齊平行抓取函式
def fetch_fm_branch_fast_parallel(dates_list, target_id):
    if not dates_list: return pd.DataFrame()
    all_data = []
    def fetch_single(d):
        url = "https://api.finmindtrade.com/api/v4/data"
        params = {"dataset": "TaiwanStockTradingDailyReport", "data_id": target_id, "start_date": d, "end_date": d}
        headers = {"Authorization": f"Bearer {FINMIND_TOKEN}"}
        try: return requests.get(url, params=params, headers=headers, timeout=15).json().get("data", [])
        except: return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_single, dates_list))
        for r in results: all_data.extend(r)
    return pd.DataFrame(all_data)
