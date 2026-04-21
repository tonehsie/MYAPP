import streamlit as st
import pandas as pd
import requests
import json
import streamlit.components.v1 as components

# 設定網頁全寬與標題
st.set_page_config(layout="wide", page_title="專業級量化互動圖表")

# 帶入您的 FinMind Token
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

st.title("高階技術分析 (白底黑白專業版)")

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
        
        # 計算均線
        df['MA10'] = df['close'].rolling(window=10).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()
        df['MA60'] = df['close'].rolling(window=60).mean()
        return df
    return None

df = get_stock_data(stock_id, start_date)

if df is not None:
    # 準備資料
    kline_data = []
    volume_data = []
    
    for index, row in df.iterrows():
        t = index.strftime('%Y-%m-%d')
        kline_data.append({
            'time': t, 'open': row['open'], 'high': row['max'], 
            'low': row['min'], 'close': row['close']
        })
        # 成交量配色：維持黑色調，但以深淺區分漲跌
        vol_color = '#000000' if row['close'] >= row['open'] else '#888888'
        volume_data.append({
            'time': t, 'value': float(row['Trading_Volume']), 'color': vol_color
        })

    def prep_ma(series):
        return [{'time': idx.strftime('%Y-%m-%d'), 'value': float(val)} for idx, val in series.dropna().items()]
        
    ma10_data = prep_ma(df['MA10'])
    ma20_data = prep_ma(df['MA20'])
    ma60_data = prep_ma(df['MA60'])

    # 嵌入前端程式碼：設定白底與黑白 K 線
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
        <style> 
            body { margin: 0; padding: 0; background-color: #ffffff; display: flex; flex-direction: column; height: 100vh; overflow: hidden; } 
            #chart-main { flex: 3; position: relative; border-bottom: 1px solid #e1e3eb; }
            #chart-vol { flex: 1; position: relative; }
        </style>
    </head>
    <body>
        <div id="chart-main"></div>
        <div id="chart-vol"></div>
        
        <script>
            try {
                // 白底配置設定
                const commonOptions = {
                    autoSize: true,
                    layout: { background: { type: 'solid', color: '#ffffff' }, textColor: '#333333' },
                    grid: { vertLines: { color: '#f0f3fa' }, horzLines: { color: '#f0f3fa' } },
                    crosshair: { mode: LightweightCharts.CrosshairMode.Normal, vertLine: { color: '#758696' }, horzLine: { color: '#758696' } },
                    rightPriceScale: { borderColor: '#e1e3eb' }
                };

                const mainChart = LightweightCharts.createChart(document.getElementById('chart-main'), {
                    ...commonOptions,
                    timeScale: { visible: false }
                });

                // 設定黑白 K 線：陽線白底黑框，陰線純黑
                const mainSeries = mainChart.addCandlestickSeries({
                    upColor: '#ffffff',       // 漲：白色填充
                    borderUpColor: '#000000', // 漲：黑色邊框
                    wickUpColor: '#000000',   // 漲：黑色影線
                    downColor: '#000000',     // 跌：黑色填充
                    borderDownColor: '#000000',
                    wickDownColor: '#000000'
                });
                mainSeries.setData(KLINE_DATA);

                // 均線：在白底下使用更鮮艷但專業的顏色
                mainChart.addLineSeries({ color: '#ff9800', lineWidth: 1.5, title: 'MA10' }).setData(MA10_DATA);
                mainChart.addLineSeries({ color: '#2196f3', lineWidth: 1.5, title: 'MA20' }).setData(MA20_DATA);
                mainChart.addLineSeries({ color: '#9c27b0', lineWidth: 1.5, title: 'MA60' }).setData(MA60_DATA);

                const volChart = LightweightCharts.createChart(document.getElementById('chart-vol'), {
                    ...commonOptions,
                    timeScale: { borderColor: '#e1e3eb', timeVisible: true }
                });

                const volumeSeries = volChart.addHistogramSeries({
                    priceFormat: { type: 'volume' },
                });
                volumeSeries.setData(VOLUME_DATA);

                // 同步機制
                mainChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
                    if (range) volChart.timeScale().setVisibleLogicalRange(range);
                });
                volChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
                    if (range) mainChart.timeScale().setVisibleLogicalRange(range);
                });

                const volMap = {}; VOLUME_DATA.forEach(d => { volMap[d.time] = d.value; });
                const klineMap = {}; KLINE_DATA.forEach(d => { klineMap[d.time] = d.close; });

                function syncCrosshair(source, target, map, series) {
                    source.subscribeCrosshairMove(p => {
                        if (!p.time || p.point.x < 0 || p.point.y < 0) target.clearCrosshairPosition();
                        else { const price = map[p.time]; if (price !== undefined) target.setCrosshairPosition(price, p.time, series); }
                    });
                }
                syncCrosshair(mainChart, volChart, volMap, volumeSeries);
                syncCrosshair(volChart, mainChart, klineMap, mainSeries);

            } catch (error) {
                document.body.innerHTML = "<div style='color:#000000; font-family:sans-serif; padding:20px;'><h3>渲染錯誤</h3><p>" + error.message + "</p></div>";
            }
        </script>
    </body>
    </html>
    """
    
    html_code = html_template.replace("KLINE_DATA", json.dumps(kline_data))
    html_code = html_code.replace("VOLUME_DATA", json.dumps(volume_data))
    html_code = html_code.replace("MA10_DATA", json.dumps(ma10_data))
    html_code = html_code.replace("MA20_DATA", json.dumps(ma20_data))
    html_code = html_code.replace("MA60_DATA", json.dumps(ma60_data))

    components.html(html_code, height=850)
else:
    st.error("查無資料，請確認 Token 是否正確。")
