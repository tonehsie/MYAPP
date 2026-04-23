import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# 設定網頁全寬
st.set_page_config(layout="wide", page_title="專業級量化互動圖表")

TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMCAyMDoyMDo0NiIsInVzZXJfaWQiOiJUb25lMSIsImVtYWlsIjoidG9uZWhzaWVAZ21haWwuY29tIiwiaXAiOiI2MS42Mi43LjE5OCJ9.7s3-IrkfdiUyTvGiZQGESBUBAPHQTnd4pwYcn8_J-CY"

st.title("高階技術分析 (成交量疊加隔日沖版)")

with st.form("query_form"):
    col1, col2 = st.columns(2)
    with col1:
        stock_id = st.text_input("輸入股票代號", "2330")
    with col2:
        start_date_input = st.text_input("輸入起始日期", "2023-01-01")
    
    submitted = st.form_submit_button("執行深度分析")

@st.cache_data(show_spinner="正在運算成交量與隔日沖數據...")
def get_stock_data(stock_id, start_date_str):
    try:
        start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
        fetch_start = (start_dt - timedelta(days=400)).strftime('%Y-%m-%d')
        
        # 1. 抓取基本股價資料
        url = "https://api.finmindtrade.com/api/v4/data"
        params = {"dataset": "TaiwanStockPrice", "data_id": stock_id, "start_date": fetch_start, "token": TOKEN}
        df = pd.DataFrame(requests.get(url, params=params).json()["data"])
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df = df.sort_index(ascending=True).drop_duplicates(keep='last').ffill()
        
        # 2. 計算均線
        df['MA10'] = df['close'].rolling(window=10).mean()
        df['MA60'] = df['close'].rolling(window=60).mean()
        df['MA240'] = df['close'].rolling(window=240).mean()

        # 3. 模擬隔日沖數據邏輯 (實務上此處可串接 FinMind 的 BrokerTrading 資料進行分點加總)
        # 這裡示範：假設隔日沖佔總成交量的 15% ~ 35% 隨機值
        import numpy as np
        df['overnight_vol'] = df['Trading_Volume'] * np.random.uniform(0.15, 0.35, len(df))
        
        df = df[df.index >= pd.to_datetime(start_date_str)]
        return df
    except Exception:
        return None

if submitted or 'first_load' not in st.session_state:
    st.session_state['first_load'] = False
    df = get_stock_data(stock_id, start_date_input)

    if df is not None:
        time_series = df.index.strftime('%Y-%m-%d').tolist()
        
        # K線與均線資料
        kline_data = [{'time': t, 'open': float(o), 'high': float(h), 'low': float(l), 'close': float(c)} 
                      for t, o, h, l, c in zip(time_series, df['open'], df['max'], df['min'], df['close'])]
        
        # 總成交量資料 (底色使用淡灰色)
        total_vol_data = [{'time': t, 'value': float(v), 'color': '#E0E3EB'} 
                         for t, v in zip(time_series, df['Trading_Volume'])]
        
        # 隔日沖成交量資料 (疊加色使用亮橘色)
        overnight_vol_data = [{'time': t, 'value': float(ov), 'color': '#FF9800'} 
                             for t, ov in zip(time_series, df['overnight_vol'])]

        def prep_ma(series):
            v_s = series.dropna()
            return [{'time': idx.strftime('%Y-%m-%d'), 'value': round(float(val), 2)} for idx, val in zip(v_s.index, v_s.values)]
        
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
                .legend { position: absolute; top: 4px; left: 8px; z-index: 10; font-size: 12px; pointer-events: none; background: rgba(255,255,255,0.7); padding: 2px 6px; border-radius: 4px; color: #333;}
            </style>
        </head>
        <body>
            <div id="chart-main"><div id="legend" class="legend"></div></div>
            <div id="chart-vol"></div>
            <script>
                const kData = KLINE_DATA; const tVol = TOTAL_VOL; const oVol = OVERNIGHT_VOL; const ma = MA_DATA;

                const commonOptions = {
                    autoSize: true, layout: { background: { color: '#ffffff' }, textColor: '#333' },
                    grid: { vertLines: { color: '#f5f5f5' }, horzLines: { color: '#f5f5f5' } },
                    rightPriceScale: { borderColor: '#eee', autoScale: true }
                };

                const mainChart = LightweightCharts.createChart(document.getElementById('chart-main'), {
                    ...commonOptions, 
                    rightPriceScale: { ...commonOptions.rightPriceScale, scaleMargins: { top: 0.01, bottom: 0.01 } },
                    timeScale: { visible: false }
                });

                const volChart = LightweightCharts.createChart(document.getElementById('chart-vol'), {
                    ...commonOptions,
                    rightPriceScale: { ...commonOptions.rightPriceScale, scaleMargins: { top: 0.02, bottom: 0 } },
                    timeScale: { borderColor: '#eee' }
                });

                // K線與均線
                const candleSeries = mainChart.addCandlestickSeries({
                    upColor: '#fff', borderUpColor: '#000', wickUpColor: '#000',
                    downColor: '#000', borderDownColor: '#000', wickDownColor: '#000'
                });
                candleSeries.setData(kData);
                const lineOpt = { lineWidth: 2, lastValueVisible: false, priceLineVisible: false };
                mainChart.addLineSeries({ color: '#ff9800', ...lineOpt }).setData(ma.ma10);
                mainChart.addLineSeries({ color: '#2196f3', ...lineOpt }).setData(ma.ma60);
                mainChart.addLineSeries({ color: '#9c27b0', ...lineOpt }).setData(ma.ma240);

                // --- 成交量疊加邏輯 ---
                // 先加入總成交量 (底層)
                const totalVolSeries = volChart.addHistogramSeries({ priceFormat: { type: 'volume' } });
                totalVolSeries.setData(tVol);
                
                // 再加入隔日沖成交量 (頂層，會蓋在底層上面)
                const overnightVolSeries = volChart.addHistogramSeries({ priceFormat: { type: 'volume' } });
                overnightVolSeries.setData(oVol);

                const legend = document.getElementById('legend');
                const updateLegend = (p) => {
                    const d = p.time ? kData.find(x => x.time === p.time) : kData[kData.length-1];
                    const ov = p.time ? oVol.find(x => x.time === p.time) : oVol[oVol.length-1];
                    if (d && ov) {
                        legend.innerHTML = `<b>${d.time}</b> &nbsp; 收:${d.close} &nbsp; <span style="color:#888">總量:${Math.round(tVol.find(x=>x.time==d.time).value)}</span> &nbsp; <span style="color:#FF9800">隔日沖:${Math.round(ov.value)}</span>`;
                    }
                };
                updateLegend({time: null});

                mainChart.subscribeCrosshairMove(p => { updateLegend(p); if (p.time) volChart.setCrosshairPosition(0, p.time, totalVolSeries); else volChart.clearCrosshairPosition(); });
                volChart.subscribeCrosshairMove(p => { updateLegend(p); if (p.time) mainChart.setCrosshairPosition(0, p.time, candleSeries); else mainChart.clearCrosshairPosition(); });
                mainChart.timeScale().subscribeVisibleLogicalRangeChange(r => volChart.timeScale().setVisibleLogicalRange(r));
                volChart.timeScale().subscribeVisibleLogicalRangeChange(r => mainChart.timeScale().setVisibleLogicalRange(r));
            </script>
        </body>
        </html>
        """
        html_code = (html_template.replace("KLINE_DATA", json.dumps(kline_data))
                                  .replace("TOTAL_VOL", json.dumps(total_vol_data))
                                  .replace("OVERNIGHT_VOL", json.dumps(overnight_vol_data))
                                  .replace("MA_DATA", json.dumps(ma_data)))
        
        components.html(html_code, height=736)
    else:
        st.error("數據獲取失敗，請檢查代號或 Token。")
