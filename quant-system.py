import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# 設定網頁全寬
st.set_page_config(layout="wide", page_title="專業級量化互動圖表")

# 您的 FinMind Token
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

st.title("高階技術分析 (黑白專業版 - 均線修復)")

# 輸入介面
col1, col2 = st.columns(2)
with col1:
    stock_id = st.text_input("輸入股票代號", "2330")
with col2:
    start_date_input = st.text_input("輸入起始日期", "2023-01-01")

@st.cache_data
def get_stock_data(stock_id, start_date_str):
    # 【關鍵修復】為了讓 MA60 正常顯示，自動多抓 100 天的資料做緩衝
    start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
    fetch_start = (start_dt - timedelta(days=150)).strftime('%Y-%m-%d')
    
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": stock_id,
        "start_date": fetch_start,
        "token": TOKEN
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    if data.get("status") == 200 and len(data.get("data", [])) > 0:
        df = pd.DataFrame(data["data"])
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df = df.sort_index(ascending=True).drop_duplicates(keep='last').ffill()
        
        # 計算均線
        df['MA10'] = df['close'].rolling(window=10).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()
        df['MA60'] = df['close'].rolling(window=60).mean()
        
        # 只保留使用者真正要看的日期範圍
        df = df[df.index >= pd.to_datetime(start_date_str)]
        return df
    return None

df = get_stock_data(stock_id, start_date_input)

if df is not None:
    kline_data = []
    volume_data = []
    for idx, row in df.iterrows():
        t = idx.strftime('%Y-%m-%d')
        kline_data.append({'time': t, 'open': row['open'], 'high': row['max'], 'low': row['min'], 'close': row['close']})
        v_color = '#000000' if row['close'] >= row['open'] else '#888888'
        volume_data.append({'time': t, 'value': float(row['Trading_Volume']), 'color': v_color})

    def prep_ma(series):
        return [{'time': idx.strftime('%Y-%m-%d'), 'value': round(float(val), 2)} for idx, val in series.dropna().items()]
    
    ma_data = {
        "ma10": prep_ma(df['MA10']),
        "ma20": prep_ma(df['MA20']),
        "ma60": prep_ma(df['MA60'])
    }

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
        <style>
            body { margin: 0; background: #fff; font-family: sans-serif; display: flex; flex-direction: column; height: 100vh; }
            #chart-main { flex: 3; border-bottom: 1px solid #eee; position: relative; }
            #chart-vol { flex: 1; }
            .legend { position: absolute; top: 10px; left: 10px; z-index: 10; font-size: 12px; pointer-events: none; line-height: 1.6; background: rgba(255,255,255,0.8); padding: 5px; border-radius: 4px; }
            .ma10 { color: #ff9800; } .ma20 { color: #2196f3; } .ma60 { color: #9c27b0; }
        </style>
    </head>
    <body>
        <div id="chart-main">
            <div id="legend" class="legend"></div>
        </div>
        <div id="chart-vol"></div>
        <script>
            const kData = KLINE_DATA;
            const vData = VOLUME_DATA;
            const ma = MA_DATA;

            const options = {
                autoSize: true,
                layout: { background: { color: '#ffffff' }, textColor: '#333' },
                grid: { vertLines: { color: '#f0f0f0' }, horzLines: { color: '#f0f0f0' } },
                rightPriceScale: { borderColor: '#ddd', autoScale: true },
                timeScale: { borderColor: '#ddd' }
            };

            const mainChart = LightweightCharts.createChart(document.getElementById('chart-main'), {...options, timeScale: {visible: false}});
            const volChart = LightweightCharts.createChart(document.getElementById('chart-vol'), options);

            // K線
            const candleSeries = mainChart.addCandlestickSeries({
                upColor: '#fff', borderUpColor: '#000', wickUpColor: '#000',
                downColor: '#000', borderDownColor: '#000', wickDownColor: '#000'
            });
            candleSeries.setData(kData);

            // 均線 - 確保在這裡添加
            const s10 = mainChart.addLineSeries({ color: '#ff9800', lineWidth: 2, title: 'MA10' });
            s10.setData(ma.ma10);
            const s20 = mainChart.addLineSeries({ color: '#2196f3', lineWidth: 2, title: 'MA20' });
            s20.setData(ma.ma20);
            const s60 = mainChart.addLineSeries({ color: '#9c27b0', lineWidth: 2, title: 'MA60' });
            s60.setData(ma.ma60);

            // 成交量
            const vSeries = volChart.addHistogramSeries({ priceFormat: { type: 'volume' } });
            vSeries.setData(vData);

            // 同步與 Legend
            const legend = document.getElementById('legend');
            const sync = (p) => {
                if (p.time) {
                    const d = kData.find(x => x.time === p.time);
                    const m10 = ma.ma10.find(x => x.time === p.time);
                    const m20 = ma.ma20.find(x => x.time === p.time);
                    const m60 = ma.ma60.find(x => x.time === p.time);
                    if (d) {
                        legend.innerHTML = `<b>${p.time}</b> O:${d.open} H:${d.high} L:${d.low} C:${d.close}<br>` +
                                         `<span class="ma10">MA10: ${m10?m10.value:'-'}</span> ` +
                                         `<span class="ma20">MA20: ${m20?m20.value:'-'}</span> ` +
                                         `<span class="ma60">MA60: ${m60?m60.value:'-'}</span>`;
                    }
                }
            };

            mainChart.subscribeCrosshairMove(p => {
                sync(p);
                if (p.time) volChart.setCrosshairPosition(0, p.time, vSeries);
            });
            volChart.subscribeCrosshairMove(p => {
                sync(p);
                if (p.time) mainChart.setCrosshairPosition(0, p.time, candleSeries);
            });

            mainChart.timeScale().subscribeVisibleLogicalRangeChange(r => volChart.timeScale().setVisibleLogicalRange(r));
            volChart.timeScale().subscribeVisibleLogicalRangeChange(r => mainChart.timeScale().setVisibleLogicalRange(r));
        </script>
    </body>
    </html>
    """
    st.components.html(
        html_template.replace("KLINE_DATA", json.dumps(kline_data))
                     .replace("VOLUME_DATA", json.dumps(volume_data))
                     .replace("MA_DATA", json.dumps(ma_data)),
        height=800
    )
