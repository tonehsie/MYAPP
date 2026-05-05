import streamlit as st
import pandas as pd
import requests
import json
import numpy as np
import datetime
import re
import concurrent.futures
import urllib.request
import ssl
import urllib3
import gc
from io import StringIO
import streamlit.components.v1 as components
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="全息量化系統 (V76.1 終極版)", initial_sidebar_state="expanded")

FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiVG9uZTEiLCJlbWFpbCI6InRvbmVoc2llQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjJ9.LQ9tOV7cgcr27W5jIrdriUnvz-6wIFxCOKzuB9F2A-0"
GITHUB_MANUAL_URL = "https://raw.githubusercontent.com/tonehsie/stock/refs/heads/main/README.md?token=GHSAT0AAAAAADZWCPTL3DW2BEKOO6XFVHZS2PXHCPA"

# ==========================================
# 前端語法模板集中區 (CSS/HTML/JS)
# ==========================================
CSS = """
<style>
.table-container { overflow: auto; max-height: 600px; width: 100%; margin-bottom: 25px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding-bottom: 10px; }
.table-container table { width: max-content !important; min-width: 40%; border-collapse: separate !important; border-spacing: 0; font-size: 15px !important; font-family: sans-serif; background-color: #fff; }
.table-container th, .table-container td { white-space: nowrap !important; padding: 10px 12px !important; border-bottom: 1px solid #dee2e6; border-right: 1px solid #dee2e6; vertical-align: middle; }
.table-container th { border-top: 1px solid #dee2e6; word-break: keep-all !important; text-align: center !important; background-color: #f1f3f5 !important; color: #333 !important; font-weight: 700 !important; line-height: 1.4; position: sticky; top: 0; z-index: 3; }
.table-container th:first-child, .table-container td:first-child { position: sticky; left: 0; background-color: #f8f9fa; z-index: 4; font-weight: bold; text-align: center !important; border-left: 1px solid #dee2e6; }
.table-container thead th:first-child { z-index: 5; }

.full-table-container { overflow-x: auto; overflow-y: visible; width: 100%; margin-bottom: 25px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); display: block; padding-bottom: 10px; }
.full-table-container table { width: max-content !important; min-width: 40%; border-collapse: separate !important; border-spacing: 0; font-size: 15px !important; font-family: sans-serif; background-color: #fff; }
.full-table-container th, .full-table-container td { white-space: nowrap !important; padding: 10px 12px !important; border-bottom: 1px solid #dee2e6; border-right: 1px solid #dee2e6; vertical-align: middle; }
.full-table-container th { border-top: 1px solid #dee2e6; word-break: keep-all !important; text-align: center !important; background-color: #f1f3f5 !important; color: #333 !important; font-weight: 700 !important; line-height: 1.4; position: sticky; top: 0; z-index: 3; }
.full-table-container th:first-child, .full-table-container td:first-child { position: sticky; left: 0; background-color: #f8f9fa; z-index: 4; font-weight: bold; text-align: center !important; border-left: 1px solid #dee2e6; }
.full-table-container thead th:first-child { z-index: 5; }

.text-left { text-align: left !important; }
.text-right { text-align: right !important; font-variant-numeric: tabular-nums; }
.loss-warning { color: #d9480f; font-weight: bold; }
.profit-warning { color: #6a1b9a; font-weight: 900; background-color: #f3e5f5; padding: 3px 6px; border-radius: 4px; border: 1px solid #ce93d8; }
.highlight-red { color: #d32f2f; font-weight: bold; }
.highlight-green { color: #2e7d32; font-weight: bold; }
.info-box { background-color: #f8f9fa; padding: 15px 20px; border-radius: 8px; margin-bottom: 25px; border-left: 6px solid #1e3a8a; font-size: 1.1rem; font-weight: bold; color: #1e3a8a; }
.section-title { margin-top: 35px; margin-bottom: 15px; color: #1e3a8a; border-bottom: 2px solid #1e3a8a; padding-bottom: 5px; font-size: 1.3rem !important; font-weight: 700 !important; }
.category-title { font-size: 1.6rem !important; font-weight: 900 !important; margin-top: 40px; color: #333; }

.ai-report-box { background-color: #fcfdfe; border: 1px solid #e9ecef; border-left: 6px solid #b71c1c; border-radius: 8px; padding: 25px; margin-bottom: 30px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); line-height: 1.8; }
.ai-report-box h4 { margin-top: 0; color: #b71c1c; font-weight: 900; font-size: 1.6rem; border-bottom: 2px dashed #ccc; padding-bottom: 10px; margin-bottom: 20px; }
.ai-report-box li { margin-bottom: 18px; font-size: 1.25rem; color: #222; }
.ai-report-box b { font-size: 1.4rem; color: #b71c1c; }
.ai-conclusion { background-color: #fff3cd; padding: 22px; border-radius: 8px; border: 2px solid #ffe69c; font-weight: 700; color: #856404; font-size: 1.45rem; }
.progress-text { font-size: 1.1rem; color: #1e3a8a; font-weight: bold; margin-bottom: 5px; }

@media (prefers-color-scheme: dark) {
    .table-container table, .full-table-container table { background-color: #1e1e1e !important; color: #e0e0e0 !important; }
    .table-container th, .table-container td, .full-table-container th, .full-table-container td { border-color: #444 !important; color: #e0e0e0 !important; }
    .table-container th, .full-table-container th { background-color: #2d2d2d !important; color: #fff !important; }
    .table-container th:first-child, .table-container td:first-child, .full-table-container th:first-child, .full-table-container td:first-child { background-color: #252525 !important; }
    .info-box { background-color: #2d2d2d !important; color: #64b5f6 !important; border-left-color: #64b5f6 !important; }
    .section-title { color: #64b5f6 !important; border-bottom-color: #64b5f6 !important; }
    .category-title { color: #fff !important; }
    .ai-report-box { background-color: #252525 !important; border-color: #444 !important; border-left-color: #ef5350 !important; color: #e0e0e0 !important; }
    .ai-report-box h4 { color: #ef5350 !important; border-bottom-color: #444 !important; }
    .ai-report-box li { color: #e0e0e0 !important; }
    .ai-report-box b { color: #ef5350 !important; }
    .ai-conclusion { background-color: #3e2723 !important; border-color: #5d4037 !important; color: #ffb74d !important; }
    .progress-text { color: #64b5f6 !important; }
    .profit-warning { background-color: #4a148c !important; color: #e1bee7 !important; border-color: #7b1fa2 !important; }
    .loss-warning { color: #ff7043 !important; }
    .highlight-red { color: #ef5350 !important; }
    .highlight-green { color: #66bb6a !important; }
}
</style>
"""

HEATMAP_STYLE_TEMPLATE = """
<style>
.heatmap-wrapper .noise-cell { background-color: transparent !important; }
.heatmap-wrapper .noise-cell span { display: none; }
#heatmap-toggle:checked ~ .heatmap-wrapper .noise-cell { background-color: var(--bg-color) !important; }
#heatmap-toggle:checked ~ .heatmap-wrapper .noise-cell span { display: inline; color: var(--txt-color) !important; text-shadow: 1px 1px 2px rgba(0,0,0,0.6); }
#heatmap-toggle:checked ~ .heatmap-wrapper .noise-cell.val-zero span { text-shadow: none !important; }
.heatmap-toggle-label { display: inline-block; margin-bottom: 12px; padding: 6px 12px; background-color: #f1f3f5; border-radius: 6px; border: 1px solid #ccc; cursor: pointer; font-weight: bold; color: #1e3a8a; user-select: none; }
#heatmap-toggle:checked + .heatmap-toggle-label { background-color: #e3f2fd; border-color: #90caf9; }
</style>
<input type="checkbox" id="heatmap-toggle" style="display: none;">
<label for="heatmap-toggle" class="heatmap-toggle-label">👁️ 切換顯示：所有隱藏數值 (含 0 與雜訊)</label>
"""

KLINE_CHART_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        body { margin: 0; background: #fff; font-family: sans-serif; display: flex; flex-direction: column; height: 100vh; overflow: hidden;}
        #chart-main { flex: 3.2; border-bottom: 2px solid #f0f3fa; position: relative; }
        #chart-vol { flex: 0.8; position: relative;}
        .legend { position: absolute; top: 4px; left: 8px; z-index: 10; font-size: 13px; pointer-events: none; background: rgba(255,255,255,0.7); padding: 2px 6px; border-radius: 4px; color: #333;}
        @media (prefers-color-scheme: dark) { body { background: #1e1e1e; } #chart-main { border-bottom: 2px solid #444; } .legend { background: rgba(30,30,30,0.7); color: #e0e0e0; } }
    </style>
</head>
<body>
    <div id="chart-main"><div id="legend" class="legend"></div></div>
    <div id="chart-vol"></div>
    <script>
        const kData = KLINE_DATA; const tVol = TOTAL_VOL; const dtVol = DAYTRADE_VOL; const ma = MA_DATA;
        const kDataMap = new Map(kData.map(x => [x.time, x]));
        const tVolMap = new Map(tVol.map(x => [x.time, x.value]));
        const dtVolMap = new Map(dtVol.map(x => [x.time, x.value]));
        const commonLocalization = { timeFormatter: d => d.year ? `${String(d.year).slice(-2)}/${String(d.month).padStart(2,'0')}/${String(d.day).padStart(2,'0')}` : (typeof d === 'string' ? d.substring(2).replace(/-/g, '/') : d) };
        const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const chartBgColor = isDark ? '#1e1e1e' : '#ffffff';
        const chartTxtColor = isDark ? '#e0e0e0' : '#333';
        const chartGridColor = isDark ? '#333333' : '#f5f5f5';
        const priceScaleConfig = { borderColor: chartGridColor, autoScale: true, minimumWidth: 80, alignLabels: true };
        const mainOptions = { autoSize: true, localization: commonLocalization, layout: { background: { color: chartBgColor }, textColor: chartTxtColor }, grid: { vertLines: { color: chartGridColor }, horzLines: { color: chartGridColor } }, rightPriceScale: { ...priceScaleConfig, scaleMargins: { top: 0.05, bottom: 0.05 } }, timeScale: { visible: false, rightOffset: 10 } };
        const volOptions = { autoSize: true, localization: commonLocalization, layout: { background: { color: chartBgColor }, textColor: chartTxtColor }, grid: { vertLines: { color: chartGridColor }, horzLines: { color: chartGridColor } }, rightPriceScale: { ...priceScaleConfig, scaleMargins: { top: 0.02, bottom: 0 } }, timeScale: { borderColor: chartGridColor, rightOffset: 10 } };
        const mainChart = LightweightCharts.createChart(document.getElementById('chart-main'), mainOptions);
        const volChart = LightweightCharts.createChart(document.getElementById('chart-vol'), volOptions);
        const candleSeries = mainChart.addCandlestickSeries({ upColor: chartBgColor, borderUpColor: isDark ? '#fff' : '#000', wickUpColor: isDark ? '#fff' : '#000', downColor: isDark ? '#fff' : '#000', borderDownColor: isDark ? '#fff' : '#000', wickDownColor: isDark ? '#fff' : '#000' });
        candleSeries.setData(kData);
        const lineOpt = { lineWidth: 1, lastValueVisible: false, priceLineVisible: false, crosshairMarkerVisible: false };
        mainChart.addLineSeries({ color: '#ff9800', ...lineOpt }).setData(ma.ma_short);
        mainChart.addLineSeries({ color: '#2196f3', ...lineOpt }).setData(ma.ma_mid);
        mainChart.addLineSeries({ color: '#9c27b0', ...lineOpt }).setData(ma.ma_long);
        const lr = LR_DATA; if (lr && lr.upper && lr.upper.length > 0) { mainChart.addLineSeries({ color: isDark ? 'rgba(100, 181, 246, 0.5)' : 'rgba(30, 58, 138, 0.4)', lineWidth: 1, lineStyle: 0, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }).setData(lr.upper); mainChart.addLineSeries({ color: isDark ? 'rgba(100, 181, 246, 0.8)' : 'rgba(30, 58, 138, 0.6)', lineWidth: 1, lineStyle: 2, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }).setData(lr.mid); mainChart.addLineSeries({ color: isDark ? 'rgba(100, 181, 246, 0.5)' : 'rgba(30, 58, 138, 0.4)', lineWidth: 1, lineStyle: 0, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }).setData(lr.lower); }
        const pat = PAT_DATA; const neck = NECK_DATA; const patColor = PAT_COLOR;
        if (pat && pat.length > 0) { mainChart.addLineSeries({ color: patColor, lineWidth: 2, lineStyle: 0, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }).setData(pat); }
        if (neck && neck.length > 0) { mainChart.addLineSeries({ color: patColor, lineWidth: 2, lineStyle: 3, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }).setData(neck); }
        const totalVolSeries = volChart.addHistogramSeries({ priceFormat: { type: 'volume' } }); totalVolSeries.setData(tVol);
        const dayTradeVolSeries = volChart.addHistogramSeries({ priceFormat: { type: 'volume' } }); dayTradeVolSeries.setData(dtVol);
        const legend = document.getElementById('legend');
        const updateLegend = (p) => { let d, dtVal, tvVal; if (p.time) { d = kDataMap.get(p.time); dtVal = dtVolMap.get(p.time); tvVal = tVolMap.get(p.time); } else { d = kData[kData.length-1]; dtVal = dtVol[dtVol.length-1].value; tvVal = tVol[tVol.length-1].value; } if (!d || dtVal === undefined || tvVal === undefined) return; const shortDate = d.time.substring(2).replace(/-/g, '/'); legend.innerHTML = `<b>${shortDate}</b> &nbsp; 開:${d.open} 高:${d.high} 低:${d.low} 收:<span style="color:${chartTxtColor}">${d.close}</span> &nbsp; <span style="color:#888">總量:${Math.round(tvVal)}</span> &nbsp; <span style="color:#FF9800">當沖:${Math.round(dtVal)}</span>`; };
        updateLegend({time: null});
        mainChart.subscribeCrosshairMove(p => { updateLegend(p); if (p.time) volChart.setCrosshairPosition(0, p.time, totalVolSeries); else volChart.clearCrosshairPosition(); });
        volChart.subscribeCrosshairMove(p => { updateLegend(p); if (p.time) mainChart.setCrosshairPosition(0, p.time, candleSeries); else mainChart.clearCrosshairPosition(); });
        let isSyncingMain = false; let isSyncingVol = false;
        mainChart.timeScale().subscribeVisibleLogicalRangeChange(r => { if (!isSyncingMain && r !== null) { isSyncingVol = true; volChart.timeScale().setVisibleLogicalRange(r); isSyncingVol = false; } });
        volChart.timeScale().subscribeVisibleLogicalRangeChange(r => { if (!isSyncingVol && r !== null) { isSyncingMain = true; mainChart.timeScale().setVisibleLogicalRange(r); isSyncingMain = false; } });
    </script>
</body>
</html>
"""

# ==========================================
# 資料快取與連線
# ==========================================
@st.cache_resource(max_entries=3)
def get_finmind_session():
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {FINMIND_TOKEN}", "User-Agent": "Mozilla/5.0"})
    retry = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

@st.cache_resource(max_entries=3)
def get_generic_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

FM_SESSION = get_finmind_session()
GENERIC_SESSION = get_generic_session()

@st.cache_data(ttl=86400, max_entries=5, show_spinner=False)
def fetch_github_manual(url):
    try:
        r = GENERIC_SESSION.get(url, timeout=5)
        if r.status_code == 200:
            r.encoding = 'utf-8'
            return r.text
        return "無法載入指南，請確認 GitHub Raw 網址是否正確。"
    except Exception as e: return f"指南載入失敗: {e}"

@st.cache_data(ttl=300, max_entries=2, show_spinner=False)
def get_api_usage(token):
    try:
        r = GENERIC_SESSION.get(f"https://api.web.finmindtrade.com/v2/user_info?token={token}", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data.get("user_count", 0), data.get("api_request_limit", 0)
    except: pass
    return None, None

# ==========================================
# 側邊欄設定
# ==========================================
st.sidebar.markdown("### 交易戰略大腦")
trade_strategy = st.sidebar.radio("交易戰略偏好", ["右側動能 (短線突破)", "左側潛伏 (中長線價值)"])
is_right_side = "右側" in trade_strategy

st.sidebar.header("戰術參數控制面板")
kline_days = st.sidebar.slider("K線顯示天數 (圖表景深)", 30, 600, 270, 10)
lookback_days = st.sidebar.selectbox("長線籌碼回溯天數 (全局黏著度分母)", [20, 60, 90, 120], index=1)
stickiness_threshold = st.sidebar.slider("主力黏著度門檻 (%)", 10.0, 80.0, 50.0, 5.0)

# 🗓️ 自訂區間選擇器
st.sidebar.divider()
st.sidebar.markdown("### 🗓️ 終極透視區：區間設定")
today_date = datetime.date.today()
default_start = today_date - datetime.timedelta(days=15)
custom_range = st.sidebar.date_input(
    "選擇全息熱力圖之戰鬥區間",
    value=(default_start, today_date),
    max_value=today_date
)

footprint_rows = st.sidebar.slider("透視區顯示筆數 (多空各 N 名)", 5, 50, 15, 5)

st.sidebar.divider()
st.sidebar.markdown("### 視覺系主菜：熱力圖設定")
heatmap_noise_pct = st.sidebar.slider("熱力圖雜訊過濾 (佔20日均量 %)", 0.0, 5.0, 0.5 if is_right_side else 1.0, 0.1)

st.sidebar.divider()
st.sidebar.markdown("### 防禦系配菜：警報器設定")
alert_smart_pct = st.sidebar.slider("警報: 聰明錢極端進出 (佔20日均量 %)", 1.0, 20.0, 10.0 if is_right_side else 5.0, 1.0)
alert_bias_drop = st.sidebar.slider("警報: 跌破主力防守乖離 < (%)", -20.0, 0.0, -3.0, 0.5)

st.sidebar.divider()
firepower_threshold = st.sidebar.slider("買方火力倍數門檻", 1.0, 5.0, 1.5, 0.1)

st.sidebar.divider()
st.sidebar.markdown("### AI 幾何形態與技術線")
enable_pattern = st.sidebar.checkbox("啟動 AI 幾何形態掃描", value=True)

pattern_mode = st.sidebar.selectbox("形態顯示模式", [
    "全自動智慧辨識 (Auto)", "反轉：W底 (雙重底)", "反轉：M頭 (雙重頂)", 
    "反轉：頭肩底", "反轉：頭肩頂", "反轉：三重底", "反轉：三重頂", "反轉：V型反轉",
    "連續：對稱三角形", "連續：上升三角形", "連續：下降三角形", "連續：上升楔形", "連續：下降楔形", "連續：矩形 (箱型整理)"
])

lr_days = st.sidebar.slider("線性迴歸通道天數 (動態趨勢)", 20, 120, 20, 5)
pattern_order = st.sidebar.slider("形態辨識靈敏度 (Order)", 2, 20, 5, 1)

st.sidebar.divider()
st.sidebar.markdown("### 淨化籌碼引擎")
filter_day_trade = st.sidebar.checkbox("剔除散戶與當沖，計算純淨加權均價", value=True)
st.sidebar.divider()

ma_short = int(st.sidebar.number_input("短均線 (天)", min_value=1, max_value=20, value=10))
ma_mid = int(st.sidebar.number_input("中均線/防守線 (天)", min_value=20, max_value=100, value=60))
ma_long = int(st.sidebar.number_input("長均線 (天)", min_value=100, max_value=300, value=240))

# ==========================================
# 主畫面 UI
# ==========================================
st.title("全息量化系統 (V76.1 終極版)")
user_count, api_limit = get_api_usage(FINMIND_TOKEN)
usage_text = f" | FinMind 額度: {user_count} / {api_limit}" if user_count is not None else ""
st.caption(f"V76.1：無斷點動態抓取邏輯、K線圖與16大模組完整回歸。{usage_text}")

with st.expander("點此閱讀【全息量化系統】四大核心模組終極實戰指南", expanded=False):
    st.markdown(fetch_github_manual(GITHUB_MANUAL_URL), unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])
with col1: 
    user_stock_id = st.text_input("個股代號", value="2330")
with col2: 
    dead_chip_input = st.text_input("死籌碼 % (董監事持股＋大股東持股，留空自動抓)")
run_btn = st.button("啟動 V76.1 決策引擎", use_container_width=True, key="run_engine")

# ==========================================
# 基礎輔助函式
# ==========================================
def is_valid(df, req_cols=None, min_len=1):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty or len(df) < min_len: return False
    if req_cols and not all(c in df.columns for c in req_cols): return False
    return True

def optimize_memory(df):
    if not is_valid(df): return df
    for col in df.columns:
        col_type = df[col].dtype
        if col_type == 'float64': df[col] = df[col].astype('float32')
        elif col_type == 'int64': df[col] = df[col].astype('int32')
        elif col_type == 'object':
            if 'trader' in col or '分點' in col or '標籤' in col:
                df[col] = df[col].astype('category')
    return df

_num_re = re.compile(r'\d+')
_LEVEL_MAP = {
    1: "1-999股", 2: "1-5張", 3: "5-10張", 4: "10-15張", 5: "15-20張",
    6: "20-30張", 7: "30-40張", 8: "40-50張", 9: "50-100張", 10: "100-200張",
    11: "200-400張", 12: "400-600張", 13: "600-800張", 14: "800-1000張", 15: "1000張以上"
}
_LEVEL_CLEAN_CACHE = {}

def safe_to_num(series, fill_val=0):
    if isinstance(series, pd.Series):
        if pd.api.types.is_numeric_dtype(series): return series.fillna(fill_val)
        valid_mask = series.notna()
        converted = pd.Series(fill_val, index=series.index, dtype=float)
        if valid_mask.any():
            cleaned = series[valid_mask].astype(str).str.replace(r'[,%＊*]', '', regex=True).str.strip()
            ignore_list = ['', 'nan', 'none', '-', 'y', 'n', 'x', '<na>', 'na', 'null']
            cleaned = cleaned.replace(ignore_list, np.nan)
            temp_converted = pd.to_numeric(cleaned, errors='coerce')
            converted.loc[valid_mask] = temp_converted.fillna(fill_val)
        return converted
    elif isinstance(series, (int, float)): 
        return series
    else:
        if pd.isna(series): return fill_val
        s_str = re.sub(r'[,%＊*]', '', str(series)).strip()
        if not s_str or s_str.lower() in ['nan', 'none', '-', 'y', 'n', 'x', '<na>', 'na', 'null']: return fill_val
        try: return float(s_str)
        except: return fill_val

def cached_finmind_api_call(url, params_tuple):
    r = FM_SESSION.get(url, params=dict(params_tuple), timeout=20)
    r.raise_for_status() 
    data = r.json().get("data")
    if data is None: raise ValueError("FinMind 回傳資料為空")
    return data

@st.cache_data(ttl=86400, max_entries=5, show_spinner=False)
def get_basic_info_finmind(tid):
    name, ind = "未知名稱", "未知產業"
    try:
        url = "https://api.finmindtrade.com/api/v4/data"
        p = {"dataset": "TaiwanStockInfo", "data_id": tid, "start_date": "2000-01-01"}
        data = cached_finmind_api_call(url, tuple(sorted(p.items())))
        if data:
            df = pd.DataFrame(data)
            if not df.empty:
                if 'stock_name' in df.columns: name = df['stock_name'].iloc[0]
                if 'industry_category' in df.columns: ind = df['industry_category'].iloc[0]
    except: pass
    return name, ind

def fetch_finmind_v50(ds, sd, tid=None, ed=None):
    url = "https://api.finmindtrade.com/api/v4/data"
    p = {"dataset": ds, "start_date": sd}
    if tid: p["data_id"] = tid
    if ed: p["end_date"] = ed
    try:
        data = cached_finmind_api_call(url, tuple(sorted(p.items())))
        return pd.DataFrame(data) if data else pd.DataFrame()
    except: return pd.DataFrame()

# ==========================================
# 核心抓取邏輯 (無斷點增強版)
# ==========================================
def fetch_heavy_data_sync_with_progress(user_stock_id, dates_tuple, max_len):
    dates = list(dates_tuple) 
    b_results = []
    a_results = {}
    cb_info_list = []

    tdcc_sd = (datetime.date.today() - datetime.timedelta(days=180)).strftime("%Y-%m-%d")
    d_end = dates[max_len-1] if max_len > 0 and max_len <= len(dates) else dates[-1]
    dt_sd = (datetime.date.today() - datetime.timedelta(days=700)).strftime("%Y-%m-%d")

    api_targets = [
        ("TaiwanStockHoldingSharesPer", tdcc_sd, None, user_stock_id),
        ("TaiwanStockMarginPurchaseShortSale", d_end, None, user_stock_id),
        ("TaiwanStockDayTrading", dt_sd, None, user_stock_id),
        ("TaiwanStockInstitutionalInvestorsBuySell", d_end, None, user_stock_id),
        ("TaiwanStockMonthRevenue", "2022-01-01", None, user_stock_id),
        ("TaiwanFuturesInstitutionalInvestors", d_end, None, "TX"),
        ("TaiwanStockDividend", "2015-01-01", None, user_stock_id),
        ("TaiwanStockPER", d_end, None, user_stock_id),
        ("TaiwanStockDispositionSecuritiesPeriod", tdcc_sd, None, user_stock_id),
        ("TaiwanStockConvertibleBondDailyOverview", dates[0], None, None),
        ("TaiwanStockBlockTrade", d_end, None, user_stock_id), 
        ("TaiwanStockSecuritiesLending", d_end, None, user_stock_id) 
    ]

    target_dates = dates[:max_len]
    total_tasks = len(target_dates) + len(api_targets)
    
    prog_container = st.empty()
    text_container = st.empty()
    prog_bar = prog_container.progress(0.0)

    def fetch_api(dataset, sd, ed, tid):
        url = "https://api.finmindtrade.com/api/v4/data"
        p = {"dataset": dataset, "start_date": sd}
        if tid: p["data_id"] = tid
        if ed: p["end_date"] = ed
        try: return dataset, cached_finmind_api_call(url, tuple(sorted(p.items())))
        except: return dataset, []

    def fetch_branch(d, tid):
        url = "https://api.finmindtrade.com/api/v4/data"
        p = {"dataset": "TaiwanStockTradingDailyReport", "data_id": tid, "start_date": d, "end_date": d}
        try: return cached_finmind_api_call(url, tuple(sorted(p.items())))
        except: return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        future_to_type = {}
        for d in target_dates:
            future_to_type[executor.submit(fetch_branch, d, user_stock_id)] = 'branch'
        for ds, sd, ed, tid in api_targets:
            future_to_type[executor.submit(fetch_api, ds, sd, ed, tid)] = 'api'

        completed = 0
        for future in concurrent.futures.as_completed(future_to_type):
            completed += 1
            prog_val = min(1.0, completed / total_tasks)
            prog_bar.progress(prog_val)
            text_container.markdown(f"<div class='progress-text'>⚡ 系統載入中... (進度: {completed} / {total_tasks})</div>", unsafe_allow_html=True)

            f_type = future_to_type[future]
            if f_type == 'branch':
                res = future.result()
                if res: b_results.extend(res)
            else:
                ds, data = future.result()
                a_results[ds] = pd.DataFrame(data)

        df_cbas_raw = a_results.get("TaiwanStockConvertibleBondDailyOverview", pd.DataFrame())
        if not df_cbas_raw.empty and 'cb_id' in df_cbas_raw.columns:
            cb_mask = df_cbas_raw['cb_id'].astype(str).str.replace(',', '', regex=False).str.startswith(user_stock_id)
            target_cbs = df_cbas_raw[cb_mask]['cb_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.replace(',', '', regex=False).str.strip().unique()
            if len(target_cbs) > 0:
                cb_futures = [executor.submit(fetch_api, "TaiwanStockConvertibleBondInfo", "2000-01-01", None, cid) for cid in target_cbs]
                for f in concurrent.futures.as_completed(cb_futures):
                    _, cb_data = f.result()
                    if cb_data: cb_info_list.extend(cb_data)

    prog_container.empty()
    text_container.empty()

    df_b = optimize_memory(pd.DataFrame.from_records(b_results)) if b_results else pd.DataFrame()
    df_cb_info = pd.DataFrame(cb_info_list)
    return df_b, a_results, df_cb_info

# ==========================================
# 爬蟲與其他分析邏輯
# ==========================================
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
            res = GENERIC_SESSION.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, verify=False)
            if res.status_code == 200: 
                res.encoding = 'big5'
                return res.text
        except: pass
    return ""

@st.cache_data(ttl=3600, max_entries=3, show_spinner=False)
def scrape_director_v50(tid):
    dd, sv = {}, 0.0
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": f"https://goodinfo.tw/tw/StockDetail.asp?STOCK_ID={tid}"
        }
        r = GENERIC_SESSION.get(f"https://goodinfo.tw/tw/StockDirectorSharehold.asp?STOCK_ID={tid}", headers=headers, timeout=10)
        if r.status_code == 200:
            r.encoding = 'utf-8'
            for df in pd.read_html(StringIO(r.text)):
                if isinstance(df.columns, pd.MultiIndex): df.columns = ['_'.join(str(c) for c in col if 'Unnamed' not in str(c)).strip('_') for col in df.columns.values]
                else: df.columns = df.columns.astype(str)
                
                tc_dir = next((c for c in df.columns if '董監' in str(c) and '持股' in str(c).replace(' ', '')), None)
                tc_large = next((c for c in df.columns if '大股東' in str(c) and '持股' in str(c).replace(' ', '')), None)
                mc = next((c for c in df.columns if '月別' in str(c)), None)
                
                if mc and (tc_dir or tc_large):
                    lt = 0.0
                    for ro in df.to_dict('records'):
                        m = str(ro.get(mc, '')).replace('/', '-').strip()
                        if re.match(r'^\d{4}-\d{2}$', m):
                            v_dir = str(ro.get(tc_dir, '0')).replace(',', '').strip() if tc_dir else '0'
                            v_large = str(ro.get(tc_large, '0')).replace(',', '').strip() if tc_large else '0'
                            try:
                                val = float(v_dir if v_dir not in ['-', '', 'nan'] else 0) + float(v_large if v_large not in ['-', '', 'nan'] else 0)
                                if 0 < val < 100:
                                    dd[m] = val
                                    if lt == 0.0: lt = val
                            except: pass
                    if dd: return dd, lt, "Goodinfo(含大股東)", []
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

def get_dead_chip_info(ds, dci, dd, sv, ce):
    if dci and str(dci).strip() != "":
        try: return float(str(dci).replace('%', '').strip()), "手動輸入"
        except: pass
    mk = str(ds)[:7].replace('/', '-')
    if dd and mk in dd: return dd[mk], f"{ce}當月"
    if dd: return list(dd.values())[0], f"{ce}最新"
    return (sv, ce) if sv > 0 else (0.0, "缺資料")

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
            r = [re.sub(r'<[^>]+>|&nbsp;|\s', '', td).strip() for td in tds]
            if trg in "".join(r): ist = True
            elif ist and len(r) >= cols:
                if r[0] == "" or "註" in r[0]: ist = False
                else: out.append(r[:cols])
    return out

@st.cache_data(ttl=3600, max_entries=3, show_spinner=False)
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
    
    for c in ["設質(張)", "解質(張)", "累積質設(張)"]: df_all[c] = safe_to_num(df_all[c]).astype(int)
        
    prd = {pd.to_datetime(r['date']).strftime('%Y-%m-%d'): r['close'] for _, r in df_pr.iterrows()}
    pps, mcs = [], []
    for r in df_all.to_dict('records'):
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
    for r in df_all.to_dict('records'):
        if r['姓名'] not in sm: sm[r['姓名']] = {"title": r['身份別'], "balance": r['累積質設(張)'], "p": "-", "mc": "-"}
        if sm[r['姓名']]["p"] == "-" and r['設質(張)'] > 0: 
            sm[r['姓名']]["p"] = r['設質日收盤價']
            sm[r['姓名']]["mc"] = r['強制賣出價(0.78)']
    sr = [{"身份別": d["title"], "姓名": n, "目前剩餘質設(張)": d["balance"], "最後設質收盤價(元)": d["p"], "估算斷頭價(0.78)": d["mc"]} for n, d in sm.items() if d["balance"] > 0]
    return pd.DataFrame(sr), df_all

def get_v50_intelligence(df_b_raw, df_p_raw, stick_thresh, global_days, dates_list):
    if not is_valid(df_b_raw) or not is_valid(df_p_raw): return {}, pd.DataFrame()
    actual_global_days = max(1, df_b_raw['date'].nunique())

    vol_col = 'Trading_Volume' if 'Trading_Volume' in df_p_raw.columns else 'Trading_volume'
    df_p = df_p_raw[['date', 'close', 'max', 'min', vol_col]].copy() if vol_col in df_p_raw.columns else df_p_raw[['date', 'close', 'max', 'min']].copy()
    df_p = df_p.assign(date=pd.to_datetime(df_p['date'])).sort_values('date', ascending=False)
    
    avg_vol_lots = (pd.to_numeric(df_p[vol_col], errors='coerce').head(20).mean()) / 1000 if vol_col in df_p.columns else 3000
    if pd.isna(avg_vol_lots) or avg_vol_lots <= 0: avg_vol_lots = 3000

    scale = max(0.2, min(20.0, avg_vol_lots / 3000.0))
    t_50, t_100, t_200, t_300 = max(10, int(50*scale)), max(20, int(100*scale)), max(40, int(200*scale)), max(60, int(300*scale))

    df_p['actual_spread'] = df_p['close'] - df_p['close'].shift(-1).fillna(df_p['close'])
    range_diff = df_p['max'] - df_p['min']
    df_p['pos'] = 0.5 
    cond_normal = range_diff > 0
    df_p.loc[cond_normal, 'pos'] = (df_p['close'] - df_p['min']) / range_diff
    df_p.loc[(~cond_normal) & (df_p['actual_spread'] > 0), 'pos'] = 1.0
    df_p.loc[(~cond_normal) & (df_p['actual_spread'] < 0), 'pos'] = 0.0
    
    pos_dict = df_p.set_index('date')['pos'].to_dict()
    latest_close = df_p['close'].iloc[0] if not df_p.empty else 0

    d5, d20, d60 = dates_list[:5], dates_list[:20] if len(dates_list)>=20 else dates_list, dates_list[:60] if len(dates_list)>=60 else dates_list
    g5_shares = df_b_raw[df_b_raw['date'].isin(d5)].groupby('securities_trader')['net_shares'].sum()
    g20_shares = df_b_raw[df_b_raw['date'].isin(d20)].groupby('securities_trader')['net_shares'].sum()
    g60_shares = df_b_raw[df_b_raw['date'].isin(d60)].groupby('securities_trader')['net_shares'].sum()
    
    stats = pd.DataFrame({'net_5d': (g5_shares / 1000).round(), 'net_20d': (g20_shares / 1000).round(), 'net_60d': (g60_shares / 1000).round()}).fillna(0).astype(int)

    g = df_b_raw.groupby('securities_trader').agg(
        tb_shares=('buy', 'sum'), ts_shares=('sell', 'sum'), net_shares=('net_shares', 'sum'),
        buy_amt=('valid_buy_amt', 'sum'), sell_amt=('valid_sell_amt', 'sum'),
        valid_b_shares=('valid_buy', 'sum'), valid_s_shares=('valid_sell', 'sum'),
        active_days=('date_dt', 'nunique'), last_date=('date_dt', 'max')
    )
    
    g['stickiness'] = (g['active_days'] / actual_global_days) * 100
    g['hoard_ratio'] = np.where(g['net_shares'] > 0, (g['net_shares'] / g['tb_shares'].replace(0, np.nan)) * 100, (g['net_shares'].abs() / g['ts_shares'].replace(0, np.nan)) * 100)
    g['hoard_ratio'] = g['hoard_ratio'].fillna(0).round(1)

    g['avg_b'] = (g['buy_amt'] / g['valid_b_shares'].replace(0, np.nan)).fillna(0)
    g['avg_s'] = (g['sell_amt'] / g['valid_s_shares'].replace(0, np.nan)).fillna(0)
    
    g = g.join(stats).fillna(0)
    
    g['tb'] = (g['tb_shares'] / 1000).round().astype(int)
    g['ts'] = (g['ts_shares'] / 1000).round().astype(int)
    g['net_lots'] = (g['net_shares'] / 1000).round().astype(int)
    
    cond_heavy = g['net_20d'].abs() >= t_300
    cond_lock = (g['net_60d'] >= t_200) & (g['net_20d'] >= t_100) & (g['net_5d'] >= t_50)
    cond_cover = (g['net_60d'] <= -t_100) & (g['net_5d'] >= t_200)
    cond_profit = (g['net_60d'] >= t_300) & (g['net_20d'] >= t_100) & (g['net_5d'] <= -t_100)
    cond_exit = (g['net_60d'] <= -t_200) & (g['net_20d'] <= -t_100) & (g['net_5d'] <= -t_100)
    cond_snap = (g['net_60d'].between(-t_200, t_200)) & (g['net_20d'].between(-t_200, t_200)) & (g['net_5d'] >= t_300)
    cond_maker = g['stickiness'] >= stick_thresh
    cond_follow = (g['stickiness'] < 10.0) & (g['net_5d'].abs() > t_50)

    g['tag'] = np.select([cond_heavy, cond_lock, cond_cover, cond_profit, cond_exit, cond_snap, cond_maker, cond_follow], ["主力重砲", "波段鎖碼", "認錯回補", "獲利調節", "棄守提款", "隔日突擊", "避險造市", "跟風小戶"], default="路人雜訊")
    tags = g['tag'].to_dict()
    g = g[(g['tb_shares'] > 0) | (g['ts_shares'] > 0)]
    
    cond_loss = (g['avg_b'] > latest_close) & (g['avg_b'] > 0) & (g['net_shares'] > 0)
    b_strs = g['avg_b'].apply(lambda x: f"{x:,.2f}" if x > 0 else "-")
    g = g.assign(b_str = np.where(cond_loss, "(虧) " + b_strs, b_strs), pos = g['last_date'].map(pos_dict).fillna(0.5).round(2))
    
    res_df = pd.DataFrame({"分點名稱": g.index, "最終標籤": g['tag'], "近60日淨買(張)": g['net_60d'].astype(int), "近20日淨買(張)": g['net_20d'].astype(int), "近5日淨買(張)": g['net_5d'].astype(int), "黏著度(%)": g['stickiness'].round(1), "囤出貨率(%)": g['hoard_ratio'], "總買(張)": g['tb'], "總賣(張)": g['ts'], "淨留倉": g['net_lots'], "買均價": g['b_str'], "賣均價": np.where(g['avg_s'] > 0, g['avg_s'].round(2).astype(str), "-"), "收盤位階": g['pos']}).sort_values('近60日淨買(張)', ascending=False)
    return tags, res_df

def calculate_dynamic_radar_depth(df_b_raw, dates_list, total_lots, df_price):
    if total_lots <= 0 or not is_valid(df_b_raw): return 15, "基本預設 (缺股本資料)"
    base_n, cap_desc = (10, "微型股本") if total_lots < 300000 else (15, "中小型股") if total_lots < 1000000 else (30, "中大型股") if total_lots < 5000000 else (50, "大型權值")

    recent_pr = df_price[df_price['日期'].isin(dates_list[:5])]
    avg_vol = recent_pr['成交量(張)'].mean() if not recent_pr.empty else 0
    turnover_5d = (avg_vol / total_lots) * 100 if total_lots > 0 else 0

    turn_desc, final_n = "", base_n
    if turnover_5d > 10.0: final_n, turn_desc = max(5, int(base_n * 0.7)), " | 高週轉降噪"
    elif turnover_5d < 1.0: final_n, turn_desc = min(50, int(base_n * 1.2)), " | 低波擴散"

    buyers = df_b_raw[df_b_raw['date'].isin(dates_list[:20])].groupby('securities_trader')[['buy', 'sell']].sum().assign(net=lambda x: (x['buy'] - x['sell']) / 1000).query('net > 0').sort_values('net', ascending=False)
    if len(buyers) > 5 and buyers.head(final_n)['net'].sum() > 0 and (buyers.head(5)['net'].sum() / buyers.head(final_n)['net'].sum()) > 0.8:
        final_n, turn_desc = max(5, min(final_n, 10)), turn_desc + " | 極度集中收斂"
    return max(5, min(final_n, 50)), f"{cap_desc}{turn_desc}"

def calculate_pure_defense_line(df_b_raw, tags, is_filter_active, total_lots, dead_chip_ratio, dynamic_n):
    if not is_valid(df_b_raw): return 0.0, 0, 0, 0.0, []
    valid_df = df_b_raw[~df_b_raw['is_short'] & ~df_b_raw['tag'].isin(["棄守提款", "避險造市"])] if is_filter_active else df_b_raw
    if not is_valid(valid_df): return 0.0, 0, 0, 0.0, []
    
    top_buyers = valid_df.groupby('securities_trader').agg(buy_vol=('buy','sum'), sell_vol=('sell','sum'), buy_amt=('valid_buy_amt','sum'), valid_buy_vol=('valid_buy','sum')).assign(net_vol=lambda x: x['buy_vol'] - x['sell_vol']).query('net_vol > 0').sort_values('net_vol', ascending=False).head(dynamic_n)
    if top_buyers.empty: return 0.0, 0, 0, 0.0, []
    
    core_branch_names = top_buyers.index.tolist()
    valid_top = top_buyers.assign(avg_buy_price=(top_buyers['buy_amt'] / top_buyers['valid_buy_vol'].replace(0, np.nan)).fillna(0)).query('avg_buy_price > 0')
    total_net_vol = valid_top['net_vol'].sum()
    
    vwap = round((valid_top['avg_buy_price'] * valid_top['net_vol']).sum() / total_net_vol, 2) if total_net_vol > 0 else 0.0
    full_net_accum, active_buyers = int(top_buyers['net_vol'].sum() / 1000), len(top_buyers)
    
    c_value = 0.0
    if total_lots > 0:
        free_float_lots = total_lots * ((100.0 - max(0.0, min(99.9, float(dead_chip_ratio)))) / 100.0)
        if free_float_lots > 0: c_value = round(min(98.0, (full_net_accum / free_float_lots) * 100), 2)
    return vwap, full_net_accum, active_buyers, c_value, core_branch_names

def get_core_period_net(df_raw, rank_dates, core_names):
    if not is_valid(df_raw) or not rank_dates or not core_names: return 0
    df_rank = df_raw[df_raw['date'].isin(rank_dates) & df_raw['securities_trader'].isin(core_names)]
    return int(round((df_rank['buy'].sum() - df_rank['sell'].sum()) / 1000))

def process_price(df):
    if not is_valid(df): return pd.DataFrame()
    df_out = df.rename(columns={"date":"日期","close":"收盤價(元)","spread":"漲跌(元)","open":"開盤價(元)","max":"最高價(元)","min":"最低價(元)"})
    for col in ["收盤價(元)", "開盤價(元)", "最高價(元)", "最低價(元)", "漲跌(元)"]:
        if col in df_out.columns: df_out[col] = safe_to_num(df_out[col])
    df_out['成交量(張)'] = (safe_to_num(df_out.get('Trading_Volume', df_out.get('Trading_volume', 0))) / 1000).round().astype(int)
    df_out = df_out.loc[:, ~df_out.columns.duplicated()].assign(斷頭價_078=lambda x: (x["收盤價(元)"] * 0.78).round(2)).rename(columns={'斷頭價_078': '斷頭價(0.78)'})
    return df_out[[c for c in ['日期','成交量(張)','開盤價(元)','最高價(元)','最低價(元)','收盤價(元)','漲跌(元)','斷頭價(0.78)'] if c in df_out.columns]].sort_values('日期', ascending=False)

def render_volume_profile(df_raw, rank_dates, top_n=15):
    if not is_valid(df_raw) or not rank_dates: return st.warning("查無足夠資料產生建倉成本分佈圖。")
    df_rank = df_raw[df_raw['date'].isin(rank_dates)]
    rank_sum = (df_rank.groupby('securities_trader')['buy'].sum() - df_rank.groupby('securities_trader')['sell'].sum()) / 1000
    target_traders = rank_sum[rank_sum > 0].nlargest(top_n).index.tolist() + rank_sum[rank_sum < 0].nsmallest(top_n).index.tolist()
    if not target_traders: return st.warning("無符合條件的活躍分點。")

    df_vp = df_rank[(df_rank['securities_trader'].isin(target_traders)) & (df_rank['price'] > 0)].assign(buy_lots=lambda x: x['buy']/1000, sell_lots=lambda x: x['sell']/1000)
    if df_vp.empty: return st.warning("無有效價格資料進行成本區間分析。")

    min_p, max_p = df_vp['price'].min(), df_vp['price'].max()
    if min_p == max_p: df_vp = df_vp.assign(price_bin=f"{min_p:.2f}")
    else:
        bin_edges = np.linspace(min_p, max_p, num=16)
        labels = [f"{bin_edges[i]:.2f} - {bin_edges[i+1]:.2f}" for i in range(len(bin_edges)-1)]
        df_vp = df_vp.assign(price_bin=pd.cut(df_vp['price'], bins=bin_edges, labels=labels, include_lowest=True))

    vp_grouped = df_vp.groupby('price_bin', observed=False)[['buy_lots', 'sell_lots']].sum().fillna(0).assign(total_lots=lambda x: x['buy_lots']+x['sell_lots'], net_lots=lambda x: x['buy_lots']-x['sell_lots'])
    if vp_grouped['total_lots'].sum() == 0: return st.warning("該區間大戶無顯著成交量。")

    poc_idx = vp_grouped['total_lots'].idxmax()
    max_vol = max(1, vp_grouped[['buy_lots', 'sell_lots']].max().max())

    html = ["<div class='full-table-container'><table><thead><tr><th style='width:20%;'>價位區間 (元)</th><th style='width:35%; text-align:left;'>買進量 (大戶建倉)</th><th style='width:35%; text-align:left;'>賣出量 (大戶倒貨)</th><th style='width:10%; text-align:right;'>淨買賣(張)</th></tr></thead><tbody>"]
    for idx, row in vp_grouped.sort_index(ascending=False).iterrows():
        if row['total_lots'] == 0: continue
        b_vol, s_vol, n_vol = int(round(row['buy_lots'])), int(round(row['sell_lots'])), int(round(row['net_lots']))
        b_w, s_w = min(100, b_vol/max_vol*100), min(100, s_vol/max_vol*100)
        poc_star = " <br><span style='color:#f57c00; font-size:12px; font-weight:900;'>[POC 核心防守]</span>" if idx == poc_idx else ""
        html.append(f"<tr style='{'background-color: rgba(255, 193, 7, 0.15);' if idx==poc_idx else ''}'><td style='font-weight:bold; font-size:14px;'>{idx}{poc_star}</td><td><div style='display:flex; align-items:center;'><div style='width:{b_w}%; background-color:#e53935; height:18px; border-radius:2px; margin-right:8px;'></div><span style='font-size:13px; font-weight:bold;'>{b_vol:,}</span></div></td><td><div style='display:flex; align-items:center;'><div style='width:{s_w}%; background-color:#43a047; height:18px; border-radius:2px; margin-right:8px;'></div><span style='font-size:13px; font-weight:bold;'>{s_vol:,}</span></div></td><td style='color:{'#d32f2f' if n_vol>0 else '#2e7d32' if n_vol<0 else '#333'}; font-weight:bold; text-align:right;'>{f'+{n_vol:,}' if n_vol>0 else f'{n_vol:,}' if n_vol!=0 else ''}</td></tr>")
    html.append("</tbody></table></div>")
    st.markdown("".join(html), unsafe_allow_html=True)

def render_institutional_vs_local(df_branch_raw, df_inst, intel_tags, top_n=4):
    if not is_valid(df_branch_raw) or not is_valid(df_inst): return st.warning("查無法人或分點資料可供比對。")
    dates_in_inst = df_inst['日期'].tolist()
    if not dates_in_inst: return
    df_recent = df_branch_raw[df_branch_raw['date'].isin(dates_in_inst)]
    top_branches = ((df_recent.groupby('securities_trader')['buy'].sum() - df_recent.groupby('securities_trader')['sell'].sum()) / 1000).round().astype(int).abs().nlargest(top_n).index.tolist()
    if not top_branches: return
    p_pivot = df_recent.groupby(['date', 'securities_trader']).apply(lambda x: (x['buy'].sum()-x['sell'].sum())/1000).reset_index(name='net').pivot(index='date', columns='securities_trader', values='net').fillna(0).astype(int)
    
    html = ["<div class='full-table-container'><table><thead><tr><th style='position:sticky; left:0; z-index:6;'>日期</th><th style='text-align:right; background-color:#f1f3f5;'>外資(張)</th><th style='text-align:right; background-color:#f1f3f5;'>投信(張)</th>"]
    for tb in top_branches: html.append(f"<th style='text-align:right;'>{tb}<br><span style='font-size:11px; color:#1e3a8a;'>{intel_tags.get(tb, '路人')[:4]}</span></th>")
    html.append("<th style='text-align:center; background-color:#e3f2fd;'>聯合作戰診斷</th></tr></thead><tbody>")
    
    for _, r in df_inst.iterrows():
        d, f_net, i_net = r['日期'], r.get('外資買賣超(張)', 0), r.get('投信買賣超(張)', 0)
        fmt = lambda v: f"<span style='color:#d32f2f; font-weight:bold;'>+{v:,}</span>" if v>0 else f"<span style='color:#2e7d32; font-weight:bold;'>{v:,}</span>" if v<0 else "<span style='color:#bbb;'>0</span>"
        local_net_sum = sum(p_pivot.at[d, tb] for tb in top_branches if d in p_pivot.index and tb in p_pivot.columns)
        inst_sum = f_net + i_net
        diag, bg, color = ("土洋共擊", "rgba(229, 57, 53, 0.15)", "#c62828") if inst_sum>0 and local_net_sum>0 else ("多殺多撤退", "rgba(67, 160, 71, 0.15)", "#2e7d32") if inst_sum<0 and local_net_sum<0 else ("法人接盤", "transparent", "#555") if inst_sum>0 and local_net_sum<0 else ("地方硬扛", "transparent", "#555") if inst_sum<0 and local_net_sum>0 else ("休兵盤整", "transparent", "#aaa")
        html.append(f"<tr><td style='position:sticky; left:0; background-color:#f8f9fa; z-index:4; font-weight:bold; text-align:center;'>{d[5:]}</td><td style='text-align:right; background-color:#fdfdfd;'>{fmt(f_net)}</td><td style='text-align:right; background-color:#fdfdfd;'>{fmt(i_net)}</td>")
        for tb in top_branches: html.append(f"<td style='text-align:right;'>{fmt(p_pivot.at[d, tb] if d in p_pivot.index and tb in p_pivot.columns else 0)}</td>")
        html.append(f"<td style='text-align:center; background-color:{bg}; color:{color}; font-weight:bold; font-size:13px;'>{diag}</td></tr>")
    html.append("</tbody></table></div>")
    st.markdown("".join(html), unsafe_allow_html=True)

def process_branch_v25(df_raw, period, actual_dates, intel_tags, df_price_raw, stick_thresh, global_days):
    try:
        if not is_valid(df_raw) or not is_valid(df_price_raw): return pd.DataFrame()
        latest_close = df_price_raw.sort_values('date', ascending=False)['close'].iloc[0]
        df = df_raw[df_raw['date'].isin(actual_dates[:period])]
        if not is_valid(df): return pd.DataFrame()
        g = df.groupby('securities_trader').agg(bv=('buy','sum'), sv=('sell','sum'), vbv=('valid_buy','sum'), vsv=('valid_sell','sum'), ba=('valid_buy_amt','sum'), sa=('valid_sell_amt','sum')).reset_index()
        g['net'] = round((g['bv'] - g['sv']) / 1000).astype(int)
        g['avg_b'] = (g['ba'] / g['vbv'].replace(0, np.nan)).fillna(0)
        g['avg_s'] = (g['sa'] / g['vsv'].replace(0, np.nan)).fillna(0)
        b, s, out, tv = g[g['net']>0].sort_values('net', ascending=False).head(15).reset_index(drop=True), g[g['net']<0].sort_values('net', ascending=True).head(15).reset_index(drop=True), [], round(g['bv'].sum()/1000) or 1
        for i in range(15):
            r = {}
            if i < len(b):
                tag, bstr = intel_tags.get(b.loc[i,'securities_trader'], '路人'), f"{b.loc[i,'avg_b']:,.2f}" if b.loc[i,'avg_b']>0 else "-"
                r.update({"買超分點": b.loc[i,'securities_trader'], "買_標籤": tag, "買_週期": "短線" if any(x in tag for x in ["突擊","跟風"]) else "中長線" if any(x in tag for x in ["鎖碼","造市","重砲"]) else "波段", "買超(張)": int(b.loc[i,'net']), "買均價": f"(虧) {bstr}" if b.loc[i,'avg_b']>latest_close and b.loc[i,'avg_b']>0 and b.loc[i,'net']>0 else bstr, "佔比": f"{(b.loc[i,'net']/tv)*100:.1f}%"})
            else: r.update({"買超分點": "-", "買_標籤": "-", "買_週期": "-", "買超(張)": 0, "買均價": "-", "佔比": "-"})
            if i < len(s):
                tag_s = intel_tags.get(s.loc[i,'securities_trader'], '路人')
                r.update({"賣超分點": s.loc[i,'securities_trader'], "賣_標籤": tag_s, "賣_週期": "短線" if any(x in tag_s for x in ["突擊","跟風"]) else "中長線" if any(x in tag_s for x in ["鎖碼","造市","重砲"]) else "波段", "賣超(張)": abs(int(s.loc[i,'net'])), "賣均價": f"{s.loc[i,'avg_s']:,.2f}" if s.loc[i,'avg_s']>0 else "-", "佔比_": f"{(abs(s.loc[i,'net'])/tv)*100:.1f}%"})
            else: r.update({"賣超分點": "-", "賣_標籤": "-", "賣_週期": "-", "賣超(張)": 0, "賣均價": "-", "佔比_": "-"})
            out.append(r)
        return pd.DataFrame(out)
    except: return pd.DataFrame()

def process_v27_ultimate_radar(df_wide, dead_chip_input, dynamic_dict, static_val, df_price, df_branch_raw, intel_tags):
    if not is_valid(df_wide, min_len=2): return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df = df_wide.sort_values('日期', ascending=True).assign(dt_end=lambda x: pd.to_datetime(x['日期']))
    if not df_price.empty:
        df_p = df_price[['日期', '收盤價(元)']].drop_duplicates('日期').sort_values('日期').assign(dt=lambda x: pd.to_datetime(x['日期']), 收盤價=lambda x: pd.to_numeric(x['收盤價(元)'], errors='coerce')).assign(ma20=lambda x: x['收盤價'].rolling(20, min_periods=1).mean())
        df = pd.merge_asof(df.sort_values('dt_end'), df_p[['dt', '收盤價(元)', 'ma20']], left_on='dt_end', right_on='dt', direction='backward')
    else: df['收盤價(元)'], df['ma20'] = 0, 0
    df['總人數變率(%)'] = (pd.to_numeric(df['總人數(人)'], errors='coerce').pct_change() * 100).fillna(0).round(2)
    df['總張數'] = pd.to_numeric(df.get('總張數', 0), errors='coerce').fillna(0)
    for c in ['100-200張_比例(%)', '200-400張_比例(%)', '400-600張_比例(%)', '600-800張_比例(%)', '800-1000張_比例(%)', '1000張以上_比例(%)']: df[c] = pd.to_numeric(df.get(c, 0), errors='coerce').fillna(0.0)
    df['pct_100'] = df['1000張以上_比例(%)'] + df['800-1000張_比例(%)'] + df['600-800張_比例(%)'] + df['400-600張_比例(%)'] + df['200-400張_比例(%)'] + df['100-200張_比例(%)']
    df['pct_200'] = df['pct_100'] - df['100-200張_比例(%)']
    df['pct_400'] = df['pct_200'] - df['200-400張_比例(%)']
    df['pct_600'] = df['pct_400'] - df['400-600張_比例(%)']
    df['pct_800'] = df['pct_600'] - df['600-800張_比例(%)']
    df['pct_1000'] = df['1000張以上_比例(%)']

    fake_dict = df_branch_raw[df_branch_raw['is_short']].groupby(['date', 'securities_trader']).apply(lambda x: (x['buy'].sum()-x['sell'].sum())/1000).reset_index(name='net').groupby('date').apply(lambda x: x[['securities_trader', 'net']].to_dict('records')).to_dict() if not df_branch_raw.empty else {}
    arr_dates = np.sort(df_branch_raw['date'].unique()) if not df_branch_raw.empty else np.array([])
    df['safe_dead_ratio'] = df['日期'].apply(lambda d: max(0.0, min(99.9, get_dead_chip_info(d, dead_chip_input, dynamic_dict, static_val, "")[0])))
    df['ct'] = np.array([100, 200, 400, 600, 800, 1000])[np.abs(np.clip(df['總張數'] * np.clip((100 - df['safe_dead_ratio']) / 100, 0.05, 1.0) * 0.01, 100, 1000).to_numpy()[:, None] - np.array([100, 200, 400, 600, 800, 1000])).argmin(axis=1)]
    conds = [df['ct']<=100, df['ct']<=200, df['ct']<=400, df['ct']<=600, df['ct']<=800]
    df['current_large_pct'] = np.select(conds, [df['pct_100'], df['pct_200'], df['pct_400'], df['pct_600'], df['pct_800']], default=df['pct_1000'])
    for c in ['pct_100', 'pct_200', 'pct_400', 'pct_600', 'pct_800', 'pct_1000']: df[f'prev_{c}'] = df[c].shift(1)
    df['raw_chg'] = (df['current_large_pct'] - np.select(conds, [df['prev_pct_100'], df['prev_pct_200'], df['prev_pct_400'], df['prev_pct_600'], df['prev_pct_800']], default=df['prev_pct_1000'])).fillna(0).round(2)

    def get_impact(row):
        if row.name == df.index[0] or row['總張數']<=0 or len(arr_dates)==0: return 0.0, []
        idx = np.searchsorted(arr_dates, row['日期'], side='right') - 1
        if idx >= 0 and (row['dt_end'] - pd.to_datetime(arr_dates[idx])).days <= 7 and arr_dates[idx] in fake_dict:
            f_vol = sum(fr['net'] for fr in fake_dict[arr_dates[idx]] if fr['net'] >= row['ct'])
            return (f_vol / max(1, row['總張數'])) * 100, [{"日期": row['日期'], "分點": fr['securities_trader'], "張數": round(fr['net'])} for fr in fake_dict[arr_dates[idx]] if fr['net'] >= row['ct']]
        return 0.0, []

    impact_res = df.apply(get_impact, axis=1)
    df['f_impact'] = impact_res.apply(lambda x: x[0]).round(2)
    df['p_chg'] = (df['raw_chg'] - df['f_impact']).round(2)
    df.loc[df.index[0], 'p_chg'] = 0.0  

    def build_diag(row):
        if row.name == df.index[0]: return "初始化"
        if row['總張數'] <= 0: return "股本為零"
        adv, lev = [], 100 / (100 - row['safe_dead_ratio']) if 0 <= row['safe_dead_ratio'] < 100 else 1
        if row['總人數變率(%)'] > 2.0 and row['p_chg'] < 0: adv.append(f"散戶增{row['總人數變率(%)']}%，大戶實質倒貨{abs(row['p_chg'])}%")
        else:
            if row['p_chg'] * lev > 2.5 and row['收盤價(元)'] > row['ma20']: adv.append(f"站上月線且純淨買超{round(row['p_chg']*lev, 2)}%")
            elif row['p_chg'] > 0.4 and row['收盤價(元)'] < row['ma20']: adv.append(f"破月線但吃貨{row['p_chg']}%")
            elif row['p_chg'] < -1.0: adv.append(f"實質流出{abs(row['p_chg'])}%")
            if row['f_impact'] > 1.2: adv.append(f"虛胖買盤潛藏{row['f_impact']}%危機")
        return " | ".join(adv) if adv else "盤整"

    df['專家雷達診斷'] = df.apply(build_diag, axis=1)
    res_df = df[['日期', '收盤價(元)', 'current_large_pct', '總人數變率(%)', 'raw_chg', 'f_impact', 'p_chg', '專家雷達診斷']].rename(columns={'current_large_pct':'大戶原持股(%)', 'raw_chg':'原始大戶變動(%)', 'f_impact':'當沖虛胖(%)', 'p_chg':'純淨大戶變動(%)'}).sort_values('日期', ascending=False)
    return res_df[~res_df['專家雷達診斷'].str.contains('初始化', na=False)], df[['日期', 'raw_chg', 'f_impact', 'p_chg']].iloc[1:], pd.DataFrame([item for sublist in impact_res.apply(lambda x: x[1]) for item in sublist])

def calculate_disposition_thresholds_v2(df_price, df_day_trade, total_lots):
    if not is_valid(df_price, min_len=6): return None
    closes, lows, volumes = df_price['收盤價(元)'].tolist()[::-1], df_price['最低價(元)'].tolist()[::-1], df_price['成交量(張)'].tolist()[::-1]
    res = {'limit_6d': closes[-6]*1.32 if len(closes)>=6 else None, 'limit_amp': min(lows[-5:])*1.25 if len(lows)>=5 else None, 'limit_30d': closes[-30]*2.0 if len(closes)>=30 else None, 'limit_60d': closes[-60]*2.3 if len(closes)>=60 else None, 'day_trade_warning': False}
    if len(df_day_trade) >= 2 and len(volumes) >= 6:
        dt_ratios = [d/v if v>0 else 0 for d, v in zip(df_day_trade['當沖總張數'].tolist()[:2], reversed(volumes[-2:]))]
        if len(dt_ratios) >= 2 and dt_ratios[0] > 0.6 and dt_ratios[1] > 0.6: res['day_trade_warning'] = True
    if total_lots > 0:
        res['current_5d_turnover'] = (sum(volumes[-5:]) / total_lots) * 100
        res['max_vol_6d'], res['max_vol_1d'], res['turnover_warning'] = (total_lots * 0.5) - sum(volumes[-5:]), total_lots * 0.1, res['current_5d_turnover'] > 10.0
    return res

def process_tdcc_dynamic_v2(df_share_wide, df_price, dead_chip_input, dynamic_dict, static_val, chip_engine):
    if not is_valid(df_share_wide) or not is_valid(df_price): return pd.DataFrame()
    df_m = pd.merge_asof(df_share_wide.assign(dt=pd.to_datetime(df_share_wide['日期'])).sort_values('dt'), df_price[['日期', '收盤價(元)']].assign(dt=pd.to_datetime(df_price['日期'])).drop_duplicates('dt').sort_values('dt'), on='dt', direction='backward').sort_values('dt', ascending=False).dropna(subset=['收盤價(元)']).query('`收盤價(元)` > 0')
    if df_m.empty: return pd.DataFrame()
    for c in ['100-200張_比例(%)', '200-400張_比例(%)', '400-600張_比例(%)', '600-800張_比例(%)', '800-1000張_比例(%)', '1000張以上_比例(%)']: df_m[c] = pd.to_numeric(df_m.get(c, 0), errors='coerce').fillna(0.0)
    df_m['pct_100'] = df_m['1000張以上_比例(%)'] + df_m['800-1000張_比例(%)'] + df_m['600-800張_比例(%)'] + df_m['400-600張_比例(%)'] + df_m['200-400張_比例(%)'] + df_m['100-200張_比例(%)']
    df_m['pct_200'] = df_m['pct_100'] - df_m['100-200張_比例(%)']
    df_m['pct_400'] = df_m['pct_200'] - df_m['200-400張_比例(%)']
    df_m['pct_600'] = df_m['pct_400'] - df_m['400-600張_比例(%)']
    df_m['pct_800'] = df_m['pct_600'] - df_m['600-800張_比例(%)']
    df_m['pct_1000'] = df_m['1000張以上_比例(%)']
    dead_info = df_m['日期'].apply(lambda d: get_dead_chip_info(d, dead_chip_input, dynamic_dict, static_val, chip_engine))
    df_m['safe_dead_ratio'], df_m['cl'] = dead_info.apply(lambda x: max(0.0, min(99.9, x[0]))), dead_info.apply(lambda x: x[1])
    df_m['ct'] = np.array([100, 200, 400, 600, 800, 1000])[np.abs(np.clip(df_m['總張數'] * np.clip((100 - df_m['safe_dead_ratio']) / 100, 0.05, 1.0) * 0.01, 100, 1000).to_numpy()[:, None] - np.array([100, 200, 400, 600, 800, 1000])).argmin(axis=1)]
    df_m['lp'] = np.select([df_m['ct']<=100, df_m['ct']<=200, df_m['ct']<=400, df_m['ct']<=600, df_m['ct']<=800], [df_m['pct_100'], df_m['pct_200'], df_m['pct_400'], df_m['pct_600'], df_m['pct_800']], default=df_m['pct_1000'])
    df_m['cd'] = np.where((df_m['safe_dead_ratio']>0) & (df_m['safe_dead_ratio']<100), np.round(np.maximum(0, (df_m['lp'] - df_m['safe_dead_ratio']) / (100.0 - df_m['safe_dead_ratio'])) * 100, 2), "-")
    df_m['st_val'] = np.select([df_m['lp']>80.0, df_m['lp']>70.0, (df_m['lp']>=40.0)&(df_m['lp']<=70.0)], ["極度集中 (防無量倒貨)", "高度鎖碼", "波段甜區 (易吸量推升)"], default="籌碼渙散")
    return pd.DataFrame({"日期": df_m['日期'], "收盤價(元)": df_m['收盤價(元)'].round(2), "大戶精算門檻": "系統判定 (" + df_m['ct'].astype(int).astype(str) + "張)", "大戶原持股(%)": df_m['lp'].round(2), "董監死籌碼(%)": np.where(df_m['safe_dead_ratio']>0, df_m['safe_dead_ratio'].apply(lambda x: f"{x:.2f}%") + " (" + df_m['cl'] + ")", "-"), "純淨活大戶C_Value(%)": df_m['cd'], "實戰判定": df_m['st_val']})

def process_branch_diff_v2(df_raw, actual_dates, fire_thresh, period_days=10):
    if not is_valid(df_raw) or not actual_dates: return pd.DataFrame()
    out, branch_grouped = [], dict(tuple(df_raw[['date', 'securities_trader', 'buy', 'sell']].groupby('date')))
    for d in actual_dates[:period_days]:
        if d not in branch_grouped: continue
        df_d = branch_grouped[d]
        b_cnt, s_cnt = df_d[df_d['buy']>0]['securities_trader'].nunique(), df_d[df_d['sell']>0]['securities_trader'].nunique()
        act_cnt = df_d[(df_d['buy']>0)|(df_d['sell']>0)]['securities_trader'].nunique()
        firepower = (df_d['buy'].sum()/b_cnt) / (df_d['sell'].sum()/s_cnt) if s_cnt>0 and df_d['sell'].sum()>0 else (99.9 if df_d['buy'].sum()>0 else 1.0)
        g_net = df_d.groupby('securities_trader').apply(lambda x: x['buy'].sum()-x['sell'].sum())
        main_power = (g_net[g_net>0].nlargest(15).sum() - abs(g_net[g_net<0].nsmallest(15).sum())) / df_d['buy'].sum() * 100 if df_d['buy'].sum()>0 else 0
        diag = []
        if firepower >= fire_thresh and ((s_cnt-b_cnt)/act_cnt*100 if act_cnt>0 else 0) > 5: diag.append(f"大戶火力壓制 ({fire_thresh}倍↑)")
        elif firepower < 0.7 and (b_cnt-s_cnt) > 50: diag.append("散戶進場 (主力倒貨)")
        if main_power > 15: diag.append(f"重兵集結 (買力 {main_power:.1f}%)")
        elif main_power < -15: diag.append(f"強力倒貨 (賣力 {abs(main_power):.1f}%)")
        out.append({"日期": d, "活躍家數": act_cnt, "買賣家數差": b_cnt-s_cnt, "籌碼集中度(%)": round((s_cnt-b_cnt)/act_cnt*100 if act_cnt>0 else 0, 1), "買方火力(倍)": round(firepower, 2), "主力成交力(%)": round(main_power, 2), "鷹眼診斷": " | ".join(diag) if diag else "中性換手"})
    return pd.DataFrame(out)

def process_v30_daily_tracking(df_branch_raw, intel_tags, df_price, df_branch_diff, actual_dates, fire_thresh, period_days=5):
    if not is_valid(df_branch_raw) or len(actual_dates) < period_days: return pd.DataFrame(), pd.DataFrame()
    out, audit_smart = [], []
    df_b = df_branch_raw[df_branch_raw['date'].isin(actual_dates[:period_days])]
    smart_dict = dict(tuple(df_b[df_b['is_smart']].groupby(['date', 'securities_trader', 'tag']).agg(bs=('buy','sum'), ss=('sell','sum'), ba=('valid_buy_amt','sum'), sa=('valid_sell_amt','sum')).reset_index().assign(net_vol=lambda x: ((x['bs']-x['ss'])/1000).round().astype(int)).groupby('date')))
    short_dict = dict(tuple(df_b[df_b['is_short']].groupby(['date', 'securities_trader']).agg(bs=('buy','sum'), ss=('sell','sum')).reset_index().assign(net_vol=lambda x: ((x['bs']-x['ss'])/1000).round().astype(int)).groupby('date')))
    price_dict, diff_dict = df_price.set_index('日期').to_dict('index') if not df_price.empty else {}, df_branch_diff.set_index('日期').to_dict('index') if not df_branch_diff.empty else {}
    
    for d in actual_dates[:period_days]:
        pr, df_d = price_dict.get(d, {}), diff_dict.get(d, {})
        cp, op, hp, lp, sp = pr.get('收盤價(元)', 0), pr.get('開盤價(元)', 0), pr.get('最高價(元)', 0), pr.get('最低價(元)', 0), float(re.sub(r'[+,]', '', str(pr.get('漲跌(元)', 0))) or 0)
        sg, sh = smart_dict.get(d, pd.DataFrame()), short_dict.get(d, pd.DataFrame())
        if d == actual_dates[0] and not sg.empty: audit_smart.extend([{"日期": d, "分點": r['securities_trader'], "標籤": r['tag'], "淨買超(張)": r['net_vol']} for _, r in sg.iterrows() if r['net_vol']!=0])
        s_net, s_trap = sg['net_vol'].sum() if not sg.empty else 0, sh[sh['net_vol']>0]['net_vol'].sum() if not sh.empty else 0
        s_long = sg[sg['bs'] > sg['ss']] if not sg.empty else pd.DataFrame()
        s_cost = max(0.0, (s_long['ba']-s_long['sa']).sum() / (s_long['bs']-s_long['ss']).sum()) if not s_long.empty and (s_long['bs']-s_long['ss']).sum()>0 else 0.0
        gap, adv = cp - s_cost if s_cost>0 and cp>0 else 0, []
        if cp <= 0: adv.append("暫停交易")
        else:
            if hp-lp > 0 and (min(cp, op)-lp)/(hp-lp) > 0.5 and s_net > 0: adv.append("探底洗盤成功")
            if s_cost == 0 and s_net < 0: adv.append("[危險]無本出貨")
            elif s_net > 300 and df_d.get('買方火力(倍)',1.0) > 1.5: adv.append("[重擊點火]")
            elif s_net > 50 and gap > 0: adv.append("主動鎖碼")
            elif s_net < -100 and sp > 0: adv.append("拉高派發")
        adv.append(df_d.get('鷹眼診斷', "中性換手"))
        out.append({"日期": d, "收盤價(元)": cp or "-", "漲跌(元)": pr.get('漲跌(元)', "-"), "聰明錢淨流(張)": int(s_net), "大戶淨加權均價": round(s_cost, 2) if s_cost>0 else ("0(無本)" if s_cost==0 and not s_long.empty else "-"), "均價落差": round(gap, 2) if s_cost>0 and cp>0 else "-", "活躍家數": df_d.get('活躍家數',0), "買賣家數差": df_d.get('買賣家數差',0), "籌碼集中度(%)": df_d.get('籌碼集中度(%)',0), "買方火力(倍)": df_d.get('買方火力(倍)',1.0), "潛在賣壓(張)": int(s_trap), "綜合診斷": " | ".join(set(adv))})
    return pd.DataFrame(out), pd.DataFrame(audit_smart).sort_values('淨買超(張)', ascending=False) if audit_smart else pd.DataFrame()

def clean_level_by_math(x):
    s = re.sub(r'[, ]|\.0', '', str(x))
    if s in _LEVEL_CLEAN_CACHE: return _LEVEL_CLEAN_CACHE[s]
    res = "合計"
    if s and s not in ["合計", "總計", "差異數"]:
        if "以上" in s: res = "1000張以上"
        elif s.isdigit() and int(s) == 99: res = "合計"
        elif s.isdigit() and 1 <= int(s) <= 14: res = _LEVEL_MAP.get(int(s), s)
        elif s.isdigit() and int(s) >= 15: res = "1000張以上"
        else:
            n = _num_re.findall(s)
            if not n: res = s
            elif len(n) > 1:
                u = int(n[-1])
                res = "1-999股" if u<=999 else "1-5張" if u<=5000 else "5-10張" if u<=10000 else "10-15張" if u<=15000 else "15-20張" if u<=20000 else "20-30張" if u<=30000 else "30-40張" if u<=40000 else "40-50張" if u<=50000 else "50-100張" if u<=100000 else "100-200張" if u<=200000 else "200-400張" if u<=400000 else "400-600張" if u<=600000 else "600-800張" if u<=800000 else "800-1000張" if u<=1000000 else "1000張以上"
            else:
                v = int(n[0])
                res = _LEVEL_MAP.get(v, "1000張以上") if v<=21 else ("1000張以上" if v>=1000000 else "800-1000張" if v>=800000 else "600-800張" if v>=600000 else "400-600張" if v>=400000 else "200-400張" if v>=200000 else "100-200張" if v>=100000 else "50-100張" if v>=5000 else "40-50張" if v>=40000 else "30-40張" if v>=30000 else "20-30張" if v>=20000 else "15-20張" if v>=15000 else "10-15張" if v>=10000 else "5-10張" if v>=5000 else "1-5張" if v>=1000 else "1-999股")
    _LEVEL_CLEAN_CACHE[s] = res
    return res

def process_tdcc(df):
    if not is_valid(df, ['HoldingSharesLevel']): return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    df = df[~df['HoldingSharesLevel'].astype(str).str.contains('差異數', na=False)].copy()
    df['LevelClean'] = df['HoldingSharesLevel'].apply(clean_level_by_math)
    df['unit'] = (safe_to_num(df.get('HoldingShares', df.get('unit', 0))) / 1000).round().astype(int)
    df['people'] = safe_to_num(df.get('people', 0)).astype(int)
    df_levels = df[~df['LevelClean'].str.contains('合計|總計', na=False)]
    p_u, p_p = df_levels.pivot_table(index='date', columns='LevelClean', values='unit', aggfunc='sum').reset_index().fillna(0), df_levels.pivot_table(index='date', columns='LevelClean', values='people', aggfunc='sum').reset_index().fillna(0)
    lvls = ['1-999股', '1-5張', '5-10張', '10-15張', '15-20張', '20-30張', '30-40張', '40-50張', '50-100張', '100-200張', '200-400張', '400-600張', '600-800張', '800-1000張', '1000張以上']
    for l in lvls:
        if l not in p_u.columns: p_u[l] = 0
        if l not in p_p.columns: p_p[l] = 0
    df_t = pd.DataFrame({'date': p_u['date'], '總張數': p_u[lvls].sum(axis=1), '總人數(人)': p_p[lvls].sum(axis=1)})
    df_w = df_t.copy()
    for l in lvls: df_w[f"{l}_張數"], df_w[f"{l}_人數"], df_w[f"{l}_比例(%)"] = p_u[l], p_p[l], (p_u[l]/df_t['總張數'].replace(0, np.nan)*100).fillna(0).round(2)
    return df_w.rename(columns={'date':'日期'}).sort_values('日期', ascending=False).head(15), pd.merge(df_t[['date','總張數']], p_u[['date']+lvls], on='date').rename(columns={'date':'日期'}).sort_values('日期', ascending=False).head(15), pd.merge(df_t[['date','總人數(人)']], p_p[['date']+lvls], on='date').rename(columns={'date':'日期'}).sort_values('日期', ascending=False).head(15)

def process_day_trading(df):
    if not is_valid(df): return pd.DataFrame()
    df_out = df.copy().rename(columns={"date": "日期"})
    df_out['當沖總張數'] = (safe_to_num(df_out.get('DayTradingVolume', df_out.get('Volume', 0))) / 1000).round().astype(int)
    return df_out[['日期', '當沖總張數']].tail(10).sort_values('日期', ascending=False)

def process_margin_and_lending(df_margin_raw, df_lending_raw):
    if not is_valid(df_margin_raw): return pd.DataFrame()
    df_m = df_margin_raw.rename(columns={"date": "日期", "MarginPurchaseBuy": "融資買進(萬元)", "MarginPurchaseSell": "融資賣出(萬元)", "MarginPurchaseCashRepayment": "融資現償(萬元)", "MarginPurchaseTodayBalance": "融資餘額(萬元)", "ShortSaleBuy": "融券買進(張)", "ShortSaleSell": "融券賣出(張)", "ShortSaleTodayBalance": "融券餘額(張)", "OffsetLoanAndShort": "資券相抵(張)"})
    for c in ["融資買進(萬元)", "融資賣出(萬元)", "融資現償(萬元)", "融資餘額(萬元)", "融券買進(張)", "融券賣出(張)", "融券餘額(張)", "資券相抵(張)", "MarginPurchaseYesterdayBalance", "ShortSaleYesterdayBalance"]:
        if c in df_m.columns: df_m[c] = safe_to_num(df_m[c]).round().astype(int)
    if '融資餘額(萬元)' in df_m.columns and 'MarginPurchaseYesterdayBalance' in df_m.columns: df_m['融資增減(萬元)'] = df_m['融資餘額(萬元)'] - df_m['MarginPurchaseYesterdayBalance']
    if '融券餘額(張)' in df_m.columns and 'ShortSaleYesterdayBalance' in df_m.columns: df_m['融券增減(張)'] = df_m['融券餘額(張)'] - df_m['ShortSaleYesterdayBalance']
    df_m['本日借券成交(張)'] = 0
    if is_valid(df_lending_raw, ['date', 'volume']): df_m = pd.merge(df_m, df_lending_raw.assign(volume=lambda x: safe_to_num(x['volume'])).groupby('date')['volume'].sum().reset_index().assign(本日借券成交=lambda x: (x['volume']/1000).round().astype(int)).rename(columns={'date':'日期', '本日借券成交':'本日借券成交(張)'}), on='日期', how='left').fillna(0)
    return df_m[[c for c in ['日期','融資買進(萬元)','融資賣出(萬元)','融資現償(萬元)','融資餘額(萬元)','融資增減(萬元)','融券買進(張)','融券賣出(張)','融券餘額(張)','融券增減(張)','資券相抵(張)','本日借券成交(張)'] if c in df_m.columns]].tail(10).sort_values('日期', ascending=False)

def process_securities_lending_detail(df):
    if not is_valid(df, ['date', 'volume']): return pd.DataFrame()
    df_out = df.assign(volume=lambda x: (safe_to_num(x['volume'])/1000).round().astype(int), fee_rate=lambda x: safe_to_num(x.get('fee_rate', 0.0)), transaction_type=lambda x: x.get('transaction_type', '未知'))
    res = df_out.groupby('date').agg(總成交張數=('volume', 'sum'), 平均費率=('fee_rate', 'mean')).join(df_out.pivot_table(index='date', columns='transaction_type', values='volume', aggfunc='sum', fill_value=0)).reset_index().rename(columns={'date': '日期', '平均費率': '平均費率(%)', '定價': '定價交易(張)', '競價': '競價交易(張)', '議借': '議借交易(張)'}).fillna(0)
    for c in ['定價交易(張)', '競價交易(張)', '議借交易(張)']:
        if c not in res.columns: res[c] = 0
    return res[['日期', '總成交張數', '平均費率(%)', '定價交易(張)', '競價交易(張)', '議借交易(張)']].tail(10).sort_values('日期', ascending=False)

def process_block_trading(df_block_raw, rank_dates):
    if not is_valid(df_block_raw, ['date']): return pd.DataFrame()
    df_b = df_block_raw[df_block_raw['date'].isin(rank_dates[:5])].rename(columns={"date": "日期", "trade_type": "交易類別", "price": "成交價(元)", "volume": "成交張數", "trading_money": "成交金額(萬元)"})
    if df_b.empty: return pd.DataFrame()
    if '成交張數' in df_b.columns: df_b['成交張數'] = (safe_to_num(df_b['成交張數']) / 1000).round().astype(int)
    if '成交金額(萬元)' in df_b.columns: df_b['成交金額(萬元)'] = (safe_to_num(df_b['成交金額(萬元)']) / 10000).round().astype(int)
    return df_b[[c for c in ['日期', '交易類別', '成交價(元)', '成交張數', '成交金額(萬元)'] if c in df_b.columns]].sort_values(['日期', '成交金額(萬元)'], ascending=[False, False])

def process_inst(df):
    if not is_valid(df): return pd.DataFrame()
    pdf = df.pivot_table(index='date', columns='name', values=['buy', 'sell'], fill_value=0).reset_index()
    pdf.columns = ['_'.join(c).strip('_') for c in pdf.columns.values]
    out = pd.DataFrame({'日期': pdf['date']})
    out['外資買賣超(張)'] = ((safe_to_num(pdf.get('buy_Foreign_Investor', 0)) - safe_to_num(pdf.get('sell_Foreign_Investor', 0))) / 1000).round().astype(int)
    out['投信買賣超(張)'] = ((safe_to_num(pdf.get('buy_Investment_Trust', 0)) - safe_to_num(pdf.get('sell_Investment_Trust', 0))) / 1000).round().astype(int)
    out['自營商(自行)買賣超(張)'] = ((safe_to_num(pdf.get('buy_Dealer_self', pdf.get('buy_Dealer', 0))) - safe_to_num(pdf.get('sell_Dealer_self', pdf.get('sell_Dealer', 0)))) / 1000).round().astype(int)
    out['自營商(避險)買賣超(張)'] = ((safe_to_num(pdf.get('buy_Dealer_Hedging', 0)) - safe_to_num(pdf.get('sell_Dealer_Hedging', 0))) / 1000).round().astype(int)
    out['三大法人買賣超(張)'] = out['外資買賣超(張)'] + out['投信買賣超(張)'] + out['自營商(自行)買賣超(張)'] + out['自營商(避險)買賣超(張)']
    return out.tail(10).sort_values('日期', ascending=False)

def process_fut_inst(df):
    if not is_valid(df): return pd.DataFrame()
    group_col = 'name' if 'name' in df.columns else 'institutional_investors'
    if group_col not in df.columns: return pd.DataFrame()
    pdf = df.assign(net=lambda x: safe_to_num(x['long_open_interest_balance_volume']) - safe_to_num(x['short_open_interest_balance_volume'])).pivot_table(index='date', columns=group_col, values='net', fill_value=0).reset_index()
    col_map = {'date': '日期'}
    for c in pdf.columns:
        if '外資' in str(c) or 'Foreign' in str(c): col_map[c] = '外資多空(口)'
        elif '投信' in str(c) or 'Investment' in str(c): col_map[c] = '投信多空(口)'
        elif '自營' in str(c) or 'Dealer' in str(c): col_map[c] = '自營多空(口)'
    pdf = pdf.rename(columns=col_map)
    for col in ['外資多空(口)', '投信多空(口)', '自營多空(口)']:
        if col not in pdf.columns: pdf[col] = 0
    return pdf[['日期', '外資多空(口)', '投信多空(口)', '自營多空(口)']].tail(10).sort_values('日期', ascending=False)

def process_per(df):
    if not is_valid(df): return pd.DataFrame()
    df_out = df.rename(columns={"date":"日期","dividend_yield":"殖利率(%)","PER":"本益比(倍)","PBR":"淨值比(倍)"}).loc[:, ~df.columns.duplicated()]
    for col in ["殖利率(%)", "本益比(倍)", "淨值比(倍)"]:
        if col in df_out.columns: df_out[col] = safe_to_num(df_out[col]).round(2)
    return df_out[[c for c in ['日期', '本益比(倍)', '淨值比(倍)', '殖利率(%)'] if c in df_out.columns]].tail(10).sort_values('日期', ascending=False)

def process_disp(df):
    if not is_valid(df): return pd.DataFrame()
    return df.rename(columns={"date":"公告日期","disposition_cnt":"處置次數","condition":"處置條件","measure":"處置措施","period_start":"處置起日","period_end":"處置迄日"})[[c for c in ['公告日期', '處置次數', '處置起日', '處置迄日', '處置條件', '處置措施'] if c in df.columns]].tail(5).sort_values('公告日期', ascending=False)

def process_div(df):
    if not is_valid(df): return pd.DataFrame()
    df_out = df.rename(columns={"date": "公告日期", "year": "股利年份", "StockEarningsDistribution": "盈餘配股(元)", "StockStatutorySurplus": "公積配股(元)", "CashEarningsDistribution": "盈餘配息(元)", "CashStatutorySurplus": "公積配息(元)"})
    if '股利年份' in df_out.columns:
        df_out['股利年份'] = df_out['股利年份'].astype(str).str.extract(r'^(\d+)', expand=False)
        return df_out[df_out['股利年份'].isin(sorted(safe_to_num(df_out['股利年份'], np.nan).dropna().unique(), reverse=True)[:5])].sort_values('公告日期', ascending=False).head(10)
    return df_out.sort_values('公告日期', ascending=False).head(10)

def process_cbas(df, current_stock_price, df_cb_info=None):
    if not is_valid(df): return pd.DataFrame()
    df_out = df.rename(columns={"date": "日期", "cb_id": "可轉債代號", "cb_name": "可轉債名稱", "conversion_price": "轉換價(元)", "underlying_stock_price": "標的股價(元)", "outstanding_amount": "未償還餘額", "close": "CB收盤價"})
    if "可轉債代號" in df_out.columns: df_out['可轉債代號'] = df_out['可轉債代號'].astype(str).str.replace(r'(\.0$|,)', '', regex=True).str.strip()
    for c in ["轉換價(元)", "標的股價(元)", "未償還餘額", "CB收盤價"]:
        if c in df_out.columns: df_out[c] = safe_to_num(df_out[c], np.nan)
    if "標的股價(元)" not in df_out.columns or df_out["標的股價(元)"].isna().all(): df_out["標的股價(元)"] = current_stock_price
    if "標的股價(元)" in df_out.columns and "轉換價(元)" in df_out.columns:
        df_out["轉換價值"] = (df_out["標的股價(元)"] / df_out["轉換價(元)"].replace(0, np.nan) * 100).round(2)
        if "CB收盤價" in df_out.columns: df_out["溢價率(%)"] = ((df_out["CB收盤價"] - df_out["轉換價值"]) / df_out["轉換價值"].replace(0, np.nan) * 100).round(2)
    if df_cb_info is not None and not df_cb_info.empty and "未償還餘額" in df_out.columns:
        df_cb_info_clean = df_cb_info.rename(columns={"stock_id": "可轉債代號", "bond_id": "可轉債代號", "cb_id": "可轉債代號", "issue_amount": "發行總額", "maturity_date": "到期日"}).drop_duplicates('可轉債代號')
        df_cb_info_clean['可轉債代號'] = df_cb_info_clean['可轉債代號'].astype(str).str.replace(r'(\.0$|,)', '', regex=True).str.strip()
        df_out = pd.merge(df_out, df_cb_info_clean, on='可轉債代號', how='left')
        if "發行總額" in df_out.columns: df_out["未償還比例(%)"] = (df_out["未償還餘額"] / safe_to_num(df_out["發行總額"], np.nan).replace(0, np.nan) * 100).round(2)
    return df_out[[c for c in ["日期", "可轉債代號", "可轉債名稱", "CB收盤價", "標的股價(元)", "轉換價(元)", "轉換價值", "溢價率(%)", "未償還餘額", "未償還比例(%)", "到期日"] if c in df_out.columns]]

def process_technical_analysis(df_price, s_ma, m_ma, l_ma):
    if not is_valid(df_price, ['收盤價(元)', '日期'], 30): return pd.DataFrame()
    df_ta = df_price.sort_values('日期', ascending=True).assign(收盤價=lambda x: pd.to_numeric(x['收盤價(元)'], errors='coerce'))
    df_ta[f'MA{s_ma}'], df_ta[f'MA{m_ma}(中線)'], df_ta[f'MA{l_ma}(長線)'] = df_ta['收盤價'].rolling(s_ma, min_periods=1).mean().round(2), df_ta['收盤價'].rolling(m_ma, min_periods=1).mean().round(2), df_ta['收盤價'].rolling(l_ma, min_periods=1).mean().round(2)
    return df_ta.sort_values('日期', ascending=False)

def process_linear_regression(df_price, lr_days):
    if not is_valid(df_price, ['收盤價(元)'], 2): return pd.DataFrame()
    df_lr = df_price.head(lr_days).sort_values('日期', ascending=True).assign(收盤價=lambda x: pd.to_numeric(x['收盤價(元)'], errors='coerce'))
    y = df_lr['收盤價'].dropna().values
    if len(y) < 2: return pd.DataFrame()
    x = np.arange(len(y))
    m, c = np.linalg.lstsq(np.vstack([x, np.ones(len(x))]).T, y, rcond=None)[0]
    std_err = np.std(y - (m * x + c))
    return df_lr.assign(LR_Mid=m*x+c, LR_Upper=(m*x+c)+2*std_err, LR_Lower=(m*x+c)-2*std_err)[['日期', 'LR_Mid', 'LR_Upper', 'LR_Lower']]

def process_geometric_patterns(df_price, kline_days, order, mode, current_price):
    if not is_valid(df_price, min_len=order * 2): return {}
    df = df_price.head(kline_days).sort_values('日期', ascending=True).reset_index(drop=True)
    lows_vals, highs_vals, dates_vals = df['最低價(元)'].values, df['最高價(元)'].values, df['日期'].values
    highs, lows = [], []
    for i in range(order, len(df) - order):
        if lows_vals[i] == np.min(lows_vals[i-order:i+order+1]): lows.append((dates_vals[i], float(lows_vals[i]), i))
        if highs_vals[i] == np.max(highs_vals[i-order:i+order+1]): highs.append((dates_vals[i], float(highs_vals[i]), i))
    if len(lows) < 2 or len(highs) < 2: return {}
    last_date, tol, is_auto = dates_vals[-1], 0.03, "Auto" in mode
    
    if "三重底" in mode or is_auto:
        if len(lows) >= 3 and lows[-3][1]>0 and lows[-2][1]>0 and abs(lows[-3][1]-lows[-2][1])/lows[-3][1]<tol and abs(lows[-2][1]-lows[-1][1])/lows[-2][1]<tol:
            b_h = [h for h in highs if lows[-3][2] < h[2] < lows[-1][2]]
            if b_h:
                h_max = max(b_h, key=lambda x: x[1])
                return {'name': '三重底', 'shape_x': [lows[-3][0], b_h[0][0], lows[-2][0], b_h[-1][0], lows[-1][0]], 'shape_y': [lows[-3][1], b_h[0][1], lows[-2][1], b_h[-1][1], lows[-1][1]], 'neck_x': [lows[-3][0], last_date], 'neck_y': [h_max[1], h_max[1]], 'color': '#9c27b0', 'desc': f"三重底 ({'已突破' if current_price>h_max[1] else '成型中'})", 'signal': 'bullish'}
    
    if "W底" in mode or is_auto:
        if len(lows) >= 2 and lows[-2][1]>0:
            b_h = [h for h in highs if lows[-2][2] < h[2] < lows[-1][2]]
            if b_h and (abs(lows[-2][1]-lows[-1][1])/lows[-2][1] <= tol or "W底" in mode):
                h_max = max(b_h, key=lambda x: x[1])
                return {'name': 'W底', 'shape_x': [lows[-2][0], h_max[0], lows[-1][0]], 'shape_y': [lows[-2][1], h_max[1], lows[-1][1]], 'neck_x': [lows[-2][0], last_date], 'neck_y': [h_max[1], h_max[1]], 'color': '#9c27b0', 'desc': f"W底 ({'已突破' if current_price>h_max[1] else '成型中'})", 'signal': 'bullish'}
                
    if "M頭" in mode or is_auto:
        if len(highs) >= 2 and highs[-2][1]>0:
            b_l = [l for l in lows if highs[-2][2] < l[2] < highs[-1][2]]
            if b_l and (abs(highs[-2][1]-highs[-1][1])/highs[-2][1] <= tol or "M頭" in mode):
                l_min = min(b_l, key=lambda x: x[1])
                return {'name': 'M頭', 'shape_x': [highs[-2][0], l_min[0], highs[-1][0]], 'shape_y': [highs[-2][1], l_min[1], highs[-1][1]], 'neck_x': [highs[-2][0], last_date], 'neck_y': [l_min[1], l_min[1]], 'color': '#d32f2f', 'desc': f"M頭 ({'已跌破' if current_price<l_min[1] else '成型中'})", 'signal': 'bearish'}

    if any(k in mode for k in ["連續", "三角形", "楔形", "矩形"]) or is_auto:
        if len(highs) >= 2 and len(lows) >= 2 and highs[-2][1]>0 and lows[-2][1]>0:
            h_diff, l_diff = (highs[-1][1]-highs[-2][1])/highs[-2][1], (lows[-1][1]-lows[-2][1])/lows[-2][1]
            p_name, p_color, p_desc, p_sig = "", "", "", "neutral"
            if abs(h_diff)<tol and abs(l_diff)<tol and ("矩形" in mode or is_auto): p_name, p_color, p_desc = "箱型矩形", "#2196f3", "矩形整理"
            elif abs(h_diff)<tol and l_diff>tol and ("上升三角形" in mode or is_auto): p_name, p_color, p_desc, p_sig = "上升三角形", "#4caf50", "偏多醞釀", "bullish"
            elif h_diff<-tol and abs(l_diff)<tol and ("下降三角形" in mode or is_auto): p_name, p_color, p_desc, p_sig = "下降三角形", "#f44336", "偏空醞釀", "bearish"
            elif h_diff<-tol and l_diff>tol and ("對稱" in mode or "收斂" in mode or is_auto): p_name, p_color, p_desc = "對稱三角形", "#ff9800", "收斂表態前"
            if p_name: return {'name': p_name, 'shape_x': [highs[-2][0], highs[-1][0]], 'shape_y': [highs[-2][1], highs[-1][1]], 'neck_x': [lows[-2][0], lows[-1][0]], 'neck_y': [lows[-2][1], lows[-1][1]], 'color': p_color, 'desc': p_desc, 'signal': p_sig}
    return {}

# ==========================================
# 渲染函式群
# ==========================================
def render_clean_html_table(df, title=""):
    if not is_valid(df): return st.warning(f"{title} 查無資料。") if title else st.warning("此區塊查無資料。")
    cols = df.columns.tolist()
    html = [f"<div class='section-title'>{title}</div>"] if title else []
    html.append("<div class='table-container'><table><thead><tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr></thead><tbody>")
    for row in df.itertuples(index=False):
        html.append("<tr>")
        for i, val in enumerate(row):
            align = "text-left" if any(k in str(cols[i]) for k in ['日期', '分點', '標籤', '週期', '名稱', '條件', '措施', '診斷']) else "text-right"
            s = str(val).strip() if pd.notna(val) else "-"
            if s and s.lower() != "nan":
                if "無本獲利" in s: s = f"<span class='profit-warning'>{s}</span>"
                elif "(虧)" in s: s = f"<span class='loss-warning'>(虧) {s.replace('(虧)', '').strip()}</span>"
                elif s.startswith("+"): s = f"<span class='highlight-red'>{s}</span>"
                elif s.startswith("-") and len(s)>1 and s[1].isdigit(): s = f"<span class='highlight-green'>{float(s.replace(',','')):,.2f}</span>" if "." in s else f"<span class='highlight-green'>{int(float(s.replace(',',''))):,}</span>"
                elif "%" not in s and any(c.isdigit() for c in s):
                    try: s = f"{float(s.replace(',','')):,.2f}" if "." in s else f"{int(float(s.replace(',',''))):,}"
                    except: pass
            html.append(f"<td class='{align}'>{s}</td>")
        html.append("</tr>")
    html.append("</tbody></table></div>")
    st.markdown("".join(html), unsafe_allow_html=True)

def render_tdcc_table_with_color(df, title=""):
    if not is_valid(df): return st.warning("此區塊查無資料。")
    df_work = df.sort_values('日期', ascending=False).reset_index(drop=True)
    cols = df_work.columns.tolist()
    html = [f"<div class='section-title'>{title}</div>"] if title else []
    html.append("<div class='table-container'><table><thead><tr>" + "".join(f"<th style='text-align: {'left' if c=='日期' else 'right'};'>{c}</th>" for c in cols) + "</tr></thead><tbody>")
    for i in range(len(df_work)):
        html.append("<tr>")
        for col in cols:
            val = df_work.at[i, col]
            if pd.isna(val): html.append("<td class='text-right'>-</td>"); continue
            if col == '日期': html.append(f"<td class='text-left' style='font-weight: bold;'>{val}</td>")
            else:
                try:
                    cv = float(val)
                    dstr = f"{int(cv):,}" if cv==int(cv) else f"{cv:,.2f}"
                    if i < len(df_work) - 1:
                        pv = float(df_work.at[i+1, col])
                        if cv > pv: html.append(f"<td class='text-right' style='background-color: rgba(229, 57, 53, 0.08);'><span style='color:#d32f2f; font-weight:bold;'>{dstr}</span></td>")
                        elif cv < pv: html.append(f"<td class='text-right' style='background-color: rgba(67, 160, 71, 0.08);'><span style='color:#2e7d32; font-weight:bold;'>{dstr}</span></td>")
                        else: html.append(f"<td class='text-right'>{dstr}</td>")
                    else: html.append(f"<td class='text-right'>{dstr}</td>")
                except: html.append(f"<td class='text-right'>{val}</td>")
        html.append("</tr>")
    html.append("</tbody></table></div>")
    st.markdown("".join(html), unsafe_allow_html=True)

def format_to_csv_string(df, title):
    return f"▼▼▼ {title} ▼▼▼\n" + (df.to_csv(index=False) + "\n" if is_valid(df) else "此區塊查無資料或無發行紀錄\n")

def render_ultimate_heatmap(df_raw, display_dates, rank_dates, intel_tags, df_fingerprint, top_n, noise_threshold):
    if not is_valid(df_raw) or not display_dates or not rank_dates: return st.warning("查無足夠資料產生熱力圖。")
    df_rank = df_raw[df_raw['date'].isin(rank_dates)].assign(net_shares=lambda x: x['buy'] - x['sell'])
    rank_sum = (df_rank.groupby('securities_trader')['net_shares'].sum() / 1000).round().astype(int)
    top_b, top_s = rank_sum[rank_sum>0].nlargest(top_n).index.tolist(), rank_sum[rank_sum<0].nsmallest(top_n).index.tolist()
    if not top_b and not top_s: return st.warning("無符合條件的活躍分點。")

    p = df_raw[df_raw['date'].isin(display_dates)].assign(net=lambda x: ((x['buy']-x['sell'])/1000).round().astype(int)).groupby(['securities_trader', 'date'])['net'].sum().reset_index().pivot(index='securities_trader', columns='date', values='net').fillna(0).astype(int).reindex(index=top_b+top_s, columns=display_dates, fill_value=0)
    max_val = max(1, p.abs().max().max())
    fp_dict = df_fingerprint.set_index('分點名稱')[['黏著度(%)', '囤出貨率(%)']].to_dict('index') if not df_fingerprint.empty else {}

    html = [HEATMAP_STYLE_TEMPLATE + "<div class='full-table-container heatmap-wrapper'><table><thead><tr><th style='min-width:140px; position:sticky; left:0; z-index:6;'>分點名稱</th><th style='min-width:90px;'>標籤</th><th style='min-width:80px;'>黏著度</th><th style='min-width:90px;'>囤/出貨率</th><th style='min-width:90px; background-color:#fff9c4;'>區間累計</th>" + "".join(f"<th style='text-align:center; font-size:13px; min-width:50px;'>{d[5:]}</th>" for d in display_dates) + "</tr></thead><tbody>"]

    def build_rows(traders, is_sell):
        if not traders: return
        html.append(f"<tr><td colspan='{5+len(display_dates)}' style='background-color:#f1f3f5; color:{'#4caf50' if is_sell else '#f44336'}; font-weight:900; text-align:center; font-size:1.1rem; letter-spacing:2px;'>{'🟢 賣超主力陣營' if is_sell else '🔴 買超主力陣營'}</td></tr>")
        for trader in traders:
            tval = rank_sum.get(trader, 0)
            html.append(f"<tr><td style='position:sticky; left:0; background-color:#f8f9fa; z-index:4; font-weight:bold;'>{trader}</td><td style='text-align:center;'>{intel_tags.get(trader, '路人')}</td><td style='text-align:right;'>{fp_dict.get(trader, {}).get('黏著度(%)', '-')}</td><td style='text-align:right;'>{fp_dict.get(trader, {}).get('囤出貨率(%)', '-')}</td><td style='text-align:right; background-color:#fffde7;'><span style='color:{'#d32f2f' if tval>0 else '#2e7d32'}; font-weight:bold;'>{f'+{tval}' if tval>0 else tval}</span></td>")
            for d in display_dates:
                v = p.at[trader, d]
                is_noise = abs(v) < noise_threshold
                alpha = min(1.0, 0.2 + 0.8 * (abs(v) / max_val))
                bg, txt, tc, zc = (f"rgba(229,57,53,{alpha:.2f})", f"+{v}", "#fff", "") if v>0 else (f"rgba(67,160,71,{alpha:.2f})", str(v), "#fff", "") if v<0 else ("transparent", "0", "#aaa", "val-zero")
                html.append(f"<td class='{'noise-cell ' + zc if is_noise or v==0 else ''}' style='--bg-color:{bg}; --txt-color:{tc}; text-align:center; font-weight:bold; {f'background-color:{bg}; color:{tc} !important; text-shadow:1px 1px 2px rgba(0,0,0,0.6);' if not (is_noise or v==0) else 'background-color:transparent;'}' title='日期: {d} | 淨額: {v}'><span>{txt}</span></td>")
            html.append("</tr>")
    build_rows(top_b, False)
    build_rows(top_s, True)
    html.append("</tbody></table></div>")
    st.markdown("".join(html), unsafe_allow_html=True)

# ==========================================
# 執行主引擎
# ==========================================
if run_btn:
    if not user_stock_id.strip(): st.warning("請先輸入股票代號！"); st.stop()

    with st.spinner(f"正在啟動 V76.1 終極版決策引擎..."):
        name, industry = get_basic_info_finmind(user_stock_id)
        if name == "未知名稱": st.error(f"查無股票代號 {user_stock_id}。"); st.stop()
            
        df_p_raw = fetch_finmind_v50("TaiwanStockPrice", (datetime.date.today() - datetime.timedelta(days=700)).strftime("%Y-%m-%d"), user_stock_id)
        if not is_valid(df_p_raw, ['date']): st.error("查無歷史股價。"); st.stop()
        
        valid_dates = df_p_raw['date'].dropna().astype(str)
        dates = sorted(valid_dates[valid_dates != ""].unique().tolist(), reverse=True)
        if not dates: st.stop()

        # 🧩 V76.1：無斷點動態計算 max_len，確保資料涵蓋自訂區間起點
        c_start, c_end = custom_range if len(custom_range) == 2 else (default_start, today_date)
        days_to_custom_start = len([d for d in dates if d >= c_start.strftime("%Y-%m-%d")])
        max_len = max(lookback_days, days_to_custom_start + 20) # 額外加20天緩衝給MA等計算
        if max_len > len(dates): max_len = len(dates)
        if max_len == 0: max_len = 1
        
        df_price = optimize_memory(process_price(df_p_raw))
        curr_price = round(float(df_price['收盤價(元)'].iloc[0]), 2) if is_valid(df_price, ['收盤價(元)']) else 0
        df_ta_full = process_technical_analysis(df_price, ma_short, ma_mid, ma_long)
        
        recent_20_vol = df_price['成交量(張)'].head(20).mean() if is_valid(df_price) else 1000
        dynamic_noise_threshold = int((recent_20_vol or 1000) * (heatmap_noise_pct / 100.0))
        dynamic_alert_threshold = int((recent_20_vol or 1000) * (alert_smart_pct / 100.0))

        df_lr_channel = process_linear_regression(df_price, lr_days)
        latest_lr_upper = df_lr_channel['LR_Upper'].iloc[-1] if is_valid(df_lr_channel) else 0.0
        latest_lr_mid = df_lr_channel['LR_Mid'].iloc[-1] if is_valid(df_lr_channel) else 0.0
        latest_lr_lower = df_lr_channel['LR_Lower'].iloc[-1] if is_valid(df_lr_channel) else 0.0
        pat_data = process_geometric_patterns(df_price, kline_days, pattern_order, pattern_mode, curr_price) if enable_pattern else {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as bg_executor:
            f_dir = bg_executor.submit(scrape_director_v50, user_stock_id)
            f_ple = bg_executor.submit(scrape_fubon_pledge, df_p_raw, user_stock_id)
            df_b_raw, ds_dict, df_cb_info = fetch_heavy_data_sync_with_progress(user_stock_id, tuple(dates), max_len)
            dynamic_dict, s_val, chip_eng, _ = f_dir.result()
            df_p_sum, df_p_det = f_ple.result()

        if not is_valid(df_b_raw): st.error(f"查無分點進出資料。"); st.stop()
            
        df_b_raw['price'] = safe_to_num(df_b_raw['price'])
        df_b_raw['buy'] = safe_to_num(df_b_raw['buy'])
        df_b_raw['sell'] = safe_to_num(df_b_raw['sell'])
        df_b_raw['valid_buy'] = np.where(df_b_raw['price']>0, df_b_raw['buy'], 0)
        df_b_raw['valid_sell'] = np.where(df_b_raw['price']>0, df_b_raw['sell'], 0)
        df_b_raw['valid_buy_amt'] = df_b_raw['valid_buy'] * df_b_raw['price']
        df_b_raw['valid_sell_amt'] = df_b_raw['valid_sell'] * df_b_raw['price']
        df_b_raw['net_shares'] = df_b_raw['buy'] - df_b_raw['sell']
        df_b_raw['date_dt'] = pd.to_datetime(df_b_raw['date'])

        parsed_dead_chip = float(str(dead_chip_input).replace('%', '').strip()) if dead_chip_input and str(dead_chip_input).strip() else None

        tags, df_debug_tags = get_v50_intelligence(df_b_raw, df_p_raw, stick_thresh=stickiness_threshold, global_days=max_len, dates_list=dates)
        df_b_raw['tag'] = df_b_raw['securities_trader'].map(tags).fillna("路人雜訊")
        df_b_raw['is_smart'] = df_b_raw['tag'].isin({"波段鎖碼", "避險造市", "獲利調節", "棄守提款", "主力重砲", "認錯回補"})
        df_b_raw['is_short'] = df_b_raw['tag'].isin({"隔日突擊", "跟風小戶"})
        
        df_s_wide, df_s_unit, df_s_ppl = process_tdcc(ds_dict.get("TaiwanStockHoldingSharesPer", pd.DataFrame()))
        current_total_shares = df_s_wide['總張數'].iloc[0] if is_valid(df_s_wide) else 0
        latest_director_holding, holding_src = get_dead_chip_info(dates[0], parsed_dead_chip, dynamic_dict, s_val, chip_eng)

        dynamic_n, _ = calculate_dynamic_radar_depth(df_b_raw, dates, current_total_shares, df_price)
        pure_vwap, main_force_vol, active_main_branches, core_c_value, core_branch_names = calculate_pure_defense_line(df_b_raw, tags, filter_day_trade, current_total_shares, latest_director_holding, dynamic_n)
        
        net_10 = get_core_period_net(df_b_raw, dates[:10], core_branch_names)
        net_60 = get_core_period_net(df_b_raw, dates[:60] if len(dates)>=60 else dates, core_branch_names)
        
        df_day_trade = optimize_memory(process_day_trading(ds_dict.get("TaiwanStockDayTrading", pd.DataFrame())))
        df_b_diff = process_branch_diff_v2(df_b_raw, dates, firepower_threshold, period_days=15)
        df_daily_tracker, _ = process_v30_daily_tracking(df_b_raw, tags, df_price, df_b_diff, dates, firepower_threshold, period_days=15)
        
        df_s_dyn = process_tdcc_dynamic_v2(df_s_wide, df_price, parsed_dead_chip, dynamic_dict, s_val, chip_eng)
        df_v27_radar, _, _ = process_v27_ultimate_radar(df_s_wide, parsed_dead_chip, dynamic_dict, s_val, df_price, df_b_raw, tags)

        df_combined_display = pd.DataFrame()
        if is_valid(df_v27_radar) and is_valid(df_s_dyn):
            df_combined_radar = pd.merge(df_s_dyn, df_v27_radar.drop(columns=['大戶原持股(%)', '收盤價(元)'], errors='ignore'), on=['日期'], how='inner')
            if is_valid(df_combined_radar):
                df_combined_radar['終極籌碼診斷'] = df_combined_radar['實戰判定'].astype(str) + " | " + df_combined_radar['專家雷達診斷'].astype(str)
                df_combined_display = optimize_memory(df_combined_radar[[c for c in ['日期', '收盤價(元)', '純淨活大戶C_Value(%)', '純淨大戶變動(%)', '總人數變率(%)', '大戶精算門檻', '當沖虛胖(%)', '終極籌碼診斷'] if c in df_combined_radar.columns]].sort_values('日期', ascending=False).head(8))

        df_margin_lending = optimize_memory(process_margin_and_lending(ds_dict.get("TaiwanStockMarginPurchaseShortSale", pd.DataFrame()), ds_dict.get("TaiwanStockSecuritiesLending", pd.DataFrame())))
        df_lending_detail = optimize_memory(process_securities_lending_detail(ds_dict.get("TaiwanStockSecuritiesLending", pd.DataFrame())))
        df_block_trade = optimize_memory(process_block_trading(ds_dict.get("TaiwanStockBlockTrade", pd.DataFrame()), dates))
        df_inst = optimize_memory(process_inst(ds_dict.get("TaiwanStockInstitutionalInvestorsBuySell", pd.DataFrame())))
        df_fut = optimize_memory(process_fut_inst(ds_dict.get("TaiwanFuturesInstitutionalInvestors", pd.DataFrame())))
        df_div = optimize_memory(process_div(ds_dict.get("TaiwanStockDividend", pd.DataFrame())))
        df_per = optimize_memory(process_per(ds_dict.get("TaiwanStockPER", pd.DataFrame())))
        df_disp = optimize_memory(process_disp(ds_dict.get("TaiwanStockDispositionSecuritiesPeriod", pd.DataFrame())))
        
        df_rev_raw = ds_dict.get("TaiwanStockMonthRevenue", pd.DataFrame())
        df_rev = pd.DataFrame()
        if is_valid(df_rev_raw, ['revenue_year', 'revenue_month']):
            df_rev = df_rev_raw.dropna(subset=['revenue_year', 'revenue_month']).assign(營收月份=lambda x: x['revenue_year'].astype(int).astype(str) + "-" + x['revenue_month'].astype(int).astype(str).str.zfill(2), 月營收=lambda x: (safe_to_num(x['revenue'])/1000000).round().astype(int)).rename(columns={'月營收':'月營收(百萬元)'})[['營收月份','月營收(百萬元)']].tail(24).sort_values('營收月份', ascending=False)

        df_cbas_raw = ds_dict.get("TaiwanStockConvertibleBondDailyOverview", pd.DataFrame())
        df_cbas = optimize_memory(process_cbas(df_cbas_raw[df_cbas_raw['cb_id'].astype(str).str.replace(',', '', regex=False).str.startswith(user_stock_id)], curr_price, df_cb_info)) if is_valid(df_cbas_raw, ['cb_id']) else pd.DataFrame()
        
        company_info_text = f"【產業】 {industry} ｜ 【股本】 {current_total_shares/10000:.2f} 億 ｜ 【市值】 {(curr_price*current_total_shares)/100000:,.2f} 億 ｜ 【死籌碼】 {director_holding_str} ｜ 【20日均量】 {int(recent_20_vol or 0):,} 張"
        
        st.subheader(f"{user_stock_id} {name} 全息戰報 (V76.1 終極版)")
        st.markdown(f"<div class='info-box'>{company_info_text}</div>", unsafe_allow_html=True)

        # 🚨 K 線圖與技術分析模組回歸 🚨
        if is_valid(df_ta_full):
            st.markdown(f"<div class='section-title'>高階技術分析 (極緻緊湊版 - {ma_short}/{ma_mid}/{ma_long}極細均線)</div>", unsafe_allow_html=True)
            df_plot = pd.merge(df_price.head(kline_days), df_ta_full[['日期', f'MA{ma_short}', f'MA{ma_mid}(中線)', f'MA{ma_long}(長線)']], on='日期', how='inner').sort_values('日期', ascending=True)
            df_plot = pd.merge(df_plot, ds_dict.get("TaiwanStockDayTrading", pd.DataFrame()).rename(columns={"date":"日期"}).assign(當沖總張數=lambda x: (safe_to_num(x.get('DayTradingVolume', x.get('Volume', 0)))/1000).round().astype(int))[['日期', '當沖總張數']], on='日期', how='left').fillna(0)
            
            lr_json = "{}"
            if is_valid(df_lr_channel):
                df_plot = pd.merge(df_plot, df_lr_channel, on='日期', how='left')
                df_plot_lr = df_plot.dropna(subset=['LR_Upper'])
                lr_json = json.dumps({"upper": [{"time": str(t), "value": float(v)} for t, v in zip(df_plot_lr['日期'], df_plot_lr['LR_Upper'])], "mid": [{"time": str(t), "value": float(v)} for t, v in zip(df_plot_lr['日期'], df_plot_lr['LR_Mid'])], "lower": [{"time": str(t), "value": float(v)} for t, v in zip(df_plot_lr['日期'], df_plot_lr['LR_Lower'])]})

            pat_js, neck_js, pat_color_js = "[]", "[]", "'transparent'"
            if pat_data:
                pat_js = json.dumps(sorted([{"time": str(x), "value": float(y)} for x, y in zip(pat_data['shape_x'], pat_data['shape_y'])], key=lambda k: k['time']))
                neck_js = json.dumps(sorted([{"time": str(x), "value": float(y)} for x, y in zip(pat_data['neck_x'], pat_data['neck_y'])], key=lambda k: k['time']))
                pat_color_js = f"'{pat_data.get('color', '#000')}'"

            ts = df_plot['日期'].astype(str).tolist()
            k_data = [{'time': t, 'open': float(o), 'high': float(h), 'low': float(l), 'close': float(c)} for t, o, h, l, c in zip(ts, df_plot['開盤價(元)'], df_plot['最高價(元)'], df_plot['最低價(元)'], df_plot['收盤價(元)'])]
            ma_d = {"ma_short": [{'time': t, 'value': float(v)} for t, v in zip(ts, df_plot[f'MA{ma_short}']) if pd.notna(v)], "ma_mid": [{'time': t, 'value': float(v)} for t, v in zip(ts, df_plot[f'MA{ma_mid}(中線)']) if pd.notna(v)], "ma_long": [{'time': t, 'value': float(v)} for t, v in zip(ts, df_plot[f'MA{ma_long}(長線)']) if pd.notna(v)]}
            
            components.html(KLINE_CHART_TEMPLATE.replace("KLINE_DATA", json.dumps(k_data)).replace("TOTAL_VOL", json.dumps([{'time': t, 'value': float(v), 'color': '#E0E3EB'} for t, v in zip(ts, df_plot['成交量(張)'])]))
                            .replace("DAYTRADE_VOL", json.dumps([{'time': t, 'value': float(v), 'color': '#FF9800'} for t, v in zip(ts, df_plot['當沖總張數'])]))
                            .replace("MA_DATA", json.dumps(ma_d)).replace("LR_DATA", lr_json).replace("PAT_DATA", pat_js).replace("NECK_DATA", neck_js).replace("PAT_COLOR", pat_color_js), height=736)

        st.markdown("<div class='category-title'>AI 全息籌碼深度診斷總結</div>", unsafe_allow_html=True)
        report_md = "<div class='ai-report-box'><h4>🧠 系統終極戰略推演與深度解析</h4><ul>"
        report_md += f"<li><b>一、 核心防守價位確認：</b><br>系統已精算出的「純淨主力防守價」為 <b>{pure_vwap:,.2f} 元</b>。目前股價距離成本線乖離率為 {((curr_price-pure_vwap)/pure_vwap*100) if pure_vwap>0 else 0:.1f}%。</li>"
        report_md += f"<li><b>二、 平日戰情 (近15日)：</b><br>近 10 日主力淨留倉 <span style='color:{'#d32f2f' if net_10>0 else '#2e7d32'}; font-weight:bold;'>{net_10:,} 張</span>。今日買方火力 {df_b_diff.iloc[0].get('買方火力(倍)',1.0) if not df_b_diff.empty else 1.0} 倍。</li>"
        report_md += "</ul></div>"
        st.markdown(report_md, unsafe_allow_html=True)

        st.markdown("---")
        
        # 🧩 區間邏輯對齊：01. 終極全息透視區
        selected_dates_list = [d for d in dates if str(c_start) <= d <= str(c_end)]
        if not selected_dates_list: selected_dates_list = dates[:15]

        st.markdown("<div class='category-title'>01. 終極全息透視區 (依自訂區間動態對齊)</div>", unsafe_allow_html=True)
        with st.expander(f"【終極全息熱力圖】 自訂區間：{selected_dates_list[-1]} ~ {selected_dates_list[0]} (共 {len(selected_dates_list)} 個交易日)", expanded=True):
            st.info("🟢 此區域完全連動左側「自訂時間區間」，排行與熱力圖橫軸已同步重算。")
            render_ultimate_heatmap(df_b_raw, selected_dates_list, selected_dates_list, tags, df_debug_tags, footprint_rows, dynamic_noise_threshold)
            
        with st.expander("【戰略系海鮮】 大戶建倉成本區間分佈 (Volume Profile)", expanded=False):
            render_volume_profile(df_b_raw, selected_dates_list, footprint_rows)

        with st.expander("【甜點】 土洋聯合作戰比對 (法人 vs 地方大戶角力)", expanded=False):
            render_institutional_vs_local(df_b_raw, df_inst, tags, top_n=4)

        # 16 大完整模組輸出
        render_clean_html_table(df_daily_tracker, "02. 平日戰情追蹤矩陣 (近15日)")
        render_clean_html_table(df_combined_display, "03. 一週集保籌碼雷達") 
        render_clean_html_table(df_block_trade, "04. 鉅額交易日報表 (大額換手追蹤)")
        render_clean_html_table(df_inst, "05. 法人買賣超 (近10天)")
        render_clean_html_table(df_margin_lending, "06-1. 散戶資券與借券總量 (近10天)")
        render_clean_html_table(df_lending_detail, "06-2. 借券成交明細與費率 (近10天)")
        render_clean_html_table(df_day_trade, "07. 現股當沖明細 (近10天)")
        render_clean_html_table(df_fut, "08. 台指期貨三大法人未平倉 (大盤)")
        render_clean_html_table(df_rev, "09. 月營收 (百萬元) (近24個月)")
        
        with st.expander("點此展開集保分級表 (近8週)", expanded=False):
            render_tdcc_table_with_color(df_s_unit, "10-1. 集保分級 - 張數表 (紅增綠減)")
            render_tdcc_table_with_color(df_s_ppl, "10-2. 集保分級 - 人數表 (紅增綠減)")
            
        render_clean_html_table(df_p_sum, "11. 董監大股東質設總覽")
        with st.expander("點此展開董監大股東質設明細", expanded=False):
            render_clean_html_table(df_p_det, "12. 董監大股東質設明細")
            
        render_clean_html_table(df_div, "13. 歷年股利政策 (近5年)")
        render_clean_html_table(df_per, "14. 本益比、淨值比與殖利率")
        render_clean_html_table(df_disp, "15. 處置有價證券狀態")
        render_clean_html_table(df_cbas, "16. CBAS 可轉債資料")

        st.divider()
        with st.expander(f"給 AI 的 V76.1 實戰精華資料包 (CSV格式)", expanded=True):
            p1 = f"請分析 {user_stock_id} {name}。\n{company_info_text}\n\n"
            p1 += f"【系統純淨加權防守價】: {pure_vwap:,.2f} 元\n【核心控盤率】: {core_c_value}%\n"
            p1 += f"【3日淨留倉】: {net_3} 張\n【10日淨留倉】: {net_10} 張\n【60日淨留倉】: {net_60} 張\n\n"
            p1 += format_to_csv_string(df_daily_tracker, "02. 平日戰情追蹤")
            p1 += format_to_csv_string(df_combined_display, "03. 集保雷達")
            p1 += format_to_csv_string(df_inst.head(10) if is_valid(df_inst) else df_inst, "05. 法人買賣超")
            p1 += format_to_csv_string(df_margin_lending.head(10) if is_valid(df_margin_lending) else df_margin_lending, "06. 資券與借券")
            p1 += format_to_csv_string(df_cbas, "16. CBAS 可轉債")
            st.code(p1, language="text")
            
        st.success(f"V76.1 終極無斷點版已成功處理 {user_stock_id}。")
        gc.collect()
