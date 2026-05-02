def process_v27_ultimate_radar(df_wide, dead_chip_input, dynamic_dict, static_val, df_price, df_branch_raw, intel_tags):
    if df_wide.empty or len(df_wide) < 2:
        st.warning("⚠️ [V27 終極雷達] 集保股權分佈資料不足 (少於2週)，無法比對趨勢，雷達模組已暫停。")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    if df_price.empty:
        st.warning("⚠️ [V27 終極雷達] 查無歷史股價，系統將以預設基準 (無動態股價加權) 強制推算大戶門檻。")

    try:
        df = df_wide.sort_values('日期', ascending=True).copy()
        df['dt_end'] = pd.to_datetime(df['日期'])
        
        if not df_price.empty:
            df_p = df_price.copy()
            df_p['dt'] = pd.to_datetime(df_p['日期'])
            df_p = df_p.drop_duplicates(subset=['dt']).sort_values('dt')
            df_p['收盤價(元)'] = pd.to_numeric(df_p['收盤價(元)'], errors='coerce')
            df_p['ma20'] = df_p['收盤價(元)'].rolling(20, min_periods=1).mean()
            df = pd.merge_asof(df.sort_values('dt_end'), df_p[['dt', '收盤價(元)', 'ma20']], left_on='dt_end', right_on='dt', direction='backward')
        else: 
            df['收盤價(元)'], df['ma20'] = 0, 0
            
        df['總人數(人)'] = pd.to_numeric(df['總人數(人)'], errors='coerce')
        df['總人數變率(%)'] = (df['總人數(人)'].pct_change() * 100).fillna(0).round(2)
        df['總張數'] = pd.to_numeric(df.get('總張數', 0), errors='coerce').fillna(0)
        
        levels_cols = ['100-200張_比例(%)', '200-400張_比例(%)', '400-600張_比例(%)', '600-800張_比例(%)', '800-1000張_比例(%)', '1000張以上_比例(%)']
        for col in levels_cols:
            df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0.0)
            
        df['pct_1000'] = df['1000張以上_比例(%)']
        df['pct_800'] = df['pct_1000'] + df['800-1000張_比例(%)']
        df['pct_600'] = df['pct_800'] + df['600-800張_比例(%)']
        df['pct_400'] = df['pct_600'] + df['400-600張_比例(%)']
        df['pct_200'] = df['pct_400'] + df['200-400張_比例(%)']
        df['pct_100'] = df['pct_200'] + df['100-200張_比例(%)']

        fake_dict = {}
        if not df_branch_raw.empty:
            df_b_tagged = df_branch_raw[['date', 'securities_trader', 'buy', 'sell']].copy()
            df_b_tagged['tag'] = df_b_tagged['securities_trader'].map(intel_tags).fillna("")
            mask_short = df_b_tagged['tag'].str.contains("隔日突擊|跟風小戶", na=False)
            df_fake = df_b_tagged[mask_short]
            if not df_fake.empty:
                df_fake_daily = df_fake.groupby(['date', 'securities_trader'])[['buy', 'sell']].sum().reset_index()
                df_fake_daily['net_buy_exact'] = (df_fake_daily['buy'] - df_fake_daily['sell']) / 1000
                fake_dict = df_fake_daily.groupby('date').apply(lambda x: x[['securities_trader', 'net_buy_exact']].to_dict('records')).to_dict()

        arr_dates_str = np.sort(df_branch_raw['date'].unique()) if not df_branch_raw.empty else np.array([])
        arr_dates_dt = pd.to_datetime(arr_dates_str) if len(arr_dates_str) > 0 else pd.Series([])

        # ---------------- 向量化核心邏輯開始 ----------------
        
        # 1. 死籌碼安全界線
        df['safe_dead_ratio'] = df['日期'].apply(lambda d: max(0.0, min(99.9, get_dead_chip_info(d, dead_chip_input, dynamic_dict, static_val, "")[0])))

        # 2. 計算動態大戶門檻 (ct)
        base_lots = np.where(df['收盤價(元)'] > 0, 15000 / df['收盤價(元)'], 1000)
        free_float_ratio = np.clip((100 - df['safe_dead_ratio']) / 100, 0.05, 1.0)
        float_1pct_lots = df['總張數'] * free_float_ratio * 0.01

        raw_threshold = np.clip(np.minimum(base_lots, float_1pct_lots), 100, 1000)
        levels = np.array([100, 200, 400, 600, 800, 1000])
        diffs = np.abs(raw_threshold[:, None] - levels)
        df['ct'] = levels[diffs.argmin(axis=1)]

        # 3. 取得當期大戶比例
        conds = [df['ct'] <= 100, df['ct'] <= 200, df['ct'] <= 400, df['ct'] <= 600, df['ct'] <= 800]
        choices = [df['pct_100'], df['pct_200'], df['pct_400'], df['pct_600'], df['pct_800']]
        df['current_large_pct'] = np.select(conds, choices, default=df['pct_1000'])

        # 4. 取得前期大戶比例 (使用 shift 函數，無須再 loop 依賴 prev_row)
        for col in ['pct_100', 'pct_200', 'pct_400', 'pct_600', 'pct_800', 'pct_1000']:
            df[f'prev_{col}'] = df[col].shift(1)

        prev_choices = [df['prev_pct_100'], df['prev_pct_200'], df['prev_pct_400'], df['prev_pct_600'], df['prev_pct_800']]
        df['prev_large_pct_adj'] = np.select(conds, prev_choices, default=df['prev_pct_1000'])

        # 原始變動
        df['raw_chg'] = (df['current_large_pct'] - df['prev_large_pct_adj']).fillna(0).round(2)

        # 5. 計算隔日沖當沖干擾 (f_impact)
        def get_impact(row):
            if row.name == df.index[0] or row['總張數'] <= 0 or len(arr_dates_str) == 0:
                return 0.0, []
            
            d_str, d_dt, ct, total_lots = row['日期'], row['dt_end'], row['ct'], max(1, row['總張數'])
            idx = np.searchsorted(arr_dates_str, d_str, side='right') - 1
            if idx >= 0:
                last_trading_date = arr_dates_str[idx]
                if (d_dt - arr_dates_dt[idx]).days <= 7 and last_trading_date in fake_dict:
                    fake_traders = fake_dict[last_trading_date]
                    f_vol = sum(fr['net_buy_exact'] for fr in fake_traders if fr['net_buy_exact'] >= ct)
                    fri_list = [{"日期": d_str, "分點": fr['securities_trader'], "張數": round(fr['net_buy_exact'])} for fr in fake_traders if fr['net_buy_exact'] >= ct]
                    return (f_vol / total_lots) * 100, fri_list
            return 0.0, []

        impact_res = df.apply(get_impact, axis=1)
        df['f_impact'] = impact_res.apply(lambda x: x[0]).round(2)
        d_fri = [item for sublist in impact_res.apply(lambda x: x[1]) for item in sublist]

        # 純淨變動
        df['p_chg'] = (df['raw_chg'] - df['f_impact']).round(2)
        df.loc[df.index[0], 'p_chg'] = 0.0  # 第一筆初始化

        # 6. 生成診斷文字
        def build_diag(row):
            if row.name == df.index[0]: return "初始化 (基準建立)"
            if row['總張數'] <= 0: return "初始化/總股本為零"
            
            adv = []
            p_chg, f_impact = row['p_chg'], row['f_impact']
            lev = 100 / (100 - row['safe_dead_ratio']) if 0 <= row['safe_dead_ratio'] < 100 else 1
            
            if row['總人數變率(%)'] > 2.0 and p_chg < 0: adv.append(f"散戶增{row['總人數變率(%)']}%，大戶實質倒貨{abs(p_chg)}%")
            else:
                if p_chg * lev > 2.5 and row['收盤價(元)'] > row['ma20']: adv.append(f"站上月線且大戶純淨買超{round(p_chg*lev, 2)}%")
                elif p_chg > 0.4 and row['收盤價(元)'] < row['ma20']: adv.append(f"跌破月線但主力吃貨{p_chg}%")
                elif p_chg < -1.0: adv.append(f"大戶實質流出{abs(p_chg)}%")
                if f_impact > 1.2: adv.append(f"虛胖買盤潛藏{f_impact}%倒貨危機")
                
            return " | ".join(adv) if adv else "盤整"

        df['專家雷達診斷'] = df.apply(build_diag, axis=1)
        
        # 準備輸出 d_math
        df_math = pd.DataFrame({
            "日期": df['日期'], "原始變動": df['raw_chg'], "當沖干擾": df['f_impact'], "純淨變動": df['p_chg']
        }).iloc[1:]

        # 綁定給最終的 DataFrame
        df['純淨大戶變動(%)'] = df['p_chg']
        df['當沖虛胖(%)'] = df['f_impact']
        df['原始大戶變動(%)'] = df['raw_chg']
        df['大戶原持股(%)'] = df['current_large_pct'].round(2)
        
        res_df = df[['日期', '收盤價(元)', '大戶原持股(%)', '總人數變率(%)', '原始大戶變動(%)', '當沖虛胖(%)', '純淨大戶變動(%)', '專家雷達診斷']].sort_values('日期', ascending=False)
        res_df = res_df[~res_df['專家雷達診斷'].str.contains('初始化', na=False)]
        
        return res_df, df_math, pd.DataFrame(d_fri)
        
    except Exception as e:
        st.error(f"🚨 [V27 終極雷達] 運算遭遇異常，模組已強制停止。錯誤原因：`{str(e)}`")
        st.info("💡 提示：這通常是因為該檔股票的特定資料表格式突變，或含有無法解析的空值。系統其他模組不受影響。")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
