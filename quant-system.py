import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components

# 設定網頁全寬與快取
st.set_page_config(layout="wide", page_title="全息量化系統 (形態展示特化版)")

st.title("高階技術分析 (古典圖表形態展示版)")
st.caption("🚀 V60.19-Demo：此版本專注於展示 W底、M頭、頭肩底、收斂三角形在 Lightweight Charts 中的渲染效果。")

# --- 1. 準備模擬資料 (對應模擬器中的四種形態) ---

# 模擬的 K 線與時間軸 (共 100 天)
base_time = pd.Timestamp('2023-01-01')
time_series = [(base_time + pd.Timedelta(days=i)).strftime('%Y-%m-%d') for i in range(100)]

# 建立一個簡單的背景走勢 (先跌後漲)
close_prices = []
p = 100
for i in range(100):
    if i < 30: p -= 0.5
    elif i < 70: p += 0.2
    else: p += 0.8
    close_prices.append(p)

kline_data = [
    {'time': t, 'open': p, 'high': p+2, 'low': p-2, 'close': p}
    for t, p in zip(time_series, close_prices)
]

# --- 2. 構建形態的幾何資料 (依照 V60.19 的 pat_data 格式) ---

# A. W底 (發生在 10~30 天)
w_bottom = {
    'name': 'W底',
    'color': '#9c27b0', # 紫色
    'lineWidth': 4,
    'lineStyle': 0, # Solid
    'shape_data': [
        {'time': time_series[10], 'value': 90},  # 左高
        {'time': time_series[15], 'value': 80},  # 左腳
        {'time': time_series[20], 'value': 88},  # 頸線高點
        {'time': time_series[25], 'value': 81},  # 右腳
        {'time': time_series[30], 'value': 92}   # 右高突破
    ],
    'neck_data': [
        {'time': time_series[10], 'value': 88},
        {'time': time_series[35], 'value': 88}
    ]
}

# B. 傾斜 M頭 (發生在 40~60 天)
m_top = {
    'name': '傾斜M頭',
    'color': '#d32f2f', # 紅色
    'lineWidth': 4,
    'lineStyle': 0,
    'shape_data': [
        {'time': time_series[40], 'value': 95},  # 左低
        {'time': time_series[45], 'value': 105}, # 左峰
        {'time': time_series[50], 'value': 98},  # 頸線低點
        {'time': time_series[55], 'value': 102}, # 右峰 (略低)
        {'time': time_series[60], 'value': 93}   # 右低跌破
    ],
    'neck_data': [
        {'time': time_series[40], 'value': 98},
        {'time': time_series[65], 'value': 98}
    ]
}

# C. 頭肩底 (發生在 65~85 天)
h_s_bottom = {
    'name': '頭肩底',
    'color': '#e91e63', # 粉紅
    'lineWidth': 4,
    'lineStyle': 0,
    'shape_data': [
        {'time': time_series[65], 'value': 100}, # 左肩
        {'time': time_series[68], 'value': 105}, # 左頸
        {'time': time_series[75], 'value': 92},  # 頭部
        {'time': time_series[80], 'value': 106}, # 右頸
        {'time': time_series[85], 'value': 102}, # 右肩
        {'time': time_series[90], 'value': 110}  # 突破
    ],
    'neck_data': [
        {'time': time_series[65], 'value': 105.5},
        {'time': time_series[95], 'value': 105.5}
    ]
}

# D. 收斂三角形 (發生在 10~90 天的大區間，為了展示交集)
triangle = {
    'name': '收斂三角形',
    'color': '#ff9800', # 橘色
    'lineWidth': 2,
    'lineStyle': 2, # Dashed
    'shape_data': [
        {'time': time_series[10], 'value': 115}, # 上界高點1
        {'time': time_series[80], 'value': 108}  # 上界高點2
    ],
    'neck_data': [
        {'time': time_series[20], 'value': 75},  # 下界低點1
        {'time': time_series[70], 'value': 85}   # 下界低點2
    ]
}

# 將所有形態打包
pattern_lines = []
for pat in [w_bottom, m_top, h_s_bottom, triangle]:
    # 加入形態主幹
    pattern_lines.append({
        "data": pat['shape_data'],
        "color": pat['color'],
        "lineWidth": pat['lineWidth'],
        "lineStyle": pat['lineStyle']
    })
    # 加入頸線/邊界線 (通常用虛線，稍微細一點)
    pattern_lines.append({
        "data": pat['neck_data'],
        "color": pat['color'],
        "lineWidth": 2,
        "lineStyle": 2 # Dashed
    })

# --- 3. 渲染 Lightweight Charts ---

html_template = """
<!DOCTYPE html>
<html>
<head>
    <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        body { margin: 0; background: #fff; font-family: sans-serif; display: flex; flex-direction: column; height: 100vh; overflow: hidden;}
        #chart-main { flex: 1; position: relative; } /* 這次為了純展示，我們把高度都給主圖 */
        .legend { position: absolute; top: 10px; left: 10px; z-index: 10; font-size: 14px; pointer-events: none; background: rgba(255,255,255,0.8); padding: 5px 10px; border-radius: 4px; color: #333; font-weight: bold;}
    </style>
</head>
<body>
    <div id="chart-main"><div id="legend" class="legend">古典幾何形態展示庫 (W底、M頭、頭肩底、收斂三角形)</div></div>
    <script>
        const kData = KLINE_DATA;
        const patLines = PATTERN_LINES;

        const mainOptions = {
            autoSize: true,
            layout: { background: { color: '#ffffff' }, textColor: '#333' },
            grid: { vertLines: { color: '#f5f5f5' }, horzLines: { color: '#f5f5f5' } },
            rightPriceScale: { borderColor: '#eee', autoScale: true, scaleMargins: { top: 0.1, bottom: 0.1 } },
            timeScale: { visible: true, borderColor: '#eee' } // 開啟時間軸方便觀察
        };

        const mainChart = LightweightCharts.createChart(document.getElementById('chart-main'), mainOptions);

        // 1. 畫 K 線 (背景底圖)
        const candleSeries = mainChart.addCandlestickSeries({
            upColor: '#e53935', borderUpColor: '#e53935', wickUpColor: '#e53935',
            downColor: '#43a047', borderDownColor: '#43a047', wickDownColor: '#43a047',
            opacity: 0.3 // 把 K 線調淡，凸顯形態線條
        });
        candleSeries.setData(kData);

        // 2. 畫出所有 AI 形態線條
        patLines.forEach(lineDef => {
            mainChart.addLineSeries({
                color: lineDef.color,
                lineWidth: lineDef.lineWidth,
                lineStyle: lineDef.lineStyle,
                lastValueVisible: false,
                priceLineVisible: false,
                crosshairMarkerVisible: false
            }).setData(lineDef.data);
        });
        
        // 讓圖表自動縮放適應所有資料
        mainChart.timeScale().fitContent();

    </script>
</body>
</html>
"""

# 將 Python 資料注入 JS
html_code = html_template.replace("KLINE_DATA", json.dumps(kline_data)).replace("PATTERN_LINES", json.dumps(pattern_lines))

# 設定高度參數 (如你所求，維持 700px 左右的高度)
components.html(html_code, height=736)
