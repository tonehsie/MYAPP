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

# 1. 系統環境初始化
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="V25.0 終極全息量化系統", layout="wide")

# 內建最新 Token
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

# 注入 CSS 確保排版
st.markdown("""
<style>
table.dataframe th, table.dataframe td { white-space: nowrap !important; text-align: center !important; }
.radar-table td:last-child { text-align: left !important; color: #ff4b4b; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🤖 V25.0 終極全息量化系統")
st.caption("核心功能：分點指紋辨識、數據除水還原、AI 戰報包生成")

# UI 輸入區
col1, col2 = st.columns([1, 1])
with col1:
    user_stock_id = st.text_input("個股代號", value="8027")
with col2:
    dead_chip_input = st.text_input("死籌碼 %", placeholder="留空則自動抓取，或手動輸入（如：15.5）")

run_btn = st.button("🚀 啟動 V25.0 引擎：執行全息除水校正", use_container_width=True)

st.divider()

# ==========================================
# 📌 工具函式庫 (修正縮進錯誤)
# ==========================================

@st.cache_data(ttl=3600)
def get_stock_name(target_id):
    try:
        res = requests.get(f"https://tw.stock.yahoo.com/quote/{target_id}.TW", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        match = re.search(r'<title>(.*?)\s*\(', res.text)
        return match.group(1).strip() if match else ""
    except:
        return ""

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
    except:
        return ""

@st.cache_data(ttl=3600)
def fetch_fm(dataset, start_date, target_id=None, end_date=None):
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {"dataset": dataset, "start_date": start_date}
    if target_id: params["data_id"] = target_id
    if end_date: params["end_date"] = end_date
    headers = {"Authorization": f"Bearer {FINMIND_TOKEN}"}
    try:
        res = requests.get(url, params=params, headers=headers, timeout=15).json()
        return pd.DataFrame(res.get("data", []))
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def scrape_director_holding(target_id):
    dynamic_dict, static_val, chip_engine, debug_log = {}, 0.0, "失敗", []
    try:
        url_good = f"https://goodinfo.tw/tw/StockDirectorSharehold.asp?STOCK_ID={target_id}"
        h = {"User-Agent": "Mozilla/5.0", "Cookie": "CLIENT_KEY=20260412;", "Referer": f"https://goodinfo.tw/tw/StockDetail.asp?STOCK_ID={target_id}"}
        res = requests.get(url_good, headers=h, timeout=8)
        if res.status_code == 200:
            res.encoding = 'utf-8'
            dfs = pd.read_html(StringIO(res.text))
            for df in dfs:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = ['_'.join(str(c) for c in col if 'Unnamed' not in str(c)).strip('_') for col in df.columns.values]
                target_col = next((c for c in df.columns if '全體董監持股' in str(c) and '持股(%)' in str(c)), None)
                month_col = next((c for c in df.columns if '月別' in str(c)), None)
                if target_col and month_col:
                    for _, row in df.iterrows():
                        m, v = str(row[month_col]).strip(), str(row[target_col]).strip()
                        if re.match(r'^\d{4}-\d{2}$', m) and v not in ['-', '', 'nan']:
                            dynamic_dict[m] = float(v)
                    if dynamic_dict:
                        return dynamic_dict, list(dynamic_dict.values())[0], "Goodinfo", debug_log
    except Exception as e:
        debug_log.append(f"G-Err: {e}")
    return {}, 0.0, "失敗", debug_log

def get_dead_chip_info(date_str, dead_chip_input, dynamic_dict, static_val, chip_engine):
    # 修正 SyntaxError: try 必須與對應的 except 在同一層
    if dead_chip_input:
        try:
            val = float(str(dead_chip_input).replace('%', '').strip())
            return val, "手動"
        except:
            pass
    
    month_key = str(date_str)[:7].replace('/', '-')
    if dynamic_dict and month_key in dynamic_dict:
        return dynamic_dict[month_key], "Goodinfo當月"
    if dynamic_dict:
        return list(dynamic_dict.values())[0], "Goodinfo最新"
    if static_val > 0:
        return static_val, chip_engine
    return 0.0, "-"

# ==========================================
# 📌 模組一：V25.0 指紋辨識引擎 (去水關鍵)
# ==========================================
def get_v25_broker_intelligence(df_raw):
    if df_raw.empty: return {}
    df = df_raw.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['securities_trader', 'date'])
    df['b_vol'] = (pd.to_numeric(df['buy'], errors='coerce').fillna(0) / 1000).astype(int)
    df['s_vol'] = (pd.to_numeric(df['sell'], errors='coerce').fillna(0) / 1000).astype(int)
    
    tags = {}
    govs = ["台銀", "土銀", "彰銀", "第一", "兆豐", "華南", "合庫", "台企銀"]
    for trader, group in df.groupby('securities_trader'):
        t_buy, t_sell = group['b_vol'].sum(), group['s_vol'].sum()
        days, net = group['date'].nunique(), t_buy - t_sell
        group['next_2d_sell'] = group['s_vol'].shift(-1).fillna(0) + group['s_vol'].shift(-2).fillna(0)
        flip_rate = group[group['b_vol'] > 50]['next_2d_sell'].sum() / t_buy if t_buy > 0 else 0
        loyalty = net / t_buy if t_buy > 0 else 0
        
        if any(g in trader for g in govs):
            tags[trader] = "🏦 [官股]"
        elif flip_rate > 0.75 and t_buy > 300:
            tags[trader] = "⚡ [隔日沖]"
        elif days >= 15 and loyalty > 0.7:
            tags[trader] = "📈 [波段主]"
        elif t_buy > 1000 and loyalty > 0.85:
            tags[trader] = "🧱 [真鎖碼]"
        else:
            tags[trader] = "🔵 一般"
    return tags

# ==========================================
# 📌 模組二：V25.0 數據除水與雷達引擎
# ==========================================
def get_smart_threshold(price, capital_bn, dead_float):
    if pd.isna(price) or price <= 0: return 1000 
    sfc = max(3000, capital_bn * 500)
    si = max(0.1, 0.5 * (100 - dead_float) / 100)
    shares_by_money = (sfc * 10000) / (price * 1000)
    shares_by_influence = (capital_bn * 10000) * (si / 100) 
    raw_threshold = max(shares_by_money, shares_by_influence)
    levels = [100, 200, 400, 600, 800, 1000]
    aligned = min(levels, key=lambda x: abs(x - raw_threshold))
    if price < 30:
        return min(aligned, 400)
    return aligned

def process_v25_radar(df_share_wide, df_price, df_branch_raw, dead_chip_input, dynamic_dict, static_val):
    if df_share_wide.empty or df_price.empty: return pd.DataFrame()
    labels = get_v25_broker_intelligence(df_branch_raw)
    df_p = df_price.sort_values('日期', ascending=True).copy()
    df_p['ma20'] = df_p['收盤價(元)'].rolling(20).mean()
    
    df_s = df_share_wide.sort_values('日期', ascending=True).copy()
    out = []
    for i in range(len(df_s)):
        row = df_s.iloc[i]
        d = row['日期']
        p_row = df_p[df_p['日期'] == d]
        cur_p = p_row['收盤價(元)'].iloc[0] if not p_row.empty else 0
        m20 = p_row['ma20'].iloc[0] if not p_row.empty else 0
        
        # 數據除水
        df_f = df_branch_raw[df_branch_raw['date'] == d]
        f_vol = 0
        if not df_f.empty:
            # 建立暫時標籤
            df_f = df_f.copy()
            df_f['tag'] = df_f['securities_trader'].map(labels)
            f_vol = df_f[df_f['tag'] == "⚡ [隔日沖]"]['buy'].sum() / 1000
        
        total_s = row['總張數']
        f_impact = (f_vol / total_s) * 100 if total_s > 0 else 0
        raw_chg = 0 if i == 0 else row['1000張以上_比例(%)'] - df_s.iloc[i-1]['1000張以上_比例(%)']
        pure_chg = round(raw_chg - f_impact, 2)
        
        dead, _ = get_dead_chip_info(d, dead_chip_input, dynamic_dict, static_val, "")
        lev = 100 / (100 - dead) if 0 < dead < 100 else 1
        intensity = round(pure_chg * lev, 2)
        
        # 實戰診斷
        advice = "🔵 趨勢盤整"
        if intensity > 2.5 and cur_p > m20:
            advice = "🚀 [真·暴力軋空]"
        elif intensity < -1.2:
            advice = "💀 [主力大舉出貨]"
        elif f_impact > 1.2:
            advice = "⚡ [隔日沖虛假訊號]"
        elif pure_chg > 0.4 and cur_p < m20:
            advice = "🧱 [主力低檔建倉]"
        
        out.append({
            "日期": d, "收盤價": cur_p, "真實變動(%)": pure_chg, 
            "除水強度": intensity, "V25.0 專家診斷": advice
        })
    return pd.DataFrame(out).sort_values('日期', ascending=False)

# ==========================================
# 📌 資料清洗與轉換函式
# ==========================================
def process_price(df):
    if df.empty: return pd.DataFrame()
    df_out = df.copy()
    df_out['Trading_Volume'] = (pd.to_numeric(df_out['Trading_Volume'], errors='coerce').fillna(0) / 1000).round().astype(int)
    df_out = df_out.rename(columns={"date":"日期","Trading_Volume":"成交量(張)","close":"收盤價(元)","open":"開盤價(元)","max":"最高價(元)","min":"最低價(元)","spread":"漲跌(元)"})
    df_out["斷頭價(0.78)"] = (df_out["收盤價(元)"] * 0.78).round(2)
    return df_out[['日期','成交量(張)','開盤價(元)','最高價(元)','最低價(元)','收盤價(元)','漲跌(元)','斷頭價(0.78)']].sort_values('日期', ascending=False)

def process_tdcc(df):
    if df.empty: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df = df[~df['HoldingSharesLevel'].astype(str).str.contains('差異數')]
    df['unit'] = (pd.to_numeric(df['unit'], errors='coerce') / 1000).fillna(0).astype(int)
    df['people'] = pd.to_numeric(df['people'], errors='coerce').fillna(0).astype(int)
    
    dates = sorted(df['date'].unique(), reverse=True)[:15]
    df = df[df['date'].isin(dates)]
    
    p_unit = df.pivot_table(index='date', columns='HoldingSharesLevel', values='unit', aggfunc='first').fillna(0)
    p_pct = df.pivot_table(index='date', columns='HoldingSharesLevel', values='percent', aggfunc='first').fillna(0)
    p_ppl = df.pivot_table(index='date', columns='HoldingSharesLevel', values='people', aggfunc='first').fillna(0)
    
    def get_col(df_p, keywords):
        return next((c for c in df_p.columns if all(k in str(c) for k in keywords)), None)

    col_1000 = get_col(p_pct, ["1000", "以上"])
    col_200_u = get_col(p_unit, ["200", "400"])
    col_200_p = get_col(p_ppl, ["200", "400"])

    res = pd.DataFrame({'日期': p_unit.index})
    res['總張數'] = p_unit.sum(axis=1).values
    res['1000張以上_比例(%)'] = p_pct[col_1000].values if col_1000 else 0
    res['200-400張_張數'] = p_unit[col_200_u].values if col_200_u else 0
    res['200-400張_人數'] = p_ppl[col_200_p].values if col_200_p else 0
    
    return res, p_unit.reset_index(), p_ppl.reset_index()

def process_branch_v25(df_raw, period, actual_dates, intel_tags):
    if df_raw.empty: return pd.DataFrame()
    df = df_raw[df_raw['date'].isin(actual_dates[:period])].copy()
    df['bv'] = (df['buy'] / 1000).astype(int)
    df['sv'] = (df['sell'] / 1000).astype(int)
    g = df.groupby('securities_trader')[['bv', 'sv']].sum().reset_index()
    g['net'] = g['bv'] - g['sv']
    
    buyers = g[g['net'] > 0].sort_values('net', ascending=False).head(15).reset_index(drop=True)
    sellers = g[g['net'] < 0].sort_values('net', ascending=True).head(15).reset_index(drop=True)
    
    out = []
    total_buy = g['bv'].sum() if g['bv'].sum() > 0 else 1
    for i in range(15):
        row = {}
        if i < len(buyers):
            n = buyers.loc[i, 'securities_trader']
            row["買超分點"] = f"{intel_tags.get(n, '🔵')} {n}"
            row["買超(張)"] = int(buyers.loc[i, 'net'])
            row["佔比"] = f"{(buyers.loc[i, 'net']/total_buy)*100:.1f}%"
        else:
            row["買超分點"] = "-"; row["買超(張)"] = 0; row["佔比"] = "-"
            
        if i < len(sellers):
            n = sellers.loc[i, 'securities_trader']
            row["賣超分點"] = f"{intel_tags.get(n, '🔵')} {n}"
            row["賣超(張)"] = abs(int(sellers.loc[i, 'net']))
            row["佔比_"] = f"{(abs(sellers.loc[i, 'net'])/total_buy)*100:.1f}%"
        else:
            row["賣超分點"] = "-"; row["賣超(張)"] = 0; row["佔比_"] = "-"
        out.append(row)
    return pd.DataFrame(out)

def fetch_fm_branch_parallel(dates_list, target_id):
    if not dates_list: return pd.DataFrame()
    all_data = []
    def fetch_single(d):
        url = "https://api.finmindtrade.com/api/v4/data"
        p = {"dataset": "TaiwanStockTradingDailyReport", "data_id": target_id, "start_date": d, "end_date": d}
        h = {"Authorization": f"Bearer {FINMIND_TOKEN}"}
        try:
            res = requests.get(url, params=p, headers=h, timeout=15).json()
            return res.get("data", [])
        except:
            return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_single, dates_list))
        for r in results:
            if r: all_data.extend(r)
    return pd.DataFrame(all_data)

# ==========================================
# 📌 執行主引擎
# ==========================================
if run_btn:
    with st.spinner(f"正在執行 V25.0 終極掃描... (包含 60 天分點路徑指紋識別)"):
        # 1. 基礎資料獲取
        name = get_stock_name(user_stock_id)
        start = (datetime.date.today() - datetime.timedelta(days=1095)).strftime("%Y-%m-%d")
        df_p_raw = fetch_fm("TaiwanStockPrice", start, user_stock_id)
        if df_p_raw.empty:
            st.error("查無股價資料"); st.stop()
        
        dates = sorted(df_p_raw['date'].unique().tolist(), reverse=True)
        df_price = process_price(df_p_raw)
        
        # 2. 籌碼大腦：指紋識別
        dynamic_dict, s_val, engine, _ = scrape_director_holding(user_stock_id)
        df_branch_raw = fetch_fm_branch_parallel(dates[:60], user_stock_id)
        intel_tags = get_v25_broker_intelligence(df_branch_raw)
        
        # 3. 集保數據處理
        df_share_raw = fetch_fm("TaiwanStockHoldingSharesPer", dates[60], user_stock_id)
        df_share_wide, df_unit, df_ppl = process_tdcc(df_share_raw)
        
        # 4. 【核心】產生 V25.0 除水雷達
        df_v25_radar = process_v25_radar(df_share_wide, df_price, df_branch_raw, dead_chip_input, dynamic_dict, s_val)
        
        # 5. 其他輔助資料 (法人、資券)
        df_inst = fetch_fm("TaiwanStockInstitutionalInvestorsBuySell", dates[10], user_stock_id)
        df_margin = fetch_fm("TaiwanStockMarginPurchaseShortSale", dates[10], user_stock_id)

        # --- 頁面呈現 ---
        st.subheader(f"📊 {user_stock_id} {name} V25.0 全息量化戰報")
        
        st.markdown("#### ▼▼▼ 1. V25.0 專家診斷雷達 (除水還原版) ▼▼▼")
        st.table(df_v25_radar.head(8))
        
        st.markdown("#### ▼▼▼ 2. 主力分點 - 近60日 (含指紋識別標籤) ▼▼▼")
        st.table(process_branch_v25(df_branch_raw, 60, dates, intel_tags))

        st.markdown("#### ▼▼▼ 3. 集保分級張數表 (近8週) ▼▼▼")
        st.table(df_unit.head(8))

        # AI 戰報生成
        st.divider()
        with st.expander("📋 【點擊複製：給 Gemini 的 V25.0 量化戰報資料包】", expanded=True):
            ai_p = f"請依下面 V25.0 除水後的資料幫我分析 {user_stock_id} {name} 的多空強度：\n\n"
            ai_p += f"- V25.0 專家診斷：{df_v25_radar['V25.0 專家診斷'].iloc[0]}\n"
            ai_p += f"- 去水後真實變動：{df_v25_radar['真實變動(%)'].iloc[0]}%\n"
            ai_p += f"- 除水強度係數：{df_v25_radar['除水強度'].iloc[0]}\n"
            # 計算噪音佔比
            noise = round(abs(df_v25_radar['真實變動(%)'].iloc[0] - (df_share_wide['1000張以上_比例(%)'].iloc[0]-df_share_wide['1000張以上_比例(%)'].iloc[1])), 2)
            ai_p += f"- 隔日沖雜訊佔比：{noise}%\n"
            ai_p += f"- 60天核心鎖碼分點：{process_branch_v25(df_branch_raw, 60, dates, intel_tags)['買超分點'].head(5).tolist()}\n"
            ai_p += "\n請針對以上純淨數據給出下週的操作建議與評分(0-100)。"
            st.code(ai_p, language="text")
