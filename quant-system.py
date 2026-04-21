import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# 設定網頁全寬與快取
st.set_page_config(layout="wide", page_title="專業級量化互動圖表")

# 您的 FinMind Token
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

st.title("高階技術分析 (極緻緊湊版 - 10/60/240均線)")

# 查詢表單
with st.form("query_form"):
    col1, col2 = st.columns(2)
    with col1:
        stock_id = st.text_input("輸入股票代號", "2330")
    with col2:
        start_date_input = st.text_input("輸入起始日期", "2023-01-01")
    
    submitted = st.form_submit_button("載入圖表")

@st.cache_data(show_spinner="正在載入專業數據...")
def get_stock_data(stock_id, start_date_str):
    try:
        start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
        # 緩衝期 400 天確保 240MA 運算
        fetch_start = (start_dt - timedelta(days=400)).strftime('%Y-%m-%d')
        
        url = "https://api.finmindtrade.com/api/v4/data"
        params = {
            "dataset": "TaiwanStockPrice",
            "data_id": stock_id,
            "start_date": fetch_start,
            "token": TOKEN
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("status") == 200 and len(data.get("data", [])) > 0:
            df = pd.DataFrame(data["data"])
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df = df.sort_index(ascending=True).drop_duplicates(keep='last').ffill()
            
            # 計算均線 (10, 60, 240)
            df['MA10'] = df['close'].rolling(window=10).mean()
            df['MA60'] = df['close'].rolling(window=60).mean()
            df['MA240'] = df['close'].rolling(window=240).mean()
            
            df = df[df.index >= pd.to_datetime(start_date_str)]
            return df if not df.empty else None
        return None
    except Exception:
        return None

if submitted or 'first_load' not in st.session_state:
    st.session_state['first_load'] = False
    df = get_stock_data(stock_id, start_date_input)

    if df is not None:
        # 高效資料處理 (向量化最佳化)
        time_series = df.index.strftime('%Y-%m-%d').tolist()
        kline_data = [
            {'time': t, 'open': float(o), 'high': float(h), 'low': float(l), 'close': float(c)}
            for t, o, h, l, c in zip(time_series, df['open'], df['max'], df['min'], df['close'])
        ]
        volume_data = [
            {'time': t, 'value': float(v), 'color': '#000000' if c >= o else '#888888'}
            for t, v, c, o in zip(time_series, df['Trading_Volume'], df['close'], df['open'])
        ]

        def prep_ma(series):
            valid_s = series.dropna()
            times = valid_s.index.strftime('%Y-%m-%d').tolist()
            return [{'time': t, 'value': round(float(v), 2)} for t, v in zip(times, valid_s.values)]
        
        ma_data = {"ma10": prep_ma(df['MA10']), "ma60": prep_ma(df['MA60']), "ma240": prep_ma(df['MA240'])}

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
            <style>
                body { margin: 0; background: #fff; font-family: sans-serif; display: flex; flex-direction: column; height: 100vh; overflow: hidden;}
                #chart-main { flex: 3.2; border-bottom: 2px solid #f0f3fa; position: relative; }
                #chart-vol { flex: 0.8; position: relative;}
                .legend { position: absolute; top: 4px; left: 8px; z-index: 10; font-size: 13px; pointer-events: none; background: rgba(255,255,255,0.7); padding: 2px 6px; border-radius: 4px; color: #333;}
            </style>
        </head>
        <body>
            <div id="chart-main"><div id="legend" class="legend"></div></div>
            <div id="chart-vol"></div>
            <script>
                const kData = KLINE_DATA;
                const vData = VOLUME_DATA;
                const ma = MA_DATA;

                const mainOptions = {
                    autoSize: true,
                    layout: { background: { color: '#ffffff' }, textColor: '#333' },
                    grid: { vertLines: { color: '#f5f5f5' }, horzLines: { color: '#f5f5f5' } },
                    rightPriceScale: { 
                        borderColor: '#eee', 
                        autoScale: true,
                        // [優化] 上下邊距極致壓縮至 1%
                        scaleMargins: { top: 0.01, bottom: 0.01 } 
                    },
                    timeScale: { visible: false }
                };

                const volOptions = {
                    autoSize: true,
                    layout: { background: { color: '#ffffff' }, textColor: '#333' },
                    grid: { vertLines: { color: '#f5f5f5' }, horzLines: { color: '#f5f5f5' } },
                    rightPriceScale: { 
                        borderColor: '#eee', 
                        autoScale: true,
                        // [優化] 成交量頂部僅留 2%
                        scaleMargins: { top: 0.02, bottom: 0 } 
                    },
                    timeScale: { borderColor: '#eee' }
                };

                const mainChart = LightweightCharts.createChart(document.getElementById('chart-main'), mainOptions);
                const volChart = LightweightCharts.createChart(document.getElementById('chart-vol'), volOptions);

                const candleSeries = mainChart.addCandlestickSeries({
                    upColor: '#fff', borderUpColor: '#000', wickUpColor: '#000',
                    downColor: '#000', borderDownColor: '#000', wickDownColor: '#000'
                });
                candleSeries.setData(kData);

                const lineOpt = { lineWidth: 2, lastValueVisible: false, priceLineVisible: false };
                mainChart.addLineSeries({ color: '#ff9800', ...lineOpt }).setData(ma.ma10);
                mainChart.addLineSeries({ color: '#2196f3', ...lineOpt }).setData(ma.ma60);
                mainChart.addLineSeries({ color: '#9c27b0', ...lineOpt }).setData(ma.ma240);

                const vSeries = volChart.addHistogramSeries({ priceFormat: { type: 'volume' } });
                vSeries.setData(vData);

                const legend = document.getElementById('legend');
                const updateLegend = (p) => {
                    const d = p.time ? kData.find(x => x.time === p.time) : kData[kData.length-1];
                    if (d) {
                        legend.innerHTML = `<b>${d.time}</b> &nbsp; 開:${d.open} 高:${d.high} 低:${d.low} 收:<span style="color:${d.close >= d.open ? '#e53935' : '#43a047'}">${d.close}</span>`;
                    }
                };
                updateLegend({time: null});

                mainChart.subscribeCrosshairMove(p => {
                    updateLegend(p);
                    if (p.time) volChart.setCrosshairPosition(0, p.time, vSeries);
                    else volChart.clearCrosshairPosition();
                });
                volChart.subscribeCrosshairMove(p => {
                    updateLegend(p);
                    if (p.time) mainChart.setCrosshairPosition(0, p.time, candleSeries);
                    else mainChart.clearCrosshairPosition();
                });

                mainChart.timeScale().subscribeVisibleLogicalRangeChange(r => volChart.timeScale().setVisibleLogicalRange(r));
                volChart.timeScale().subscribeVisibleLogicalRangeChange(r => mainChart.timeScale().setVisibleLogicalRange(r));
            </script>
        </body>
        </html>
        """
        html_code = html_template.replace("KLINE_DATA", json.dumps(kline_data)).replace("VOLUME_DATA", json.dumps(volume_data)).replace("MA_DATA", json.dumps(ma_data))
        
        # [優化] 整個圖表外層容器高度縮減 8% (由 800 減至 700)
        components.html(html_code, height=700)
    else:
        st.warning("查無資料。")
