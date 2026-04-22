import json
import streamlit.components.v1 as components

def render_kline_with_daytrade(kline_data, volume_data, dt_volume_data):
    """
    參數說明：
    - kline_data: list of dict, 格式 [{'time': '2023-01-01', 'open': 100, 'high': 105, 'low': 99, 'close': 102}, ...]
    - volume_data: list of dict, 格式 [{'time': '2023-01-01', 'value': 5000, 'color': '#b2b5be'}, ...] (總量，依漲跌給顏色)
    - dt_volume_data: list of dict, 格式 [{'time': '2023-01-01', 'value': 1500}, ...] (當沖量)
    """
    
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
        <style>
            body { margin: 0; padding: 0; display: flex; flex-direction: column; height: 100vh; font-family: sans-serif; background: #fff; }
            #chart-main { flex: 3; position: relative; border-bottom: 1px solid #eee; }
            #chart-vol { flex: 1; position: relative; }
            .legend { position: absolute; top: 8px; left: 8px; z-index: 10; font-size: 13px; background: rgba(255,255,255,0.85); padding: 4px 8px; border-radius: 4px; pointer-events: none; }
        </style>
    </head>
    <body>
        <div id="chart-main"><div id="legend" class="legend"></div></div>
        <div id="chart-vol"></div>
        <script>
            // 1. 接收 Python 傳遞的 JSON 資料
            const kData = _KLINE_DATA_;
            const vData = _VOLUME_DATA_;
            const dtData = _DT_VOLUME_DATA_;

            // 2. 建立主圖 (K線) 與副圖 (成交量)
            const mainChart = LightweightCharts.createChart(document.getElementById('chart-main'), {
                layout: { background: { color: '#ffffff' }, textColor: '#333' },
                grid: { vertLines: { color: '#f5f5f5' }, horzLines: { color: '#f5f5f5' } },
                rightPriceScale: { autoScale: true },
                timeScale: { visible: false } // 隱藏主圖時間軸，靠副圖顯示
            });

            const volChart = LightweightCharts.createChart(document.getElementById('chart-vol'), {
                layout: { background: { color: '#ffffff' }, textColor: '#333' },
                grid: { vertLines: { color: '#f5f5f5' }, horzLines: { color: '#f5f5f5' } },
                timeScale: { borderColor: '#eee' }
            });

            // 3. 繪製 K 線
            const candleSeries = mainChart.addCandlestickSeries({
                upColor: '#ffffff', borderUpColor: '#d32f2f', wickUpColor: '#d32f2f',
                downColor: '#008b8b', borderDownColor: '#008b8b', wickDownColor: '#008b8b'
            });
            candleSeries.setData(kData);

            // 4. 繪製總成交量 (底層，決定基礎顏色)
            const vSeries = volChart.addHistogramSeries({
                priceFormat: { type: 'volume' },
                priceScaleId: '' // 鎖定與疊加圖同軸
            });
            vSeries.setData(vData);

            // 5. 繪製當沖量 (上層疊加，固定橘紅色)
            const dtSeries = volChart.addHistogramSeries({
                color: 'rgba(255, 82, 82, 0.85)',
                priceFormat: { type: 'volume' },
                priceScaleId: '' // 必須與 vSeries 共用空 ID 才能完美重疊
            });
            dtSeries.setData(dtData);

            // 6. 綁定雙圖表的時間軸，達成同步縮放與平移
            mainChart.timeScale().subscribeVisibleLogicalRangeChange(r => volChart.timeScale().setVisibleLogicalRange(r));
            volChart.timeScale().subscribeVisibleLogicalRangeChange(r => mainChart.timeScale().setVisibleLogicalRange(r));

            // 7. 十字游標連動與動態資訊板 (Legend)
            const legend = document.getElementById('legend');
            function updateLegend(param) {
                const time = param.time;
                // 若沒有游標時間，預設顯示最後一筆
                const d = time ? kData.find(x => x.time === time) : kData[kData.length - 1];
                const v = time ? vData.find(x => x.time === time) : vData[vData.length - 1];
                const dt = time ? dtData.find(x => x.time === time) : dtData[dtData.length - 1];
                
                if (d) {
                    let text = `<b>${d.time}</b> &nbsp; 開:${d.open} 高:${d.high} 低:${d.low} 收:<span style="color:#000">${d.close}</span>`;
                    if (v) text += ` &nbsp; | &nbsp; 總量:${v.value}`;
                    // 若當沖大於 0 才顯示紅色當沖字樣
                    if (dt && dt.value > 0) text += ` &nbsp; 沖:<span style="color:#d32f2f; font-weight:bold">${dt.value}</span>`;
                    legend.innerHTML = text;
                }
            }

            mainChart.subscribeCrosshairMove(updateLegend);
            volChart.subscribeCrosshairMove(updateLegend);
            
            // 同步十字線位置
            mainChart.subscribeCrosshairMove(p => {
                if(p.time) volChart.setCrosshairPosition(0, p.time, vSeries);
                else volChart.clearCrosshairPosition();
            });
            volChart.subscribeCrosshairMove(p => {
                if(p.time) mainChart.setCrosshairPosition(0, p.time, candleSeries);
                else mainChart.clearCrosshairPosition();
            });

            // 初始化文字
            updateLegend({});
        </script>
    </body>
    </html>
    """
    
    # 確保傳入的資料皆轉為安全的 JSON 字串，避免 Python 單引號造成 JS 解析錯誤
    html_code = html_template.replace('_KLINE_DATA_', json.dumps(kline_data)) \
                             .replace('_VOLUME_DATA_', json.dumps(volume_data)) \
                             .replace('_DT_VOLUME_DATA_', json.dumps(dt_volume_data))
    
    # 渲染至 Streamlit
    components.html(html_code, height=700)
