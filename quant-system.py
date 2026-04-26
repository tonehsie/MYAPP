# --- 防彈版 API 額度查詢 (移除容易報錯的快取與全域 session) ---
def get_api_usage(token):
    try:
        import requests
        r = requests.get(f"https://api.web.finmindtrade.com/v2/user_info?token={token}", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict):
                return data.get("user_count", 0), data.get("api_request_limit", 0)
    except Exception:
        pass
    return "未知", "未知"

st.sidebar.header("戰術參數控制面板")
kline_days = st.sidebar.slider("K線顯示天數 (圖表景深)", 30, 600, 270, 10)
lookback_days = st.sidebar.selectbox("長線籌碼回溯天數 (全局黏著度分母)", [20, 60, 90, 120], index=1)
stickiness_threshold = st.sidebar.slider("主力黏著度門檻 (%)", 10.0, 80.0, 50.0, 5.0)
footprint_days = st.sidebar.slider("足跡明細追蹤天數 (顯示範圍)", 3, 60, 20, 1)
footprint_rows = st.sidebar.slider("足跡矩陣顯示筆數 (多空各 N 名)", 5, 50, 15, 5)
firepower_threshold = st.sidebar.slider("買方火力倍數門檻", 1.0, 5.0, 1.5, 0.1)

st.sidebar.divider()
st.sidebar.markdown("### AI 幾何形態與技術線")
enable_pattern = st.sidebar.checkbox("啟動 AI 幾何形態掃描", value=True)

pattern_mode = st.sidebar.selectbox("形態顯示模式", [
    "全自動智能辨識 (Auto)", 
    "反轉：W底 (雙重底)", "反轉：M頭 (雙重頂)", 
    "反轉：頭肩底", "反轉：頭肩頂", 
    "反轉：三重底", "反轉：三重頂",
    "反轉：V型反轉",
    "連續：對稱三角形", 
    "連續：上升三角形", "連續：下降三角形",
    "連續：上升楔形", "連續：下降楔形",
    "連續：矩形 (箱型整理)"
])

lr_days = st.sidebar.slider("線性迴歸通道天數 (動態趨勢)", 20, 120, 20, 5)
pattern_order = st.sidebar.slider("形態辨識靈敏度 (Order)", 2, 20, 5, 1)

st.sidebar.divider()
st.sidebar.markdown("### 淨化籌碼引擎")
filter_day_trade = st.sidebar.checkbox("剔除散戶與當沖，計算純淨加權均價", value=True)
st.sidebar.divider()
ma_short = st.sidebar.number_input("短均線 (天)", min_value=1, max_value=20, value=10)
ma_mid = st.sidebar.number_input("中均線/防守線 (天)", min_value=20, max_value=100, value=60)
ma_long = st.sidebar.number_input("長均線 (天)", min_value=100, max_value=300, value=240)

# --- 主介面 ---
st.title("全息量化系統 (V60.56 終極完全體)")
try:
    user_count, api_limit = get_api_usage(FINMIND_TOKEN)
    usage_text = f" | FinMind 額度: {user_count} / {api_limit}"
except Exception:
    usage_text = " | FinMind 額度: 無法取得"

st.caption(f"V60.56：修正主力均價倖存者偏差、加入重倉大戶與程式造市分離、校準隔日沖干擾與法人重疊防呆機制。{usage_text}")
