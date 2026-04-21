import streamlit as st
import pandas as pd
import requests
import json
import streamlit.components.v1 as components

# 設定網頁全寬與標題
st.set_page_config(layout="wide", page_title="專業級量化互動圖表")

# 帶入您的 FinMind Token
TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

st.title("高階互動技術圖表 (內建 TradingView 引擎)")

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

    # 鎖定載入 4.2.1 穩定版的 Lightweight Charts 引擎，並設定上下分層邊距
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
        <style> 
            body { margin: 0; padding: 0; background-color: #131722; overflow: hidden; } 
            #tvchart { position: absolute; top: 0; left: 0; width: 100%; height: 100%; }
        </style>
    </head>
    <body>
        <div id="tvchart"></div>
        <script>
            try {
                const chartOptions = {
                    autoSize: true,
                    layout: { background: { type: 'solid', color: '#131722' }, textColor: '#d1d4dc' },
                    grid: { vertLines: { color: '#2b2b43' }, horzLines: { color: '#2b2b43' } },
                    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
                    rightPriceScale: { 
                        borderColor: '#2b2b43', 
                        autoScale: true,
                        // 主圖表 (K線與均線) 佔據上方空間，距離底部保留 25% 的空白區域
                        scaleMargins: { top: 0.05, bottom: 0.25 }
                    },
                    timeScale: { borderColor: '#2b2b43', timeVisible: true }
                };
                
                const chart = LightweightCharts.createChart(document.getElementById('tvchart'), chartOptions);

                // 設定 K 線
                const mainSeries = chart.addCandlestickSeries({
                    upColor: '#ef5350', downColor: '#26a69a', borderVisible: false,
                    wickUpColor: '#ef5350', wickDownColor: '#26a69a'
                });
                mainSeries.setData(KLINE_DATA);

                // 設定均線
                const ma10 = chart.addLineSeries({ color: 'orange', lineWidth: 1.5, title: 'MA10' });
                ma10.setData(MA10_DATA);
                const ma20 = chart.addLineSeries({ color: 'cyan', lineWidth: 1.5, title: 'MA20' });
                ma20.setData(MA20_DATA);
                const ma60 = chart.addLineSeries({ color: 'magenta', lineWidth: 1.5, title: 'MA60' });
                ma60.setData(MA60_DATA);

                // 設定獨立的成交量 Y 軸區塊
                chart.priceScale('volume').applyOptions({
                    // 成交量圖表從上方 80% 處開始，佔據最底部 20% (與主圖表保留 5% 的實體留白)
                    scaleMargins: { top: 0.8, bottom: 0 },
                });
                
                const volumeSeries = chart.addHistogramSeries({
                    priceFormat: { type: 'volume' },
                    priceScaleId: 'volume',
                });
                volumeSeries.setData(VOLUME_DATA);
                
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

    # 在 Streamlit 中渲染圖表
    components.html(html_code, height=750)
else:
    st.error("查無資料，請確認代號或日期是否正確，或您的 Token 權限是否正常。")
