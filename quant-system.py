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
import time
from io import StringIO
import streamlit.components.v1 as components
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="全息量化系統 (V75.9 終極版)", initial_sidebar_state="expanded")

FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiVG9uZTEiLCJlbWFpbCI6InRvbmVoc2llQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjJ9.LQ9tOV7cgcr27W5jIrdriUnvz-6wIFxCOKzuB9F2A-0"
GITHUB_MANUAL_URL = "https://raw.githubusercontent.com/tonehsie/stock/refs/heads/main/README.md?token=GHSAT0AAAAAADZWCPTL3DW2BEKOO6XFVHZS2PXHCPA"

# ==========================================
# 前端語法模板集中區 (CSS/HTML/JS)
# ==========================================
CSS = """
<style>
/* 一般表格，最高 600px 捲動 */
.table-container { overflow: auto; max-height: 600px; width: 100%; margin-bottom: 25px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding-bottom: 10px; }
.table-container table { width: max-content !important; min-width: 40%; border-collapse: separate !important; border-spacing: 0; font-size: 15px !important; font-family: sans-serif; background-color: #fff; }
.table-container th, .table-container td { white-space: nowrap !important; padding: 10px 12px !important; border-bottom: 1px solid #dee2e6; border-right: 1px solid #dee2e6; vertical-align: middle; }
.table-container th { border-top: 1px solid #dee2e6; word-break: keep-all !important; text-align: center !important; background-color: #f1f3f5 !important; color: #333 !important; font-weight: 700 !important; line-height: 1.4; position: sticky; top: 0; z-index: 3; }
.table-container th:first-child, .table-container td:first-child { position: sticky; left: 0; background-color: #f8f9fa; z-index: 4; font-weight: bold; text-align: center !important; border-left: 1px solid #dee2e6; }
.table-container thead th:first-child { z-index: 5; }

/* 視覺化圖表專用：無限長高、無垂直捲軸、完美推擠下層 */
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
.stTabs [data-baseweb='tab-list'] { gap: 10px; }
.stTabs [data-baseweb='tab'] { height: 50px; white-space: pre-wrap; background-color: #f8f9fa; border-radius: 4px 4px 0 0; padding: 10px 20px; font-weight: bold; }
.stTabs [aria-selected='true'] { background-color: #e3f2fd !important; color: #1e3a8a !important; border-bottom: 3px solid #1e3a8a !important; }

/* 強化版 AI 報告樣式 */
.ai-report-box { background-color: #fcfdfe; border: 1px solid #e9ecef; border-left: 6px solid #b71c1c; border-radius: 8px; padding: 25px; margin-bottom: 30px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); line-height: 1.8; }
.ai-report-box h4 { margin-top: 0; color: #b71c1c; font-weight: 900; font-size: 1.6rem; border-bottom: 2px dashed #ccc; padding-bottom: 10px; margin-bottom: 20px; }
.ai-report-box ul { margin-bottom: 20px; padding-left: 20px; }
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
    .stTabs [data-baseweb='tab'] { background-color: #2d2d2d !important; color: #aaa !important; }
    .stTabs [aria-selected='true'] { background-color: #1a237e !important; color: #64b5f6 !important; border-bottom-color: #64b5f6 !important; }
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
        
        /* 圖表區深色模式自動反轉 */
        @media (prefers-color-scheme: dark) {
            body { background: #1e1e1e; }
            #chart-main { border-bottom: 2px solid #444; }
            .legend { background: rgba(30,30,30,0.7); color: #e0e0e0; }
        }
    </style>
</head>
<body>
    <div id="chart-main"><div id="legend" class="legend"></div></div>
    <div id="chart-vol"></div>
    <script>
        const kData = KLINE_DATA;
        const tVol = TOTAL_VOL;
        const dtVol = DAYTRADE_VOL;
        const ma = MA_DATA;
        
        const kDataMap = new Map(kData.map(x => [x.time, x]));
        const tVolMap = new Map(tVol.map(x => [x.time, x.value]));
        const dtVolMap = new Map(dtVol.map(x => [x.time, x.value]));

        const commonLocalization = {
            timeFormatter: businessDayOrTimestamp => {
                if (businessDayOrTimestamp.year) {
                    const y = String(businessDayOrTimestamp.year).slice(-2);
                    const m = String(businessDayOrTimestamp.month).padStart(2, '0');
                    const d = String(businessDayOrTimestamp.day).padStart(2, '0');
                    return `${y}/${m}/${d}`;
                }
                if (typeof businessDayOrTimestamp === 'string') {
                    return businessDayOrTimestamp.substring(2).replace(/-/g, '/');
                }
                return businessDayOrTimestamp;
            }
        };

        const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const chartBgColor = isDark ? '#1e1e1e' : '#ffffff';
        const chartTxtColor = isDark ? '#e0e0e0' : '#333';
        const chartGridColor = isDark ? '#333333' : '#f5f5f5';

        const priceScaleConfig = {
            borderColor: chartGridColor,
            autoScale: true,
            minimumWidth: 80, 
            alignLabels: true
        };

        const mainOptions = {
            autoSize: true,
            localization: commonLocalization,
            layout: { background: { color: chartBgColor }, textColor: chartTxtColor },
            grid: { vertLines: { color: chartGridColor }, horzLines: { color: chartGridColor } },
            rightPriceScale: { ...priceScaleConfig, scaleMargins: { top: 0.05, bottom: 0.05 } },
            timeScale: { visible: false, rightOffset: 10 }
        };

        const volOptions = {
            autoSize: true,
            localization: commonLocalization,
            layout: { background: { color: chartBgColor }, textColor: chartTxtColor },
            grid: { vertLines: { color: chartGridColor }, horzLines: { color: chartGridColor } },
            rightPriceScale: { ...priceScaleConfig, scaleMargins: { top: 0.02, bottom: 0 } },
            timeScale: { borderColor: chartGridColor, rightOffset: 10 }
        };

        const mainChart = LightweightCharts.createChart(document.getElementById('chart-main'), mainOptions);
        const volChart = LightweightCharts.createChart(document.getElementById('chart-vol'), volOptions);

        const candleSeries = mainChart.addCandlestickSeries({
            upColor: chartBgColor, borderUpColor: isDark ? '#fff' : '#000', wickUpColor: isDark ? '#fff' : '#000',
            downColor: isDark ? '#fff' : '#000', borderDownColor: isDark ? '#fff' : '#000', wickDownColor: isDark ? '#fff' : '#000'
        });
        candleSeries.setData(kData);

        const lineOpt = { lineWidth: 1, lastValueVisible: false, priceLineVisible: false, crosshairMarkerVisible: false };
        mainChart.addLineSeries({ color: '#ff9800', ...lineOpt }).setData(ma.ma_short);
        mainChart.addLineSeries({ color: '#2196f3', ...lineOpt }).setData(ma.ma_mid);
        mainChart.addLineSeries({ color: '#9c27b0', ...lineOpt }).setData(ma.ma_long);

        const lr = LR_DATA;
        if (lr && lr.upper && lr.upper.length > 0) {
            mainChart.addLineSeries({ color: isDark ? 'rgba(100, 181, 246, 0.5)' : 'rgba(30, 58, 138, 0.4)', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Solid, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }).setData(lr.upper);
            mainChart.addLineSeries({ color: isDark ? 'rgba(100, 181, 246, 0.8)' : 'rgba(30, 58, 138, 0.6)', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }).setData(lr.mid);
            mainChart.addLineSeries({ color: isDark ? 'rgba(100, 181, 246, 0.5)' : 'rgba(30, 58, 138, 0.4)', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Solid, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }).setData(lr.lower);
        }

        const pat = PAT_DATA;
        const neck = NECK_DATA;
        const patColor = PAT_COLOR;
        if (pat && pat.length > 0) {
            mainChart.addLineSeries({ color: patColor, lineWidth: 2, lineStyle: LightweightCharts.LineStyle.Solid, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }).setData(pat);
        }
        if (neck && neck.length > 0) {
            mainChart.addLineSeries({ color: patColor, lineWidth: 2, lineStyle: LightweightCharts.LineStyle.Dotted, crosshairMarkerVisible: false, lastValueVisible: false, priceLineVisible: false }).setData(neck);
        }

        const totalVolSeries = volChart.addHistogramSeries({ priceFormat: { type: 'volume' } });
        totalVolSeries.setData(tVol);
        const dayTradeVolSeries = volChart.addHistogramSeries({ priceFormat: { type: 'volume' } });
        dayTradeVolSeries.setData(dtVol);

        const legend = document.getElementById('legend');
        const updateLegend = (p) => {
            let d, dtVal, tvVal;
            if (p.time) {
                d = kDataMap.get(p.time);
                dtVal = dtVolMap.get(p.time);
                tvVal = tVolMap.get(p.time);
            } else {
                d = kData[kData.length-1];
                dtVal = dtVol[dtVol.length-1].value;
                tvVal = tVol[tVol.length-1].value;
            }
            
            if (!d || dtVal === undefined || tvVal === undefined) return;

            const shortDate = d.time.substring(2).replace(/-/g, '/');
            legend.innerHTML = `<b>${shortDate}</b> &nbsp; 開:${d.open} 高:${d.high} 低:${d.low} 收:<span style="color:${chartTxtColor}">${d.close}</span> &nbsp; <span style="color:#888">總量:${Math.round(tvVal)}</span> &nbsp; <span style="color:#FF9800">當沖:${Math.round(dtVal)}</span>`;
        };
        updateLegend({time: null});

        mainChart.subscribeCrosshairMove(p => {
            updateLegend(p);
            if (p.time) volChart.setCrosshairPosition(0, p.time, totalVolSeries);
            else volChart.clearCrosshairPosition();
        });
        volChart.subscribeCrosshairMove(p => {
            updateLegend(p);
            if (p.time) mainChart.setCrosshairPosition(0, p.time, candleSeries);
            else mainChart.clearCrosshairPosition();
        });

        let isSyncingMain = false;
        let isSyncingVol = false;

        mainChart.timeScale().subscribeVisibleLogicalRangeChange(r => {
            if (!isSyncingMain && r !== null) {
                isSyncingVol = true;
                volChart.timeScale().setVisibleLogicalRange(r);
                isSyncingVol = false;
            }
        });
        volChart.timeScale().subscribeVisibleLogicalRangeChange(r => {
            if (!isSyncingVol && r !== null) {
                isSyncingMain = true;
                mainChart.timeScale().setVisibleLogicalRange(r);
                isSyncingMain = false;
            }
        });
    </script>
</body>
</html>
"""

st.markdown(CSS, unsafe_allow_html=True)

# 🎯 統一防呆檢驗工具
def is_valid(df, req_cols=None, min_len=1):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty or len(df) < min_len: return False
    if req_cols and not all(c in df.columns for c in req_cols): return False
    return True

def optimize_memory(df):
    if not is_valid(df): return df
    for col in df.columns:
        col_type = df[col].dtype
        if col_type == 'float64':
            df[col] = df[col].astype('float32')
        elif col_type == 'int64':
            df[col] = df[col].astype('int32')
        elif col_type == 'object':
            if 'trader' in col or '分點' in col or '標籤' in col:
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

st.sidebar.markdown("### 交易戰略大腦")
trade_strategy = st.sidebar.radio("交易戰略偏好", ["右側動能 (短線突破)", "左側潛伏 (中長線價值)"])
is_right_side = "右側" in trade_strategy

st.sidebar.header("戰術參數控制面板")
kline_days = st.sidebar.slider("K線顯示天數 (圖表景深)", 30, 600, 270, 10)
lookback_days = st.sidebar.selectbox("長線籌碼回溯天數 (全局黏著度分母)", [20, 60, 90, 120], index=1)
stickiness_threshold = st.sidebar.slider("主力黏著度門檻 (%)", 10.0, 80.0, 50.0, 5.0)

# 🗓️ 自訂區間選擇器：這將直接連動到「終極全息透視區」
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
enable_pattern = st.sidebar.checkbox("啟動 AI 幾幾何形態掃描", value=True)

pattern_mode = st.sidebar.selectbox("形態顯示模式", [
    "全自動智慧辨識 (Auto)", 
    "反轉：W底 (雙重底)", "反轉：M頭 (雙重頂)", 
    "反轉：頭肩底", "反轉：頭肩頂", 
    "反轉：三重底", "反轉：三重頂",
    "反轉：V型反轉",
    "連續：對稱三角形", 
    "連續：上升三角形", "連續：下降三角形",
    "連續：上升楔形", "連續：下降楔形",
    "連續：矩形 (箱型整理)"
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

st.title("全息量化系統 (V75.9 終極版)")
user_count, api_limit = get_api_usage(FINMIND_TOKEN)
usage_text = f" | FinMind 額度: {user_count} / {api_limit}" if user_count is not None else ""
st.caption(f"V75.9：終極全息透視區支援側邊欄自訂時間區間。{usage_text}")

with st.expander("點此閱讀【全息量化系統】四大核心模組終極實戰指南", expanded=False):
    st.markdown(fetch_github_manual(GITHUB_MANUAL_URL), unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])
with col1: 
    user_stock_id = st.text_input("個股代號", value="2330")
with col2: 
    dead_chip_input = st.text_input("死籌碼 % (董監事持股＋大股東持股，留空自動抓)")
run_btn = st.button("啟動 V75.9 決策引擎", use_container_width=True, key="run_engine")

# ==========================================
# 基礎資料處理函式
# ==========================================
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
    if data is None:
        raise ValueError("FinMind 回傳資料為空")
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
    except:
        return pd.DataFrame()

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
        ("TaiwanStockConvertibleBondDailyOverview", dates[0], None, None),
        ("TaiwanStockBlockTrade", d_end, None, user_stock_id), 
        ("TaiwanStockSecuritiesLending", d_end, None, user_stock_id) 
    ]

    total_tasks = max_len + len(api_targets)
    
    prog_container = st.empty()
    text_container = st.empty()
    prog_bar = prog_container.progress(0.0)

    def fetch_api(dataset, sd, ed, tid):
        url = "https://api.finmindtrade.com/api/v4/data"
        p = {"dataset": dataset, "start_date": sd}
        if tid: p["data_id"] = tid
        if ed: p["end_date"] = ed
        try:
            return dataset, cached_finmind_api_call(url, tuple(sorted(p.items())))
        except:
            return dataset, []

    def fetch_branch(d, tid):
        url = "https://api.finmindtrade.com/api/v4/data"
        p = {"dataset": "TaiwanStockTradingDailyReport", "data_id": tid, "start_date": d, "end_date": d}
        try:
            return cached_finmind_api_call(url, tuple(sorted(p.items())))
        except:
            return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        future_to_type = {}
        for d in dates[:max_len]:
            future_to_type[executor.submit(fetch_branch, d, user_stock_id)] = 'branch'
        for ds, sd, ed, tid in api_targets:
            future_to_type[executor.submit(fetch_api, ds, sd, ed, tid)] = 'api'

        completed = 0
        for future in concurrent.futures.as_completed(future_to_type):
            completed += 1
            prog_val = min(1.0, completed / total_tasks)
            prog_bar.progress(prog_val)
            text_container.markdown(f"<div class='progress-text'>⚡ 系統載入中... 正在與 FinMind 同步資料 (進度: {completed} / {total_tasks})</div>", unsafe_allow_html=True)

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
                text_container.markdown(f"<div class='progress-text'>🔍 正在掃描並擴充可轉債(CBAS)資訊...</div>", unsafe_allow_html=True)
                cb_futures = [executor.submit(fetch_api, "TaiwanStockConvertibleBondInfo", "2000-01-01", None, cid) for cid in target_cbs]
                for f in concurrent.futures.as_completed(cb_futures):
                    _, cb_data = f.result()
                    if cb_data: cb_info_list.extend(cb_data)

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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
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
                                val_dir = float(v_dir) if v_dir not in ['-', '', 'nan'] else 0.0
                                val_large = float(v_large) if v_large not in ['-', '', 'nan'] else 0.0
                                val = val_dir + val_large
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
    
    for c in ["設質(張)", "解質(張)", "累積質設(張)"]: 
        df_all[c] = safe_to_num(df_all[c]).astype(int)
        
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
    g = g[(g['tb_shares'] > 0) | (g['ts_shares'] > 0)]
    
    cond_loss = (g['avg_b'] > latest_close) & (g['avg_b'] > 0) & (g['net_shares'] > 0)
    b_strs = g['avg_b'].apply(lambda x: f"{x:,.2f}" if x > 0 else "-")
    g = g.assign(
        b_str = np.where(cond_loss, "(虧) " + b_strs, b_strs),
        pos = g['last_date'].map(pos_dict).fillna(0.5).round(2)
    )
    
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
    if total_lots <= 0 or not is_valid(df_b_raw): return 15, "基本預設 (缺股本資料)"
    if total_lots < 300000: base_n, cap_desc = 10, "微型股本"
    elif total_lots < 1000000: base_n, cap_desc = 15, "中小型股"
    elif total_lots < 5000000: base_n, cap_desc = 30, "中大型股"
    else: base_n, cap_desc = 50, "大型權值"

    recent_dates = dates_list[:5]
    recent_pr = df_price[df_price['日期'].isin(recent_dates)]
    avg_vol = recent_pr['成交量(張)'].mean() if not recent_pr.empty else 0
    turnover_5d = (avg_vol / total_lots) * 100 if total_lots > 0 else 0

    turn_desc = ""
    final_n = base_n
    if turnover_5d > 10.0: 
        final_n = max(5, int(base_n * 0.7))
        turn_desc = " | 高週轉降噪"
    elif turnover_5d < 1.0: 
        final_n = min(50, int(base_n * 1.2))
        turn_desc = " | 低波擴散"

    df_20 = df_b_raw[df_b_raw['date'].isin(dates_list[:20])]
    g = df_20.groupby('securities_trader')[['buy', 'sell']].sum()
    g = g.assign(net = (g['buy'] - g['sell']) / 1000)
    buyers = g[g['net'] > 0].sort_values('net', ascending=False)

    if len(buyers) > 5:
        top5_sum = buyers.head(5)['net'].sum()
        topN_sum = buyers.head(final_n)['net'].sum() if len(buyers) >= final_n else buyers['net'].sum()
        if topN_sum > 0 and (top5_sum / topN_sum) > 0.8:
            final_n = max(5, min(final_n, 10))
            turn_desc += " | 極度集中收斂"

    final_n = max(5, min(final_n, 50))
    return final_n, f"{cap_desc}{turn_desc}"

def calculate_pure_defense_line(df_b_raw, tags, is_filter_active, total_lots, dead_chip_ratio, dynamic_n):
    if not is_valid(df_b_raw): return 0.0, 0, 0, 0.0, []
    
    if is_filter_active: 
        valid_df = df_b_raw[~df_b_raw['is_short'] & ~df_b_raw['tag'].isin(["棄守提款", "避險造市"])]
    else: 
        valid_df = df_b_raw

    if not is_valid(valid_df): return 0.0, 0, 0, 0.0, []
    
    broker_stats = valid_df.groupby('securities_trader').agg(
        buy_vol=('buy', 'sum'),
        sell_vol=('sell', 'sum'),
        buy_amt=('valid_buy_amt', 'sum'),
        valid_buy_vol=('valid_buy', 'sum')
    )
    
    broker_stats = broker_stats.assign(net_vol = broker_stats['buy_vol'] - broker_stats['sell_vol'])
    top_buyers = broker_stats[broker_stats['net_vol'] > 0].sort_values('net_vol', ascending=False).head(dynamic_n)
    
    if top_buyers.empty: return 0.0, 0, 0, 0.0, []
    
    core_branch_names = top_buyers.index.tolist()
    
    top_buyers = top_buyers.assign(avg_buy_price = (top_buyers['buy_amt'] / top_buyers['valid_buy_vol'].replace(0, np.nan)).fillna(0))
    valid_top_buyers = top_buyers[top_buyers['avg_buy_price'] > 0]
    total_net_vol = valid_top_buyers['net_vol'].sum()
    
    vwap = round((valid_top_buyers['avg_buy_price'] * valid_top_buyers['net_vol']).sum() / total_net_vol, 2) if total_net_vol > 0 else 0.0
    
    full_net_accum = int(top_buyers['net_vol'].sum() / 1000)
    active_buyers = len(top_buyers)
    
    c_value = 0.0
    if total_lots > 0:
        safe_dead_ratio = max(0.0, min(99.9, float(dead_chip_ratio)))
        free_float_ratio = (100.0 - safe_dead_ratio) / 100.0
        free_float_lots = total_lots * free_float_ratio
        if free_float_lots > 0:
            raw_c = (full_net_accum / free_float_lots) * 100
            c_value = round(min(98.0, raw_c), 2)

    return vwap, full_net_accum, active_buyers, c_value, core_branch_names

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
            
    if 'Trading_Volume' in df_out.columns: df_out['成交量(張)'] = (safe_to_num(df_out['Trading_Volume']) / 1000).round().astype(int)
    elif 'Trading_volume' in df_out.columns: df_out['成交量(張)'] = (safe_to_num(df_out['Trading_volume']) / 1000).round().astype(int)
    else: df_out['成交量(張)'] = 0
    
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]
    df_out = df_out.assign(斷頭價_078 = (df_out["收盤價(元)"] * 0.78).round(2)).rename(columns={'斷頭價_078': '斷頭價(0.78)'})
    
    cols_to_keep = ['日期','成交量(張)','開盤價(元)','最高價(元)','最低價(元)','收盤價(元)','漲跌(元)','斷頭價(0.78)']
    return df_out[[c for c in cols_to_keep if c in df_out.columns]].sort_values('日期', ascending=False)

def render_volume_profile(df_raw, rank_dates, top_n=15):
    if not is_valid(df_raw) or not rank_dates:
        st.warning("查無足夠資料產生建倉成本分佈圖。")
        return

    df_rank = df_raw[df_raw['date'].isin(rank_dates)]
    rank_sum = (df_rank.groupby('securities_trader')['net_shares'].sum() / 1000).round().astype(int)
    
    top_b = rank_sum[rank_sum > 0].nlargest(top_n).index.tolist()
    top_s = rank_sum[rank_sum < 0].nsmallest(top_n).index.tolist()
    target_traders = top_b + top_s
    
    if not target_traders:
        st.warning("無符合條件的活躍分點。")
        return

    df_vp = df_rank[(df_rank['securities_trader'].isin(target_traders)) & (df_rank['price'] > 0)].assign(
        buy_lots = lambda x: x['buy'] / 1000,
        sell_lots = lambda x: x['sell'] / 1000
    )
    if df_vp.empty:
        st.warning("無有效價格資料進行成本區間分析。")
        return

    min_p = df_vp['price'].min()
    max_p = df_vp['price'].max()
    
    if min_p == max_p:
        labels = [f"{min_p:.2f}"]
        df_vp = df_vp.assign(price_bin = labels[0])
    else:
        bin_edges = np.linspace(min_p, max_p, num=16)
        labels = [f"{bin_edges[i]:.2f} - {bin_edges[i+1]:.2f}" for i in range(len(bin_edges)-1)]
        df_vp = df_vp.assign(price_bin = pd.cut(df_vp['price'], bins=bin_edges, labels=labels, include_lowest=True))

    vp_grouped = df_vp.groupby('price_bin', observed=False)[['buy_lots', 'sell_lots']].sum().fillna(0)
    vp_grouped = vp_grouped.assign(
        total_lots = vp_grouped['buy_lots'] + vp_grouped['sell_lots'],
        net_lots = vp_grouped['buy_lots'] - vp_grouped['sell_lots']
    )
    
    if vp_grouped['total_lots'].sum() == 0:
        st.warning("該區間大戶無顯著成交量。")
        return

    poc_idx = vp_grouped['total_lots'].idxmax()
    max_vol_for_scale = vp_grouped[['buy_lots', 'sell_lots']].max().max()
    if max_vol_for_scale == 0: max_vol_for_scale = 1

    html_parts = ["<div class='full-table-container'><table><thead><tr>"]
    html_parts.append("<th style='width: 20%;'>價位區間 (元)</th>")
    html_parts.append("<th style='width: 35%; text-align: left;'>買進量 (大戶建倉)</th>")
    html_parts.append("<th style='width: 35%; text-align: left;'>賣出量 (大戶倒貨)</th>")
    html_parts.append("<th style='width: 10%; text-align: right;'>淨買賣(張)</th>")
    html_parts.append("</tr></thead><tbody>")

    vp_grouped = vp_grouped.sort_index(ascending=False)

    for idx, row in vp_grouped.iterrows():
        if row['total_lots'] == 0: continue
            
        b_vol = int(round(row['buy_lots']))
        s_vol = int(round(row['sell_lots']))
        n_vol = int(round(row['net_lots']))
        
        b_width = min(100, (b_vol / max_vol_for_scale) * 100) if max_vol_for_scale > 0 else 0
        s_width = min(100, (s_vol / max_vol_for_scale) * 100) if max_vol_for_scale > 0 else 0

        is_poc = (idx == poc_idx)
        row_bg = "background-color: rgba(255, 193, 7, 0.15);" if is_poc else ""
        poc_star = " <br><span style='color:#f57c00; font-size:12px; font-weight:900;'>[POC 核心防守]</span>" if is_poc else ""

        html_parts.append(f"<tr style='{row_bg}'>")
        html_parts.append(f"<td style='font-weight: bold; font-size:14px;'>{idx}{poc_star}</td>")
        
        b_txt = f"{b_vol:,}" if b_vol > 0 else ""
        s_txt = f"{s_vol:,}" if s_vol > 0 else ""
        
        html_parts.append(f"<td><div style='display: flex; align-items: center;'><div style='width: {b_width}%; background-color: #e53935; height: 18px; border-radius: 2px; margin-right: 8px;'></div><span style='font-size: 13px; font-weight:bold;'>{b_txt}</span></div></td>")
        html_parts.append(f"<td><div style='display: flex; align-items: center;'><div style='width: {s_width}%; background-color: #43a047; height: 18px; border-radius: 2px; margin-right: 8px;'></div><span style='font-size: 13px; font-weight:bold;'>{s_txt}</span></div></td>")
        
        if n_vol != 0:
            net_color = "#d32f2f" if n_vol > 0 else "#2e7d32"
            net_txt = f"+{n_vol:,}" if n_vol > 0 else f"{n_vol:,}"
            html_parts.append(f"<td style='color: {net_color}; font-weight: bold; text-align: right;'>{net_txt}</td>")
        else:
            html_parts.append(f"<td style='text-align: right;'></td>")
            
        html_parts.append("</tr>")
        
    html_parts.append("</tbody></table></div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)

def render_institutional_vs_local(df_branch_raw, df_inst, intel_tags, top_n=4):
    if not is_valid(df_branch_raw) or not is_valid(df_inst):
        st.warning("查無法人或分點資料可供比對。")
        return
        
    dates_in_inst = df_inst['日期'].tolist()
    if not dates_in_inst: return
    
    df_recent = df_branch_raw[df_branch_raw['date'].isin(dates_in_inst)]
    rank_sum = (df_recent.groupby('securities_trader')['net_shares'].sum() / 1000).round().astype(int)
    
    top_branches = rank_sum.abs().nlargest(top_n).index.tolist()
    if not top_branches: return
    
    p = df_recent.groupby(['date', 'securities_trader'])['net_shares'].sum().reset_index()
    p['net'] = (p['net_shares'] / 1000).round().astype(int)
    p_pivot = p.pivot(index='date', columns='securities_trader', values='net').fillna(0).astype(int)
    
    html_parts = ["<div class='full-table-container'><table><thead><tr>"]
    html_parts.append("<th style='position: sticky; left: 0; z-index: 6;'>日期</th>")
    html_parts.append("<th style='text-align: right; background-color: #f1f3f5;'>外資(張)</th>")
    html_parts.append("<th style='text-align: right; background-color: #f1f3f5;'>投信(張)</th>")
    
    for tb in top_branches:
        tag_short = intel_tags.get(tb, "路人")[:4]
        html_parts.append(f"<th style='text-align: right;'>{tb}<br><span style='font-size:11px; color:#1e3a8a;'>{tag_short}</span></th>")
    
    html_parts.append("<th style='text-align: center; background-color: #e3f2fd;'>聯合作戰診斷</th></tr></thead><tbody>")
    
    for _, row in df_inst.iterrows():
        d = row['日期']
        f_net = row.get('外資買賣超(張)', 0)
        i_net = row.get('投信買賣超(張)', 0)
        
        html_parts.append("<tr>")
        html_parts.append(f"<td style='position: sticky; left: 0; background-color: #f8f9fa; z-index: 4; font-weight:bold; text-align:center;'>{d[5:]}</td>")
        
        def format_net(val):
            if val > 0: return f"<span style='color:#d32f2f; font-weight:bold;'>+{val:,}</span>"
            elif val < 0: return f"<span style='color:#2e7d32; font-weight:bold;'>{val:,}</span>"
            return "<span style='color:#bbb;'>0</span>"
            
        html_parts.append(f"<td style='text-align:right; background-color: #fdfdfd;'>{format_net(f_net)}</td>")
        html_parts.append(f"<td style='text-align:right; background-color: #fdfdfd;'>{format_net(i_net)}</td>")
        
        local_net_sum = 0
        for tb in top_branches:
            val = p_pivot.at[d, tb] if d in p_pivot.index and tb in p_pivot.columns else 0
            local_net_sum += val
            html_parts.append(f"<td style='text-align:right;'>{format_net(val)}</td>")
            
        inst_sum = f_net + i_net
        if inst_sum > 0 and local_net_sum > 0:
            diag = "土洋共擊"
            bg = "rgba(229, 57, 53, 0.15)"
            color = "#c62828"
        elif inst_sum < 0 and local_net_sum < 0:
            diag = "多殺多撤退"
            bg = "rgba(67, 160, 71, 0.15)"
            color = "#2e7d32"
        elif inst_sum > 0 and local_net_sum < 0:
            diag = "法人接盤"
            bg = "transparent"
            color = "#555"
        elif inst_sum < 0 and local_net_sum > 0:
            diag = "地方硬扛"
            bg = "transparent"
            color = "#555"
        else:
            diag = "休兵盤整"
            bg = "transparent"
            color = "#aaa"
            
        html_parts.append(f"<td style='text-align:center; background-color:{bg}; color:{color}; font-weight:bold; font-size:13px;'>{diag}</td>")
        html_parts.append("</tr>")
        
    html_parts.append("</tbody></table></div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)

def process_branch_v25(df_raw, period, actual_dates, intel_tags, df_price_raw, stick_thresh, global_days):
    try:
        if not is_valid(df_raw) or not is_valid(df_price_raw): return pd.DataFrame()
        latest_close = df_price_raw.sort_values('date', ascending=False)['close'].iloc[0]
        df = df_raw[df_raw['date'].isin(actual_dates[:period])]
        if not is_valid(df): return pd.DataFrame()
        
        g = df.groupby('securities_trader').agg(
            bv=('buy', 'sum'), sv=('sell', 'sum'), 
            vbv=('valid_buy', 'sum'), vsv=('valid_sell', 'sum'),
            ba=('valid_buy_amt', 'sum'), sa=('valid_sell_amt', 'sum')
        ).reset_index()
        
        g['net'] = round((g['bv'] - g['sv']) / 1000).astype(int)
        g['avg_b'] = (g['ba'] / g['vbv'].replace(0, np.nan)).fillna(0)
        g['avg_s'] = (g['sa'] / g['vsv'].replace(0, np.nan)).fillna(0)
        
        b = g[g['net'] > 0].sort_values('net', ascending=False).head(15).reset_index(drop=True)
        s = g[g['net'] < 0].sort_values('net', ascending=True).head(15).reset_index(drop=True)
        out, tv = [], round(g['bv'].sum() / 1000) if g['bv'].sum() > 0 else 1
        
        for i in range(15):
            r = {}
            if i < len(b): 
                b_str = f"{round(b.loc[i,'avg_b'], 2):,.2f}" if b.loc[i,'avg_b'] > 0 else "-"
                if b.loc[i,'avg_b'] > latest_close and b.loc[i,'avg_b'] > 0 and b.loc[i,'net'] > 0: b_str = f"(虧) {b_str}"
                raw_tag = intel_tags.get(b.loc[i,'securities_trader'], '路人雜訊')
                attr = "短線" if any(x in raw_tag for x in ["隔日突擊", "跟風小戶"]) else "中長線" if any(x in raw_tag for x in ["波段鎖碼", "避險造市", "主力重砲"]) else "波段"
                r["買超分點"] = b.loc[i,'securities_trader']
                r["買_標籤"] = raw_tag
                r["買_週期"] = attr
                r["買超(張)"] = int(b.loc[i,'net'])
                r["買均價"] = b_str
                r["佔比"] = f"{(b.loc[i,'net']/tv)*100:.1f}%" if tv > 0 else "-"
            else: r["買超分點"], r["買_標籤"], r["買_週期"], r["買超(張)"], r["買均價"], r["佔比"] = "-", "-", "-", 0, "-", "-"
            
            if i < len(s): 
                raw_tag_s = intel_tags.get(s.loc[i,'securities_trader'], '路人雜訊')
                attr_s = "短線" if any(x in raw_tag_s for x in ["隔日突擊", "跟風小戶"]) else "中長線" if any(x in raw_tag_s for x in ["波段鎖碼", "避險造市", "主力重砲"]) else "波段"
                r["賣超分點"] = s.loc[i,'securities_trader']
                r["賣_標籤"] = raw_tag_s
                r["賣_週期"] = attr_s
                r["賣超(張)"] = abs(int(s.loc[i,'net']))
                r["賣均價"] = f"{round(s.loc[i,'avg_s'], 2):,.2f}" if s.loc[i,'avg_s'] > 0 else "-"
                r["佔比_"] = f"{(abs(s.loc[i,'net'])/tv)*100:.1f}%" if tv > 0 else "-"
            else: r["賣超分點"], r["賣_標籤"], r["賣_週期"], r["賣超(張)"], r["賣均價"], r["佔比_"] = "-", "-", "-", 0, "-", "-"
            out.append(r)
        return pd.DataFrame(out)
    except Exception:
        return pd.DataFrame()

def process_v27_ultimate_radar(df_wide, dead_chip_input, dynamic_dict, static_val, df_price, df_branch_raw, intel_tags):
    if not is_valid(df_wide, min_len=2):
        st.warning("⚠️ [V27 終極雷達] 集保股權分佈資料不足 (少於2週)，無法比對趨勢，雷達模組已暫停。")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    if not is_valid(df_price):
        st.warning("⚠️ [V27 終極雷達] 查無歷史股價，系統將以預設基準 (無動態股價加權) 強制推算大戶門檻。")

    try:
        df = df_wide.sort_values('日期', ascending=True)
        df = df.assign(dt_end=pd.to_datetime(df['日期']))
        
        if not df_price.empty:
            df_p = df_price[['日期', '收盤價(元)']].drop_duplicates(subset=['日期']).sort_values('日期')
            df_p['dt'] = pd.to_datetime(df_p['dt'] if 'dt' in df_p.columns else df_p['日期'])
            df_p['收盤價(元)'] = pd.to_numeric(df_p['收盤價(元)'], errors='coerce')
            df_p['ma20'] = df_p['收盤價(元)'].rolling(20, min_periods=1).mean()
            df = pd.merge_asof(df.sort_values('dt_end'), df_p[['dt', '收盤價(元)', 'ma20']], left_on='dt_end', right_on='dt', direction='backward')
        else: 
            df['收盤價(元)'], df['ma20'] = 0, 0
            
        df['總人數(人)'] = pd.to_numeric(df['總人數(人)'], errors='coerce')
        df['總人數變率(%)'] = (df['總人數(人)'].pct_change() * 100).fillna(0).round(2)
        df['總張數'] = pd.to_numeric(df.get('總張數', 0), errors='coerce').fillna(0)
        
        levels_cols = ['100-200張_比例(%)', '200-400張_比例(%)', '400-600張_比例(%)', '600-800張_比例(%)', '800-1000張_比例(%)', '1000張以上_比例(%)']
        for col in levels_cols:
            df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0.0)
            
        df['pct_1000'] = df['1000張以上_比例(%)']
        df['pct_800'] = df['pct_1000'] + df['800-1000張_比例(%)']
        df['pct_600'] = df['pct_800'] + df['600-800張_比例(%)']
        df['pct_400'] = df['pct_600'] + df['400-600張_比例(%)']
        df['pct_200'] = df['pct_400'] + df['200-400張_比例(%)']
        df['pct_100'] = df['pct_200'] + df['100-200張_比例(%)']

        fake_dict = {}
        if not df_branch_raw.empty:
            mask_short = df_branch_raw['is_short']
            df_fake = df_branch_raw[mask_short]
            if not df_fake.empty:
                df_fake_daily = df_fake.groupby(['date', 'securities_trader'])[['buy', 'sell']].sum().reset_index()
                df_fake_daily['net_buy_exact'] = (df_fake_daily['buy'] - df_fake_daily['sell']) / 1000
                fake_dict = df_fake_daily.groupby('date').apply(lambda x: x[['securities_trader', 'net_buy_exact']].to_dict('records')).to_dict()

        arr_dates_str = np.sort(df_branch_raw['date'].unique()) if not df_branch_raw.empty else np.array([])
        arr_dates_dt = pd.to_datetime(arr_dates_str) if len(arr_dates_str) > 0 else pd.Series([], dtype='datetime64[ns]')

        df['safe_dead_ratio'] = df['日期'].apply(lambda d: max(0.0, min(99.9, get_dead_chip_info(d, dead_chip_input, dynamic_dict, static_val, "")[0])))

        free_float_ratio = np.clip((100 - df['safe_dead_ratio']) / 100, 0.05, 1.0)
        float_1pct_lots = df['總張數'] * free_float_ratio * 0.01

        raw_threshold = np.clip(float_1pct_lots, 100, 1000)
        levels = np.array([100, 200, 400, 600, 800, 1000])
        
        diffs = np.abs(raw_threshold.to_numpy()[:, None] - levels)
        df['ct'] = levels[diffs.argmin(axis=1)]

        conds = [df['ct'] <= 100, df['ct'] <= 200, df['ct'] <= 400, df['ct'] <= 600, df['ct'] <= 800]
        choices = [df['pct_100'], df['pct_200'], df['pct_400'], df['pct_600'], df['pct_800']]
        df['current_large_pct'] = np.select(conds, choices, default=df['pct_1000'])

        for col in ['pct_100', 'pct_200', 'pct_400', 'pct_600', 'pct_800', 'pct_1000']:
            df[f'prev_{col}'] = df[col].shift(1)

        prev_choices = [df['prev_pct_100'], df['prev_pct_200'], df['prev_pct_400'], df['prev_pct_600'], df['prev_pct_800']]
        df['prev_large_pct_adj'] = np.select(conds, prev_choices, default=df['prev_pct_1000'])

        df['raw_chg'] = (df['current_large_pct'] - df['prev_large_pct_adj']).fillna(0).round(2)

        def get_impact(row):
            if row.name == df.index[0] or row['總張數'] <= 0 or len(arr_dates_str) == 0:
                return 0.0, []
            
            d_str, d_dt, ct, total_lots = row['日期'], row['dt_end'], row['ct'], max(1, row['總張數'])
            idx = np.searchsorted(arr_dates_str, d_str, side='right') - 1
            if idx >= 0:
                last_trading_date = arr_dates_str[idx]
                if (d_dt - arr_dates_dt[idx]).days <= 7 and last_trading_date in fake_dict:
                    fake_traders = fake_dict[last_trading_date]
                    f_vol = sum(fr['net_buy_exact'] for fr in fake_traders if fr['net_buy_exact'] >= ct)
                    fri_list = [{"日期": d_str, "分點": fr['securities_trader'], "張數": round(fr['net_buy_exact'])} for fr in fake_traders if fr['net_buy_exact'] >= ct]
                    return (f_vol / total_lots) * 100, fri_list
            return 0.0, []

        impact_res = df.apply(get_impact, axis=1)
        df['f_impact'] = impact_res.apply(lambda x: x[0]).round(2)
        d_fri = [item for sublist in impact_res.apply(lambda x: x[1]) for item in sublist]

        df['p_chg'] = (df['raw_chg'] - df['f_impact']).round(2)
        df.loc[df.index[0], 'p_chg'] = 0.0  

        def build_diag(row):
            if row.name == df.index[0]: return "初始化 (基準建立)"
            if row['總張數'] <= 0: return "初始化/總股本為零"
            
            adv = []
            p_chg, f_impact = row['p_chg'], row['f_impact']
            lev = 100 / (100 - row['safe_dead_ratio']) if 0 <= row['safe_dead_ratio'] < 100 else 1
            
            if row['總人數變率(%)'] > 2.0 and p_chg < 0: adv.append(f"散戶增{row['總人數變率(%)']}%，大戶實質倒貨{abs(p_chg)}%")
            else:
                if p_chg * lev > 2.5 and row['收盤價(元)'] > row['ma20']: adv.append(f"站上月線且大戶純淨買超{round(p_chg*lev, 2)}%")
                elif p_chg > 0.4 and row['收盤價(元)'] < row['ma20']: adv.append(f"跌破月線但主力吃貨{p_chg}%")
                elif p_chg < -1.0: adv.append(f"大戶實質流出{abs(p_chg)}%")
                if f_impact > 1.2: adv.append(f"虛胖買盤潛藏{f_impact}%倒貨危機")
                
            return " | ".join(adv) if adv else "盤整"

        df['專家雷達診斷'] = df.apply(build_diag, axis=1)
        
        df_math = pd.DataFrame({
            "日期": df['日期'], "原始變動": df['raw_chg'], "當沖干擾": df['f_impact'], "純淨變動": df['p_chg']
        }).iloc[1:]

        df['純淨大戶變動(%)'] = df['p_chg']
        df['當沖虛胖(%)'] = df['f_impact']
        df['原始大戶變動(%)'] = df['raw_chg']
        df['大戶原持股(%)'] = df['current_large_pct'].round(2)
        
        res_df = df[['日期', '收盤價(元)', '大戶原持股(%)', '總人數變率(%)', '原始大戶變動(%)', '當沖虛胖(%)', '純淨大戶變動(%)', '專家雷達診斷']].sort_values('日期', ascending=False)
        res_df = res_df[~res_df['專家雷達診斷'].str.contains('初始化', na=False)]
        
        return res_df, df_math, pd.DataFrame(d_fri)
        
    except Exception as e:
        st.error(f"🚨 [V27 終極雷達] 運算遭遇異常，模組已強制停止。錯誤原因：`{str(e)}`")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def calculate_disposition_thresholds_v2(df_price, df_day_trade, total_lots):
    if not is_valid(df_price, min_len=6): return None
    df_asc = df_price.sort_values('日期', ascending=True).reset_index(drop=True)
    closes = df_asc['收盤價(元)'].tolist()
    lows = df_asc['最低價(元)'].tolist()
    volumes_lots = df_asc['成交量(張)'].tolist()

    res = {
        'limit_6d': closes[-6] * 1.32 if len(closes) >= 6 else None,
        'limit_amp': min(lows[-5:]) * 1.25 if len(lows) >= 5 else None,
        'limit_30d': closes[-30] * 2.0 if len(closes) >= 30 else None,
        'limit_60d': closes[-60] * 2.3 if len(closes) >= 60 else None,
    }

    res['day_trade_warning'] = False
    if not df_day_trade.empty and len(df_day_trade) >= 2:
        dt_vol = df_day_trade['當沖總張數'].tolist()[:6]
        vol_recent = volumes_lots[-6:]
        dt_ratios = [d / v if v > 0 else 0 for d, v in zip(dt_vol, reversed(vol_recent))]
        if len(dt_ratios) >= 2 and dt_ratios[0] > 0.6 and dt_ratios[1] > 0.6:
            res['day_trade_warning'] = True

    if total_lots > 0:
        recent_5d_vol_lots = sum(volumes_lots[-5:])
        max_volume_tomorrow_lots = (total_lots * 0.5) - recent_5d_vol_lots
        res['current_5d_turnover'] = (recent_5d_vol_lots / total_lots) * 100
        res['max_vol_6d'] = max_volume_tomorrow_lots
        res['max_vol_1d'] = total_lots * 0.1
        res['turnover_warning'] = res['current_5d_turnover'] > 10.0 
    else:
        res['current_5d_turnover'] = 0
        res['max_vol_6d'] = None
        res['max_vol_1d'] = None
        res['turnover_warning'] = False
    return res

def process_tdcc_dynamic_v2(df_share_wide, df_price, dead_chip_input, dynamic_dict, static_val, chip_engine):
    if not is_valid(df_share_wide) or not is_valid(df_price): return pd.DataFrame()
    
    df_s = df_share_wide.assign(dt=pd.to_datetime(df_share_wide['日期']))
    df_p = df_price[['日期', '收盤價(元)']].assign(dt=pd.to_datetime(df_price['日期'])).drop_duplicates(subset=['dt']).sort_values('dt')
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

    free_float_ratio = np.clip((100 - df_m['safe_dead_ratio']) / 100, 0.05, 1.0)
    float_1pct_lots = df_m['總張數'] * free_float_ratio * 0.01

    raw_threshold = np.clip(float_1pct_lots, 100, 1000)

    levels = np.array([100, 200, 400, 600, 800, 1000])
    
    diffs = np.abs(raw_threshold.to_numpy()[:, None] - levels)
    df_m['ct'] = levels[diffs.argmin(axis=1)]

    conds = [df_m['ct'] <= 100, df_m['ct'] <= 200, df_m['ct'] <= 400, df_m['ct'] <= 600, df_m['ct'] <= 800]
    choices = [df_m['pct_100'], df_m['pct_200'], df_m['pct_400'], df_m['pct_600'], df_m['pct_800']]
    df_m['lp'] = np.select(conds, choices, default=df_m['pct_1000'])

    mask_valid_dead = (df_m['safe_dead_ratio'] > 0) & (df_m['safe_dead_ratio'] < 100)
    cv = np.maximum(0, (df_m['lp'] - df_m['safe_dead_ratio']) / (100.0 - df_m['safe_dead_ratio']))
    df_m['cd'] = np.where(mask_valid_dead, np.round(cv * 100, 2), "-")

    st_conds = [df_m['lp'] > 80.0, df_m['lp'] > 70.0, (df_m['lp'] >= 40.0) & (df_m['lp'] <= 70.0)]
    st_choices = ["極度集中 (防無量倒貨)", "高度鎖碼", "波段甜區 (易吸量推升)"]
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
    if not is_valid(df_raw) or not actual_dates: return pd.DataFrame()
    out = [] 
    branch_grouped = dict(tuple(df_raw[['date', 'securities_trader', 'buy', 'sell']].groupby('date')))
    for d in actual_dates[:period_days]:
        if d not in branch_grouped: continue
        df_d = branch_grouped[d]
        
        buy_branches, sell_branches = df_d[df_d['buy'] > 0], df_d[df_d['sell'] > 0]
        
        buy_count = buy_branches['securities_trader'].nunique()
        sell_count = sell_branches['securities_trader'].nunique()
        diff_count = buy_count - sell_count
        active_count = df_d[(df_d['buy'] > 0) | (df_d['sell'] > 0)]['securities_trader'].nunique()
        concentration = ((sell_count - buy_count) / active_count * 100) if active_count > 0 else 0
        
        total_buy_vol, total_sell_vol = buy_branches['buy'].sum(), sell_branches['sell'].sum()
        avg_b = total_buy_vol / buy_count if buy_count > 0 else 0
        avg_s = total_sell_vol / sell_count if sell_count > 0 else 0
        firepower = (avg_b / avg_s) if avg_s > 0 else (99.9 if avg_b > 0 else 1.0)
        
        daily_total_vol = df_d['buy'].sum() 
        main_power = 0
        if daily_total_vol > 0:
            g_net = df_d.groupby('securities_trader').apply(lambda x: x['buy'].sum() - x['sell'].sum())
            top_15_buy_vol = g_net[g_net > 0].nlargest(15).sum()
            top_15_sell_vol = abs(g_net[g_net < 0].nsmallest(15).sum())
            main_power = (top_15_buy_vol - top_15_sell_vol) / daily_total_vol * 100
        
        diag = []
        if firepower >= fire_thresh and concentration > 5: diag.append(f"大戶火力壓制 ({fire_thresh}倍↑)")
        elif firepower < 0.7 and diff_count > 50: diag.append("散戶進場 (主力倒貨)")
        elif active_count > 500 and firepower < 1.0: diag.append("籌碼極度發散 (熱門當沖雷區)")
            
        if main_power > 15: diag.append(f"主力重兵集結 (買力 {main_power:.1f}%)")
        elif main_power < -15: diag.append(f"大戶強力倒貨 (賣力 {abs(main_power):.1f}%)")
        
        if diff_count > 50 and main_power < 0: diag.append("散戶螞蟻搬象接刀")
            
        out.append({
            "日期": d, 
            "活躍家數": active_count, 
            "買賣家數差": diff_count, 
            "籌碼集中度(%)": round(concentration, 1), 
            "買方火力(倍)": round(firepower, 2), 
            "主力成交力(%)": round(main_power, 2), 
            "鷹眼診斷": " | ".join(diag) if diag else "中性換手"
        })
    return pd.DataFrame(out)

def process_v30_daily_tracking(df_branch_raw, intel_tags, df_price, df_branch_diff, actual_dates, fire_thresh, period_days=5):
    if not is_valid(df_branch_raw) or len(actual_dates) < period_days: return pd.DataFrame(), pd.DataFrame()
    out, audit_smart_money = [], []
    df_b = df_branch_raw[df_branch_raw['date'].isin(actual_dates[:period_days])]

    df_smart_all = df_b[df_b['is_smart']].groupby(['date', 'securities_trader', 'tag']).agg(
        bs=('buy','sum'), ss=('sell','sum'), buy_amt=('valid_buy_amt','sum'), sell_amt=('valid_sell_amt','sum')
    ).reset_index()
    
    df_smart_all['net_vol'] = ((df_smart_all['bs'] - df_smart_all['ss']) / 1000).round().astype(int)
    smart_dict = dict(tuple(df_smart_all.groupby('date'))) if not df_smart_all.empty else {}

    df_short_all = df_b[df_b['is_short']].groupby(['date', 'securities_trader']).agg(bs=('buy','sum'), ss=('sell','sum')).reset_index()
    df_short_all['net_vol'] = ((df_short_all['bs'] - df_short_all['ss']) / 1000).round().astype(int)
    short_dict = dict(tuple(df_short_all.groupby('date'))) if not df_short_all.empty else {}

    price_dict = df_price.set_index('日期').to_dict('index') if not df_price.empty else {}
    diff_dict = df_branch_diff.set_index('日期').to_dict('index') if not df_branch_diff.empty else {}
    
    for d in actual_dates[:period_days]:
        pr_row = price_dict.get(d, {})
        cp = pr_row.get('收盤價(元)', 0)
        op = pr_row.get('開盤價(元)', 0)
        hp = pr_row.get('最高價(元)', 0)
        lp = pr_row.get('最低價(元)', 0)
        sp_raw = pr_row.get('漲跌(元)', 0)
        
        try: sp_num = float(re.sub(r'[+,]', '', str(sp_raw)).strip())
        except: sp_num = 0.0
        
        diff_row = diff_dict.get(d, {})
        bsd = diff_row.get('買賣家數差', 0)
        firepower = diff_row.get('買方火力(倍)', 1.0)
        active_cnt = diff_row.get('活躍家數', 0)
        concentration = diff_row.get('籌碼集中度(%)', 0)
        eye_diag = diff_row.get('鷹眼診斷', "")

        smart_grouped = smart_dict.get(d, pd.DataFrame(columns=['securities_trader', 'tag', 'bs', 'ss', 'buy_amt', 'sell_amt', 'net_vol']))
        short_grouped = short_dict.get(d, pd.DataFrame(columns=['securities_trader', 'bs', 'ss', 'net_vol']))
        
        if d == actual_dates[0]:
            for r in smart_grouped.to_dict('records'):
                if r['net_vol'] != 0: audit_smart_money.append({"日期": d, "分點": r['securities_trader'], "標籤": r['tag'], "淨買超(張)": r['net_vol']})
        
        smart_net = smart_grouped['net_vol'].sum() if not smart_grouped.empty else 0
        short_trap = short_grouped[short_grouped['net_vol'] > 0]['net_vol'].sum() if not short_grouped.empty else 0
        
        total_n = 0
        if not smart_grouped.empty:
            s_ret_long = smart_grouped[smart_grouped['bs'] - smart_grouped['ss'] > 0]
            total_n = (s_ret_long['bs'] - s_ret_long['ss']).sum()
            total_net_amt = (s_ret_long['buy_amt'] - s_ret_long['sell_amt']).sum()
            smart_avg_cost = max(0.0, total_net_amt / total_n) if total_n > 0 else 0.0
        else: 
            smart_avg_cost = 0.0
            
        gap = cp - smart_avg_cost if smart_avg_cost > 0 and cp > 0 else 0
        
        adv = []
        if cp <= 0: adv.append("股價無紀錄或暫停交易")
        else:
            day_range = hp - lp
            lower_shadow = min(cp, op) - lp
            if day_range > 0 and (lower_shadow / day_range) > 0.5 and smart_net > 0: adv.append("探底洗盤成功，主力護盤")
            
            if smart_avg_cost == 0 and smart_net < 0: adv.append("[危險]主力零成本無本出貨中")
            elif smart_net > 300 and firepower > 1.5: adv.append("[重擊點火]大戶重力掃貨推升")
            elif smart_net > 50 and gap > 0: adv.append("主動鎖碼/強勢推升")
            elif smart_net > 50 and gap < 0: adv.append("大戶承接/弱勢護盤")
            elif smart_net < -100 and sp_num > 0: adv.append("拉高派發/撤退")
            elif smart_net < -100 and sp_num <= 0: adv.append("波段棄守/多殺多")
            
        if eye_diag and eye_diag != "中性換手": adv.append(eye_diag)
        elif not adv: adv.append("盤整/無明顯特徵")

        out.append({
            "日期": d, "收盤價(元)": cp if cp > 0 else "-", "漲跌(元)": sp_raw if cp > 0 else "-", "聰明錢淨流(張)": int(smart_net), 
            "大戶淨加權均價": round(smart_avg_cost, 2) if smart_avg_cost > 0 else ("0 (無本獲利)" if smart_avg_cost == 0 and total_n > 0 else "-"), 
            "均價落差": round(gap, 2) if smart_avg_cost > 0 and cp > 0 else "-", 
            "活躍家數": active_cnt, "買賣家數差": bsd, "籌碼集中度(%)": concentration,
            "買方火力(倍)": firepower, "潛在賣壓(張)": int(short_trap), "綜合診斷": " | ".join(adv)
        })
    return pd.DataFrame(out), pd.DataFrame(audit_smart_money).sort_values('淨買超(張)', ascending=False) if audit_smart_money else pd.DataFrame()

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
            elif len(n) > 1:
                u = int(n[-1])
                if u <= 999: res = "1-999股"
                elif u <= 5000: res = "1-5張"
                elif u <= 10000: res = "5-10張"
                elif u <= 15000: res = "10-15張"
                elif u <= 20000: res = "15-20張"
                elif u <= 30000: res = "20-30張"
                elif u <= 40000: res = "30-40張"
                elif u <= 50000: res = "40-50張"
                elif u <= 100000: res = "50-100張"
                elif u <= 200000: res = "100-200張"
                elif u <= 400000: res = "200-400張"
                elif u <= 600000: res = "400-600張"
                elif u <= 800000: res = "600-800張"
                elif u <= 1000000: res = "800-1000張"
                else: res = "1000張以上"
            else:
                v = int(n[0])
                if v <= 21:
                    if 1 <= v <= 14: res = _LEVEL_MAP.get(v, s)
                    elif v >= 15: res = "1000張以上"
                else:
                    if v >= 1000000: res = "1000張以上"
                    elif v >= 800000: res = "800-1000張"
                    elif v >= 600000: res = "600-800張"
                    elif v >= 400000: res = "400-600張"
                    elif v >= 200000: res = "200-400張"
                    elif v >= 100000: res = "100-200張"
                    elif v >= 5000:   res = "50-100張"
                    elif v >= 40000:  res = "40-50張"
                    elif v >= 30000:  res = "30-40張"
                    elif v >= 20000:  res = "20-30張"
                    elif v >= 15000:  res = "15-20張"
                    elif v >= 10000:  res = "10-15張"
                    elif v >= 5000:   res = "5-10張"
                    elif v >= 1000:   res = "1-5張"
                    else: res = "1-999股"
                
    _LEVEL_CLEAN_CACHE[s] = res
    return res

def process_tdcc(df):
    if not is_valid(df, ['HoldingSharesLevel']): 
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
    df = df[~df['HoldingSharesLevel'].astype(str).str.contains('差異數', na=False)].copy()
    df['LevelClean'] = df['HoldingSharesLevel'].apply(clean_level_by_math)
    
    if 'HoldingShares' in df.columns:
        df['unit'] = (safe_to_num(df['HoldingShares']) / 1000).round().astype(int)
    elif 'unit' in df.columns:
        df['unit'] = (safe_to_num(df['unit']) / 1000).round().astype(int)
    else:
        df['unit'] = 0

    if 'people' in df.columns:
        df['people'] = safe_to_num(df['people']).astype(int)
    else:
        df['people'] = 0

    dates = sorted(df['date'].unique(), reverse=True)[:15]
    df = df[df['date'].isin(dates)]
    df_levels = df[~df['LevelClean'].str.contains('合計|總計', na=False)]
    if not is_valid(df_levels): return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
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
    
    for l in lvls: df_w[f"{l}_張數"], df_w[f"{l}_人數"], df_w[f"{l}_比例(%)"] = p_u[l], p_p[l], (p_u[l] / df_t['總張數'].replace(0, np.nan) * 100).fillna(0).round(2)
    df_w = df_w.rename(columns={'date': '日期'}).sort_values('日期', ascending=False)
    df_unit = pd.merge(df_t[['date', '總張數']], p_u[['date']+lvls], on='date').rename(columns={'date': '日期'}).sort_values('日期', ascending=False)
    df_ppl = pd.merge(df_t[['date', '總人數(人)']], p_p[['date']+lvls], on='date').rename(columns={'date': '日期'}).sort_values('日期', ascending=False)
    return df_w, df_unit, df_ppl

def process_day_trading(df):
    if not is_valid(df): return pd.DataFrame()
    df_out = df.copy()
    if 'DayTradingVolume' in df_out.columns: df_out['當沖總張數'] = (safe_to_num(df_out['DayTradingVolume']) / 1000).round().astype(int)
    elif 'Volume' in df_out.columns: df_out['當沖總張數'] = (safe_to_num(df_out['Volume']) / 1000).round().astype(int)
    df_out = df_out.rename(columns={"date": "日期"})
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]
    
    cols = [c for c in ['日期', '當沖總張數'] if c in df_out.columns]
    return df_out[cols].tail(10).sort_values('日期', ascending=False)

def process_margin_and_lending(df_margin_raw, df_lending_raw):
    if not is_valid(df_margin_raw): return pd.DataFrame()
    df_m = df_margin_raw.copy()
    for c in ["MarginPurchaseBuy", "MarginPurchaseSell", "MarginPurchaseCashRepayment", "MarginPurchaseTodayBalance", "MarginPurchaseYesterdayBalance", "ShortSaleBuy", "ShortSaleSell", "ShortSaleCashRepayment", "ShortSaleTodayBalance", "OffsetLoanAndShort", "ShortSaleYesterdayBalance"]:
        if c in df_m.columns: df_m[c] = safe_to_num(df_m[c]).round().astype(int)
    df_out = df_m.rename(columns={
        "date": "日期", "MarginPurchaseBuy": "融資買進(萬元)", "MarginPurchaseSell": "融資賣出(萬元)", 
        "MarginPurchaseCashRepayment": "融資現償(萬元)", "MarginPurchaseTodayBalance": "融資餘額(萬元)", 
        "ShortSaleBuy": "融券買進(張)", "ShortSaleSell": "融券賣出(張)", 
        "ShortSaleTodayBalance": "融券餘額(張)", "OffsetLoanAndShort": "資券相抵(張)"
    })
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]
    
    if '融資餘額(萬元)' in df_out.columns and 'MarginPurchaseYesterdayBalance' in df_out.columns:
        prev_margin = safe_to_num(df_out['MarginPurchaseYesterdayBalance']).round().astype(int)
        df_out['融資增減(萬元)'] = df_out['融資餘額(萬元)'] - prev_margin
    if '融券餘額(張)' in df_out.columns and 'ShortSaleYesterdayBalance' in df_out.columns:
        prev_short = safe_to_num(df_out['ShortSaleYesterdayBalance']).round().astype(int)
        df_out['融券增減(張)'] = df_out['融券餘額(張)'] - prev_short
        
    df_out['本日借券成交(張)'] = 0
    if is_valid(df_lending_raw, ['date', 'volume']):
        df_l = df_lending_raw.copy()
        df_l['volume'] = safe_to_num(df_l['volume'])
        g_lending = df_l.groupby('date')['volume'].sum().reset_index()
        g_lending['本日借券成交(張)'] = (g_lending['volume'] / 1000).round().astype(int)
        df_out = pd.merge(df_out, g_lending[['date', '本日借券成交(張)']].rename(columns={'date':'日期'}), on='日期', how='left').fillna(0)
    
    cols = [c for c in ['日期','融資買進(萬元)','融資賣出(萬元)','融資現償(萬元)','融資餘額(萬元)','融資增減(萬元)','融券買進(張)','融券賣出(張)','融券餘額(張)','融券增減(張)','資券相抵(張)','本日借券成交(張)'] if c in df_out.columns]
    return df_out[cols].tail(10).sort_values('日期', ascending=False)

def process_securities_lending_detail(df):
    if not is_valid(df, ['date', 'volume']): return pd.DataFrame()
    df_out = df.copy()
    df_out['volume'] = (safe_to_num(df_out['volume']) / 1000).round().astype(int)
    
    if 'fee_rate' in df_out.columns: df_out['fee_rate'] = safe_to_num(df_out['fee_rate'])
    else: df_out['fee_rate'] = 0.0
        
    if 'transaction_type' not in df_out.columns: df_out['transaction_type'] = '未知'
        
    pivot_df = df_out.pivot_table(index='date', columns='transaction_type', values='volume', aggfunc='sum', fill_value=0)
    daily_stats = df_out.groupby('date').agg(總成交張數=('volume', 'sum'), 平均費率=('fee_rate', 'mean'))
    
    res = daily_stats.join(pivot_df).reset_index().rename(columns={'date': '日期', '平均費率': '平均費率(%)'}).fillna(0)
    res['平均費率(%)'] = res['平均費率(%)'].round(2)
    
    col_map = {'定價': '定價交易(張)', '競價': '競價交易(張)', '議借': '議借交易(張)'}
    res = res.rename(columns=col_map)
    for c in ['定價交易(張)', '競價交易(張)', '議借交易(張)']:
        if c not in res.columns: res[c] = 0
        
    cols = ['日期', '總成交張數', '平均費率(%)', '定價交易(張)', '競價交易(張)', '議借交易(張)']
    return res[[c for c in cols if c in res.columns]].tail(10).sort_values('日期', ascending=False)

def process_block_trading(df_block_raw, rank_dates):
    if not is_valid(df_block_raw, ['date']): return pd.DataFrame()
    target_dates = rank_dates[:5]
    df_b = df_block_raw[df_block_raw['date'].isin(target_dates)].copy()
    if df_b.empty: return pd.DataFrame()
    
    df_b = df_b.rename(columns={
        "date": "日期", "trade_type": "交易類別", "price": "成交價(元)", "volume": "成交張數", "trading_money": "成交金額(萬元)"
    })
    
    if '成交張數' in df_b.columns: df_b['成交張數'] = (safe_to_num(df_b['成交張數']) / 1000).round().astype(int)
    if '成交金額(萬元)' in df_b.columns: df_b['成交金額(萬元)'] = (safe_to_num(df_b['成交金額(萬元)']) / 10000).round().astype(int)
    
    cols = [c for c in ['日期', '交易類別', '成交價(元)', '成交張數', '成交金額(萬元)'] if c in df_b.columns]
    return df_b[cols].sort_values(['日期', '成交金額(萬元)'], ascending=[False, False])

def process_inst(df):
    if not is_valid(df): return pd.DataFrame()
    pdf = df.pivot_table(index='date', columns='name', values=['buy', 'sell'], fill_value=0).reset_index()
    pdf.columns = ['_'.join(c).strip('_') for c in pdf.columns.values]
    out = pd.DataFrame({'日期': pdf['date']})
    length = len(pdf)
    f_b = safe_to_num(pdf.get('buy_Foreign_Investor', pd.Series([0]*length)))
    f_s = safe_to_num(pdf.get('sell_Foreign_Investor', pd.Series([0]*length)))
    out['外資買賣超(張)'] = ((f_b - f_s) / 1000).round().astype(int)
    i_b = safe_to_num(pdf.get('buy_Investment_Trust', pd.Series([0]*length)))
    i_s = safe_to_num(pdf.get('sell_Investment_Trust', pd.Series([0]*length)))
    out['投信買賣超(張)'] = ((i_b - i_s) / 1000).round().astype(int)
    ds_b = safe_to_num(pdf.get('buy_Dealer_self', pdf.get('buy_Dealer', pd.Series([0]*length))))
    ds_s = safe_to_num(pdf.get('sell_Dealer_self', pdf.get('sell_Dealer', pd.Series([0]*length))))
    out['自營商(自行)買賣超(張)'] = ((ds_b - ds_s) / 1000).round().astype(int)
    dh_b = safe_to_num(pdf.get('buy_Dealer_Hedging', pd.Series([0]*length)))
    dh_s = safe_to_num(pdf.get('sell_Dealer_Hedging', pd.Series([0]*length)))
    out['自營商(避險)買賣超(張)'] = ((dh_b - dh_s) / 1000).round().astype(int)
    out['三大法人買賣超(張)'] = out['外資買賣超(張)'] + out['投信買賣超(張)'] + out['自營商(自行)買賣超(張)'] + out['自營商(避險)買賣超(張)']
    return out.tail(10).sort_values('日期', ascending=False)

def process_fut_inst(df):
    if not is_valid(df): return pd.DataFrame()
    df['net'] = safe_to_num(df['long_open_interest_balance_volume']) - safe_to_num(df['short_open_interest_balance_volume'])
    
    group_col = 'name' if 'name' in df.columns else 'institutional_investors'
    if group_col not in df.columns: return pd.DataFrame()
    
    pdf = df.pivot_table(index='date', columns=group_col, values='net', fill_value=0).reset_index()
    pdf.columns.name = None
    
    col_map = {'date': '日期'}
    for c in pdf.columns:
        if '外資' in str(c) or 'Foreign' in str(c): col_map[c] = '外資多空(口)'
        elif '投信' in str(c) or 'Investment' in str(c): col_map[c] = '投信多空(口)'
        elif '自營' in str(c) or 'Dealer' in str(c): col_map[c] = '自營多空(口)'
        
    pdf = pdf.rename(columns=col_map)
    
    for col in ['外資多空(口)', '投信多空(口)', '自營多空(口)']:
        if col not in pdf.columns: pdf[col] = 0
        
    cols = ['日期', '外資多空(口)', '投信多空(口)', '自營多空(口)']
    return pdf[cols].tail(10).sort_values('日期', ascending=False)

def process_per(df):
    if not is_valid(df): return pd.DataFrame()
    df_out = df.copy().rename(columns={"date":"日期","dividend_yield":"殖利率(%)","PER":"本益比(倍)","PBR":"淨值比(倍)"})
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]
    for col in ["殖利率(%)", "本益比(倍)", "淨值比(倍)"]: 
        if col in df_out.columns: df_out[col] = safe_to_num(df_out[col]).round(2)
    cols = [c for c in ['日期', '本益比(倍)', '淨值比(倍)', '殖利率(%)'] if c in df_out.columns]
    return df_out[cols].tail(10).sort_values('日期', ascending=False)

def process_disp(df):
    if not is_valid(df): return pd.DataFrame()
    df_out = df.copy().rename(columns={"date":"公告日期","disposition_cnt":"處置次數","condition":"處置條件","measure":"處置措施","period_start":"處置起日","period_end":"處置迄日"})
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]
    cols = [c for c in ['公告日期', '處置次數', '處置起日', '處置迄日', '處置條件', '處置措施'] if c in df_out.columns]
    return df_out[cols].tail(5).sort_values('公告日期', ascending=False)

def process_div(df):
    if not is_valid(df): return pd.DataFrame()
    df_out = df.rename(columns={"date": "公告日期", "year": "股利年份", "StockEarningsDistribution": "盈餘配股(元)", "StockStatutorySurplus": "公積配股(元)", "CashEarningsDistribution": "盈餘配息(元)", "CashStatutorySurplus": "公積配息(元)"})
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]
    cols = [c for c in ["公告日期", "股利年份", "盈餘配息(元)", "公積配息(元)", "盈餘配股(元)", "公積配股(元)"] if c in df_out.columns]
    if '股利年份' in df_out.columns:
        valid_year_mask = df_out['股利年份'].notna() & (~df_out['股利年份'].astype(str).str.lower().isin(['nan', '<na>', 'none', '']))
        extracted_year = pd.Series(index=df_out.index, dtype='object', name='股利年份')
        extracted_year[valid_year_mask] = df_out.loc[valid_year_mask, '股利年份'].astype(str).str.extract(r'^(\d+)', expand=False)
        
        year_num = safe_to_num(extracted_year, fill_val=np.nan)
        recent = sorted(year_num.dropna().unique(), reverse=True)[:5]
        return df_out[year_num.isin(recent)][cols].sort_values('公告日期', ascending=False).head(10)
    return df_out[cols].sort_values('公告日期', ascending=False).head(10)

def process_cbas(df, current_stock_price, df_cb_info=None):
    if not is_valid(df): return pd.DataFrame()
    df_out = df.copy().rename(columns={"date": "日期", "cb_id": "可轉債代號", "cb_name": "可轉債名稱", "conversion_price": "轉換價(元)", "ConversionPrice": "轉換價(元)", "underlying_stock_price": "標的股價(元)", "PriceOfUnderlyingStock": "標的股價(元)", "outstanding_amount": "未償還餘額", "OutstandingAmount": "未償還餘額", "outstanding_balance": "未償還餘額", "close": "CB收盤價", "closing_price": "CB收盤價", "conversion_premium_rate": "溢價率(%)", "premium_rate": "溢價率(%)", "PremiumRate": "溢價率(%)", "theoretical_value": "轉換價值", "TheoreticalValue": "轉換價值"})
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]
    
    if "可轉債代號" in df_out.columns: df_out['可轉債代號'] = df_out['可轉債代號'].astype(str).str.replace(r'(\.0$|,)', '', regex=True).str.strip()
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
        df_cb_info_clean = df_cb_info_clean.loc[:, ~df_cb_info_clean.columns.duplicated()]
        if "可轉債代號" in df_cb_info_clean.columns:
            df_cb_info_clean['可轉債代號'] = df_cb_info_clean['可轉債代號'].astype(str).str.replace(r'(\.0$|,)', '', regex=True).str.strip()
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

def process_technical_analysis(df_price, s_ma, m_ma, l_ma):
    try:
        if not is_valid(df_price, ['收盤價(元)', '日期'], 30): return pd.DataFrame()
        
        s_ma, m_ma, l_ma = int(s_ma), int(m_ma), int(l_ma) 
        df_ta = df_price.sort_values('日期', ascending=True).copy()
        
        df_ta['收盤價(元)'] = pd.to_numeric(df_ta['收盤價(元)'], errors='coerce').astype('float64')
        
        df_ta[f'MA{s_ma}'] = df_ta['收盤價(元)'].rolling(window=s_ma, min_periods=1).mean().round(2)
        df_ta[f'MA{m_ma}(中線)'] = df_ta['收盤價(元)'].rolling(window=m_ma, min_periods=1).mean().round(2)
        df_ta[f'MA{l_ma}(長線)'] = df_ta['收盤價(元)'].rolling(window=l_ma, min_periods=1).mean().round(2)
        
        df_ta['中線乖離(%)'] = ((df_ta['收盤價(元)'] - df_ta[f'MA{m_ma}(中線)']) / df_ta[f'MA{m_ma}(中線)'].replace(0, np.nan) * 100).round(2)
        cond_up = df_ta['收盤價(元)'] > df_ta[f'MA{m_ma}(中線)']
        cond_down = df_ta['收盤價(元)'] < df_ta[f'MA{m_ma}(中線)']
        df_ta['技術面診斷'] = np.select([cond_up, cond_down], ["站上中線防守", "跌破中線防守"], default="盤整")
        
        return df_ta.sort_values('日期', ascending=False)
    except Exception:
        return pd.DataFrame()

def process_linear_regression(df_price, lr_days):
    try:
        if not is_valid(df_price, ['收盤價(元)'], 2): return pd.DataFrame()
        df_lr = df_price.head(lr_days).sort_values('日期', ascending=True).copy()
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
    except Exception:
        return pd.DataFrame()

def process_geometric_patterns(df_price, kline_days, order, mode, current_price):
    try:
        if not is_valid(df_price, min_len=order * 2): return {}
        df = df_price.head(kline_days).sort_values('日期', ascending=True).reset_index(drop=True)
        
        lows_vals = df['最低價(元)'].values
        highs_vals = df['最高價(元)'].values
        dates_vals = df['日期'].values
        
        highs, lows = [], []
        for i in range(order, len(df) - order):
            if lows_vals[i] == np.min(lows_vals[i-order:i+order+1]):
                lows.append((dates_vals[i], float(lows_vals[i]), i))
            if highs_vals[i] == np.max(highs_vals[i-order:i+order+1]):
                highs.append((dates_vals[i], float(highs_vals[i]), i))
                
        if len(lows) < 2 or len(highs) < 2: return {}

        last_date = dates_vals[-1]
        tol = 0.03
        is_auto = "Auto" in mode
        
        if "三重底" in mode or is_auto:
            if len(lows) >= 3:
                l1, l2, l3 = lows[-3], lows[-2], lows[-1]
                if l1[1] > 0 and l2[1] > 0 and abs(l1[1]-l2[1])/l1[1] < tol and abs(l2[1]-l3[1])/l2[1] < tol:
                    b_h = [h for h in highs if l1[2] < h[2] < l3[2]]
                    if b_h:
                        h_max = max(b_h, key=lambda x: x[1])
                        status = "已突破頸線" if current_price > h_max[1] else "成型中"
                        return {
                            'name': '三重底', 'shape_x': [l1[0], b_h[0][0], l2[0], b_h[-1][0], l3[0]], 'shape_y': [l1[1], b_h[0][1], l2[1], b_h[-1][1], l3[1]],
                            'neck_x': [l1[0], last_date], 'neck_y': [h_max[1], h_max[1]], 'color': '#9c27b0', 'desc': f"三重底 ({status})", 'signal': 'bullish'
                        }
        
        if "三重頂" in mode or is_auto:
            if len(highs) >= 3:
                h1, h2, h3 = highs[-3], highs[-2], highs[-1]
                if h1[1] > 0 and h2[1] > 0 and abs(h1[1]-h2[1])/h1[1] < tol and abs(h2[1]-h3[1])/h2[1] < tol:
                    b_l = [l for l in lows if h1[2] < l[2] < h3[2]]
                    if b_l:
                        l_min = min(b_l, key=lambda x: x[1])
                        status = "已跌破頸線" if current_price < l_min[1] else "成型中"
                        return {
                            'name': '三重頂', 'shape_x': [h1[0], b_l[0][0], h2[0], b_l[-1][0], h3[0]], 'shape_y': [h1[1], b_l[0][1], h2[1], b_l[-1][1], h3[1]],
                            'neck_x': [h1[0], last_date], 'neck_y': [l_min[1], l_min[1]], 'color': '#d32f2f', 'desc': f"三重頂 ({status})", 'signal': 'bearish'
                        }

        if "頭肩底" in mode or is_auto:
            if len(lows) >= 3:
                l1, l2, l3 = lows[-3], lows[-2], lows[-1]
                if l1[1] > 0 and l2[1] < l1[1] and l2[1] < l3[1] and abs(l1[1]-l3[1])/l1[1] < 0.05: 
                    b_h1 = [h for h in highs if l1[2] < l[2] < h2[2]]
                    b_h2 = [h for h in highs if l2[2] < h[2] < l3[2]]
                    if b_h1 and b_h2:
                        h1, h2 = max(b_h1, key=lambda x: x[1]), max(b_h2, key=lambda x: x[1])
                        status = "已突破頸線" if current_price > max(h1[1], h2[1]) else "打右肩中"
                        return {
                            'name': '頭肩底', 'shape_x': [l1[0], h1[0], l2[0], h2[0], l3[0]], 'shape_y': [l1[1], h1[1], l2[1], h2[1], l3[1]],
                            'neck_x': [l1[0], last_date], 'neck_y': [h1[1], h2[1]], 'color': '#e91e63', 'desc': f"頭肩底 ({status})", 'signal': 'bullish'
                        }
                        
        if "頭肩頂" in mode or is_auto:
            if len(highs) >= 3:
                h1, h2, h3 = highs[-3], highs[-2], highs[-1]
                if h1[1] > 0 and h2[1] > h1[1] and h2[1] > h3[1] and abs(h1[1]-h3[1])/h1[1] < 0.05: 
                    b_l1 = [l for l in lows if h1[2] < l[2] < h2[2]]
                    b_l2 = [l for l in lows if h2[2] < l[2] < h3[2]]
                    if b_l1 and b_l2:
                        l1, l2 = min(b_l1, key=lambda x: x[1]), min(b_l2, key=lambda x: x[1])
                        status = "已跌破頸線" if current_price < min(l1[1], l2[1]) else "做右肩中"
                        return {
                            'name': '頭肩頂', 'shape_x': [h1[0], l1[0], h2[0], l2[0], h3[0]], 'shape_y': [h1[1], l1[1], h2[1], l2[1], h3[1]],
                            'neck_x': [l1[0], last_date], 'neck_y': [l1[1], l2[1]], 'color': '#d32f2f', 'desc': f"頭肩頂 ({status})", 'signal': 'bearish'
                        }

        if "W底" in mode or is_auto:
            if len(lows) >= 2:
                l1, l2 = lows[-2], lows[-1]
                between_highs = [h for h in highs if l1[2] < h[2] < l2[2]]
                if between_highs and l1[1] > 0:
                    h1 = max(between_highs, key=lambda x: x[1])
                    diff = abs(l1[1] - l2[1]) / l1[1]
                    if diff <= tol or "W底" in mode:
                        status = "已突破頸線" if current_price > h1[1] else "成型中"
                        desc = f"標準 W底 ({status})" if diff <= tol else f"強制標示 W底 ({status})"
                        return {
                            'name': 'W底', 'shape_x': [l1[0], h1[0], l2[0]], 'shape_y': [l1[1], h1[1], l2[1]],
                            'neck_x': [l1[0], last_date], 'neck_y': [h1[1], h1[1]], 'color': '#9c27b0', 'desc': desc, 'signal': 'bullish'
                        }

        if "M頭" in mode or is_auto:
            if len(highs) >= 2:
                h1, h2 = highs[-2], highs[-1]
                between_lows = [l for l in lows if h1[2] < l[2] < h2[2]]
                if between_lows and h1[1] > 0:
                    l1 = min(between_lows, key=lambda x: x[1])
                    diff = abs(h1[1] - h2[1]) / h1[1]
                    if diff <= tol or "M頭" in mode:
                        status = "已跌破頸線" if current_price < l1[1] else "成型中"
                        desc = f"標準 M頭 ({status})" if diff <= tol else f"強制標示 M頭 ({status})"
                        return {
                            'name': 'M頭', 'shape_x': [h1[0], l1[0], h2[0]], 'shape_y': [h1[1], l1[1], h2[1]],
                            'neck_x': [h1[0], last_date], 'neck_y': [l1[1], l1[1]], 'color': '#d32f2f', 'desc': desc, 'signal': 'bearish'
                        }

        if any(k in mode for k in ["連續", "三角形", "楔形", "矩形"]) or is_auto:
            if len(highs) >= 2 and len(lows) >= 2:
                h1, h2 = highs[-2], highs[-1]
                l1, l2 = lows[-2], lows[-1]
                h_diff = (h2[1] - h1[1]) / h1[1] if h1[1] > 0 else 0
                l_diff = (l2[1] - l1[1]) / l1[1] if l1[1] > 0 else 0
                p_name, p_color, p_desc, p_sig = "", "", "", "neutral"
                if abs(h_diff) < tol and abs(l_diff) < tol and ("矩形" in mode or is_auto):
                    p_name, p_color, p_desc = "箱型矩形", "#2196f3", "矩形整理 (等待突破)"
                elif abs(h_diff) < tol and l_diff > tol and ("上升三角形" in mode or is_auto):
                    p_name, p_color, p_desc, p_sig = "上升三角形", "#4caf50", "上升三角形 (偏多醞釀)", "bullish"
                elif h_diff < -tol and abs(l_diff) < tol and ("下降三角形" in mode or is_auto):
                    p_name, p_color, p_desc, p_sig = "下降三角形", "#f44336", "下降三角形 (偏空醞釀)", "bearish"
                elif h_diff < -tol and l_diff > tol and ("對稱" in mode or "收斂" in mode or is_auto):
                    p_name, p_color, p_desc = "對稱三角形", "#ff9800", "對稱三角形 (收斂表態前)"
                elif h_diff > tol and l_diff > tol and l_diff > h_diff and ("上升楔形" in mode or is_auto):
                    p_name, p_color, p_desc, p_sig = "上升楔形", "#ff5722", "上升楔形 (上漲力道衰退，偏空)", "bearish"
                elif h_diff < -tol and l_diff < -tol and h_diff < l_diff and ("下降楔形" in mode or is_auto):
                    p_name, p_color, p_desc, p_sig = "下降楔形", "#8bc34a", "下降楔形 (殺跌力道衰退，偏多)", "bullish"
                if p_name or not is_auto:
                    if not p_name: p_name, p_color, p_desc = mode.split('：')[-1].strip(), "#999", f"強制標示 {mode.split('：')[-1]}"
                    return {'name': p_name, 'shape_x': [h1[0], h2[0]], 'shape_y': [h1[1], h2[1]], 'neck_x': [l1[0], l2[0]], 'neck_y': [l1[1], l2[1]], 'color': p_color, 'desc': p_desc, 'signal': p_sig}
                    
        if "V型反轉" in mode or is_auto:
            if len(lows) >= 1 and len(highs) >= 2:
                l1 = lows[-1]
                h_before = [h for h in highs if h[2] < l1[2]] 
                h_after = [h for h in highs if h[2] > l1[2]]
                if h_before and h_after and l1[1] > 0:
                    hb, ha = h_before[-1], h_after[0]
                    if (hb[1]-l1[1])/l1[1] > 0.1 and (ha[1]-l1[1])/l1[1] > 0.1: 
                        status = "已突破下降趨勢" if current_price > ha[1] else "反轉進行中"
                        return {
                            'name': 'V型反轉', 
                            'shape_x': [hb[0], l1[0], ha[0]], 
                            'shape_y': [hb[1], l1[1], ha[1]], 
                            'neck_x': [hb[0], ha[0]], 
                            'neck_y': [hb[1], ha[1]], 
                            'color': '#00bcd4', 
                            'desc': f"深V反轉 ({status})", 
                            'signal': 'bullish'
                        }
        return {}
    except Exception:
        return {}

def render_clean_html_table(df, title=""):
    if not is_valid(df):
        if title: st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
        st.warning("此區塊查無資料。")
        return
        
    text_keywords = {'日期', '分點', '標籤', '週期', '名稱', '姓名', '身份別', '條件', '措施', '診斷', '代號', '類別'}
    cols = df.columns.tolist()
    align_classes = ["text-left" if any(k in str(col) for k in text_keywords) else "text-right" for col in cols]
    
    html_parts = []
    if title: 
        html_parts.append(f"<div class='section-title'>{title}</div>")
        
    html_parts.append("<div class='table-container'><table><thead><tr>")
    html_parts.extend([f"<th>{col}</th>" for col in cols])
    html_parts.append("</tr></thead><tbody>")
    
    for row in df.itertuples(index=False):
        html_parts.append("<tr>")
        for i, val in enumerate(row):
            align_class = align_classes[i]
            display_val = "-"
            
            if pd.notna(val):
                s = str(val).strip()
                if s and s.lower() != "nan":
                    if "無本獲利" in s:
                        display_val = f"<span class='profit-warning'>{s}</span>"
                    elif "(虧)" in s:
                        display_val = f"<span class='loss-warning'>(虧) {s.replace('(虧)', '').strip()}</span>"
                    elif s.startswith("+"):
                        display_val = f"<span class='highlight-red'>{s}</span>"
                    elif s.startswith("-") and len(s) > 1 and s[1].isdigit():
                        try:
                            f_val = float(s.replace(',', ''))
                            formatted_s = f"{f_val:,.2f}" if "." in s else f"{int(f_val):,}"
                            display_val = f"<span class='highlight-green'>{formatted_s}</span>"
                        except:
                            display_val = f"<span class='highlight-green'>{s}</span>"
                    else:
                        if "%" in s: display_val = s
                        else:
                            try:
                                f_val = float(s.replace(',', ''))
                                display_val = f"{f_val:,.2f}" if "." in s else f"{int(f_val):,}"
                            except: display_val = s
            html_parts.append(f"<td class='{align_class}'>{display_val}</td>")
        html_parts.append("</tr>")
        
    html_parts.append("</tbody></table></div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)

def render_tdcc_table_with_color(df, title=""):
    """專屬集保表渲染器：維持原始數據，依據前一週的增減變換字體紅綠色"""
    if not is_valid(df):
        if title: st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
        st.warning("此區塊查無資料。")
        return
        
    df_work = df.copy()
    df_work = df_work.sort_values('日期', ascending=False).reset_index(drop=True)
    cols = df_work.columns.tolist()
    
    html_parts = []
    if title: 
        html_parts.append(f"<div class='section-title'>{title}</div>")
        
    html_parts.append("<div class='table-container'><table><thead><tr>")
    for col in cols:
        align = "left" if col == '日期' else "right"
        html_parts.append(f"<th style='text-align: {align};'>{col}</th>")
    html_parts.append("</tr></thead><tbody>")
    
    for i in range(len(df_work)):
        html_parts.append("<tr>")
        for col in cols:
            val = df_work.at[i, col]
            
            if pd.isna(val):
                html_parts.append("<td class='text-right'>-</td>")
                continue
                
            if col == '日期':
                html_parts.append(f"<td class='text-left' style='font-weight: bold;'>{val}</td>")
            else:
                try:
                    curr_val = float(val)
                    display_str = f"{int(curr_val):,}" if curr_val == int(curr_val) else f"{curr_val:,.2f}"
                    
                    if i < len(df_work) - 1:
                        prev_val = float(df_work.at[i+1, col])
                        if curr_val > prev_val:
                            display_html = f"<span style='color: #d32f2f; font-weight: bold;'>{display_str}</span>"
                            bg_style = "background-color: rgba(229, 57, 53, 0.08);"
                        elif curr_val < prev_val:
                            display_html = f"<span style='color: #2e7d32; font-weight: bold;'>{display_str}</span>"
                            bg_style = "background-color: rgba(67, 160, 71, 0.08);"
                        else:
                            display_html = display_str
                            bg_style = ""
                    else:
                        display_html = display_str
                        bg_style = ""
                        
                    html_parts.append(f"<td class='text-right' style='{bg_style}'>{display_html}</td>")
                except:
                    html_parts.append(f"<td class='text-right'>{val}</td>")
        html_parts.append("</tr>")
        
    html_parts.append("</tbody></table></div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)

def format_to_csv_string(df, title):
    header = f"▼▼▼ {title} ▼▼▼\n"
    if not is_valid(df): return header + "此區塊查無資料或無發行紀錄\n"
    return header + df.to_csv(index=False) + "\n"

def render_ultimate_heatmap(df_raw, display_dates, rank_dates, intel_tags, df_fingerprint, top_n, noise_threshold):
    """
    終極全息熱力圖：橫軸為 display_dates，排行基準為 rank_dates
    """
    if not is_valid(df_raw) or not display_dates or not rank_dates:
        st.warning("查無足夠資料產生熱力圖。")
        return

    # 1. 根據「排行區間 (rank_dates)」計算總量，用來決定誰是買/賣超前 N 名
    df_rank = df_raw[df_raw['date'].isin(rank_dates)].copy()
    df_rank['net_shares'] = df_rank['buy'] - df_rank['sell']
    rank_sum = (df_rank.groupby('securities_trader')['net_shares'].sum() / 1000).round().astype(int)

    top_b = rank_sum[rank_sum > 0].nlargest(top_n).index.tolist()
    top_s = rank_sum[rank_sum < 0].nsmallest(top_n).index.tolist()
    
    if not top_b and not top_s:
        st.warning("無符合條件的活躍分點。")
        return

    # 2. 準備「戰鬥足跡 (display_dates)」的每日數據
    df_disp = df_raw[df_raw['date'].isin(display_dates)].copy()
    df_disp['net_shares'] = df_disp['buy'] - df_disp['sell']
    p_shares = df_disp.groupby(['securities_trader', 'date'])['net_shares'].sum().reset_index()
    p_shares['net'] = (p_shares['net_shares'] / 1000).round().astype(int)
    p = p_shares.pivot(index='securities_trader', columns='date', values='net').fillna(0).astype(int)
    
    target_traders = top_b + top_s
    # 重新對齊：確保橫軸與縱軸一致
    p = p.reindex(index=target_traders, columns=display_dates, fill_value=0)

    max_val = p.abs().max().max()
    if max_val == 0: max_val = 1

    fp_dict = {}
    if not df_fingerprint.empty:
        fp_dict = df_fingerprint.set_index('分點名稱')[['黏著度(%)', '囤出貨率(%)']].to_dict('index')

    html_parts = [HEATMAP_STYLE_TEMPLATE + "<div class='full-table-container heatmap-wrapper'><table><thead><tr>"]
    
    html_parts.append("<th style='min-width: 140px; position: sticky; left: 0; z-index: 6;'>分點名稱</th>")
    html_parts.append("<th style='min-width: 90px;'>標籤</th>")
    html_parts.append("<th style='min-width: 80px;'>黏著度</th>")
    html_parts.append("<th style='min-width: 90px;'>囤/出貨率</th>")
    html_parts.append("<th style='min-width: 90px; background-color: #fff9c4;'>選定區間累計</th>")
    for d in display_dates:
        html_parts.append(f"<th style='text-align: center; font-size: 13px; min-width: 50px;'>{d[5:]}</th>")
    html_parts.append("</tr></thead><tbody>")

    def build_rows(traders, is_sell_side):
        if not traders: return
        
        sec_title = "🟢 賣超主力陣營 (依選定區間排序)" if is_sell_side else "🔴 買超主力陣營 (依選定區間排序)"
        sec_color = "#4caf50" if is_sell_side else "#f44336"
        html_parts.append(f"<tr><td colspan='{5 + len(display_dates)}' style='background-color: #f1f3f5; color: {sec_color}; font-weight: 900; text-align: center !important; font-size: 1.1rem; letter-spacing: 2px;'>{sec_title}</td></tr>")

        for trader in traders:
            html_parts.append("<tr>")
            tag = intel_tags.get(trader, "路人雜訊")
            
            st_val = fp_dict.get(trader, {}).get('黏著度(%)', "-")
            hr_val = fp_dict.get(trader, {}).get('囤出貨率(%)', "-")
            total_val = rank_sum.get(trader, 0)
            
            total_str = f"<span style='color:#d32f2f; font-weight:bold;'>+{total_val}</span>" if total_val > 0 else f"<span style='color:#2e7d32; font-weight:bold;'>{total_val}</span>"
            
            html_parts.append(f"<td style='position: sticky; left: 0; background-color: #f8f9fa; z-index: 4; font-weight: bold;'>{trader}</td>")
            html_parts.append(f"<td style='text-align: center;'>{tag}</td>")
            html_parts.append(f"<td style='text-align: right;'>{st_val}%</td>")
            html_parts.append(f"<td style='text-align: right;'>{hr_val}%</td>")
            html_parts.append(f"<td style='text-align: right; background-color: #fffde7;'>{total_str}</td>")

            for d in display_dates:
                val = p.at[trader, d]
                is_noise = abs(val) < noise_threshold
                alpha = min(1.0, 0.2 + 0.8 * (abs(val) / max_val)) if max_val > 0 else 0.2
                
                if val > 0:
                    bg = f"rgba(229, 57, 53, {alpha:.2f})"
                    txt = f"+{val}"
                    txt_color = "#fff"
                    zero_class = ""
                elif val < 0:
                    bg = f"rgba(67, 160, 71, {alpha:.2f})"
                    txt = str(val)
                    txt_color = "#fff"
                    zero_class = ""
                else:
                    bg = "transparent"
                    txt = "0"
                    txt_color = "#aaa"
                    zero_class = "val-zero"
                    is_noise = True 

                cell_class = f"noise-cell {zero_class}".strip() if is_noise else ""
                cell_style = f"--bg-color: {bg}; --txt-color: {txt_color}; text-align: center; font-weight: bold; "
                if not is_noise:
                    cell_style += f"background-color: {bg}; color: {txt_color} !important; text-shadow: 1px 1px 2px rgba(0,0,0,0.6);"
                else:
                    cell_style += "background-color: transparent;"

                tooltip = f"日期: {d} | 分點: {trader} | 淨額: {val} 張"
                html_parts.append(f"<td class='{cell_class}' style='{cell_style}' title='{tooltip}'><span>{txt}</span></td>")
            html_parts.append("</tr>")

    build_rows(top_b, False)
    build_rows(top_s, True)
    
    html_parts.append("</tbody></table></div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)

# ==========================================
# 執行主引擎
# ==========================================
if run_btn:
    if not user_stock_id.strip(): 
        st.warning("請先在上方輸入股票代號！")
        st.stop()

    with st.spinner(f"正在啟動 V75.9 終極版決策引擎..."):
        
        name, industry = get_basic_info_finmind(user_stock_id)
        if name == "未知名稱": 
            st.error(f"查無股票代號 {user_stock_id} 的基本資料。")
            st.stop()
            
        df_p_raw = fetch_finmind_v50("TaiwanStockPrice", (datetime.date.today() - datetime.timedelta(days=700)).strftime("%Y-%m-%d"), user_stock_id)
        if not is_valid(df_p_raw, ['date']): 
            st.error("查無歷史股價資料。")
            st.stop()
        
        valid_dates = df_p_raw['date'].dropna().astype(str)
        dates = sorted(valid_dates[valid_dates != ""].unique().tolist(), reverse=True)
        if not dates: st.stop()
            
        max_len = lookback_days if len(dates) >= lookback_days else len(dates)
        if max_len == 0: max_len = 1
        
        df_price = optimize_memory(process_price(df_p_raw))
        curr_price = round(float(df_price['收盤價(元)'].iloc[0]), 2) if is_valid(df_price, ['收盤價(元)']) else 0
        df_ta_full = process_technical_analysis(df_price, ma_short, ma_mid, ma_long)
        
        recent_20_vol = df_price['成交量(張)'].head(20).mean() if is_valid(df_price) else 1000
        dynamic_noise_threshold = int(recent_20_vol * (heatmap_noise_pct / 100.0))
        dynamic_alert_threshold = int(recent_20_vol * (alert_smart_pct / 100.0))

        df_lr_channel = process_linear_regression(df_price, lr_days)
        latest_lr_upper = df_lr_channel['LR_Upper'].iloc[-1] if is_valid(df_lr_channel) else 0.0
        latest_lr_mid = df_lr_channel['LR_Mid'].iloc[-1] if is_valid(df_lr_channel) else 0.0
        latest_lr_lower = df_lr_channel['LR_Lower'].iloc[-1] if is_valid(df_lr_channel) else 0.0
        
        pat_data = {}
        if enable_pattern:
            pat_data = process_geometric_patterns(df_price, kline_days, pattern_order, pattern_mode, curr_price)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as bg_executor:
            f_dir = bg_executor.submit(scrape_director_v50, user_stock_id)
            f_ple = bg_executor.submit(scrape_fubon_pledge, df_p_raw, user_stock_id)
            df_b_raw, ds_dict, df_cb_info = fetch_heavy_data_sync_with_progress(user_stock_id, tuple(dates), max_len)
            dynamic_dict, s_val, chip_eng, _ = f_dir.result()
            df_p_sum, df_p_det = f_ple.result()

        if not is_valid(df_b_raw):
            st.error(f"查無 {user_stock_id} 的分點進出資料。")
            st.stop()
            
        df_b_raw['price'] = safe_to_num(df_b_raw['price'])
        df_b_raw['buy'] = safe_to_num(df_b_raw['buy'])
        df_b_raw['sell'] = safe_to_num(df_b_raw['sell'])
        df_b_raw['valid_buy'] = np.where(df_b_raw['price'] > 0, df_b_raw['buy'], 0)
        df_b_raw['valid_sell'] = np.where(df_b_raw['price'] > 0, df_b_raw['sell'], 0)
        df_b_raw['valid_buy_amt'] = df_b_raw['valid_buy'] * df_b_raw['price']
        df_b_raw['valid_sell_amt'] = df_b_raw['valid_sell'] * df_b_raw['price']
        df_b_raw['net_shares'] = df_b_raw['buy'] - df_b_raw['sell']
        df_b_raw['date_dt'] = pd.to_datetime(df_b_raw['date'])

        parsed_dead_chip = None
        if dead_chip_input and str(dead_chip_input).strip() != "":
            try: parsed_dead_chip = float(str(dead_chip_input).replace('%', '').strip())
            except: pass

        tags, df_debug_tags = get_v50_intelligence(df_b_raw, df_p_raw, stick_thresh=stickiness_threshold, global_days=max_len, dates_list=dates)
        df_b_raw['tag'] = df_b_raw['securities_trader'].map(tags).fillna("路人雜訊")
        df_b_raw['is_smart'] = df_b_raw['tag'].isin({"波段鎖碼", "避險造市", "獲利調節", "棄守提款", "主力重砲", "認錯回補"})
        df_b_raw['is_short'] = df_b_raw['tag'].isin({"隔日突擊", "跟風小戶"})
        
        df_s_raw = ds_dict.get("TaiwanStockHoldingSharesPer", pd.DataFrame())
        df_s_wide, df_s_unit, df_s_ppl = process_tdcc(df_s_raw)
        
        current_total_shares = df_s_wide['總張數'].iloc[0] if is_valid(df_s_wide) else 0
        capital_str = f"{current_total_shares / 10000:.2f} 億" if current_total_shares > 0 else "計算中..."
        latest_director_holding, holding_src = get_dead_chip_info(dates[0], parsed_dead_chip, dynamic_dict, s_val, chip_eng)
        director_holding_str = f"{latest_director_holding:.2f}% ({holding_src})" if latest_director_holding > 0 else "無資料"

        dynamic_n, radar_reason = calculate_dynamic_radar_depth(df_b_raw, dates, current_total_shares, df_price)
        pure_vwap, main_force_vol, active_main_branches, core_c_value, core_branch_names = calculate_pure_defense_line(
            df_b_raw, tags, filter_day_trade, current_total_shares, latest_director_holding, dynamic_n
        )
        
        net_3 = get_core_period_net(df_b_raw, dates[:3], core_branch_names)
        net_10 = get_core_period_net(df_b_raw, dates[:10], core_branch_names)
        net_60 = get_core_period_net(df_b_raw, dates[:60] if len(dates)>=60 else dates, core_branch_names)
        
        df_day_trade = optimize_memory(process_day_trading(ds_dict.get("TaiwanStockDayTrading", pd.DataFrame())))
        df_b_diff = process_branch_diff_v2(df_b_raw, dates, firepower_threshold, period_days=15)
        df_daily_tracker, df_audit_smart = process_v30_daily_tracking(df_b_raw, tags, df_price, df_b_diff, dates, firepower_threshold, period_days=15)
        
        df_s_dyn = process_tdcc_dynamic_v2(df_s_wide, df_price, parsed_dead_chip, dynamic_dict, s_val, chip_eng)
        df_v27_radar, _, _ = process_v27_ultimate_radar(df_s_wide, parsed_dead_chip, dynamic_dict, s_val, df_price, df_b_raw, tags)

        df_combined_display = pd.DataFrame()
        if is_valid(df_v27_radar) and is_valid(df_s_dyn):
            df_v27_clean = df_v27_radar.drop(columns=['大戶原持股(%)', '收盤價(元)'], errors='ignore')
            df_combined_radar = pd.merge(df_s_dyn, df_v27_clean, on=['日期'], how='inner')
            if is_valid(df_combined_radar):
                df_combined_radar['終極籌碼診斷'] = df_combined_radar['實戰判定'].astype(str) + " | " + df_combined_radar['專家雷達診斷'].astype(str)
                display_cols = ['日期', '收盤價(元)', '純淨活大戶C_Value(%)', '純淨大戶變動(%)', '總人數變率(%)', '大戶精算門檻', '當沖虛胖(%)', '終極籌碼診斷']
                df_combined_display = optimize_memory(df_combined_radar[[c for c in display_cols if c in df_combined_radar.columns]].sort_values('日期', ascending=False).head(8))

        df_margin_lending = optimize_memory(process_margin_and_lending(ds_dict.get("TaiwanStockMarginPurchaseShortSale", pd.DataFrame()), ds_dict.get("TaiwanStockSecuritiesLending", pd.DataFrame())))
        df_inst = optimize_memory(process_inst(ds_dict.get("TaiwanStockInstitutionalInvestorsBuySell", pd.DataFrame())))
        df_rev = optimize_memory(fetch_finmind_v50("TaiwanStockMonthRevenue", "2022-01-01", user_stock_id)) # 營收簡化處理

        market_cap_str = f"{(curr_price * current_total_shares) / 100000:,.2f} 億" if current_total_shares > 0 else "計算中..."
        company_info_text = f"【產業】 {industry} ｜ 【股本】 {capital_str} ｜ 【市值】 {market_cap_str} ｜ 【董監死籌碼】 {director_holding_str} ｜ 【20日均量】 {int(recent_20_vol):,} 張"
        
        st.subheader(f"{user_stock_id} {name} 全息戰報 (V75.9 終極版)")
        st.markdown(f"<div class='info-box'>{company_info_text}</div>", unsafe_allow_html=True)

        # 🧩 區間邏輯處理：對齊 01 區的戰略範圍
        if len(custom_range) == 2:
            c_start, c_end = custom_range
            selected_dates_list = [d for d in dates if str(c_start) <= d <= str(c_end)]
            if not selected_dates_list:
                st.warning("⚠️ 自訂區間無交易資料，系統將回退至預設 15 天。")
                selected_dates_list = dates[:15]
        else:
            selected_dates_list = dates[:15]

        st.markdown("<div class='category-title'>01. 終極全息透視區 (依自訂區間動態對齊)</div>", unsafe_allow_html=True)
        
        with st.expander(f"【終極全息熱力圖】 自訂區間：{selected_dates_list[-1]} ~ {selected_dates_list[0]} (共 {len(selected_dates_list)} 個交易日)", expanded=True):
            st.info(f"🟢 此區域目前完全連動左側「自訂時間區間」。區間內的買賣超累計排行已重算。")
            render_ultimate_heatmap(
                df_b_raw, 
                selected_dates_list,      # 橫軸足跡
                selected_dates_list,      # 排行基準：直接看這段時間誰最強
                tags, 
                df_debug_tags, 
                footprint_rows, 
                dynamic_noise_threshold
            )
            
        with st.expander(f"【戰略系海鮮】 大戶建倉成本區間分佈 (Volume Profile)", expanded=False):
            render_volume_profile(df_b_raw, selected_dates_list, footprint_rows)

        with st.expander(f"【甜點】 土洋聯合作戰比對 (近10日法人 vs 地方大戶角力)", expanded=False):
            render_institutional_vs_local(df_b_raw, df_inst, tags, top_n=4)

        # 其他區塊維持原樣
        render_clean_html_table(df_daily_tracker, "02. 平日戰情追蹤矩陣 (近15日)")
        render_clean_html_table(df_combined_display, "03. 一週集保籌碼雷達") 
        render_clean_html_table(df_inst, "05. 法人買賣超 (近10天)")
        render_clean_html_table(df_margin_lending, "06. 散戶資券與借券總量 (近10天)")
        
        with st.expander("點此展開集保分級表 (近8週)", expanded=False):
            render_tdcc_table_with_color(df_s_unit, "10-1. 集保分級 - 張數表 (紅增綠減)")
            render_tdcc_table_with_color(df_s_ppl, "10-2. 集保分級 - 人數表 (紅增綠減)")
            
        st.divider()
        st.success(f"V75.9 終極版已完成處理 {user_stock_id}。")
        gc.collect()
