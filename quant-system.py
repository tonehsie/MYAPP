import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# 設定網頁全寬與快取清除機制
st.set_page_config(layout="wide", page_title="專業級量化互動圖表")

# 您的 FinMind Token
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

st.title("高階技術分析 (極速最佳化版)")

# [最佳化 2] 使用 form 包裝輸入區塊，避免每打一個字就重整網頁
with st.form("query_form"):
    col1, col2 = st.columns(2)
    with col1:
        stock_id = st.text_input("輸入股票代號", "2330")
    with col2:
        start_date_input = st.text_input("輸入起始日期", "2023-01-01")
    
    # 加上送出按鈕
    submitted = st.form_submit_button("載入圖表")

# 透過 FinMind API 抓取資料 (加入快取)
@st.cache_data(show_spinner="正在向 FinMind 抓取資料...")
def get_stock_data(stock_id, start_date_str):
    try:
        start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
        # 擴大緩衝期至 400 天，確保 240MA(年線) 能夠計算
        fetch_start = (start_dt - timedelta(days=400)).strftime('%Y-%m-%d')
        
        url = "https://api.finmindtrade.com/api/v4/data"
        params = {
            "dataset": "TaiwanStockPrice",
            "data_id": stock_id,
            "start_date": fetch_start,
            "token": TOKEN
        }
        response = requests.get(url, params=params, timeout=10) # 加上 timeout 防呆
        data = response.json()
        
        if data.get("status") == 200 and len(data.get("data", [])) > 0:
            df = pd.DataFrame(data["data"])
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            # 確保資料品質
            df = df.sort_index(ascending=True)
            df = df[~df.index.duplicated(keep='last')]
            df = df.ffill()
            
            # 計算均線 (10, 60, 240)
            df['MA10'] = df['close'].rolling(window=10).mean()
            df['MA60'] = df['close'].rolling(window=60).mean()
            df['MA240'] = df['close'].rolling(window=240).mean()
            
            # 只保留使用者指定的起始日期之後的資料
            df = df[df.index >= pd.to_datetime(start_date_str)]
            
            if df.empty:
                return None
            return df
        return None
    except Exception as e:
        st.error(f"資料抓取或處理時發生錯誤: {e}")
        return None

# 初次載入或按下按鈕時執行
if submitted or 'first_load' not in st.session_state:
    st.session_state['first_load'] = False
    
    df = get_stock_data(stock_id, start_date_input)

    if df is not None:
        # [最佳化 1] 捨棄緩慢的 iterrows，改用 zip 進行極速陣列建構
        time_series = df.index.strftime('%Y-%m-%d').tolist()
        
        # 快速建構 K 線資料
        kline_data = [
            {'time': t, 'open': float(o), 'high': float(h), 'low': float(l), 'close': float(c)}
            for t, o, h, l, c in zip(time_series, df['open'], df['max'], df['min'], df['close'])
        ]
        
        # 快速建構成交量資料
        volume_data = [
            {'time': t, 'value': float(v), 'color': '#000000' if c >= o else '#888888'}
            for t, v, c, o in zip(time_series, df['Trading_Volume'], df['close'], df['open'])
        ]

        def prep_ma(series):
            # 去除 NaN 後快速建構格式
            valid_s = series.dropna()
            times = valid_s.index.strftime('%Y-%m-%d').tolist()
            return [{'time': t, 'value': round(float(v), 2)} for t, v in zip(times, valid_s.values)]
        
        ma_data = {
            "ma10": prep_ma(df['MA10']),
            "ma60": prep_ma(df['MA60']),
            "ma240": prep_ma(df['MA240'])
        }

        # 準備注入前端的 HTML 與 JS
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
            <style>
                body { margin: 0; background: #fff; font-family: sans-serif; display: flex; flex-direction: column; height: 100vh; overflow: hidden;}
                #chart-main { flex: 3; border-bottom: 1px solid #eee; position: relative; }
                #chart-vol { flex: 1; position: relative;}
                .legend { position: absolute; top: 10px; left: 10px; z-index: 10; font-size: 13px; pointer-events: none; line-height: 1.6; background: rgba(255,255,255,0.85); padding: 6px 10px; border-radius: 4px; color: #333; box-shadow: 0 1px 3px rgba(0,0,0,0.1);}
            </style>
        </head>
        <body>
            <div id="chart-main">
                <div id="legend" class="legend">準備載入數據...</div>
            </div>
            <div id="chart-vol"></div>
            <script>
                // 接收來自 Python 的資料
                const kData = KLINE_DATA;
                const vData = VOLUME_DATA;
                const ma = MA_DATA;

                // 共用設定
                const options = {
                    autoSize: true,
                    layout: { background: { color: '#ffffff' }, textColor: '#333' },
                    grid: { vertLines: { color: '#f0f0f0' }, horzLines: { color: '#f0f0f0' } },
                    rightPriceScale: { borderColor: '#ddd', autoScale: true },
                    timeScale: { borderColor: '#ddd' }
                };

                // 建立圖表容器
                const mainChart = LightweightCharts.createChart(document.getElementById('chart-main'), {...options, timeScale: {visible: false}});
                const volChart = LightweightCharts.createChart(document.getElementById('chart-vol'), options);

                // 設定主 K 線 (白底黑白風格)
                const candleSeries = mainChart.addCandlestickSeries({
                    upColor: '#fff', borderUpColor: '#000', wickUpColor: '#000',
                    downColor: '#000', borderDownColor: '#000', wickDownColor: '#000'
                });
                candleSeries.setData(kData);

                // 設定均線 (隱藏右側標籤與水平線)
                const s10 = mainChart.addLineSeries({ color: '#ff9800', lineWidth: 2, lastValueVisible: false, priceLineVisible: false });
                s10.setData(ma.ma10);
                const s60 = mainChart.addLineSeries({ color: '#2196f3', lineWidth: 2, lastValueVisible: false, priceLineVisible: false });
                s60.setData(ma.ma60);
                const s240 = mainChart.addLineSeries({ color: '#9c27b0', lineWidth: 2, lastValueVisible: false, priceLineVisible: false });
                s240.setData(ma.ma240);

                // 設定成交量
                const vSeries = volChart.addHistogramSeries({ priceFormat: { type: 'volume' } });
                vSeries.setData(vData);

                // 左上角 Legend 數值同步邏輯
                const legend = document.getElementById('legend');
                const syncLegend = (p) => {
                    if (p.time) {
                        const d = kData.find(x => x.time === p.time);
                        if (d) {
                            legend.innerHTML = `<b>${p.time}</b> &nbsp;&nbsp; 開: <span style="color:#000">${d.open}</span> &nbsp; 高: <span style="color:#000">${d.high}</span> &nbsp; 低: <span style="color:#000">${d.low}</span> &nbsp; 收: <span style="font-weight:bold; color:${d.close >= d.open ? '#e53935' : '#43a047'}">${d.close}</span>`;
                        }
                    } else if (kData.length > 0) {
                        // 滑鼠移開時，顯示最後一筆資料
                        const d = kData[kData.length - 1];
                        legend.innerHTML = `<b>${d.time}</b> &nbsp;&nbsp; 開: <span style="color:#000">${d.open}</span> &nbsp; 高: <span style="color:#000">${d.high}</span> &nbsp; 低: <span style="color:#000">${d.low}</span> &nbsp; 收: <span style="font-weight:bold; color:${d.close >= d.open ? '#e53935' : '#43a047'}">${d.close}</span>`;
                    }
                };
                
                // 初始顯示最後一筆
                syncLegend({time: null});

                // 十字線雙向綁定
                mainChart.subscribeCrosshairMove(p => {
                    syncLegend(p);
                    if (p.time) volChart.setCrosshairPosition(0, p.time, vSeries);
                    else volChart.clearCrosshairPosition();
                });
                volChart.subscribeCrosshairMove(p => {
                    syncLegend(p);
                    if (p.time) mainChart.setCrosshairPosition(0, p.time, candleSeries);
                    else mainChart.clearCrosshairPosition();
                });

                // 時間軸拖曳與縮放綁定
                mainChart.timeScale().subscribeVisibleLogicalRangeChange(r => {
                    if(r) volChart.timeScale().setVisibleLogicalRange(r);
                });
                volChart.timeScale().subscribeVisibleLogicalRangeChange(r => {
                    if(r) mainChart.timeScale().setVisibleLogicalRange(r);
                });
            </script>
        </body>
        </html>
        """
        
        # 將 JSON 注入模板並渲染
        html_code = html_template.replace("KLINE_DATA", json.dumps(kline_data))
        html_code = html_code.replace("VOLUME_DATA", json.dumps(volume_data))
        html_code = html_code.replace("MA_DATA", json.dumps(ma_data))
        
        components.html(html_code, height=800)
    else:
        st.warning("查無資料，請確認股票代號與日期是否正確，或此區間是否有交易紀錄。")
