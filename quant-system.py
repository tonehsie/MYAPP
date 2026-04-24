@st.cache_data(ttl=3600, show_spinner=False)
def scrape_block_v50(tid, ad):
    if not ad: return pd.DataFrame(), []
    td, bd, dl = ad[:3], [], []
    with requests.Session() as session:
        session.headers.update({"User-Agent": "Mozilla/5.0"})
        def fd(d):
            dtw = d.replace("-", "")
            dtp = f"{int(d.split('-')[0])-1911}/{d.split('-')[1]}/{d.split('-')[2]}"
            rl = []
            try:
                r = session.get(f"https://www.twse.com.tw/rwd/zh/block/BFIAUU?date={dtw}&response=json", timeout=5, verify=False)
                if r.status_code == 200 and isinstance(r.json().get("data"), list):
                    for ro in r.json()["data"]:
                        if tid in str(ro): rl.append([d, "TWSE", ro])
            except: pass
            try:
                r = session.get(f"https://www.tpex.org.tw/www/zh-tw/blockTrade/quote?date={dtp}&id=&response=json", timeout=5, verify=False)
                if r.status_code == 200 and "tables" in r.json() and r.json()["tables"]:
                    if isinstance(r.json()["tables"][0].get("data"), list):
                        for ro in r.json()["tables"][0]["data"]:
                            if tid in str(ro): rl.append([d, "TPEx", ro])
            except: pass
            return rl
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            for data in ex.map(fd, td):
                if data: bd.extend(data)
    if not bd: return pd.DataFrame(), list(set(dl))
    p = []
    for i in bd:
        date, src, row = i
        num_vals = []
        for c in row:
            c_str = re.sub(r'<[^>]+>', '', str(c)).replace(',', '').strip()
            # 排除時間冒號格式，並確保可以轉換為數字
            if c_str and ':' not in c_str and c_str.replace('.', '', 1).isdigit():
                num_vals.append(float(c_str))
        
        # 依據台股鉅額交易明細表慣例，最後三個數字依序必為：成交量、成交價、成交金額
        if len(num_vals) >= 3:
            amt = num_vals[-1]
            price = num_vals[-2]
            vol = num_vals[-3]
            
            # 轉換單位為萬與張 (防呆機制：大於特定數值才除以倍數，避免原資料已是萬或張)
            amt_wan = amt / 10000 if amt > 100000 else amt
            vol_zhang = vol / 1000 if vol > 1000 else vol
            
            tt = next((re.sub(r'<[^>]+>', '', str(c)).strip() for c in row if any(x in str(c) for x in ["配對","交易","單一","組合","逐筆"])), "鉅額")
            
            p.append({"日期": date, "交易別": tt, "成交量(張)": int(vol_zhang), "成交價(元)": round(price, 2), "成交金額(萬元)": int(amt_wan)})
            
    return pd.DataFrame(p).sort_values("日期", ascending=False), list(set(dl))
