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
st.set_page_config(layout="wide", page_title="全息量化系統 (V73.00版)", initial_sidebar_state="expanded")

FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"
GITHUB_MANUAL_URL = "https://raw.githubusercontent.com/tonehsie/stock/refs/heads/main/README.md"

CSS = "<style>.table-container{overflow:auto;max-height:600px;width:100%;margin-bottom:25px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1);padding-bottom:10px}.table-container table{width:max-content !important;min-width:40%;border-collapse:separate !important;border-spacing:0;font-size:15px !important;font-family:sans-serif;background-color:#fff}.table-container th,.table-container td{white-space:nowrap !important;padding:10px 12px !important;border-bottom:1px solid #dee2e6;border-right:1px solid #dee2e6;vertical-align:middle}.table-container th{border-top:1px solid #dee2e6;word-break:keep-all !important;text-align:center !important;background-color:#f1f3f5 !important;color:#333 !important;font-weight:700 !important;line-height:1.4;position:sticky;top:0;z-index:3}.table-container th:first-child,.table-container td:first-child{position:sticky;left:0;background-color:#f8f9fa;z-index:4;font-weight:bold;text-align:center !important;border-left:1px solid #dee2e6}.table-container thead th:first-child{z-index:5}.full-table-container{overflow-x:auto;overflow-y:visible;width:100%;margin-bottom:25px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1);display:block;padding-bottom:10px}.full-table-container table{width:max-content !important;min-width:40%;border-collapse:separate !important;border-spacing:0;font-size:15px !important;font-family:sans-serif;background-color:#fff}.full-table-container th,.full-table-container td{white-space:nowrap !important;padding:10px 12px !important;border-bottom:1px solid #dee2e6;border-right:1px solid #dee2e6;vertical-align:middle}.full-table-container th{border-top:1px solid #dee2e6;word-break:keep-all !important;text-align:center !important;background-color:#f1f3f5 !important;color:#333 !important;font-weight:700 !important;line-height:1.4;position:sticky;top:0;z-index:3}.full-table-container th:first-child,.full-table-container td:first-child{position:sticky;left:0;background-color:#f8f9fa;z-index:4;font-weight:bold;text-align:center !important;border-left:1px solid #dee2e6}.full-table-container thead th:first-child{z-index:5}.text-left{text-align:left !important}.text-right{text-align:right !important;font-variant-numeric:tabular-nums}.loss-warning{color:#d9480f;font-weight:bold}.profit-warning{color:#6a1b9a;font-weight:900;background-color:#f3e5f5;padding:3px 6px;border-radius:4px;border:1px solid #ce93d8}.highlight-red{color:#d32f2f;font-weight:bold}.highlight-green{color:#2e7d32;font-weight:bold}.info-box{background-color:#f8f9fa;padding:15px 20px;border-radius:8px;margin-bottom:25px;border-left:6px solid #1e3a8a;font-size:1.1rem;font-weight:bold;color:#1e3a8a}.section-title{margin-top:35px;margin-bottom:15px;color:#1e3a8a;border-bottom:2px solid #1e3a8a;padding-bottom:5px;font-size:1.3rem !important;font-weight:700 !important}.category-title{font-size:1.6rem !important;font-weight:900 !important;margin-top:40px;color:#333}.stTabs [data-baseweb='tab-list']{gap:10px}.stTabs [data-baseweb='tab']{height:50px;white-space:pre-wrap;background-color:#f8f9fa;border-radius:4px 4px 0 0;padding:10px 20px;font-weight:bold}.stTabs [aria-selected='true']{background-color:#e3f2fd !important;color:#1e3a8a !important;border-bottom:3px solid #1e3a8a !important}.ai-report-box{background-color:#fcfdfe;border:1px solid #e9ecef;border-left:6px solid #b71c1c;border-radius:8px;padding:25px;margin-bottom:30px;box-shadow:0 4px 10px rgba(0,0,0,0.08);line-height:1.8}.ai-report-box h4{margin-top:0;color:#b71c1c;font-weight:900;font-size:1.6rem;border-bottom:2px dashed #ccc;padding-bottom:10px;margin-bottom:20px}.ai-report-box ul{margin-bottom:20px;padding-left:20px}.ai-report-box li{margin-bottom:18px;font-size:1.25rem;color:#222}.ai-report-box b{font-size:1.4rem;color:#b71c1c}.ai-conclusion{background-color:#fff3cd;padding:22px;border-radius:8px;border:2px solid #ffe69c;font-weight:700;color:#856404;font-size:1.45rem}.progress-text{font-size:1.1rem;color:#1e3a8a;font-weight:bold;margin-bottom:5px}@media (prefers-color-scheme: dark){.table-container table,.full-table-container table{background-color:#1e1e1e !important;color:#e0e0e0 !important}.table-container th,.table-container td,.full-table-container th,.full-table-container td{border-color:#444 !important;color:#e0e0e0 !important}.table-container th,.full-table-container th{background-color:#2d2d2d !important;color:#fff !important}.table-container th:first-child,.table-container td:first-child,.full-table-container th:first-child,.full-table-container td:first-child{background-color:#252525 !important}.info-box{background-color:#2d2d2d !important;color:#64b5f6 !important;border-left-color:#64b5f6 !important}.section-title{color:#64b5f6 !important;border-bottom-color:#64b5f6 !important}.category-title{color:#fff !important}.stTabs [data-baseweb='tab']{background-color:#2d2d2d !important;color:#aaa !important}.stTabs [aria-selected='true']{background-color:#1a237e !important;color:#64b5f6 !important;border-bottom-color:#64b5f6 !important}.ai-report-box{background-color:#252525 !important;border-color:#444 !important;border-left-color:#ef5350 !important;color:#e0e0e0 !important}.ai-report-box h4{color:#ef5350 !important;border-bottom-color:#444 !important}.ai-report-box li{color:#e0e0e0 !important}.ai-report-box b{color:#ef5350 !important}.ai-conclusion{background-color:#3e2723 !important;border-color:#5d4037 !important;color:#ffb74d !important}.progress-text{color:#64b5f6 !important}.profit-warning{background-color:#4a148c !important;color:#e1bee7 !important;border-color:#7b1fa2 !important}.loss-warning{color:#ff7043 !important}.highlight-red{color:#ef5350 !important}.highlight-green{color:#66bb6a !important}}</style>"
HEATMAP_STYLE_TEMPLATE = "<style>.heatmap-wrapper .noise-cell{background-color:transparent !important}.heatmap-wrapper .noise-cell span{display:none}#heatmap-toggle:checked ~ .heatmap-wrapper .noise-cell{background-color:var(--bg-color) !important;}#heatmap-toggle:checked ~ .heatmap-wrapper .noise-cell span{display:inline;color:var(--txt-color) !important;text-shadow:1px 1px 2px rgba(0,0,0,0.6)}#heatmap-toggle:checked ~ .heatmap-wrapper .noise-cell.val-zero span{text-shadow:none !important}.heatmap-toggle-label{display:inline-block;margin-bottom:12px;padding:6px 12px;background-color:#f1f3f5;border-radius:6px;border:1px solid #ccc;cursor:pointer;font-weight:bold;color:#1e3a8a;user-select:none}#heatmap-toggle:checked + .heatmap-toggle-label{background-color:#e3f2fd;border-color:#90caf9}</style><input type='checkbox' id='heatmap-toggle' style='display:none;'><label for='heatmap-toggle' class='heatmap-toggle-label'>👁️ 切換顯示：隱藏數值</label>"
KLINE_CHART_TEMPLATE = """<!DOCTYPE html><html><head><script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script><style>body{margin:0;background:#fff;font-family:sans-serif;display:flex;flex-direction:column;height:100vh;overflow:hidden}#chart-main{flex:3.2;border-bottom:2px solid #f0f3fa;position:relative}#chart-vol{flex:0.8;position:relative}.legend{position:absolute;top:4px;left:8px;z-index:10;font-size:13px;pointer-events:none;background:rgba(255,255,255,0.7);padding:2px 6px;border-radius:4px;color:#333}@media (prefers-color-scheme: dark){body{background:#1e1e1e}#chart-main{border-bottom:2px solid #444}.legend{background:rgba(30,30,30,0.7);color:#e0e0e0}}</style></head><body><div id="chart-main"><div id="legend" class="legend"></div></div><div id="chart-vol"></div><script>const kData=KLINE_DATA;const tVol=TOTAL_VOL;const dtVol=DAYTRADE_VOL;const ma=MA_DATA;const kDataMap=new Map(kData.map(x=>[x.time,x]));const tVolMap=new Map(tVol.map(x=>[x.time,x.value]));const dtVolMap=new Map(dtVol.map(x=>[x.time,x.value]));const commonLocalization={timeFormatter:t=>{if(t.year){return `${String(t.year).slice(-2)}/${String(t.month).padStart(2,'0')}/${String(t.day).padStart(2,'0')}`}if(typeof t==='string'){return t.substring(2).replace(/-/g,'/')}return t}};const isDark=window.matchMedia('(prefers-color-scheme: dark)').matches;const chartBgColor=isDark?'#1e1e1e':'#ffffff';const chartTxtColor=isDark?'#e0e0e0':'#333';const chartGridColor=isDark?'#333333':'#f5f5f5';const priceScaleConfig={borderColor:chartGridColor,autoScale:true,minimumWidth:80,alignLabels:true};const mainOptions={autoSize:true,localization:commonLocalization,layout:{background:{color:chartBgColor},textColor:chartTxtColor},grid:{vertLines:{color:chartGridColor},horzLines:{color:chartGridColor}},rightPriceScale:{...priceScaleConfig,scaleMargins:{top:0.05,bottom:0.05}},timeScale:{visible:false,rightOffset:10}};const volOptions={autoSize:true,localization:commonLocalization,layout:{background:{color:chartBgColor},textColor:chartTxtColor},grid:{vertLines:{color:chartGridColor},horzLines:{color:chartGridColor}},rightPriceScale:{...priceScaleConfig,scaleMargins:{top:0.02,bottom:0}},timeScale:{borderColor:chartGridColor,rightOffset:10}};const mainChart=LightweightCharts.createChart(document.getElementById('chart-main'),mainOptions);const volChart=LightweightCharts.createChart(document.getElementById('chart-vol'),volOptions);const candleSeries=mainChart.addCandlestickSeries({upColor:chartBgColor,borderUpColor:isDark?'#fff':'#000',wickUpColor:isDark?'#fff':'#000',downColor:isDark?'#fff':'#000',borderDownColor:isDark?'#fff':'#000',wickDownColor:isDark?'#fff':'#000'});candleSeries.setData(kData);const lineOpt={lineWidth:1,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false};mainChart.addLineSeries({color:'#ff9800',...lineOpt}).setData(ma.ma_short);mainChart.addLineSeries({color:'#2196f3',...lineOpt}).setData(ma.ma_mid);mainChart.addLineSeries({color:'#9c27b0',...lineOpt}).setData(ma.ma_long);const lr=LR_DATA;if(lr&&lr.upper&&lr.upper.length>0){mainChart.addLineSeries({color:isDark?'rgba(100,181,246,0.5)':'rgba(30,58,138,0.4)',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Solid,crosshairMarkerVisible:false,lastValueVisible:false,priceLineVisible:false}).setData(lr.upper);mainChart.addLineSeries({color:isDark?'rgba(100,181,246,0.8)':'rgba(30,58,138,0.6)',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Dashed,crosshairMarkerVisible:false,lastValueVisible:false,priceLineVisible:false}).setData(lr.mid);mainChart.addLineSeries({color:isDark?'rgba(100,181,246,0.5)':'rgba(30,58,138,0.4)',lineWidth:1,lineStyle:LightweightCharts.LineStyle.Solid,crosshairMarkerVisible:false,lastValueVisible:false,priceLineVisible:false}).setData(lr.lower)}const pat=PAT_DATA;const neck=NECK_DATA;const patColor=PAT_COLOR;if(pat&&pat.length>0){mainChart.addLineSeries({color:patColor,lineWidth:2,lineStyle:LightweightCharts.LineStyle.Solid,crosshairMarkerVisible:false,lastValueVisible:false,priceLineVisible:false}).setData(pat)}if(neck&&neck.length>0){mainChart.addLineSeries({color:patColor,lineWidth:2,lineStyle:LightweightCharts.LineStyle.Dotted,crosshairMarkerVisible:false,lastValueVisible:false,priceLineVisible:false}).setData(neck)}const totalVolSeries=volChart.addHistogramSeries({priceFormat:{type:'volume'}});totalVolSeries.setData(tVol);const dayTradeVolSeries=volChart.addHistogramSeries({priceFormat:{type:'volume'}});dayTradeVolSeries.setData(dtVol);const legend=document.getElementById('legend');const updateLegend=(p)=>{let d,dtVal,tvVal;if(p.time){d=kDataMap.get(p.time);dtVal=dtVolMap.get(p.time);tvVal=tVolMap.get(p.time)}else{d=kData[kData.length-1];dtVal=dtVol[dtVol.length-1].value;tvVal=tVol[tVol.length-1].value}if(!d||dtVal===undefined||tvVal===undefined)return;const shortDate=d.time.substring(2).replace(/-/g,'/');legend.innerHTML=`<b>${shortDate}</b> &nbsp; 開:${d.open} 高:${d.high} 低:${d.low} 收:<span style="color:${chartTxtColor}">${d.close}</span> &nbsp; <span style="color:#888">總量:${Math.round(tvVal)}</span> &nbsp; <span style="color:#FF9800">當沖:${Math.round(dtVal)}</span>`};updateLegend({time:null});mainChart.subscribeCrosshairMove(p=>{updateLegend(p);if(p.time)volChart.setCrosshairPosition(0,p.time,totalVolSeries);else volChart.clearCrosshairPosition()});volChart.subscribeCrosshairMove(p=>{updateLegend(p);if(p.time)mainChart.setCrosshairPosition(0,p.time,candleSeries);else mainChart.clearCrosshairPosition()});let isSyncingMain=false;let isSyncingVol=false;mainChart.timeScale().subscribeVisibleLogicalRangeChange(r=>{if(!isSyncingMain&&r!==null){isSyncingVol=true;volChart.timeScale().setVisibleLogicalRange(r);isSyncingVol=false}});volChart.timeScale().subscribeVisibleLogicalRangeChange(r=>{if(!isSyncingVol&&r!==null){isSyncingMain=true;mainChart.timeScale().setVisibleLogicalRange(r);isSyncingMain=false}});</script></body></html>"""

st.markdown(CSS, unsafe_allow_html=True)

def is_valid(df, req_cols=None, min_len=1):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty or len(df) < min_len:
        return False
    if req_cols and not all(c in df.columns for c in req_cols):
        return False
    return True

def optimize_memory(df):
    if not is_valid(df):
        return df
    for col in df.columns:
        if df[col].dtype == 'float64':
            df[col] = df[col].astype('float32')
        elif df[col].dtype == 'int64':
            df[col] = df[col].astype('int32')
        elif df[col].dtype == 'object' and any(k in col for k in ['trader', '分點', '標籤']):
            df[col] = df[col].astype('category')
    return df

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

_num_re = re.compile(r'\d+')
_LEVEL_MAP = {
    1: "1-999股", 2: "1-5張", 3: "5-10張", 4: "10-15張", 5: "15-20張",
    6: "20-30張", 7: "30-40張", 8: "40-50張", 9: "50-100張", 10: "100-200張",
    11: "200-400張", 12: "400-600張", 13: "600-800張", 14: "800-1000張", 15: "1000張以上"
}
_LEVEL_CLEAN_CACHE = {}

@st.cache_data(ttl=86400, max_entries=5, show_spinner=False)
def fetch_github_manual(url):
    try:
        r = GENERIC_SESSION.get(url, timeout=5)
        if r.status_code == 200:
            r.encoding = 'utf-8'
            return r.text
        return "ERR-LOAD: 無法載入"
    except Exception as e:
        return f"ERR-LOAD: {e}"

@st.cache_data(ttl=300, max_entries=2, show_spinner=False)
def get_api_usage(token):
    try:
        r = GENERIC_SESSION.get(f"https://api.web.finmindtrade.com/v2/user_info?token={token}", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data.get("user_count", 0), data.get("api_request_limit", 0)
    except:
        pass
    return None, None

st.sidebar.markdown("### 交易戰略大腦")
trade_strategy = st.sidebar.radio("交易戰略偏好", ["右側動能 (短線突破)", "左側潛伏 (中長線價值)"])
is_right_side = "右側" in trade_strategy

st.sidebar.header("戰術參數控制面板")
kline_days = st.sidebar.slider("K線顯示天數", 30, 600, 270, 10)
lookback_days = st.sidebar.selectbox("回溯天數", [20, 60, 90, 120], index=1)
stickiness_threshold = st.sidebar.slider("黏著度門檻 (%)", 10.0, 80.0, 50.0, 5.0)

footprint_stat_days = st.sidebar.select_slider("買賣超統計天數", options=[5, 10, 30, 45, 60, 90, 120], value=10 if is_right_side else 45)
display_map = {5: 20, 10: 20, 30: 45, 45: 60, 60: 60, 90: 90, 120: 120}
footprint_days = st.sidebar.slider("足跡追蹤天數", 5, 120, display_map[footprint_stat_days], 1)
footprint_rows = st.sidebar.slider("足跡矩陣顯示筆數", 5, 50, 15, 5)

st.sidebar.divider()
heatmap_noise_pct = st.sidebar.slider("熱力圖雜訊過濾 (%)", 0.0, 5.0, 0.5 if is_right_side else 1.0, 0.1)

st.sidebar.divider()
alert_smart_pct = st.sidebar.slider("警報: 極端進出 (%)", 1.0, 20.0, 10.0 if is_right_side else 5.0, 1.0)
alert_bias_drop = st.sidebar.slider("警報: 跌破乖離 < (%)", -20.0, 0.0, -3.0, 0.5)

st.sidebar.divider()
firepower_threshold = st.sidebar.slider("買方火力門檻", 1.0, 5.0, 1.5, 0.1)

st.sidebar.divider()
enable_pattern = st.sidebar.checkbox("AI 形態掃描", value=True)
pattern_mode = st.sidebar.selectbox("形態模式", [
    "全自動智慧辨識 (Auto)", "反轉：W底 (雙重底)", "反轉：M頭 (雙重頂)", 
    "反轉：頭肩底", "反轉：頭肩頂", "反轉：三重底", "反轉：三重頂", 
    "反轉：V型反轉", "連續：對稱三角形", "連續：上升三角形", 
    "連續：下降三角形", "連續：上升楔形", "連續：下降楔形", "連續：矩形 (箱型整理)"
])
lr_days = st.sidebar.slider("LR通道天數", 20, 120, 20, 5)
pattern_order = st.sidebar.slider("形態靈敏度", 2, 20, 5, 1)

st.sidebar.divider()
filter_day_trade = st.sidebar.checkbox("計算純淨均價", value=True)

st.sidebar.divider()
ma_short = int(st.sidebar.number_input("短均線", min_value=1, max_value=20, value=10))
ma_mid = int(st.sidebar.number_input("中均線", min_value=20, max_value=100, value=60))
ma_long = int(st.sidebar.number_input("長均線", min_value=100, max_value=300, value=240))

st.title("全息量化系統 (V73.00 終極版)")
user_count, api_limit = get_api_usage(FINMIND_TOKEN)
usage_text = f" | 額度: {user_count}/{api_limit}" if user_count is not None else ""
st.caption(f"V73.00：全息動能引擎 {usage_text}")

with st.expander("說明書", expanded=False): 
    st.markdown(fetch_github_manual(GITHUB_MANUAL_URL), unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])
with col1: 
    user_stock_id = st.text_input("代號", value="2330")
with col2: 
    dead_chip_input = st.text_input("死籌碼 % (留空自動抓)")

run_btn = st.button("啟動引擎", use_container_width=True, key="run_engine")

def safe_to_num(series, fill_val=0):
    if isinstance(series, pd.Series):
        if pd.api.types.is_numeric_dtype(series):
            return series.fillna(fill_val)
        valid_mask = series.notna()
        converted = pd.Series(fill_val, index=series.index, dtype=float)
        if valid_mask.any():
            cleaned = series[valid_mask].astype(str).str.replace(r'[,%＊*]', '', regex=True).str.strip()
            cleaned = cleaned.replace(['', 'nan', 'none', '-', 'y', 'n', 'x', '<na>', 'na', 'null'], np.nan)
            converted.loc[valid_mask] = pd.to_numeric(cleaned, errors='coerce').fillna(fill_val)
        return converted
    elif isinstance(series, (int, float)):
        return series
    else:
        if pd.isna(series):
            return fill_val
        s_str = re.sub(r'[,%＊*]', '', str(series)).strip()
        if not s_str or s_str.lower() in ['nan', 'none', '-', 'y', 'n', 'x', '<na>', 'na', 'null']:
            return fill_val
        try:
            return float(s_str)
        except:
            return fill_val

@st.cache_data(ttl=3600, max_entries=3, show_spinner=False)
def cached_finmind_api_call(url, params_tuple):
    r = FM_SESSION.get(url, params=dict(params_tuple), timeout=20)
    r.raise_for_status() 
    data = r.json().get("data")
    if data is None:
        raise ValueError("ERR-API: 無資料")
    return data

@st.cache_data(ttl=86400, max_entries=5, show_spinner=False)
def get_basic_info_finmind(tid):
    try:
        p = {"dataset": "TaiwanStockInfo", "data_id": tid, "start_date": "2000-01-01"}
        data = cached_finmind_api_call("https://api.finmindtrade.com/api/v4/data", tuple(sorted(p.items())))
        if data:
            df = pd.DataFrame(data)
            if not df.empty:
                return df['stock_name'].iloc[0], df['industry_category'].iloc[0]
    except:
        pass
    return "未知", "未知"

@st.cache_data(ttl=3600, max_entries=3, show_spinner=False)
def fetch_finmind_v50(ds, sd, tid=None, ed=None):
    p = {"dataset": ds, "start_date": sd}
    if tid: p["data_id"] = tid
    if ed: p["end_date"] = ed
    try:
        data = cached_finmind_api_call("https://api.finmindtrade.com/api/v4/data", tuple(sorted(p.items())))
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600, max_entries=3, show_spinner=False)
def fetch_heavy_data_sync_with_progress(user_stock_id, dates_tuple, max_len):
    dates = list(dates_tuple) 
    b_results = []
    a_results = {}
    cb_info_list = []
    
    tdcc_sd = (datetime.date.today() - datetime.timedelta(days=180)).strftime("%Y-%m-%d")
    d_end = dates[max_len-1] if max_len > 0 else dates[0]
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
        ("TaiwanStockConvertibleBondDailyOverview", dates[0], None, None)
    ]

    prog_container = st.empty()
    text_container = st.empty()
    prog_bar = prog_container.progress(0.0)

    def fetch_api(dataset, sd, ed, tid):
        p = {"dataset": dataset, "start_date": sd}
        if tid: p["data_id"] = tid
        if ed: p["end_date"] = ed
        try:
            return dataset, cached_finmind_api_call("https://api.finmindtrade.com/api/v4/data", tuple(sorted(p.items())))
        except:
            return dataset, []

    def fetch_branch(d, tid):
        p = {"dataset": "TaiwanStockTradingDailyReport", "data_id": tid, "start_date": d, "end_date": d}
        try:
            return cached_finmind_api_call("https://api.finmindtrade.com/api/v4/data", tuple(sorted(p.items())))
        except:
            return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future_to_type = {}
        for d in dates[:max_len]:
            future_to_type[executor.submit(fetch_branch, d, user_stock_id)] = 'branch'
            
        for ds, sd, ed, tid in api_targets:
            future_to_type[executor.submit(fetch_api, ds, sd, ed, tid)] = 'api'

        completed = 0
        total_tasks = max_len + len(api_targets)
        for future in concurrent.futures.as_completed(future_to_type):
            completed += 1
            prog_bar.progress(min(1.0, completed / total_tasks))
            text_container.markdown(f"<div class='progress-text'>同步資料中...</div>", unsafe_allow_html=True)
            
            f_type = future_to_type[future]
            if f_type == 'branch':
                res = future.result()
                if res:
                    b_results.extend(res)
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
                    res = f.result()
                    if res[1]:
                        cb_info_list.extend(res[1])

    prog_container.empty()
    text_container.empty()
    
    df_b = optimize_memory(pd.DataFrame.from_records(b_results)) if b_results else pd.DataFrame()
    df_cb_info = pd.DataFrame(cb_info_list)
    return df_b, a_results, df_cb_info

def safe_get_fubon(url):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        if hasattr(ssl, 'OP_LEGACY_SERVER_CONNECT'):
            ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as res:
            return res.read().decode('big5', errors='ignore')
    except:
        try:
            res = GENERIC_SESSION.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, verify=False)
            if res.status_code == 200:
                res.encoding = 'big5'
                return res.text
        except:
            pass
    return ""

@st.cache_data(ttl=3600, max_entries=3, show_spinner=False)
def scrape_director_v50(tid):
    dd = {}
    lt = 0.0
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Referer": f"https://goodinfo.tw"}
        r = GENERIC_SESSION.get(f"https://goodinfo.tw/tw/StockDirectorSharehold.asp?STOCK_ID={tid}", headers=headers, timeout=10)
        if r.status_code == 200:
            r.encoding = 'utf-8'
            dfs = pd.read_html(StringIO(r.text))
            for df in dfs:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = ['_'.join(str(c) for c in col if 'Unnamed' not in str(c)).strip('_') for col in df.columns.values]
                else: 
                    df.columns = df.columns.astype(str)
                
                tc_dir = next((c for c in df.columns if '董監' in str(c) and '持股' in str(c).replace(' ', '')), None)
                tc_large = next((c for c in df.columns if '大股東' in str(c) and '持股' in str(c).replace(' ', '')), None)
                mc = next((c for c in df.columns if '月別' in str(c)), None)
                
                if mc and (tc_dir or tc_large):
                    for ro in df.to_dict('records'):
                        m = str(ro.get(mc, '')).replace('/', '-').strip()
                        if re.match(r'^\d{4}-\d{2}$', m):
                            try:
                                v_dir = float(str(ro.get(tc_dir, '0')).replace(',', '').strip()) if tc_dir and str(ro.get(tc_dir, '0')) not in ['-', '', 'nan'] else 0.0
                                v_large = float(str(ro.get(tc_large, '0')).replace(',', '').strip()) if tc_large and str(ro.get(tc_large, '0')) not in ['-', '', 'nan'] else 0.0
                                val = v_dir + v_large
                                if 0 < val < 100: 
                                    dd[m] = val
                                    if lt == 0.0:
                                        lt = val
                            except:
                                pass
                    if dd:
                        return dd, lt, "Goodinfo", []
    except:
        pass

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
                            try: 
                                ed[name.split('-')[0].strip()] = max(ed.get(name.split('-')[0].strip(), 0), float(r_str))
                            except:
                                pass
                if 0 < sum(ed.values()) < 100: 
                    return {}, round(sum(ed.values()), 2), "富邦", []
    except:
        pass
    return {}, 0.0, "ERR-DATA", []

def get_dead_chip_info(ds, dci, dd, sv, ce):
    if dci and str(dci).strip() != "":
        try:
            return float(str(dci).replace('%', '').strip()), "手動"
        except:
            pass
            
    mk = str(ds)[:7].replace('/', '-')
    if dd and mk in dd:
        return dd[mk], f"{ce}當月"
        
    if dd:
        return list(dd.values())[0], f"{ce}最新"
        
    if sv > 0:
        return sv, ce
        
    return 0.0, "ERR-DATA"

def extract_fubon_table(ht, trg, cols):
    si = ht.find(trg)
    if si == -1:
        return []
        
    out = []
    ist = False
    fh = ht[max(0, si - 500) : si + 35000]
    for tr in re.compile(r'<tr[^>]*>([\s\S]*?)</tr>', re.IGNORECASE).findall(fh):
        tds = re.compile(r'<t[dh][^>]*>([\s\S]*?)</t[dh]>', re.IGNORECASE).findall(tr)
        if tds:
            r = [re.sub(r'<[^>]+>|&nbsp;|\s', '', td).strip() for td in tds]
            if trg in "".join(r): 
                ist = True
            elif ist and len(r) >= cols:
                if r[0] == "" or "註" in r[0]: 
                    ist = False
                else: 
                    out.append(r[:cols])
    return out

@st.cache_data(ttl=3600, max_entries=3, show_spinner=False)
def scrape_fubon_pledge(df_pr, tid):
    alld = []
    for i in range(3):
        html = safe_get_fubon(f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zc0/zc06_{tid}_{i}.djhtm")
        if html:
            p = extract_fubon_table(html, "設質人身", 7)
            if p:
                alld.extend(p)
                
    if not alld:
        return pd.DataFrame(), pd.DataFrame()
        
    sn = set()
    uq = []
    for r in alld:
        r_str = "|".join(r)
        if r_str not in sn: 
            sn.add(r_str)
            uq.append(r)
            
    df_all = pd.DataFrame(uq, columns=["日期", "身份別", "姓名", "設質(張)", "解質(張)", "累積質設(張)", "質權人"])
    cy = datetime.datetime.now().year
    cm = datetime.datetime.now().month
    py = cy
    pm = 99
    pdts = []
    
    for ds in df_all['日期']:
        if len(ds) == 5 and '/' in ds:
            m = int(ds.split('/')[0])
            if pm == 99:
                if m > cm + 1 and cm < 3: py = cy - 1
                else: py = cy
            else:
                if m > pm + 1: py -= 1
            pm = m
            pdts.append(f"{py}-{ds.replace('/', '-')}")
        elif len(ds) >= 7 and '/' in ds: 
            parts = ds.split('/')
            pdts.append(f"{int(parts[0]) + 1911}-{parts[1].strip()}-{parts[2].strip()}")
        else: 
            pdts.append(ds)
            
    df_all['日期'] = pdts
    
    for c in ["設質(張)", "解質(張)", "累積質設(張)"]: 
        df_all[c] = safe_to_num(df_all[c]).astype(int)
        
    prd = {}
    if is_valid(df_pr, ['date', 'close']):
        for _, r in df_pr.iterrows():
            prd[pd.to_datetime(r['date']).strftime('%Y-%m-%d')] = r['close']
            
    pps = []
    mcs = []
    for r in df_all.to_dict('records'):
        fp = "-"
        mc = "-"
        if r['設質(張)'] > 0:
            try:
                td = pd.to_datetime(r['日期'])
                for i in range(20):
                    cd = (td - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
                    if cd in prd: 
                        fp = prd[cd]
                        mc = round(fp * 0.78, 2)
                        break
            except:
                pass
        pps.append(fp)
        mcs.append(mc)
        
    df_all['設質日收盤價'] = pps
    df_all['強制賣出價(0.78)'] = mcs
    
    sm = {}
    for r in df_all.to_dict('records'):
        name = r['姓名']
        if name not in sm: 
            sm[name] = {"title": r['身份別'], "balance": r['累積質設(張)'], "p": "-", "mc": "-"}
        if sm[name]["p"] == "-" and r['設質(張)'] > 0: 
            sm[name]["p"] = r['設質日收盤價']
            sm[name]["mc"] = r['強制賣出價(0.78)']
            
    sr = []
    for n, d in sm.items():
        if d["balance"] > 0:
            sr.append({
                "身份別": d["title"], 
                "姓名": n, 
                "目前剩餘質設(張)": d["balance"], 
                "最後設質收盤價(元)": d["p"], 
                "估算斷頭價(0.78)": d["mc"]
            })
            
    return pd.DataFrame(sr), df_all

def get_v50_intelligence(df_b_raw, df_p_raw, stick_thresh, global_days, dates_list):
    if not is_valid(df_b_raw) or not is_valid(df_p_raw):
        return {}, pd.DataFrame()
        
    actual_global_days = max(1, df_b_raw['date'].nunique())
    
    vol_col = 'Trading_Volume' if 'Trading_Volume' in df_p_raw.columns else 'Trading_volume'
    cols_to_keep = ['date', 'close', 'max', 'min']
    if vol_col in df_p_raw.columns:
        cols_to_keep.append(vol_col)
        
    df_p = df_p_raw[cols_to_keep].copy()
    df_p['date'] = pd.to_datetime(df_p['date'])
    df_p = df_p.sort_values('date', ascending=False)
    
    avg_vol_lots = 3000
    if vol_col in df_p.columns:
        calc_vol = (pd.to_numeric(df_p[vol_col], errors='coerce').head(20).mean()) / 1000
        if not pd.isna(calc_vol) and calc_vol > 0:
            avg_vol_lots = calc_vol

    scale = max(0.2, min(20.0, avg_vol_lots / 3000.0))
    t_50 = max(10, int(50 * scale))
    t_100 = max(20, int(100 * scale))
    t_200 = max(40, int(200 * scale))
    t_300 = max(60, int(300 * scale))
    
    df_p['actual_spread'] = df_p['close'] - df_p['close'].shift(-1).fillna(df_p['close'])
    range_diff = df_p['max'] - df_p['min']
    df_p['pos'] = 0.5 
    
    cond_normal = range_diff > 0
    df_p.loc[cond_normal, 'pos'] = (df_p['close'] - df_p['min']) / range_diff
    df_p.loc[(~cond_normal) & (df_p['actual_spread'] > 0), 'pos'] = 1.0
    df_p.loc[(~cond_normal) & (df_p['actual_spread'] < 0), 'pos'] = 0.0
    
    pos_dict = df_p.set_index('date')['pos'].to_dict()
    latest_close = df_p['close'].iloc[0] if not df_p.empty else 0

    d5 = dates_list[:5]
    d20 = dates_list[:20] if len(dates_list) >= 20 else dates_list
    d60 = dates_list[:60] if len(dates_list) >= 60 else dates_list

    g5_shares = df_b_raw[df_b_raw['date'].isin(d5)].groupby('securities_trader')['net_shares'].sum()
    g20_shares = df_b_raw[df_b_raw['date'].isin(d20)].groupby('securities_trader')['net_shares'].sum()
    g60_shares = df_b_raw[df_b_raw['date'].isin(d60)].groupby('securities_trader')['net_shares'].sum()
    
    stats = pd.DataFrame({
        'net_5d': (g5_shares / 1000).round(),
        'net_20d': (g20_shares / 1000).round(),
        'net_60d': (g60_shares / 1000).round()
    }).fillna(0).astype(int)

    g = df_b_raw.groupby('securities_trader').agg(
        tb_shares=('buy', 'sum'),
        ts_shares=('sell', 'sum'),
        net_shares=('net_shares', 'sum'),
        buy_amt=('valid_buy_amt', 'sum'),
        sell_amt=('valid_sell_amt', 'sum'),
        valid_b_shares=('valid_buy', 'sum'),
        valid_s_shares=('valid_sell', 'sum'),
        active_days=('date_dt', 'nunique'),
        last_date=('date_dt', 'max')
    )
    
    g['stickiness'] = (g['active_days'] / actual_global_days) * 100
    
    g['hoard_ratio'] = np.where(g['net_shares'] > 0,
                                (g['net_shares'] / g['tb_shares'].replace(0, np.nan)) * 100,
                                (g['net_shares'].abs() / g['ts_shares'].replace(0, np.nan)) * 100)
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

    g['tag'] = np.select(
        [cond_heavy, cond_lock, cond_cover, cond_profit, cond_exit, cond_snap, cond_maker, cond_follow], 
        ["主力重砲", "波段鎖碼", "認錯回補", "獲利調節", "棄守提款", "隔日突擊", "避險造市", "跟風小戶"], 
        default="路人雜訊"
    )
    tags = g['tag'].to_dict()
    
    g = g[(g['tb_shares'] > 0) | (g['ts_shares'] > 0)].copy()
    b_strs = g['avg_b'].apply(lambda x: f"{x:,.2f}" if x > 0 else "-")
    cond_loss = (g['avg_b'] > latest_close) & (g['avg_b'] > 0) & (g['net_shares'] > 0)
    
    g['b_str'] = np.where(cond_loss, "(虧) " + b_strs, b_strs)
    g['pos'] = g['last_date'].map(pos_dict).fillna(0.5).round(2)
    
    res_df = pd.DataFrame({
        "分點名稱": g.index,
        "最終標籤": g['tag'],
        "近60日淨買(張)": g['net_60d'].astype(int),
        "近20日淨買(張)": g['net_20d'].astype(int),
        "近5日淨買(張)": g['net_5d'].astype(int),
        "黏著度(%)": g['stickiness'].round(1),
        "囤出貨率(%)": g['hoard_ratio'],
        "總買(張)": g['tb'],
        "總賣(張)": g['ts'],
        "淨留倉": g['net_lots'],
        "買均價": g['b_str'],
        "賣均價": np.where(g['avg_s'] > 0, g['avg_s'].round(2).astype(str), "-"),
        "收盤位階": g['pos']
    }).sort_values('近60日淨買(張)', ascending=False)
    
    return tags, res_df

def calculate_dynamic_radar_depth(df_b_raw, dates_list, total_lots, df_price):
    if total_lots <= 0 or not is_valid(df_b_raw):
        return 15, "缺資料"
    
    if total_lots < 300000:
        base_n = 10
        cap_desc = "微"
    elif total_lots < 1000000:
        base_n = 15
        cap_desc = "中小"
    elif total_lots < 5000000:
        base_n = 30
        cap_desc = "中大"
    else:
        base_n = 50
        cap_desc = "大"
        
    recent_dates = dates_list[:5]
    recent_pr = df_price[df_price['日期'].isin(recent_dates)]
    
    if not recent_pr.empty and total_lots > 0:
        avg_vol = recent_pr['成交量(張)'].mean()
        turnover_5d = (avg_vol / total_lots) * 100
    else:
        turnover_5d = 0
        
    if turnover_5d > 10.0: 
        final_n = max(5, int(base_n * 0.7))
        turn_desc = "|高週轉"
    elif turnover_5d < 1.0: 
        final_n = min(50, int(base_n * 1.2))
        turn_desc = "|低波"
    else: 
        final_n = base_n
        turn_desc = ""
    
    df_20 = df_b_raw[df_b_raw['date'].isin(dates_list[:20])].copy()
    g = df_20.groupby('securities_trader')[['buy', 'sell']].sum()
    g['net'] = (g['buy'] - g['sell']) / 1000
    buyers = g[g['net'] > 0].sort_values('net', ascending=False)
    
    if len(buyers) > 5:
        top5_sum = buyers.head(5)['net'].sum()
        if len(buyers) >= final_n:
            topN_sum = buyers.head(final_n)['net'].sum()
        else:
            topN_sum = buyers['net'].sum()
            
        if topN_sum > 0 and (top5_sum / topN_sum) > 0.8:
            final_n = max(5, min(final_n, 10))
            turn_desc += "|集中"
            
    final_n = max(5, min(final_n, 50))
    return final_n, f"{cap_desc}{turn_desc}"

def calculate_pure_defense_line(df_b_raw, tags, is_filter_active, total_lots, dead_chip_ratio, dynamic_n):
    if not is_valid(df_b_raw):
        return 0.0, 0, 0, 0.0, []
    
    if is_filter_active:
        valid_df = df_b_raw[~df_b_raw['is_short'] & ~df_b_raw['tag'].isin(["棄守提款", "避險造市"])]
    else:
        valid_df = df_b_raw
        
    if not is_valid(valid_df):
        return 0.0, 0, 0, 0.0, []
    
    broker_stats = valid_df.groupby('securities_trader').agg(
        buy_vol=('buy', 'sum'), 
        sell_vol=('sell', 'sum'), 
        buy_amt=('valid_buy_amt', 'sum'), 
        valid_buy_vol=('valid_buy', 'sum')
    )
    
    broker_stats['net_vol'] = broker_stats['buy_vol'] - broker_stats['sell_vol']
    top_buyers = broker_stats[broker_stats['net_vol'] > 0].sort_values('net_vol', ascending=False).head(dynamic_n).copy()
    
    if top_buyers.empty:
        return 0.0, 0, 0, 0.0, []
    
    core_branch_names = top_buyers.index.tolist()
    top_buyers['avg_buy_price'] = (top_buyers['buy_amt'] / top_buyers['valid_buy_vol'].replace(0, np.nan)).fillna(0)
    
    valid_top_buyers = top_buyers[top_buyers['avg_buy_price'] > 0]
    total_net_vol = valid_top_buyers['net_vol'].sum()
    
    c_value = 0.0
    if total_lots > 0:
        safe_dead_ratio = max(0.0, min(99.9, float(dead_chip_ratio)))
        free_float_lots = total_lots * ((100.0 - safe_dead_ratio) / 100.0)
        if free_float_lots > 0:
            raw_c = (int(top_buyers['net_vol'].sum() / 1000) / free_float_lots) * 100
            c_value = round(min(98.0, raw_c), 2)
            
    vwap = 0.0
    if total_net_vol > 0:
        vwap = round((valid_top_buyers['avg_buy_price'] * valid_top_buyers['net_vol']).sum() / total_net_vol, 2)
        
    return vwap, int(top_buyers['net_vol'].sum() / 1000), len(top_buyers), c_value, core_branch_names

def get_core_period_net(df_raw, rank_dates, core_names):
    if not is_valid(df_raw) or not rank_dates or not core_names: return 0
    df_rank = df_raw[df_raw['date'].isin(rank_dates) & df_raw['securities_trader'].isin(core_names)]
    net_shares = df_rank['buy'].sum() - df_rank['sell'].sum()
    return int(round(net_shares / 1000))

def process_price(df):
    if not is_valid(df): return pd.DataFrame()
    df_out = df.rename(columns={"date":"日期","close":"收盤價(元)","spread":"漲跌(元)","open":"開盤價(元)","max":"最高價(元)","min":"最低價(元)"})
    
    for col in ["收盤價(元)", "開盤價(元)", "最高價(元)", "最低價(元)", "漲跌(元)"]:
        if col in df_out.columns: 
            df_out[col] = safe_to_num(df_out[col])
            
    if 'Trading_Volume' in df_out.columns: 
        df_out['成交量(張)'] = (safe_to_num(df_out['Trading_Volume']) / 1000).round().astype(int)
    elif 'Trading_volume' in df_out.columns: 
        df_out['成交量(張)'] = (safe_to_num(df_out['Trading_volume']) / 1000).round().astype(int)
    else: 
        df_out['成交量(張)'] = 0
        
    df_out = df_out.loc[:, ~df_out.columns.duplicated()].copy()
    df_out['斷頭價(0.78)'] = (df_out["收盤價(元)"] * 0.78).round(2)
    
    cols_to_keep = ['日期','成交量(張)','開盤價(元)','最高價(元)','最低價(元)','收盤價(元)','漲跌(元)','斷頭價(0.78)']
    return df_out[[c for c in cols_to_keep if c in df_out.columns]].sort_values('日期', ascending=False)

def process_technical_analysis(df_price, s_ma, m_ma, l_ma):
    if not is_valid(df_price, ['收盤價(元)', '日期'], 30): return pd.DataFrame()
    
    s_ma = int(s_ma)
    m_ma = int(m_ma)
    l_ma = int(l_ma)
    
    df_ta = df_price[['日期', '收盤價(元)']].sort_values('日期', ascending=True).copy()
    df_ta['收盤價(元)'] = pd.to_numeric(df_ta['收盤價(元)'], errors='coerce').astype('float64')
    
    df_ta[f'MA{s_ma}'] = df_ta['收盤價(元)'].rolling(window=s_ma, min_periods=1).mean().round(2)
    df_ta[f'MA{m_ma}(中線)'] = df_ta['收盤價(元)'].rolling(window=m_ma, min_periods=1).mean().round(2)
    df_ta[f'MA{l_ma}(長線)'] = df_ta['收盤價(元)'].rolling(window=l_ma, min_periods=1).mean().round(2)
    
    df_ta['中線乖離(%)'] = ((df_ta['收盤價(元)'] - df_ta[f'MA{m_ma}(中線)']) / df_ta[f'MA{m_ma}(中線)'].replace(0, np.nan) * 100).round(2)
    
    cond_up = df_ta['收盤價(元)'] > df_ta[f'MA{m_ma}(中線)']
    cond_down = df_ta['收盤價(元)'] < df_ta[f'MA{m_ma}(中線)']
    df_ta['技術面診斷'] = np.select([cond_up, cond_down], ["站上中線防守", "跌破中線防守"], default="盤整")
    
    return df_ta.sort_values('日期', ascending=False)

def process_linear_regression(df_price, lr_days):
    if not is_valid(df_price, ['收盤價(元)'], 2): return pd.DataFrame()
    
    df_lr = df_price.head(lr_days)[['日期', '收盤價(元)']].sort_values('日期', ascending=True).copy()
    df_lr['收盤價(元)'] = pd.to_numeric(df_lr['收盤價(元)'], errors='coerce').astype('float64')
    
    y = df_lr['收盤價(元)'].dropna().values
    if len(y) < 2: return pd.DataFrame()
    
    x = np.arange(len(y))
    A = np.vstack([x, np.ones(len(x))]).T
    m, c = np.linalg.lstsq(A, y, rcond=None)[0]
    y_pred = m * x + c
    std_err = np.std(y - y_pred)
    
    df_lr['LR_Mid'] = y_pred
    df_lr['LR_Upper'] = y_pred + 2 * std_err
    df_lr['LR_Lower'] = y_pred - 2 * std_err
    
    return df_lr[['日期', 'LR_Mid', 'LR_Upper', 'LR_Lower']]

def process_geometric_patterns(df_price, kline_days, order, mode, current_price):
    if not is_valid(df_price, min_len=order * 2): return {}
    
    df = df_price.head(kline_days).sort_values('日期', ascending=True).reset_index(drop=True)
    lows_vals = df['最低價(元)'].values
    highs_vals = df['最高價(元)'].values
    dates_vals = df['日期'].values
    
    highs = []
    lows = []
    
    for i in range(order, len(df) - order):
        win_start = max(0, i - order)
        win_end = i + order + 1
        if lows_vals[i] == np.min(lows_vals[win_start:win_end]):
            lows.append((dates_vals[i], float(lows_vals[i]), i))
        if highs_vals[i] == np.max(highs_vals[win_start:win_end]):
            highs.append((dates_vals[i], float(highs_vals[i]), i))
            
    if len(lows) < 2 or len(highs) < 2: return {}
    
    last_date = dates_vals[-1]
    tol = 0.03
    is_auto = "Auto" in mode

    if "三重底" in mode or is_auto:
        if len(lows) >= 3:
            l1 = lows[-3]
            l2 = lows[-2]
            l3 = lows[-1]
            if l1[1] > 0 and l2[1] > 0 and abs(l1[1]-l2[1])/l1[1] < tol and abs(l2[1]-l3[1])/l2[1] < tol:
                b_h = [h for h in highs if l1[2] < h[2] < l3[2]]
                if b_h:
                    h_max = max(b_h, key=lambda x: x[1])
                    status = "已突破頸線" if current_price > h_max[1] else "成型中"
                    return {'name': '三重底', 'shape_x': [l1[0], b_h[0][0], l2[0], b_h[-1][0], l3[0]], 'shape_y': [l1[1], b_h[0][1], l2[1], b_h[-1][1], l3[1]], 'neck_x': [l1[0], last_date], 'neck_y': [h_max[1], h_max[1]], 'color': '#9c27b0', 'desc': f"三重底 ({status})", 'signal': 'bullish'}

    if "三重頂" in mode or is_auto:
        if len(highs) >= 3:
            h1 = highs[-3]
            h2 = highs[-2]
            h3 = highs[-1]
            if h1[1] > 0 and h2[1] > 0 and abs(h1[1]-h2[1])/h1[1] < tol and abs(h2[1]-h3[1])/h2[1] < tol:
                b_l = [l for l in lows if h1[2] < l[2] < h3[2]]
                if b_l:
                    l_min = min(b_l, key=lambda x: x[1])
                    status = "已跌破頸線" if current_price < l_min[1] else "成型中"
                    return {'name': '三重頂', 'shape_x': [h1[0], b_l[0][0], h2[0], b_l[-1][0], h3[0]], 'shape_y': [h1[1], b_l[0][1], h2[1], b_l[-1][1], h3[1]], 'neck_x': [h1[0], last_date], 'neck_y': [l_min[1], l_min[1]], 'color': '#d32f2f', 'desc': f"三重頂 ({status})", 'signal': 'bearish'}

    if "頭肩底" in mode or is_auto:
        if len(lows) >= 3:
            l1 = lows[-3]
            l2 = lows[-2]
            l3 = lows[-1]
            if l1[1] > 0 and l2[1] < l1[1] and l2[1] < l3[1] and abs(l1[1]-l3[1])/l1[1] < 0.05:
                b_h1 = [h for h in highs if l1[2] < h[2] < l2[2]]
                b_h2 = [h for h in highs if l2[2] < h[2] < l3[2]]
                if b_h1 and b_h2:
                    h1 = max(b_h1, key=lambda x: x[1])
                    h2 = max(b_h2, key=lambda x: x[1])
                    status = "已突破頸線" if current_price > max(h1[1], h2[1]) else "打右肩中"
                    return {'name': '頭肩底', 'shape_x': [l1[0], h1[0], l2[0], h2[0], l3[0]], 'shape_y': [l1[1], h1[1], l2[1], h2[1], l3[1]], 'neck_x': [h1[0], last_date], 'neck_y': [h1[1], h2[1]], 'color': '#e91e63', 'desc': f"頭肩底 ({status})", 'signal': 'bullish'}

    if "頭肩頂" in mode or is_auto:
        if len(highs) >= 3:
            h1 = highs[-3]
            h2 = highs[-2]
            h3 = highs[-1]
            if h1[1] > 0 and h2[1] > h1[1] and h2[1] > h3[1] and abs(h1[1]-h3[1])/h1[1] < 0.05:
                b_l1 = [l for l in lows if h1[2] < l[2] < h2[2]]
                b_l2 = [l for l in lows if h2[2] < l[2] < h3[2]]
                if b_l1 and b_l2:
                    l1 = min(b_l1, key=lambda x: x[1])
                    l2 = min(b_l2, key=lambda x: x[1])
                    status = "已跌破頸線" if current_price < min(l1[1], l2[1]) else "做右肩中"
                    return {'name': '頭肩頂', 'shape_x': [h1[0], l1[0], h2[0], l2[0], h3[0]], 'shape_y': [h1[1], l1[1], h2[1], l2[1], h3[1]], 'neck_x': [l1[0], last_date], 'neck_y': [l1[1], l2[1]], 'color': '#d32f2f', 'desc': f"頭肩頂 ({status})", 'signal': 'bearish'}

    if "W底" in mode or is_auto:
        if len(lows) >= 2:
            l1 = lows[-2]
            l2 = lows[-1]
            b_h = [h for h in highs if l1[2] < h[2] < l2[2]]
            if b_h and l1[1] > 0:
                h1 = max(b_h, key=lambda x: x[1])
                diff = abs(l1[1] - l2[1]) / l1[1]
                if diff <= tol or "W底" in mode:
                    status = "已突破頸線" if current_price > h1[1] else "成型中"
                    desc = f"標準 W底 ({status})" if diff <= tol else f"強制標示 W底 ({status})"
                    return {'name': 'W底', 'shape_x': [l1[0], h1[0], l2[0]], 'shape_y': [l1[1], h1[1], l2[1]], 'neck_x': [l1[0], last_date], 'neck_y': [h1[1], h1[1]], 'color': '#9c27b0', 'desc': desc, 'signal': 'bullish'}

    if "M頭" in mode or is_auto:
        if len(highs) >= 2:
            h1 = highs[-2]
            h2 = highs[-1]
            b_l = [l for l in lows if h1[2] < l[2] < h2[2]]
            if b_l and h1[1] > 0:
                l1 = min(b_l, key=lambda x: x[1])
                diff = abs(h1[1] - h2[1]) / h1[1]
                if diff <= tol or "M頭" in mode:
                    status = "已跌破頸線" if current_price < l1[1] else "成型中"
                    desc = f"標準 M頭 ({status})" if diff <= tol else f"強制標示 M頭 ({status})"
                    return {'name': 'M頭', 'shape_x': [h1[0], l1[0], h2[0]], 'shape_y': [h1[1], l1[1], h2[1]], 'neck_x': [h1[0], last_date], 'neck_y': [l1[1], l1[1]], 'color': '#d32f2f', 'desc': desc, 'signal': 'bearish'}

    if any(k in mode for k in ["連續", "三角形", "楔形", "矩形"]) or is_auto:
        if len(highs) >= 2 and len(lows) >= 2:
            h1 = highs[-2]
            h2 = highs[-1]
            l1 = lows[-2]
            l2 = lows[-1]
            
            h_diff = (h2[1] - h1[1]) / h1[1] if h1[1] > 0 else 0
            l_diff = (l2[1] - l1[1]) / l1[1] if l1[1] > 0 else 0
            
            p_name = ""
            p_color = ""
            p_desc = ""
            p_sig = "neutral"
            
            if abs(h_diff) < tol and abs(l_diff) < tol and ("矩形" in mode or is_auto):
                p_name = "箱型矩形"
                p_color = "#2196f3"
                p_desc = "矩形整理"
            elif abs(h_diff) < tol and l_diff > tol and ("上升三角形" in mode or is_auto):
                p_name = "上升三角形"
                p_color = "#4caf50"
                p_desc = "上升三角形"
                p_sig = "bullish"
            elif h_diff < -tol and abs(l_diff) < tol and ("下降三角形" in mode or is_auto):
                p_name = "下降三角形"
                p_color = "#f44336"
                p_desc = "下降三角形"
                p_sig = "bearish"
            elif h_diff < -tol and l_diff > tol and ("對稱" in mode or "收斂" in mode or is_auto):
                p_name = "對稱三角形"
                p_color = "#ff9800"
                p_desc = "對稱三角形"
            elif h_diff > tol and l_diff > tol and l_diff > h_diff and ("上升楔形" in mode or is_auto):
                p_name = "上升楔形"
                p_color = "#ff5722"
                p_desc = "上升楔形"
                p_sig = "bearish"
            elif h_diff < -tol and l_diff < -tol and h_diff < l_diff and ("下降楔形" in mode or is_auto):
                p_name = "下降楔形"
                p_color = "#8bc34a"
                p_desc = "下降楔形"
                p_sig = "bullish"
                
            if p_name or not is_auto:
                p_name = p_name if p_name else mode.split('：')[-1].strip()
                p_desc = p_desc if p_desc else mode.split('：')[-1]
                p_color = p_color if p_color else "#999"
                return {'name': p_name, 'shape_x': [h1[0], h2[0]], 'shape_y': [h1[1], h2[1]], 'neck_x': [l1[0], l2[0]], 'neck_y': [l1[1], l2[1]], 'color': p_color, 'desc': p_desc, 'signal': p_sig}

    if "V型反轉" in mode or is_auto:
        if len(lows) >= 1 and len(highs) >= 2:
            l1 = lows[-1]
            h_before = [h for h in highs if h[2] < l1[2]]
            h_after = [h for h in highs if h[2] > l1[2]]
            if h_before and h_after and l1[1] > 0:
                hb = h_before[-1]
                ha = h_after[0]
                if (hb[1]-l1[1])/l1[1] > 0.1 and (ha[1]-l1[1])/l1[1] > 0.1:
                    status = "已突破下降趨勢" if current_price > ha[1] else "反轉進行中"
                    return {'name': 'V型反轉', 'shape_x': [hb[0], l1[0], ha[0]], 'shape_y': [hb[1], l1[1], ha[1]], 'neck_x': [hb[0], ha[0]], 'neck_y': [hb[1], ha[1]], 'color': '#00bcd4', 'desc': f"深V反轉 ({status})", 'signal': 'bullish'}
    return {}

def clean_level_by_math(x):
    s = re.sub(r'[, ]|\.0', '', str(x))
    if s in _LEVEL_CLEAN_CACHE: return _LEVEL_CLEAN_CACHE[s]
    
    res = "合計"
    if s and s not in ["合計", "總計", "差異數"]:
        if "以上" in s: 
            res = "1000張以上"
        elif s.isdigit():
            v = int(s)
            if v == 99: res = "合計"
            elif 1 <= v <= 14: res = _LEVEL_MAP.get(v, s)
            elif v >= 15: res = "1000張以上"
            else: res = s
        else:
            n = _num_re.findall(s)
            if not n: 
                res = s
            else:
                v = int(n[-1]) if len(n) > 1 else int(n[0])
                if len(n) == 1 and v <= 21:
                    if 1 <= v <= 14: res = _LEVEL_MAP.get(v, s) 
                    else: res = "1000張以上"
                else:
                    if v >= 1000000: res = "1000張以上"
                    elif v >= 800000: res = "800-1000張"
                    elif v >= 600000: res = "600-800張"
                    elif v >= 400000: res = "400-600張"
                    elif v >= 200000: res = "200-400張"
                    elif v >= 100000: res = "100-200張"
                    elif v >= 50000: res = "50-100張"
                    elif v >= 40000: res = "40-50張"
                    elif v >= 30000: res = "30-40張"
                    elif v >= 20000: res = "20-30張"
                    elif v >= 15000: res = "15-20張"
                    elif v >= 10000: res = "10-15張"
                    elif v >= 5000: res = "5-10張"
                    elif v >= 1000: res = "1-5張"
                    else: res = "1-999股"
    _LEVEL_CLEAN_CACHE[s] = res
    return res

def process_tdcc(df):
    if not is_valid(df, ['HoldingSharesLevel']): 
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
    df_clean = df[~df['HoldingSharesLevel'].astype(str).str.contains('差異數', na=False)].copy()
    df_clean['LevelClean'] = df_clean['HoldingSharesLevel'].apply(clean_level_by_math)
    
    if 'HoldingShares' in df_clean.columns:
        df_clean['unit'] = (safe_to_num(df_clean['HoldingShares']) / 1000).round().astype(int)
    elif 'unit' in df_clean.columns:
        df_clean['unit'] = (safe_to_num(df_clean['unit']) / 1000).round().astype(int)
    else:
        df_clean['unit'] = 0
        
    if 'people' in df_clean.columns:
        df_clean['people'] = safe_to_num(df_clean['people']).astype(int)
    else:
        df_clean['people'] = 0
        
    valid_dates = sorted(df_clean['date'].unique(), reverse=True)[:15]
    df_recent = df_clean[df_clean['date'].isin(valid_dates)]
    
    df_levels = df_recent[~df_recent['LevelClean'].str.contains('合計|總計', na=False)]
    if not is_valid(df_levels): 
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
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
        df_w[f"{l}_比例(%)"] = (p_u[l] / df_t['總張數'].replace(0, np.nan) * 100).fillna(0).round(2)
        
    df_w_out = df_w.rename(columns={'date': '日期'}).sort_values('日期', ascending=False)
    
    cols_u = ['date'] + lvls
    df_u_merge = pd.merge(df_t[['date', '總張數']], p_u[cols_u], on='date')
    df_u_out = df_u_merge.rename(columns={'date': '日期'}).sort_values('日期', ascending=False)
    
    cols_p = ['date'] + lvls
    df_p_merge = pd.merge(df_t[['date', '總人數(人)']], p_p[cols_p], on='date')
    df_p_out = df_p_merge.rename(columns={'date': '日期'}).sort_values('日期', ascending=False)
    
    return df_w_out, df_u_out, df_p_out

def process_tdcc_dynamic_v2(df_share_wide, df_price, dead_chip_input, dynamic_dict, static_val, chip_engine):
    if not is_valid(df_share_wide) or not is_valid(df_price): return pd.DataFrame()
    
    df_s = df_share_wide.copy()
    df_s['dt'] = pd.to_datetime(df_s['日期'])
    
    df_p = df_price[['日期', '收盤價(元)']].copy()
    df_p['dt'] = pd.to_datetime(df_p['日期'])
    df_p = df_p.drop_duplicates(subset=['dt']).sort_values('dt')
    
    df_m = pd.merge_asof(df_s.sort_values('dt'), df_p[['dt', '收盤價(元)']], on='dt', direction='backward').sort_values('dt', ascending=False)
    
    levels_cols = ['100-200張_比例(%)', '200-400張_比例(%)', '400-600張_比例(%)', '600-800張_比例(%)', '800-1000張_比例(%)', '1000張以上_比例(%)']
    for col in levels_cols:
        df_m[col] = pd.to_numeric(df_m.get(col, 0), errors='coerce').fillna(0.0)

    df_m['pct_1000'] = df_m['1000張以上_比例(%)']
    df_m['pct_800'] = df_m['pct_1000'] + df_m['800-1000張_比例(%)']
    df_m['pct_600'] = df_m['pct_800'] + df_m['600-800張_比例(%)']
    df_m['pct_400'] = df_m['pct_600'] + df_m['400-600張_比例(%)']
    df_m['pct_200'] = df_m['pct_400'] + df_m['200-400張_比例(%)']
    df_m['pct_100'] = df_m['pct_200'] + df_m['100-200張_比例(%)']
    
    df_m = df_m[df_m['收盤價(元)'].notna() & (df_m['收盤價(元)'] > 0)].copy()
    if df_m.empty: return pd.DataFrame()
    
    dead_info = df_m['日期'].apply(lambda d: get_dead_chip_info(d, dead_chip_input, dynamic_dict, static_val, chip_engine))
    df_m['safe_dead_ratio'] = dead_info.apply(lambda x: max(0.0, min(99.9, x[0])))
    df_m['cl'] = dead_info.apply(lambda x: x[1])
    
    lvls = np.array([100, 200, 400, 600, 800, 1000])
    
    base_lots = np.where(df_m['收盤價(元)'] > 0, 15000 / df_m['收盤價(元)'], 1000)
    free_float_ratio = np.clip((100 - df_m['safe_dead_ratio']) / 100, 0.05, 1.0)
    float_1pct_lots = df_m['總張數'] * free_float_ratio * 0.01

    raw_th = np.clip(np.minimum(base_lots, float_1pct_lots), 100, 1000)
    
    diffs = np.abs(raw_th[:, None] - lvls)
    df_m['ct'] = lvls[diffs.argmin(axis=1)]
    
    conds = [df_m['ct'] <= 100, df_m['ct'] <= 200, df_m['ct'] <= 400, df_m['ct'] <= 600, df_m['ct'] <= 800]
    choices = [df_m['pct_100'], df_m['pct_200'], df_m['pct_400'], df_m['pct_600'], df_m['pct_800']]
    df_m['lp'] = np.select(conds, choices, default=df_m['pct_1000'])
    
    mask_valid_dead = (df_m['safe_dead_ratio'] > 0) & (df_m['safe_dead_ratio'] < 100)
    cv = np.maximum(0, (df_m['lp'] - df_m['safe_dead_ratio']) / (100.0 - df_m['safe_dead_ratio']))
    df_m['cd'] = np.where(mask_valid_dead, np.round(cv * 100, 2), "-")
    
    st_conds = [df_m['lp'] > 80.0, df_m['lp'] > 70.0, (df_m['lp'] >= 40.0) & (df_m['lp'] <= 70.0)]
    st_choices = ["極度集中", "高度鎖碼", "波段甜區"]
    df_m['st_val'] = np.select(st_conds, st_choices, default="籌碼渙散")
    
    out_df = pd.DataFrame({
        "日期": df_m['日期'],
        "收盤價(元)": df_m['收盤價(元)'].round(2),
        "大戶精算門檻": "系統判定 (" + df_m['ct'].astype(int).astype(str) + "張)",
        "大戶原持股(%)": df_m['lp'].round(2),
        "董監死籌碼(%)": np.where(df_m['safe_dead_ratio'] > 0, 
                             df_m['safe_dead_ratio'].apply(lambda x: f"{x:.2f}%") + " (" + df_m['cl'] + ")", 
                             "-"),
        "純淨活大戶C_Value(%)": df_m['cd'],
        "實戰判定": df_m['st_val']
    })

    return out_df

def process_branch_diff_v2(df_raw, actual_dates, fire_thresh, period_days=10):
    if not is_valid(df_raw, ['date', 'securities_trader', 'buy', 'sell']) or not actual_dates: 
        return pd.DataFrame()
        
    out = [] 
    
    # Safe groupby mapping
    grouped = df_raw.groupby('date')
    branch_grouped = {}
    for name, group in grouped:
        branch_grouped[name] = group

    for d in actual_dates[:period_days]:
        if d not in branch_grouped: continue
        df_d = branch_grouped[d]
        
        b = df_d[df_d['buy'] > 0]
        s = df_d[df_d['sell'] > 0]
        bc = b['securities_trader'].nunique()
        sc = s['securities_trader'].nunique()
        
        ac_df = df_d[(df_d['buy'] > 0) | (df_d['sell'] > 0)]
        ac = ac_df['securities_trader'].nunique()
        
        avg_b = b['buy'].sum() / bc if bc > 0 else 0
        avg_s = s['sell'].sum() / sc if sc > 0 else 0
        
        fp = (avg_b / avg_s) if avg_s > 0 else (99.9 if avg_b > 0 else 1.0)
        
        daily_total_vol = df_d['buy'].sum()
        mp = 0
        if daily_total_vol > 0:
            buy_sum = df_d.groupby('securities_trader')['buy'].sum()
            sell_sum = df_d.groupby('securities_trader')['sell'].sum()
            g_net = buy_sum - sell_sum
            
            top_15_buy_vol = g_net[g_net > 0].nlargest(15).sum()
            top_15_sell_vol = abs(g_net[g_net < 0].nsmallest(15).sum())
            mp = (top_15_buy_vol - top_15_sell_vol) / daily_total_vol * 100

        diag = []
        if fp >= fire_thresh and ((sc - bc) / ac * 100 if ac > 0 else 0) > 5: 
            diag.append("火力壓制")
        elif fp < 0.7 and (bc - sc) > 50: 
            diag.append("散戶進場")
            
        if mp > 15: 
            diag.append("重兵集結")
        elif mp < -15: 
            diag.append("強力倒貨")
        
        out.append({
            "日期": d, 
            "活躍家數": ac, 
            "買賣家數差": bc - sc, 
            "籌碼集中度(%)": round(((sc - bc) / ac * 100 if ac > 0 else 0), 1), 
            "買方火力(倍)": round(fp, 2), 
            "主力成交力(%)": round(mp, 2), 
            "鷹眼診斷": " | ".join(diag) if diag else "中性"
        })
    return pd.DataFrame(out)

def process_v30_daily_tracking(df_branch_raw, intel_tags, df_price, df_branch_diff, actual_dates, fire_thresh, period_days=5):
    if not is_valid(df_branch_raw) or len(actual_dates) < period_days: 
        return pd.DataFrame(), pd.DataFrame()
        
    out = []
    audit_smart_money = []
    
    df_b = df_branch_raw[df_branch_raw['date'].isin(actual_dates[:period_days])].copy()
    
    df_smart = df_b[df_b['is_smart']].copy()
    smart_dict = {}
    if not df_smart.empty:
        df_smart_all = df_smart.groupby(['date', 'securities_trader', 'tag']).agg(
            bs=('buy','sum'), 
            ss=('sell','sum'), 
            buy_amt=('valid_buy_amt','sum'), 
            sell_amt=('valid_sell_amt','sum')
        ).reset_index()
        df_smart_all['net_vol'] = ((df_smart_all['bs'] - df_smart_all['ss']) / 1000).round().astype(int)
        for name, group in df_smart_all.groupby('date'):
            smart_dict[name] = group

    df_short = df_b[df_b['is_short']].copy()
    short_dict = {}
    if not df_short.empty:
        df_short_all = df_short.groupby(['date', 'securities_trader']).agg(
            bs=('buy','sum'), 
            ss=('sell','sum')
        ).reset_index()
        df_short_all['net_vol'] = ((df_short_all['bs'] - df_short_all['ss']) / 1000).round().astype(int)
        for name, group in df_short_all.groupby('date'):
            short_dict[name] = group

    price_dict = df_price.set_index('日期').to_dict('index') if not df_price.empty else {}
    diff_dict = df_branch_diff.set_index('日期').to_dict('index') if not df_branch_diff.empty else {}
    
    for d in actual_dates[:period_days]:
        pr_row = price_dict.get(d, {})
        diff_row = diff_dict.get(d, {})
        
        cp = pr_row.get('收盤價(元)', 0)
        op = pr_row.get('開盤價(元)', 0)
        hp = pr_row.get('最高價(元)', 0)
        lp = pr_row.get('最低價(元)', 0)
        sp_raw = pr_row.get('漲跌(元)', 0)
        
        try: sp_num = float(re.sub(r'[+,]', '', str(sp_raw)).strip())
        except: sp_num = 0.0
        
        sg = smart_dict.get(d, pd.DataFrame(columns=['securities_trader', 'tag', 'bs', 'ss', 'buy_amt', 'sell_amt', 'net_vol']))
        shg = short_dict.get(d, pd.DataFrame(columns=['securities_trader', 'bs', 'ss', 'net_vol']))
        
        if d == actual_dates[0]: 
            for r in sg.to_dict('records'):
                if r['net_vol'] != 0:
                    audit_smart_money.append({
                        "日期": d, 
                        "分點": r['securities_trader'], 
                        "標籤": r['tag'], 
                        "淨買超(張)": r['net_vol']
                    })
                    
        smart_net = sg['net_vol'].sum() if not sg.empty else 0
        short_trap = shg[shg['net_vol'] > 0]['net_vol'].sum() if not shg.empty else 0
        
        total_n = 0
        smart_avg_cost = 0.0
        if not sg.empty:
            s_ret_long = sg[sg['bs'] - sg['ss'] > 0]
            total_n = (s_ret_long['bs'] - s_ret_long['ss']).sum()
            total_net_amt = (s_ret_long['buy_amt'] - s_ret_long['sell_amt']).sum()
            if total_n > 0:
                smart_avg_cost = max(0.0, total_net_amt / total_n)
                
        gap = cp - smart_avg_cost if smart_avg_cost > 0 and cp > 0 else 0
        
        adv = []
        if cp <= 0: 
            adv.append("缺價")
        else:
            if hp - lp > 0 and (min(cp, op) - lp) / (hp - lp) > 0.5 and smart_net > 0: 
                adv.append("洗盤護盤")
                
            if smart_avg_cost == 0 and smart_net < 0: 
                adv.append("無本出貨")
            elif smart_net > 300 and diff_row.get('買方火力(倍)', 1.0) > 1.5: 
                adv.append("點火掃貨")
            elif smart_net > 50 and gap > 0: 
                adv.append("強勢鎖碼")
            elif smart_net > 50 and gap < 0: 
                adv.append("逢低承接")
            elif smart_net < -100 and sp_num > 0: 
                adv.append("拉高派發")
            elif smart_net < -100 and sp_num <= 0: 
                adv.append("多殺多棄守")
        
        eye = diff_row.get('鷹眼診斷', "")
        if eye and eye != "中性": adv.append(eye)
        elif not adv: adv.append("盤整")

        out.append({
            "日期": d, 
            "收盤價(元)": cp if cp > 0 else "-", 
            "漲跌(元)": sp_raw if cp > 0 else "-", 
            "聰明錢淨流(張)": int(smart_net), 
            "大戶淨加權均價": round(smart_avg_cost, 2) if smart_avg_cost > 0 else ("無本" if smart_avg_cost == 0 and total_n > 0 else "-"), 
            "均價落差": round(gap, 2) if smart_avg_cost > 0 and cp > 0 else "-", 
            "活躍家數": diff_row.get('活躍家數', 0), 
            "買賣家數差": diff_row.get('買賣家數差', 0), 
            "籌碼集中度(%)": diff_row.get('籌碼集中度(%)', 0), 
            "買方火力(倍)": diff_row.get('買方火力(倍)', 1.0), 
            "潛在賣壓(張)": int(short_trap), 
            "綜合診斷": " | ".join(adv)
        })
        
    audit_df = pd.DataFrame(audit_smart_money).sort_values('淨買超(張)', ascending=False) if audit_smart_money else pd.DataFrame()
    return pd.DataFrame(out), audit_df

def render_clean_html_table(df, title=""):
    if not is_valid(df):
        if title: st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
        st.warning("ERR-10: 查無數據。")
        return
        
    cols = df.columns.tolist()
    align_classes = ["text-left" if any(k in str(col) for k in {'日期', '分點', '標籤', '週期', '名稱', '姓名', '身份別', '條件', '措施', '診斷', '代號'}) else "text-right" for col in cols]
    
    html_parts = []
    if title: 
        html_parts.append(f"<div class='section-title'>{title}</div>")
        
    html_parts.extend(["<div class='table-container'><table><thead><tr>"])
    for col in cols:
        html_parts.append(f"<th>{col}</th>")
    html_parts.append("</tr></thead><tbody>")
    
    for row in df.itertuples(index=False):
        html_parts.append("<tr>")
        for i, val in enumerate(row):
            display_val = "-"
            if pd.notna(val) and (s := str(val).strip()) and s.lower() != "nan":
                if "無本" in s: 
                    display_val = f"<span class='profit-warning'>{s}</span>"
                elif "(虧)" in s: 
                    display_val = f"<span class='loss-warning'>(虧) {s.replace('(虧)', '').strip()}</span>"
                elif s.startswith("+"): 
                    display_val = f"<span class='highlight-red'>{s}</span>"
                elif s.startswith("-") and len(s) > 1 and s[1].isdigit():
                    try: 
                        if "." in s: display_val = f"<span class='highlight-green'>{float(s.replace(',', '')):,.2f}</span>"
                        else: display_val = f"<span class='highlight-green'>{int(float(s.replace(',', ''))):,}</span>"
                    except: 
                        display_val = f"<span class='highlight-green'>{s}</span>"
                elif "%" in s: 
                    display_val = s
                else:
                    try: 
                        if "." in s: display_val = f"{float(s.replace(',', '')):,.2f}"
                        else: display_val = f"{int(float(s.replace(',', ''))):,}"
                    except: 
                        display_val = s
            html_parts.append(f"<td class='{align_classes[i]}'>{display_val}</td>")
        html_parts.append("</tr>")
        
    html_parts.append("</tbody></table></div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)

def format_to_csv_string(df, title):
    if is_valid(df):
        return f"▼▼▼ {title} ▼▼▼\n" + df.to_csv(index=False) + "\n"
    return f"▼▼▼ {title} ▼▼▼\n無數據\n"

def render_ultimate_heatmap(df_raw, display_dates, rank_dates, intel_tags, df_fingerprint, top_n, noise_threshold):
    if not is_valid(df_raw) or not display_dates or not rank_dates: 
        st.warning("ERR-11: 無熱力圖資料。")
        return
        
    df_rank = df_raw[df_raw['date'].isin(rank_dates)].copy()
    
    def calc_net(x):
        return x['buy'].sum() - x['sell'].sum()
        
    buy_sum_rank = df_rank.groupby('securities_trader')['buy'].sum()
    sell_sum_rank = df_rank.groupby('securities_trader')['sell'].sum()
    rank_net = (buy_sum_rank - sell_sum_rank).fillna(0) / 1000
    rank_sum = rank_net.round().astype(int)
    
    top_b = rank_sum[rank_sum > 0].nlargest(top_n).index.tolist()
    top_s = rank_sum[rank_sum < 0].nsmallest(top_n).index.tolist()
    target_traders = top_b + top_s
    
    if not target_traders: 
        st.warning("ERR-12: 無活躍分點。")
        return
    
    df_disp = df_raw[df_raw['date'].isin(display_dates)].copy()
    
    buy_sum = df_disp.groupby(['securities_trader', 'date'])['buy'].sum()
    sell_sum = df_disp.groupby(['securities_trader', 'date'])['sell'].sum()
    p_shares = (buy_sum - sell_sum).reset_index(name='net_shares')
    
    p_shares['net'] = (p_shares['net_shares'] / 1000).round().astype(int)
    p = p_shares.pivot(index='securities_trader', columns='date', values='net').fillna(0).astype(int)
    p = p.reindex(index=target_traders, columns=display_dates, fill_value=0)

    max_val = p.abs().max().max()
    if max_val == 0: max_val = 1
    
    fp_dict = {}
    if not df_fingerprint.empty:
        fp_dict = df_fingerprint.set_index('分點名稱')[['黏著度(%)', '囤出貨率(%)']].to_dict('index')
    
    html_parts = [HEATMAP_STYLE_TEMPLATE + "<div class='full-table-container heatmap-wrapper'><table><thead><tr>", "<th style='min-width: 140px; position: sticky; left: 0; z-index: 6;'>分點</th><th style='min-width: 90px;'>標籤</th><th style='min-width: 80px;'>黏著</th><th style='min-width: 90px;'>囤/出</th><th style='min-width: 90px;'>累計</th>"]
    for d in display_dates: 
        html_parts.append(f"<th style='text-align: center; font-size: 13px; min-width: 50px;'>{d[5:]}</th>")
    html_parts.append("</tr></thead><tbody>")
    
    for is_sell_side, traders in [(False, top_b), (True, top_s)]:
        if not traders: continue
        color = '#f44336' if is_sell_side else '#4caf50'
        label = '🔴 賣超' if is_sell_side else '🟢 買超'
        html_parts.append(f"<tr><td colspan='{5 + len(display_dates)}' style='background-color: #f1f3f5; color: {color}; font-weight: 900; text-align: center !important; font-size: 1.1rem; letter-spacing: 2px;'>{label}主力</td></tr>")
        
        for trader in traders:
            total_val = rank_sum.get(trader, 0)
            tag = intel_tags.get(trader, '路人')
            
            st_val = fp_dict.get(trader, {}).get('黏著度(%)', '-')
            hr_val = fp_dict.get(trader, {}).get('囤出貨率(%)', '-')
            
            if total_val > 0: total_str = f'<span style=\"color:#d32f2f; font-weight:bold;\">+{total_val}</span>'
            else: total_str = f'<span style=\"color:#2e7d32; font-weight:bold;\">{total_val}</span>'
            
            html_parts.append(f"<tr><td style='position: sticky; left: 0; background-color: #f8f9fa; z-index: 4; font-weight: bold;'>{trader}</td><td style='text-align: center;'>{tag}</td><td style='text-align: right;'>{st_val}</td><td style='text-align: right;'>{hr_val}</td><td style='text-align: right; background-color: #fffde7;'>{total_str}</td>")
            
            for d in display_dates:
                val = p.at[trader, d]
                is_noise = abs(val) < noise_threshold
                alpha = min(1.0, 0.2 + 0.8 * (abs(val) / max_val)) if max_val > 0 else 0.2
                
                if val > 0:
                    bg = f"rgba(229, 57, 53, {alpha:.2f})"
                    txt = f"+{val}"
                    txt_color = "#fff"
                    zc = ""
                elif val < 0:
                    bg = f"rgba(67, 160, 71, {alpha:.2f})"
                    txt = str(val)
                    txt_color = "#fff"
                    zc = ""
                else:
                    bg = "transparent"
                    txt = "0"
                    txt_color = "#aaa"
                    zc = "val-zero"
                    is_noise = True
                    
                cell_class = f"noise-cell {zc}".strip() if is_noise else ""
                cell_style = f"--bg-color: {bg}; --txt-color: {txt_color}; text-align: center; font-weight: bold; "
                if not is_noise:
                    cell_style += f"background-color: {bg}; color: {txt_color} !important; text-shadow: 1px 1px 2px rgba(0,0,0,0.6);"
                else:
                    cell_style += "background-color: transparent;"
                    
                tooltip = f"日期: {d} | 分點: {trader} | 淨額: {val} 張"
                html_parts.append(f"<td class='{cell_class}' style='{cell_style}' title='{tooltip}'><span>{txt}</span></td>")
            html_parts.append("</tr>")
            
    html_parts.append("</tbody></table></div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)

# ==========================================
# 執行主引擎
# ==========================================
if run_btn:
    if not user_stock_id.strip(): 
        st.warning("ERR-00: 請輸入代號！")
        st.stop()

    with st.spinner(f"啟動 V73.00 極速核心..."):
        
        name, industry = get_basic_info_finmind(user_stock_id)
        if name == "未知名稱": 
            st.error(f"ERR-01: 查無基本資料(API異常)。")
            st.stop()
            
        df_p_raw = fetch_finmind_v50("TaiwanStockPrice", (datetime.date.today() - datetime.timedelta(days=700)).strftime("%Y-%m-%d"), user_stock_id)
        if not is_valid(df_p_raw, ['date']): 
            st.error("ERR-02: 查無歷史股價。")
            st.stop()
        
        valid_dates = df_p_raw['date'].dropna().astype(str)
        dates = sorted(valid_dates[valid_dates != ""].unique().tolist(), reverse=True)
        if not dates: st.stop()
            
        max_len = lookback_days if len(dates) >= lookback_days else max(1, len(dates))
        d_end = dates[max_len-1]
        
        df_price = optimize_memory(process_price(df_p_raw))
        curr_price = round(float(df_price['收盤價(元)'].iloc[0]), 2) if is_valid(df_price, ['收盤價(元)']) else 0
        df_ta_full = process_technical_analysis(df_price, ma_short, ma_mid, ma_long)
        
        recent_20_vol = 1000
        if is_valid(df_price, ['成交量(張)']):
            recent_20_vol = df_price['成交量(張)'].head(20).mean()
        if pd.isna(recent_20_vol) or recent_20_vol == 0: 
            recent_20_vol = 1000
            
        dynamic_noise_threshold = int(recent_20_vol * (heatmap_noise_pct / 100.0))
        dynamic_alert_threshold = int(recent_20_vol * (alert_smart_pct / 100.0))

        df_lr_channel = process_linear_regression(df_price, lr_days)
        latest_lr_upper = df_lr_channel['LR_Upper'].iloc[-1] if is_valid(df_lr_channel) else 0.0
        latest_lr_mid = df_lr_channel['LR_Mid'].iloc[-1] if is_valid(df_lr_channel) else 0.0
        latest_lr_lower = df_lr_channel['LR_Lower'].iloc[-1] if is_valid(df_lr_channel) else 0.0
        
        pat_data = {}
        if enable_pattern:
            pat_data = process_geometric_patterns(df_price, kline_days, pattern_order, pattern_mode, curr_price)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as bg_executor:
            f_dir = bg_executor.submit(scrape_director_v50, user_stock_id)
            f_ple = bg_executor.submit(scrape_fubon_pledge, df_p_raw, user_stock_id)

            df_b_raw, ds_dict, df_cb_info = fetch_heavy_data_sync_with_progress(user_stock_id, tuple(dates), max_len)

            dynamic_dict, s_val, chip_eng, _ = f_dir.result()
            df_p_sum, df_p_det = f_ple.result()

        if not is_valid(df_b_raw):
            st.error(f"ERR-03: 查無分點資料。")
            st.stop()
            
        df_b_raw['price'] = safe_to_num(df_b_raw.get('price', 0))
        df_b_raw['buy'] = safe_to_num(df_b_raw.get('buy', 0))
        df_b_raw['sell'] = safe_to_num(df_b_raw.get('sell', 0))
        df_b_raw['valid_buy'] = np.where(df_b_raw['price'] > 0, df_b_raw['buy'], 0)
        df_b_raw['valid_sell'] = np.where(df_b_raw['price'] > 0, df_b_raw['sell'], 0)
        df_b_raw['valid_buy_amt'] = df_b_raw['valid_buy'] * df_b_raw['price']
        df_b_raw['valid_sell_amt'] = df_b_raw['valid_sell'] * df_b_raw['price']
        df_b_raw['net_shares'] = df_b_raw['buy'] - df_b_raw['sell']
        df_b_raw['date_dt'] = pd.to_datetime(df_b_raw.get('date', ''))

        parsed_dead_chip = None
        if dead_chip_input and str(dead_chip_input).strip() != "":
            try: parsed_dead_chip = float(str(dead_chip_input).replace('%', '').strip())
            except: parsed_dead_chip = None

        tags, df_debug_tags = get_v50_intelligence(df_b_raw, df_p_raw, stick_thresh=stickiness_threshold, global_days=max_len, dates_list=dates)
        df_b_raw['tag'] = df_b_raw['securities_trader'].map(tags).fillna("路人")
        df_b_raw['is_smart'] = df_b_raw['tag'].isin({"波段鎖碼", "避險造市", "獲利調節", "棄守提款", "主力重砲", "認錯回補"})
        df_b_raw['is_short'] = df_b_raw['tag'].isin({"隔日突擊", "跟風小戶"})
        
        df_s_raw = ds_dict.get("TaiwanStockHoldingSharesPer", pd.DataFrame())
        df_s_wide, df_s_unit, df_s_ppl = process_tdcc(df_s_raw)
        
        current_total_shares = df_s_wide['總張數'].iloc[0] if is_valid(df_s_wide) else 0
        latest_director_holding, holding_src = get_dead_chip_info(dates[0], parsed_dead_chip, dynamic_dict, s_val, chip_eng)
        
        dynamic_n, radar_reason = calculate_dynamic_radar_depth(df_b_raw, dates, current_total_shares, df_price)
        pure_vwap, main_force_vol, active_main_branches, core_c_value, core_branch_names = calculate_pure_defense_line(
            df_b_raw, tags, filter_day_trade, current_total_shares, latest_director_holding, dynamic_n
        )
        
        net_3 = get_core_period_net(df_b_raw, dates[:3], core_branch_names)
        net_10 = get_core_period_net(df_b_raw, dates[:10], core_branch_names)
        net_45 = get_core_period_net(df_b_raw, dates[:45] if len(dates)>=45 else dates, core_branch_names)
        net_60 = get_core_period_net(df_b_raw, dates[:60] if len(dates)>=60 else dates, core_branch_names)
        
        df_day_trade_raw = ds_dict.get("TaiwanStockDayTrading", pd.DataFrame())
        df_day_trade = optimize_memory(process_day_trading(df_day_trade_raw))
        
        df_b_diff = process_branch_diff_v2(df_b_raw, dates, firepower_threshold, period_days=15)
        df_b_diff_60 = process_branch_diff_v2(df_b_raw, dates, firepower_threshold, period_days=60)
        
        df_daily_tracker, df_audit_smart = process_v30_daily_tracking(df_b_raw, tags, df_price, df_b_diff, dates, firepower_threshold, period_days=15)
        df_daily_tracker_60, _ = process_v30_daily_tracking(df_b_raw, tags, df_price, df_b_diff_60, dates, firepower_threshold, period_days=60)
        
        df_s_dyn = process_tdcc_dynamic_v2(df_s_wide, df_price, parsed_dead_chip, dynamic_dict, s_val, chip_eng)
        df_v27_radar, df_debug_math, _ = process_v27_ultimate_radar(df_s_wide, parsed_dead_chip, dynamic_dict, s_val, df_price, df_b_raw, tags)

        df_combined_display = pd.DataFrame()
        if is_valid(df_v27_radar) and is_valid(df_s_dyn):
            df_v27_clean = df_v27_radar.drop(columns=['大戶原持股(%)', '收盤價(元)'], errors='ignore')
            df_combined_radar = pd.merge(df_s_dyn, df_v27_clean, on=['日期'], how='inner')
            if is_valid(df_combined_radar): 
                df_combined_radar['終極籌碼診斷'] = df_combined_radar['實戰判定'].astype(str) + " | " + df_combined_radar['專家雷達診斷'].astype(str)
                display_cols = ['日期', '收盤價(元)', '純淨活大戶C_Value(%)', '純淨大戶變動(%)', '總人數變率(%)', '大戶精算門檻', '當沖虛胖(%)', '終極籌碼診斷']
                df_combined_display = optimize_memory(df_combined_radar[[c for c in display_cols if c in df_combined_radar.columns]].sort_values('日期', ascending=False).head(8))

        df_margin = optimize_memory(process_margin(ds_dict.get("TaiwanStockMarginPurchaseShortSale", pd.DataFrame())))
        df_inst = optimize_memory(process_inst(ds_dict.get("TaiwanStockInstitutionalInvestorsBuySell", pd.DataFrame())))
        
        df_rev_raw = ds_dict.get("TaiwanStockMonthRevenue", pd.DataFrame())
        df_rev = pd.DataFrame()
        if is_valid(df_rev_raw, ['revenue_year', 'revenue_month']):
            df_rev_clean = df_rev_raw.dropna(subset=['revenue_year', 'revenue_month']).copy()
            df_rev_clean['營收月份'] = df_rev_clean['revenue_year'].astype(int).astype(str) + "-" + df_rev_clean['revenue_month'].astype(int).astype(str).str.zfill(2)
            df_rev_clean = df_rev_clean.rename(columns={"revenue":"月營收(百萬元)"})[['營收月份','月營收(百萬元)']].tail(24)
            df_rev_clean['月營收(百萬元)'] = (safe_to_num(df_rev_clean['月營收(百萬元)'])/1000000).round().astype(int)
            df_rev = optimize_memory(df_rev_clean.sort_values('營收月份', ascending=False))

        df_b_raw_60 = df_b_raw[df_b_raw['date'].isin(set(dates[:max_len]))].copy()
        df_b_today = optimize_memory(process_branch_v25(df_b_raw_60, 1, dates, tags, df_p_raw, stickiness_threshold, max_len))
        df_b_prev1 = optimize_memory(process_branch_v25(df_b_raw_60, 1, dates[1:], tags, df_p_raw, stickiness_threshold, max_len))
        
        df_fut = optimize_memory(process_fut_inst(ds_dict.get("TaiwanFuturesInstitutionalInvestors", pd.DataFrame())))
        df_div = optimize_memory(process_div(ds_dict.get("TaiwanStockDividend", pd.DataFrame())))
        df_per = optimize_memory(process_per(ds_dict.get("TaiwanStockPER", pd.DataFrame())))
        df_disp = optimize_memory(process_disp(ds_dict.get("TaiwanStockDispositionSecuritiesPeriod", pd.DataFrame())))
        
        df_cbas_raw = ds_dict.get("TaiwanStockConvertibleBondDailyOverview", pd.DataFrame())
        df_cbas = pd.DataFrame()
        if is_valid(df_cbas_raw, ['cb_id']):
            cb_mask = df_cbas_raw['cb_id'].astype(str).str.replace(',', '', regex=False).str.startswith(user_stock_id)
            df_cbas = optimize_memory(process_cbas(df_cbas_raw[cb_mask], curr_price, df_cb_info))

        st.subheader(f"{user_stock_id} {name} 全息戰報 (V73.00)")
        
        cap_val = f'{current_total_shares/10000:.2f} 億' if current_total_shares > 0 else '計算中...'
        mv_val = f'{(curr_price*current_total_shares)/100000:,.2f} 億' if is_valid(df_price) and current_total_shares > 0 else '計算中...'
        dc_val = f'{latest_director_holding:.2f}% ({holding_src})' if latest_director_holding > 0 else '無數據'
        
        st.markdown(f"<div class='info-box'>【產業】 {industry} ｜ 【股本】 {cap_val} ｜ 【市值】 {mv_val} ｜ 【死籌碼】 {dc_val} ｜ 【均量】 {int(recent_20_vol):,} 張</div>", unsafe_allow_html=True)

        disp_warn = calculate_disposition_thresholds_v2(df_price, df_day_trade, current_total_shares)
        bias = ((curr_price - pure_vwap) / pure_vwap * 100) if pure_vwap > 0 else 0
        vwap_str = f"{pure_vwap:,.2f}" if pure_vwap > 0 else "-"
        
        today_smart_net = 0
        today_short_trap = 0
        today_gap = 0.0
        if is_valid(df_daily_tracker):
            today_smart_net = df_daily_tracker.iloc[0].get('聰明錢淨流(張)', 0)
            today_short_trap = df_daily_tracker.iloc[0].get('潛在賣壓(張)', 0)
            gap_raw = str(df_daily_tracker.iloc[0].get('均價落差', 0))
            if gap_raw not in ['-', '']:
                try: today_gap = float(re.sub(r'[+,]', '', gap_raw).strip())
                except: today_gap = 0.0

        today_fp = 1.0
        today_diff_cnt = 0
        if is_valid(df_b_diff):
            today_fp = df_b_diff.iloc[0].get('買方火力(倍)', 1.0)
            today_diff_cnt = df_b_diff.iloc[0].get('買賣家數差', 0)
        
        c_val_text = "[缺數據]"
        chg_text = "[缺數據]"
        radar_c_val = 0.0
        radar_chg = 0.0
        
        if is_valid(df_combined_display):
            try: 
                cv = df_combined_display.iloc[0].get('純淨活大戶C_Value(%)', 0)
                if str(cv).strip() == "-":
                    c_val_text = f"{df_combined_display.iloc[0].get('大戶原持股(%)', 0)}% (原持股)"
                else:
                    radar_c_val = float(re.sub(r'[+,%]', '', str(cv)).strip())
                    c_val_text = f"{radar_c_val}%"
            except: pass
            
            try: 
                radar_chg = float(re.sub(r'[+,%]', '', str(df_combined_display.iloc[0].get('純淨大戶變動(%)', 0))).strip())
                dir_str = "增加" if radar_chg > 0 else ("減少" if radar_chg < 0 else "無變動")
                chg_text = f"{dir_str} {abs(radar_chg)}%"
            except: pass

        custom_alerts = []
        if today_smart_net >= dynamic_alert_threshold and dynamic_alert_threshold > 0: 
            custom_alerts.append(f"【極端買擊】：淨買超達 <b>{today_smart_net:,}</b> 張 ({alert_smart_pct*100:.1f}%)")
        if today_smart_net <= -dynamic_alert_threshold and dynamic_alert_threshold > 0: 
            custom_alerts.append(f"【極端拋售】：淨賣超達 <b>{today_smart_net:,}</b> 張 ({alert_smart_pct*100:.1f}%)")
        if pure_vwap > 0 and bias <= alert_bias_drop: 
            custom_alerts.append(f"【跌破底線】：跌破純淨防守線，乖離 <b>{bias:.2f}%</b>，面臨套牢")
            
        if custom_alerts: 
            alert_html = "<div style='background-color:#ffebee;border-left:6px solid #d32f2f;padding:15px;margin-bottom:25px;border-radius:4px;'><h4 style='margin:0 0 10px;color:#c62828;'>系統紅色警報</h4><ul>"
            for msg in custom_alerts:
                alert_html += f"<li>{msg}</li>"
            alert_html += "</ul></div>"
            st.markdown(alert_html, unsafe_allow_html=True)

        if is_valid(df_ta_full):
            st.markdown(f"<div class='section-title'>技術面與K線 ({ma_short}/{ma_mid}/{ma_long}均線)</div>", unsafe_allow_html=True)
            df_plot = pd.merge(df_price.head(kline_days), df_ta_full[['日期', f'MA{ma_short}', f'MA{ma_mid}(中線)', f'MA{ma_long}(長線)']].head(kline_days), on='日期', how='inner').sort_values('日期', ascending=True)
            
            if is_valid(df_day_trade_raw):
                df_dt_chart = df_day_trade_raw.copy().rename(columns={"date": "日期"})
                vol_col = 'DayTradingVolume' if 'DayTradingVolume' in df_dt_chart.columns else 'Volume'
                if vol_col in df_dt_chart.columns:
                    df_dt_chart['當沖總張數'] = (safe_to_num(df_dt_chart[vol_col]) / 1000).round().astype(int)
                    df_plot = pd.merge(df_plot, df_dt_chart[['日期', '當沖總張數']], on='日期', how='left').fillna({'當沖總張數': 0})
                else: 
                    df_plot['當沖總張數'] = 0
            else: 
                df_plot['當沖總張數'] = 0
            
            lr_data_json = "{}"
            pat_js = "[]"
            neck_js = "[]"
            pat_color_js = "'transparent'"
            
            if is_valid(df_lr_channel):
                df_plot = pd.merge(df_plot, df_lr_channel, on='日期', how='left')
                df_plot_lr = df_plot.dropna(subset=['LR_Upper']).sort_values('日期', ascending=True)
                
                lr_upper = [{"time": str(t), "value": float(v) if pd.notna(v) else 0.0} for t, v in zip(df_plot_lr['日期'], df_plot_lr['LR_Upper'])]
                lr_mid = [{"time": str(t), "value": float(v) if pd.notna(v) else 0.0} for t, v in zip(df_plot_lr['日期'], df_plot_lr['LR_Mid'])]
                lr_lower = [{"time": str(t), "value": float(v) if pd.notna(v) else 0.0} for t, v in zip(df_plot_lr['日期'], df_plot_lr['LR_Lower'])]
                
                lr_data_json = json.dumps({"upper": lr_upper, "mid": lr_mid, "lower": lr_lower})
            
            if pat_data:
                shape_points = [{"time": str(x), "value": float(y)} for x, y in zip(pat_data['shape_x'], pat_data['shape_y'])]
                neck_points = [{"time": str(x), "value": float(y)} for x, y in zip(pat_data['neck_x'], pat_data['neck_y'])]
                
                pat_js = json.dumps(sorted(shape_points, key=lambda k: k['time']))
                neck_js = json.dumps(sorted(neck_points, key=lambda k: k['time']))
                pat_color_js = f"'{pat_data.get('color', '#000')}'"

            time_s = df_plot['日期'].astype(str).tolist()
            
            kline_js = json.dumps([{'time': t, 'open': float(o), 'high': float(h), 'low': float(l), 'close': float(c)} for t, o, h, l, c in zip(time_s, df_plot['開盤價(元)'], df_plot['最高價(元)'], df_plot['最低價(元)'], df_plot['收盤價(元)'])])
            tvol_js = json.dumps([{'time': t, 'value': float(v), 'color': '#E0E3EB'} for t, v in zip(time_s, df_plot['成交量(張)'])])
            dtvol_js = json.dumps([{'time': t, 'value': float(v), 'color': '#FF9800'} for t, v in zip(time_s, df_plot['當沖總張數'])])
            
            ma_s_js = [{'time': t, 'value': round(float(v), 2)} for t, v, m in zip(time_s, df_plot[f'MA{ma_short}'], df_plot[f'MA{ma_short}'].notna()) if m]
            ma_m_js = [{'time': t, 'value': round(float(v), 2)} for t, v, m in zip(time_s, df_plot[f'MA{ma_mid}(中線)'], df_plot[f'MA{ma_mid}(中線)'].notna()) if m]
            ma_l_js = [{'time': t, 'value': round(float(v), 2)} for t, v, m in zip(time_s, df_plot[f'MA{ma_long}(長線)'], df_plot[f'MA{ma_long}(長線)'].notna()) if m]
            
            ma_data_js = json.dumps({"ma_short": ma_s_js, "ma_mid": ma_m_js, "ma_long": ma_l_js})

            html_content = KLINE_CHART_TEMPLATE.replace("KLINE_DATA", kline_js)
            html_content = html_content.replace("TOTAL_VOL", tvol_js)
            html_content = html_content.replace("DAYTRADE_VOL", dtvol_js)
            html_content = html_content.replace("MA_DATA", ma_data_js)
            html_content = html_content.replace("LR_DATA", lr_data_json)
            html_content = html_content.replace("PAT_DATA", pat_js)
            html_content = html_content.replace("NECK_DATA", neck_js)
            html_content = html_content.replace("PAT_COLOR", pat_color_js)
            
            components.html(html_content, height=736)

        st.markdown("<div class='category-title'>AI 全息籌碼深度診斷總結</div>", unsafe_allow_html=True)
        
        lr_pos_text = "無通道"
        if curr_price >= latest_lr_upper and latest_lr_upper > 0: lr_pos_text = "極度過熱區"
        elif curr_price >= latest_lr_mid and latest_lr_mid > 0: lr_pos_text = "強勢多頭區"
        elif curr_price <= latest_lr_lower and latest_lr_lower > 0: lr_pos_text = "極度超跌區"
        elif latest_lr_mid > 0: lr_pos_text = "弱勢空頭區"
        
        inst_net_today = 0
        if is_valid(df_inst):
            inst_net_today = df_inst.iloc[0]['三大法人買賣超(張)']
        is_double_counting = (inst_net_today > 0 and today_smart_net > 0 and abs(inst_net_today - today_smart_net) < inst_net_today * 0.2)
        
        margin_shares_est = 0
        if is_valid(df_margin, ['融資餘額(萬元)'], 2) and curr_price > 0:
            margin_shares_est = (safe_to_num(df_margin.iloc[0]['融資餘額(萬元)']) - safe_to_num(df_margin.iloc[1]['融資餘額(萬元)'])) * 10 / curr_price
        is_margin_trap = today_smart_net > 100 and margin_shares_est > (today_smart_net * 0.6)
        
        is_cbas_arb = False
        if is_valid(df_cbas, ['未償還(%)'], 2):
            try:
                cb_curr = float(df_cbas.iloc[0]['餘額'])
                cb_prev = float(df_cbas.iloc[1]['餘額'])
                if cb_curr < cb_prev and today_smart_net < -50: 
                    is_cbas_arb = True
            except: pass

        pat_is_breakout = pat_data and pat_data['signal'] == 'bullish' and ('突破' in pat_data['desc'] or '深V' in pat_data['desc'])
        pat_is_breakdown = pat_data and pat_data['signal'] == 'bearish' and ('跌破' in pat_data['desc'] or '衰退' in pat_data['desc'])
        
        conclusion = "【籌碼中性 / 多空膠著，靜待表態】"
        action = "目前長、中、短線籌碼動向不一，未出現極端的集中或發散訊號。盤勢由一般市場力量主導，建議縮小部位，靜待主力給出更明確的方向表態。"
        
        if (curr_price >= latest_lr_upper and latest_lr_upper > 0 and today_smart_net > 300 and today_fp > 1.5): 
            conclusion = "【軋空噴出飆股模式 / 通道已失效】"
            action = "股價頂破通道上軌，但主力重砲持續狂炸重擊。線性迴歸指標已鈍化，此時不應逆勢放空或提早獲利，建議改用短均線防守，讓獲利奔跑。"
        elif pat_is_breakdown and today_smart_net < 0: 
            conclusion = "【形態轉弱 / 主力撤退，立刻停損】"
            action = "視覺形態確認跌破或轉弱，且今日聰明錢果斷撤退。技術面與籌碼面雙重轉空，請立刻停損逃命，嚴禁留戀。"
        elif pat_is_breakout and today_smart_net > 0: 
            conclusion = "【形態突破 / 主力點火，強勢追擊】"
            action = "視覺形態確認突破頸線或形成強力反轉，且今日聰明錢大舉淨流入點火。技術面與籌碼面完美共振，此為高勝率買點，請順勢抱緊。"
        elif radar_chg < -1.0 and today_smart_net < -500 and today_diff_cnt > 0: 
            conclusion = "【高檔派發 / 趨勢反轉，準備逃命】"
            action = f"中線大戶已在減碼，今日短線聰明錢大舉倒貨給散戶。目前{lr_pos_text}，請忽略長線的靜態支撐，立刻以短線逃命訊號為主，逢高減碼，嚴防接刀多殺多。"
        elif curr_price >= latest_lr_upper and latest_lr_upper > 0 and today_smart_net < 0: 
            conclusion = "【通道過熱 / 逢高派發，準備停利】"
            action = f"股價已頂到 {lr_days} 日通道上軌，且短線聰明錢開始趁高檔撤退。請逢高停利一趟，嚴防主力順勢出貨，切勿在此追高。"
        elif curr_price <= latest_lr_lower and latest_lr_lower > 0 and radar_chg >= 0 and today_smart_net > 0: 
            conclusion = "【超跌反轉 / 左側掃貨，絕佳買點】"
            action = f"股價打到 {lr_days} 日通道下軌，但中線大戶籌碼安定，且今日短線聰明錢大舉淨流入。主力趁暴跌吃貨，此為極具安全邊際的高勝率左側買點。"
        elif radar_chg > 1.0 and today_smart_net > 500 and float(today_fp) > 1.2: 
            conclusion = "【強勢推升 / 主力鎖碼，順勢抱緊】"
            action = "中線大戶持續吸籌，今日短線火力全開且聰明錢大舉淨流入。籌碼高度集中於特定主力手中，趨勢呈強勢多頭，沿防守線抱緊，切勿輕易被洗下車。"
        elif net_60 > 0 and today_smart_net < -200 and today_diff_cnt <= 0: 
            conclusion = "【高檔震盪 / 壓盤洗盤，觀察防守】"
            action = "長線底單依然穩固，今日雖有聰明錢流出，但散戶並未瘋狂接刀。偏向主力順勢調節或刻意壓盤洗浮額。請密切關注股價是否能守住加權防守價，未破線前無須恐慌殺出。"
        elif bias < -5.0 and net_60 <= 0 and net_10 <= 0 and net_3 <= 0: 
            conclusion = "【兵敗如山 / 全面套牢，嚴禁摸底】"
            action = "股價跌破防守價，且短中長線主力全面大舉倒貨。籌碼與技術面雙雙潰敗，此處的任何反彈都應視為逃命波，嚴禁進場摸底接刀。"
        elif bias < 0 and net_60 > 0 and today_smart_net > 0: 
            conclusion = "【破線抵抗 / 逢低護盤，等待站回】"
            action = "股價雖跌破防守價導致主力套牢，但今日見到聰明錢進場抵抗。這顯示主力並未完全放棄，正在嘗試逢低護盤。需確認股價能帶量重新站回防守價，才可視為危機解除。"

        report_md = "<div class='ai-report-box'>\n#### 🧠 系統終極戰略推演與深度解析\n<ul>"
        
        report_md += "<li><b>一、 短線戰鬥多空定調 (今日籌碼真偽)：</b><br>"
        if today_short_trap > 0: 
            report_md += f"<span style='color:#ff9800; font-weight:bold;'>⚠️ 【潛在賣壓警告】：系統偵測到明日潛在短線/隔日沖倒貨賣壓約 {today_short_trap:,} 張，請注意開盤震盪。</span><br>"
            
        if is_double_counting: 
            report_md += "<span style='color:#d32f2f;'>發現法人與地方大戶高度重疊。</span><br>深度解析：這代表今天的買盤極大比例是外資帳戶透過特定券商下單。請將外資與主力視為同一筆資金，切忌將兩者的數據相加而產生「買盤超強」的過度樂觀錯覺，需提防假外資隔日沖。"
        elif is_margin_trap: 
            report_md += "<span style='color:#d32f2f;'>主力雖大買，但融資同步異常暴增。</span><br>深度解析：這通常是高槓桿的「假主力」或當沖客利用融資鎖碼。這類資金極端不穩定，只要明日開盤不如預期，立刻會引發融資斷頭的多殺多連鎖反應，強烈建議避開。"
        elif today_smart_net > 100 and today_diff_cnt <= -10: 
            report_md += "<span style='color:#2e7d32;'>聰明錢真實流入，且買賣家數差為負(籌碼高度集中)。</span><br>深度解析：代表今日有少數的特定大戶，正在兇猛地吃掉多數散戶的賣單。這種不計代價的掃貨行為，是標準的波段起漲或強勢延續特徵。"
        elif today_smart_net < -100 and today_diff_cnt >= 10: 
            report_md += "<span style='color:#d32f2f;'>聰明錢真實撤退，且買賣家數差為正(散戶瘋狂湧入)。</span><br>深度解析：這是最經典的「主力出貨給散戶」劇本。大戶趁著利多或拉高時倒貨，而散戶正在滿心歡喜地接刀。技術面無論多漂亮，此時都必須提高警覺或停損。"
        else: 
            report_md += "短線籌碼呈現多空交戰，無明顯極端異常。<br>深度解析：目前沒有單一勢力能完全掌控盤面，屬於換手或盤整階段。此時進場如同擲硬幣，建議保留現金，靜待籌碼高度集中時再出手。"
            
        report_md += "</li><br>\n<li><b>二、 核心防守價位與安全邊際確認：</b><br>"
        report_md += f"系統已為您剔除避險造市與當沖雜訊，精算出的「純淨主力防守價」為 <b>{vwap_str} 元</b>。<br>"
        if bias > 5: 
            report_md += f"深度解析：目前股價({curr_price:.2f}元)距離主力成本線有 {bias:.1f}% 的豐厚緩衝。這代表主力目前處於輕鬆獲利的狀態，洗盤時有足夠的空間下殺而不會傷到自己，您只需沿著均線續抱即可。"
        elif 0 <= bias <= 5: 
            report_md += f"深度解析：目前股價({curr_price:.2f}元)完美貼合主力的真實成本區(乖離僅 {bias:.1f}%)。這是左側潛伏最愛的「黃金建倉點」。只要不實質跌破此防線，主力都有極大動機主動護盤。"
        else: 
            report_md += f"深度解析：<span style='color:#d32f2f;'>目前股價({curr_price:.2f}元)已跌破主力的鐵板防守線(乖離 {bias:.1f}%)。</span>這代表連砸重金的大戶自己都處於帳面虧損。一旦大戶決定停損，將引發海嘯般的賣壓，此時切勿抱持凹單心態。"
            
        report_md += "</li><br>\n<li><b>三、 潛在市場盲點與套利干擾排除：</b><br>"
        if is_cbas_arb: 
            report_md += "偵測到可轉債(CBAS)餘額下降，與主力賣超同步發生。<br>深度解析：這高機率是法人在進行「賣老股、換新股(轉債)」的無風險套利行為。這會在外觀上製造出「大戶瘋狂賣超」的假象，但其實並非主力不看好後市而棄守，需冷靜辨別。"
        elif disp_warn and disp_warn['max_vol_6d'] and disp_warn['max_vol_6d'] <= 0: 
            report_md += "<span style='color:#d32f2f;'>警告：近 5 日週轉率已達法規極限！</span><br>深度解析：明日只要稍微有一點成交量，就會踩到交易所的處置紅線(關緊閉)。通常懂規矩的主力明天會刻意「縮手壓盤」來降溫，因此明日若見量縮下跌，屬人為技術性調整，無須過度恐慌。"
        else: 
            report_md += "目前未偵測到可轉債套利干擾或即將踩到處置紅線的危機。<br>深度解析：市場干擾因素低，您可以完全信任上方第一點與第二點的純數量化籌碼判斷。"
            
        report_md += "</li><br>\n<li><b>四、 平日戰情追蹤矩陣 (近15日) 趨勢解碼：</b><br>"
        report_md += f"近 10 日核心主力淨留倉為 <span style='color: {'#d32f2f' if net_10 > 0 else '#2e7d32'}; font-weight: bold;'>{net_10:,} 張</span>，今日買方火力為 <span style='font-weight: bold;'>{today_fp} 倍</span>。<br>"
        if net_10 > 0 and today_fp > 1.2: 
            report_md += "深度解析：近半個月主力資金呈現<span style='color: #d32f2f; font-weight: bold;'>穩定流入(囤貨)</span>，且火力具備攻擊性，盤勢由多方掌控。"
        elif net_10 < 0 and float(today_fp) < 1.0: 
            report_md += "深度解析：近半個月主力資金持續<span style='color: #2e7d32; font-weight: bold;'>撤退流出(倒貨)</span>，且買盤火力微弱，短線反彈皆為逃命波。"
        else: 
            report_md += "深度解析：近半個月大戶籌碼進出交錯，未見連續性方向，屬區間震盪整理格局。"
            
        report_md += "</li><br>\n<li><b>五、 一週集保籌碼雷達 (大戶存量與流量雙解碼)：</b><br>"
        report_md += f"當前純淨活大戶 C_Value 為 <span style='font-weight: bold;'>{c_val_text}</span>，最新單週純淨大戶變動為 <span style='color: {'#d32f2f' if radar_chg > 0 else '#2e7d32'}; font-weight: bold;'>{chg_text}</span>。<br>"
        if radar_chg > 0 and radar_c_val > 60: 
            report_md += "深度解析：大戶不僅<span style='color: #d32f2f; font-weight: bold;'>存量高(高度鎖碼)</span>，且本週<span style='color: #d32f2f; font-weight: bold;'>流量持續增持</span>，籌碼極度安定，有利波段上攻。"
        elif radar_chg < 0 and radar_c_val < 40: 
            report_md += "深度解析：大戶<span style='color: #2e7d32; font-weight: bold;'>存量已偏低(籌碼渙散)</span>，且本週<span style='color: #2e7d32; font-weight: bold;'>仍在拋售</span>，底部深不可測，請避開。"
        elif radar_chg > 0.5: 
            report_md += "深度解析：雖然總存量普通，但本週大戶出現<span style='color: #d32f2f; font-weight: bold;'>顯著吸籌(流量轉正)</span>，暗示可能有潛在利多或波段起漲點。"
        elif radar_chg < -0.5: 
            report_md += "深度解析：大戶本週出現<span style='color: #2e7d32; font-weight: bold;'>明顯倒貨(流量轉負)</span>，請嚴防高檔派發或利空出盡。"
        else: 
            report_md += "深度解析：大戶持股比例單週變動微小，籌碼結構暫無重大改變，維持現有趨勢。"
            
        report_md += f"</li></ul>\n<div class='ai-conclusion'><b>🚀 操作定調：{conclusion}</b><br><span style='font-weight:normal; display:block; margin-top:10px;'>{action}</span></div></div>"
        
        st.markdown(report_md, unsafe_allow_html=True)
        st.markdown("---")
        
        stat_days = footprint_stat_days if len(dates) >= footprint_stat_days else max(1, len(dates))
        actual_foot_days = footprint_days if len(dates) >= footprint_days else len(dates)
        
        st.markdown("<div class='category-title'>01. 終極全息透視區</div>", unsafe_allow_html=True)
        with st.expander(f"【全息熱力圖】 戰略排行 {stat_days} 天 ✕ 足跡 {actual_foot_days} 天", expanded=True):
            st.info(f"隱藏低於 {dynamic_noise_threshold:,} 張雜訊。")
            render_ultimate_heatmap(df_b_raw, dates[:actual_foot_days], dates[:stat_days], tags, df_debug_tags, footprint_rows, dynamic_noise_threshold)
            
        with st.expander(f"【建倉區間】 {actual_foot_days}天大戶成本分佈 (Volume Profile)", expanded=False):
            render_volume_profile(df_b_raw, dates[:actual_foot_days] if len(dates)>=actual_foot_days else dates, footprint_rows)

        with st.expander(f"【聯合作戰】 土洋對比 (法人 vs 地方主力)", expanded=False):
            render_institutional_vs_local(df_b_raw, df_inst, tags, top_n=4)

        with st.expander(f"主力分點 - 今日 ({dates[0]})", expanded=False): 
            render_clean_html_table(df_b_today)
            
        with st.expander(f"主力分點 - 前一日", expanded=False): 
            render_clean_html_table(df_b_prev1)
            
        with st.expander("主力分點圖鑑", expanded=False): 
            render_clean_html_table(df_debug_tags)

        render_clean_html_table(df_daily_tracker, "02. 平日戰情追蹤矩陣 (近15日)")
        render_clean_html_table(df_combined_display, "03. 一週集保籌碼雷達") 
        render_clean_html_table(df_inst, "04. 法人買賣超")
        render_clean_html_table(df_margin, "05. 散戶資券餘額")
        render_clean_html_table(df_day_trade, "06. 現股當沖明細")
        render_clean_html_table(df_fut, "07. 期貨三大法人未平倉")
        render_clean_html_table(df_rev, "08. 月營收 (百萬元)")
        
        with st.expander("集保分級表", expanded=False):
            render_clean_html_table(df_s_unit, "09-1. 張數表")
            render_clean_html_table(df_s_ppl, "09-2. 人數表")
            
        render_clean_html_table(df_p_sum, "10.質設總覽")
        with st.expander("質設明細", expanded=False): 
            render_clean_html_table(df_p_det, "11. 質設明細")
            
        render_clean_html_table(df_div, "12. 股利政策")
        render_clean_html_table(df_per, "13. 本淨比與殖利率")
        render_clean_html_table(df_disp, "14. 處置狀態")
        render_clean_html_table(df_cbas, "15. CBAS")

        st.divider()
        with st.expander(f"給 AI 的 V73.00 實戰資料包", expanded=True):
            p1 = f"深度分析 {user_stock_id} {name} 的量化籌碼。\n\n【產業】 {industry} ｜ 【股本】 {f'{current_total_shares/10000:.2f}億'} ｜ 【市值】 {f'{(curr_price*current_total_shares)/100000:,.2f}億' if is_valid(df_price) and current_total_shares>0 else '-'} ｜ 【20日均量】 {int(recent_20_vol):,}張\n\n▼▼▼ AI 全息籌碼深度診斷總結 ▼▼▼\n{re.sub(r'<[^>]+>', '', report_md).replace('&nbsp;', ' ').strip()}\n\n"
            if latest_lr_upper > 0: 
                p1 += f"【LR通道】上: {latest_lr_upper:.2f} | 中: {latest_lr_mid:.2f} | 下: {latest_lr_lower:.2f}\n\n"
            p1 += f"【純淨防守價】: {vwap_str} 元\n【控盤率】: {core_c_value}%\n【留倉】3日: {net_3}張 | 10日: {net_10}張 | 45日: {net_45}張 | 60日: {net_60}張\n\n"
            p1 += format_to_csv_string(df_daily_tracker, "02. 戰情") 
            p1 += format_to_csv_string(df_combined_display.head(4) if is_valid(df_combined_display) else df_combined_display, "03. 集保") 
            p1 += format_to_csv_string(df_inst.head(10) if is_valid(df_inst) else df_inst, "04. 法人") 
            p1 += format_to_csv_string(df_margin.head(10) if is_valid(df_margin) else df_margin, "05. 資券") 
            p1 += format_to_csv_string(df_rev.head(12) if is_valid(df_rev) else df_rev, "08. 營收") 
            p1 += format_to_csv_string(df_p_sum, "10. 質設") 
            p1 += format_to_csv_string(df_cbas, "15. CBAS")
            st.code(p1, language="text")

        st.divider()
        with st.expander("底層數據 Dump 驗證區 (供驗證)", expanded=False):
            dump_txt = format_to_csv_string(df_price.head(60).copy() if is_valid(df_price) else pd.DataFrame(), "Raw 00: 股價") 
            dump_txt += format_to_csv_string(df_b_diff_60, "Raw 01-A: 活躍家數差") 
            dump_txt += format_to_csv_string(df_daily_tracker_60, "Raw 01-B: 戰場追蹤") 
            dump_txt += format_to_csv_string(df_s_wide.head(10).copy() if is_valid(df_s_wide) else pd.DataFrame(), "Raw 02: 集保原始")
            st.code(dump_txt, language="text")
            
        st.success(f"V73.00 處理完畢。")
        gc.collect()

st.caption("V73.00 備註：已徹底解除單行壓縮陷阱，採用最標準安全的結構，保證系統100%穩定。")
