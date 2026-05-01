為了將股市老手的盤感徹底公式化，並無縫融入你現有的全息量化系統（V71.12.4）架構中，我為你重新設計了四大核心運算模組。

由於你提供的完整應用程式碼較長，我將重構最具關鍵性的邏輯函數。你可以直接將以下函數替換或新增至你原本的程式碼中，並在主程式區塊進行呼叫。

### 一、 監管套利預警模組（改寫 `calculate_disposition_thresholds`）
現代主力會精算監管紅線來決定洗盤節奏。新版模組加入了法規中「近 6 日累積漲跌幅超過 32%」與「連續當沖佔比超過 60%」的判定標準。這能幫助系統在主管機關公告「注意股」之前，提前發出流動性枯竭的警告。

```python
def calculate_disposition_thresholds_v2(df_price, df_day_trade, total_lots):
    if df_price.empty or len(df_price) < 6: return None
    df_asc = df_price.sort_values('日期', ascending=True).reset_index(drop=True)
    closes = df_asc['收盤價(元)'].tolist()
    lows = df_asc['最低價(元)'].tolist()
    volumes_lots = df_asc['成交量(張)'].tolist()

    res = {
        'limit_6d': closes[-6] * 1.32 if len(closes) >= 6 else None, # 6日漲幅32%紅線
        'limit_amp': min(lows[-5:]) * 1.25 if len(lows) >= 5 else None,
        'limit_30d': closes[-30] * 2.0 if len(closes) >= 30 else None,
        'limit_60d': closes[-60] * 2.3 if len(closes) >= 60 else None,
    }

    # 加入當沖過熱紅線預測 (連續兩日大於60%)
    res['day_trade_warning'] = False
    if not df_day_trade.empty and len(df_day_trade) >= 2:
        dt_vol = df_day_trade['當沖總張數'].tolist()[:6]
        vol_recent = volumes_lots[-6:]
        dt_ratios = [d / v if v > 0 else 0 for d, v in zip(dt_vol, reversed(vol_recent))]
        if len(dt_ratios) >= 2 and dt_ratios > 0.6 and dt_ratios[1] > 0.6:
            res['day_trade_warning'] = True

    if total_lots > 0:
        recent_5d_vol_lots = sum(volumes_lots[-5:])
        res['current_5d_turnover'] = (recent_5d_vol_lots / total_lots) * 100
        # 週轉率極端過高紅線 (10%以上)
        res['turnover_warning'] = res['current_5d_turnover'] > 10.0 
    return res
```

### 二、 籌碼甜區與極端過濾模組（升級 `process_tdcc_dynamic`）
大戶籌碼並不是越集中越好。新模組加入了老手判斷的「籌碼甜區（40% ~ 70%）」以及「極度集中高危險區（>80%）」，避免買入流動性過低、容易無量崩跌的死水盤。

```python
def process_tdcc_dynamic_v2(df_share_wide, df_price, dead_chip_input, dynamic_dict, static_val, chip_engine):
    if df_share_wide.empty or df_price.empty: return pd.DataFrame()
    # (保留原有的資料合併與整理邏輯...)
    df_s, df_p = df_share_wide.copy(), df_price.copy()
    df_s['dt'], df_p['dt'] = pd.to_datetime(df_s['日期']), pd.to_datetime(df_p['日期'])
    df_p = df_p.drop_duplicates(subset=['dt']).sort_values('dt')
    df_m = pd.merge_asof(df_s.sort_values('dt'), df_p[['dt', '收盤價(元)']], on='dt', direction='backward').sort_values('dt', ascending=False)
    
    # 簡化展示大戶加總，保留你原本的 get_pct 邏輯
    df_m['pct_1000'] = pd.to_numeric(df_m.get('1000張以上_比例(%)', 0), errors='coerce').fillna(0.0)
    
    out =
    for row in df_m.to_dict('records'):
        p = row.get('收盤價(元)', 0)
        if pd.isna(p) or p <= 0: continue
        cur_dead, cl = get_dead_chip_info(row['日期'], dead_chip_input, dynamic_dict, static_val, chip_engine)
        total_lots = row.get('總張數', 0)
        safe_dead_ratio = max(0.0, min(99.9, cur_dead))
        
        # 取得大戶真實比例
        ct = get_smart_threshold(p, total_lots, safe_dead_ratio)
        lp = row.get('pct_1000', 0) # 假設以千張大戶為基準
        
        # 導入老手甜區判斷邏輯
        st_val = "籌碼渙散"
        if 40.0 <= lp <= 70.0:
            st_val = "波段甜區 (易吸量推升)"
        elif lp > 80.0:
            st_val = "極度集中 (防無量倒貨)"
        elif lp > 70.0:
            st_val = "高度鎖碼"

        out.append({
            "日期": row['日期'], 
            "收盤價(元)": round(float(p), 2), 
            "大戶原持股(%)": round(lp, 2), 
            "董監死籌碼(%)": f"{float(safe_dead_ratio):.2f}%", 
            "實戰判定": st_val
        })
    return pd.DataFrame(out)
```

### 三、 資金接力與主力成交力模組（優化 `process_branch_diff`）
為了看穿真實的買盤力道，這裡加入「主力成交力」的計算公式（Top 15 淨買賣超佔總成交量的比例）。數值越大，代表籌碼被極少數大戶收走的力道越強。

```python
def process_branch_diff_v2(df_raw, actual_dates, fire_thresh, period_days=10):
    if df_raw.empty or not actual_dates: return pd.DataFrame()
    out =
    branch_grouped = dict(tuple(df_raw[['date', 'securities_trader', 'buy', 'sell']].groupby('date')))
    for d in actual_dates[:period_days]:
        if d not in branch_grouped: continue
        df_d = branch_grouped[d]
        
        # 計算當日總成交量 (以單邊計算)
        daily_total_vol = df_d['buy'].sum() 
        if daily_total_vol == 0: continue
            
        # 計算 Top 15 買賣家
        g_net = df_d.groupby('securities_trader').apply(lambda x: x['buy'].sum() - x['sell'].sum())
        top_15_buy_vol = g_net[g_net > 0].nlargest(15).sum()
        top_15_sell_vol = abs(g_net[g_net < 0].nsmallest(15).sum())
        
        # 老手指標：主力成交力 (Main Power)
        main_power = (top_15_buy_vol - top_15_sell_vol) / daily_total_vol * 100
        
        buy_count = df_d[df_d['buy'] > 0]['securities_trader'].nunique()
        sell_count = df_d[df_d['sell'] > 0]['securities_trader'].nunique()
        diff_count = buy_count - sell_count
        
        diag =
        if main_power > 15: diag.append(f"主力重兵集結 (買力 {main_power:.1f}%)")
        elif main_power < -15: diag.append(f"大戶強力倒貨 (賣力 {abs(main_power):.1f}%)")
        
        if diff_count > 50 and main_power < 0: diag.append("散戶螞蟻搬象接刀")
            
        out.append({
            "日期": d, 
            "活躍家數": df_d['securities_trader'].nunique(), 
            "買賣家數差": diff_count, 
            "主力成交力(%)": round(main_power, 2), 
            "鷹眼診斷": " | ".join(diag) if diag else "中性換手"
        })
    return pd.DataFrame(out)
```

### 四、 微觀五檔防騙線介面（新增即時數據擴充）
由於你的系統目前串接的是 FinMind 的盤後日線資料，無法看到盤中微觀的五檔掛單。為了解決主力「假牆撤單」的騙線手法，我為你編寫了一個獨立的 Tick Data 解析模組。未來若你串接具備逐筆明細的即時 API（如 Shioaji 或 XQ），便可直接套用此邏輯來辨識內外盤失衡。

```python
def detect_orderbook_spoofing(order_book_tick, trade_tick):
    """
    未來即時串接擴充模組：用於破解盤中假牆與內外盤騙線
    order_book_tick: 包含 bid_vol_1~5, ask_vol_1~5 
    trade_tick: 包含最新成交價量與內外盤標記 (inside/outside)
    """
    # 1. 內外盤失衡判定
    total_ask_vol = sum([order_book_tick[f'ask_vol_{i}'] for i in range(1, 6)])
    total_bid_vol = sum([order_book_tick[f'bid_vol_{i}'] for i in range(1, 6)])
    
    # 2. 判定賣壓假牆：上方掛滿大單，但真實成交多在內盤
    if total_ask_vol > total_bid_vol * 1.5:
        if trade_tick['trade_type'] == 'inside':
            return "短線偏空：賣方主動讓價，買盤被動承接"
        elif trade_tick['cancel_rate_ask'] > 0.8:
            return "誘空假牆：上方大單頻繁撤單，準備向上突圍"
            
    # 3. 判定買盤假牆：下方掛滿大單，但真實成交多在外盤
    if total_bid_vol > total_ask_vol * 1.5:
        if trade_tick['trade_type'] == 'outside':
            return "短線偏多：買方主動吃價，賣盤被動成交"
        elif trade_tick['cancel_rate_bid'] > 0.8:
            return "誘多假牆：下方大單為虛假支撐，慎防破底"

    return "結構正常"
```

### 系統整合建議：
在你的主程式 `if run_btn:` 執行區塊中，請確保傳入 `df_day_trade` 給新的處置預測模組，以完整發揮防禦效果：
```python
# 取得當沖資料後
df_day_trade = process_day_trading(ds_dict.get("TaiwanStockDayTrading", pd.DataFrame()))

# 將升級後的 V2 函數替換進去
disp_warn = calculate_disposition_thresholds_v2(df_price, df_day_trade, current_total_shares)
df_b_diff = process_branch_diff_v2(df_b_raw, dates, firepower_threshold, period_days=15)
df_s_dyn = process_tdcc_dynamic_v2(df_s_wide, df_price, parsed_dead_chip, dynamic_dict, s_val, chip_eng)
```

如此一來，你的系統在生成最終 AI 報告與表格時，就能自動將大戶甜區、短線主力接力數據以及法規監管紅線一併納入運算，將事後諸葛的看圖說故事，進階為事前預判的量化兵推。
