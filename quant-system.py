import streamlit as st
import pandas as pd
import requests
import json
import streamlit.components.v1 as components

# 設定網頁全寬與標題
st.set_page_config(layout="wide", page_title="專業級量化互動圖表")

# 帶入您的 FinMind Token
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

st.title("高階互動技術圖表 (雙視窗分離連動版)")

# 建立輸入介面
col1, col2 = st.columns(2)
with col1:
    stock_id = st.text_input("輸入股票代號 (例如: 2330)", "2330")
with col2:
    start_date = st.text_input("輸入起始日期 (例如: 2023-01-01)", "2023-01-01")

# 透過 FinMind API 抓取資料
@st.cache_data
def get_stock_data(stock_id, start_date):
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": stock_id,
        "start_date": start_date,
        "token": TOKEN
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    if data.get("status") == 200 and len(data.get("data", [])) > 0:
        df = pd.DataFrame(data["data"])
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        # 確保日期排序與去除重複
        df = df.sort_index(ascending=True)
        df = df[~df.index.duplicated(keep='last')]
        df = df.ffill()
        
        # 計算高階參考線：10日、20日、60日均線
        df['MA10'] = df['close'].rolling(window=10).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()
        df['MA60'] = df['close'].rolling(window=60).mean()
        return df
    return None

df = get_stock_data(stock_id, start_date)

if df is not None:
    # 準備 TradingView 引擎專用的資料格式
    kline_data = []
    volume_data = []
    
    for index, row in df.iterrows():
        t = index.strftime('%Y-%m-%d')
        kline_data.append({
            'time': t, 'open': row['open'], 'high': row['max'], 
            'low': row['min'], 'close': row['close']
        })
        # 收盤大於等於開盤為紅，反之為綠
        color = '#ef5350' if row['close'] >= row['open'] else '#26a69a'
        volume_data.append({
            'time': t, 'value': float(row['Trading_Volume']), 'color': color
        })

    def prep_ma(series):
        return [{'time': idx.strftime('%Y-%m-%d'), 'value': float(val)} for idx, val in series.dropna().items()]
        
    ma10_data = prep_ma(df['MA10'])
    ma20_data = prep_ma(df['MA20'])
    ma60_data = prep_ma(df['MA60'])

    # 嵌入前端程式碼，建立雙 div 視窗並進行 JS 雙向綁定
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
        <style> 
            body { margin: 0; padding: 0; background-color: #131722; display: flex; flex-direction: column; height: 100vh; overflow: hidden; } 
            /* 物理分離的關鍵：上方 K 線區塊佔據 75%，並加一條實體分隔線 */
            #chart-main { flex: 3; position: relative; border-bottom: 2px solid #2b2b43; }
            /* 下方成交量區塊佔據 25% */
            #chart-vol { flex: 1; position: relative; }
        </style>
    </head>
    <body>
        <div id="chart-main"></div>
        <div id="chart-vol"></div>
        
        <script>
            try {
                // 共用的基礎外觀設定
                const commonOptions = {
                    autoSize: true,
                    layout: { background: { type: 'solid', color: '#131722' }, textColor: '#d1d4dc' },
                    grid: { vertLines: { color: '#2b2b43' }, horzLines: { color: '#2b2b43' } },
                    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
                    rightPriceScale: { borderColor: '#2b2b43' }
                };

                // --- 1. 建立主圖表 (K線與均線) ---
                const mainChart = LightweightCharts.createChart(document.getElementById('chart-main'), {
                    ...commonOptions,
                    timeScale: { visible: false } // 隱藏主圖表的時間軸，讓畫面更緊湊
                });

                const mainSeries = mainChart.addCandlestickSeries({
                    upColor: '#ef5350', downColor: '#26a69a', borderVisible: false,
                    wickUpColor: '#ef5350', wickDownColor: '#26a69a'
                });
                mainSeries.setData(KLINE_DATA);

                mainChart.addLineSeries({ color: 'orange', lineWidth: 1.5, title: 'MA10' }).setData(MA10_DATA);
                mainChart.addLineSeries({ color: 'cyan', lineWidth: 1.5, title: 'MA20' }).setData(MA20_DATA);
                mainChart.addLineSeries({ color: 'magenta', lineWidth: 1.5, title: 'MA60' }).setData(MA60_DATA);

                // --- 2. 建立副圖表 (成交量) ---
                const volChart = LightweightCharts.createChart(document.getElementById('chart-vol'), {
                    ...commonOptions,
                    timeScale: { borderColor: '#2b2b43', timeVisible: true }
                });

                const volumeSeries = volChart.addHistogramSeries({
                    priceFormat: { type: 'volume' },
                });
                volumeSeries.setData(VOLUME_DATA);

                // --- 3. 建立 O(1) 查詢表，用於十字線同步 ---
                const volMap = {};
                VOLUME_DATA.forEach(d => { volMap[d.time] = d.value; });
                const klineMap = {};
                KLINE_DATA.forEach(d => { klineMap[d.time] = d.close; });

                // --- 4. 雙向綁定：同步縮放與平移 (時間軸) ---
                mainChart.timeScale().subscribeVisibleLogicalRangeChange(timeRange => {
                    if (timeRange) volChart.timeScale().setVisibleLogicalRange(timeRange);
                });
                volChart.timeScale().subscribeVisibleLogicalRangeChange(timeRange => {
                    if (timeRange) mainChart.timeScale().setVisibleLogicalRange(timeRange);
                });

                // --- 5. 雙向綁定：同步滑鼠十字線 ---
                function syncCrosshair(sourceChart, targetChart, dataMap, targetSeries) {
                    sourceChart.subscribeCrosshairMove(param => {
                        if (!param.time || param.point.x < 0 || param.point.y < 0) {
                            targetChart.clearCrosshairPosition();
                        } else {
                            const price = dataMap[param.time];
                            if (price !== undefined) {
                                targetChart.setCrosshairPosition(price, param.time, targetSeries);
                            }
                        }
                    });
                }
                syncCrosshair(mainChart, volChart, volMap, volumeSeries);
                syncCrosshair(volChart, mainChart, klineMap, mainSeries);

            } catch (error) {
                document.body.innerHTML = "<div style='color:#ef5350; font-family:sans-serif; padding:20px;'><h3>圖表渲染失敗</h3><p>錯誤訊息: " + error.message + "</p></div>";
            }
        </script>
    </body>
    </html>
    """
    
    # 注入實際數據
    html_code = html_template.replace("KLINE_DATA", json.dumps(kline_data))
    html_code = html_code.replace("VOLUME_DATA", json.dumps(volume_data))
    html_code = html_code.replace("MA10_DATA", json.dumps(ma10_data))
    html_code = html_code.replace("MA20_DATA", json.dumps(ma20_data))
    html_code = html_code.replace("MA60_DATA", json.dumps(ma60_data))

    # 在 Streamlit 中渲染圖表，拉高容器確保雙視窗完美顯示
    components.html(html_code, height=850)
else:
    st.error("查無資料，請確認代號或日期是否正確，或您的 Token 權限是否正常。")
