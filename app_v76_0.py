import datetime as dt
import json
import logging
import os
import re
from io import StringIO

import altair as alt
import numpy as np
import pandas as pd
import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


st.set_page_config(
    page_title="股票研究資料產生器",
    layout="wide",
    initial_sidebar_state="expanded",
)

LOGGER = logging.getLogger("stock_research")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

API_URL = "https://api.finmindtrade.com/api/v4/data"
SHARES_PER_LOT = 1000
LOTS_PER_YI_SHARES = 100000


def get_secret(name: str, default: str = "") -> str:
    try:
        if name in st.secrets:
            return str(st.secrets[name]).strip()
        if "general" in st.secrets and name in st.secrets["general"]:
            return str(st.secrets["general"][name]).strip()
    except Exception as exc:
        LOGGER.warning("讀取 secret 失敗: %s", exc)
    return str(os.getenv(name, default)).strip()


FINMIND_TOKEN = get_secret("FINMIND_TOKEN")


def make_session() -> requests.Session:
    session = requests.Session()
    if FINMIND_TOKEN:
        session.headers.update({"Authorization": f"Bearer {FINMIND_TOKEN}"})
    session.headers.update({"User-Agent": "stock-research-app/1.0"})
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


SESSION = make_session()


def safe_num(value, fill=0.0):
    if isinstance(value, pd.Series):
        if pd.api.types.is_numeric_dtype(value):
            return value.fillna(fill)
        cleaned = (
            value.astype("string")
            .str.replace(",", "", regex=False)
            .str.replace("%", "", regex=False)
            .str.strip()
        )
        return pd.to_numeric(cleaned, errors="coerce").fillna(fill)
    if pd.isna(value):
        return fill
    try:
        return float(str(value).replace(",", "").replace("%", "").strip())
    except Exception:
        return fill


def shares_to_lots(value):
    converted = safe_num(value) / SHARES_PER_LOT
    if isinstance(converted, pd.Series):
        return converted.round().astype(int)
    return int(round(float(converted)))


def lots_to_yi_shares(lots: float) -> float:
    return float(lots) / LOTS_PER_YI_SHARES


def format_signed(value, suffix=""):
    value = safe_num(value)
    sign = "+" if value > 0 else ""
    return f"{sign}{value:,.0f}{suffix}"


@st.cache_data(ttl=900, max_entries=256, show_spinner=False)
def finmind_data(dataset: str, stock_id: str = "", start_date: str = "", end_date: str = "") -> pd.DataFrame:
    params = {"dataset": dataset}
    if stock_id:
        params["data_id"] = stock_id
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    response = SESSION.get(API_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data")
    if data is None:
        msg = payload.get("msg") or payload.get("message") or "FinMind 無 data 欄位"
        raise ValueError(f"{dataset}: {msg}")
    return pd.DataFrame(data)


def fetch_dataset(dataset: str, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
    try:
        return finmind_data(dataset, stock_id, start_date, end_date)
    except Exception as exc:
        LOGGER.warning("%s 讀取失敗: %s", dataset, exc)
        return pd.DataFrame()


def process_price(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()
    rename = {
        "date": "日期",
        "open": "開盤",
        "max": "最高",
        "min": "最低",
        "close": "收盤",
        "spread": "漲跌",
    }
    df = raw.rename(columns=rename).copy()
    for col in ["開盤", "最高", "最低", "收盤", "漲跌"]:
        if col in df.columns:
            df[col] = safe_num(df[col])
    vol_col = "Trading_Volume" if "Trading_Volume" in df.columns else "Trading_volume"
    df["成交量(張)"] = shares_to_lots(df[vol_col]) if vol_col in df.columns else 0
    df["日期"] = pd.to_datetime(df["日期"], errors="coerce")
    df = df.dropna(subset=["日期"]).sort_values("日期").reset_index(drop=True)
    return df[["日期", "開盤", "最高", "最低", "收盤", "漲跌", "成交量(張)"]]


def add_technical_indicators(price: pd.DataFrame, short_ma: int, mid_ma: int, long_ma: int, lr_days: int) -> pd.DataFrame:
    if price.empty:
        return price
    df = price.copy()
    for ma in [short_ma, mid_ma, long_ma]:
        df[f"MA{ma}"] = df["收盤"].rolling(ma, min_periods=1).mean()
    df["量均20"] = df["成交量(張)"].rolling(20, min_periods=1).mean()
    df["乖離中線(%)"] = ((df["收盤"] - df[f"MA{mid_ma}"]) / df[f"MA{mid_ma}"].replace(0, np.nan) * 100).round(2)

    df["LR_Mid"] = np.nan
    df["LR_Upper"] = np.nan
    df["LR_Lower"] = np.nan
    window = min(int(lr_days), len(df))
    if window >= 2:
        segment = df.tail(window)
        x = np.arange(len(segment), dtype=float)
        y = segment["收盤"].to_numpy(dtype=float)
        slope, intercept = np.polyfit(x, y, 1)
        pred = slope * x + intercept
        err = y - pred
        std = float(np.std(err, ddof=1)) if len(err) > 2 else float(np.std(err))
        idx = segment.index
        df.loc[idx, "LR_Mid"] = pred
        df.loc[idx, "LR_Upper"] = pred + 2 * std
        df.loc[idx, "LR_Lower"] = pred - 2 * std
    return df


def detect_swings(price: pd.DataFrame, order: int = 5) -> tuple[list[dict], list[dict]]:
    if price.empty or len(price) < order * 2 + 1:
        return [], []
    highs = []
    lows = []
    high_values = price["最高"].to_numpy()
    low_values = price["最低"].to_numpy()
    dates = price["日期"].dt.strftime("%Y-%m-%d").to_numpy()
    for i in range(order, len(price) - order):
        h_window = high_values[i - order : i + order + 1]
        l_window = low_values[i - order : i + order + 1]
        if high_values[i] == np.nanmax(h_window):
            highs.append({"日期": dates[i], "價位": float(high_values[i]), "index": i})
        if low_values[i] == np.nanmin(l_window):
            lows.append({"日期": dates[i], "價位": float(low_values[i]), "index": i})
    return highs, lows


def analyze_price_structure(price: pd.DataFrame, order: int) -> dict:
    highs, lows = detect_swings(price, order)
    latest = float(price["收盤"].iloc[-1]) if not price.empty else 0.0
    recent_high = max(highs[-3:], key=lambda x: x["價位"], default=None)
    recent_low = min(lows[-3:], key=lambda x: x["價位"], default=None)
    pattern = "區間整理"
    signal = "neutral"
    reason = "尚未形成明確型態，先以支撐壓力與均線位置追蹤。"

    if len(lows) >= 2 and len(highs) >= 1:
        l1, l2 = lows[-2], lows[-1]
        between_highs = [h for h in highs if l1["index"] < h["index"] < l2["index"]]
        if between_highs and l1["價位"] > 0:
            neckline = max(between_highs, key=lambda x: x["價位"])
            diff = abs(l1["價位"] - l2["價位"]) / l1["價位"]
            if diff <= 0.04 and latest > neckline["價位"]:
                pattern = "W 底突破"
                signal = "bullish"
                reason = f"兩個低點接近，且收盤突破頸線 {neckline['價位']:.2f}。"
            elif diff <= 0.04:
                pattern = "W 底觀察"
                signal = "watch_bull"
                reason = f"兩個低點接近，但尚未突破頸線 {neckline['價位']:.2f}。"

    if len(highs) >= 2 and len(lows) >= 1:
        h1, h2 = highs[-2], highs[-1]
        between_lows = [l for l in lows if h1["index"] < l["index"] < h2["index"]]
        if between_lows and h1["價位"] > 0:
            neckline = min(between_lows, key=lambda x: x["價位"])
            diff = abs(h1["價位"] - h2["價位"]) / h1["價位"]
            if diff <= 0.04 and latest < neckline["價位"]:
                pattern = "M 頭跌破"
                signal = "bearish"
                reason = f"兩個高點接近，且收盤跌破頸線 {neckline['價位']:.2f}。"
            elif diff <= 0.04 and signal == "neutral":
                pattern = "M 頭觀察"
                signal = "watch_bear"
                reason = f"兩個高點接近，但尚未跌破頸線 {neckline['價位']:.2f}。"

    return {
        "型態": pattern,
        "訊號": signal,
        "原因": reason,
        "近期壓力": recent_high["價位"] if recent_high else np.nan,
        "近期支撐": recent_low["價位"] if recent_low else np.nan,
        "高點": highs[-8:],
        "低點": lows[-8:],
    }


def process_institution(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty or "date" not in raw.columns:
        return pd.DataFrame()
    df = raw.copy()
    for col in ["buy", "sell"]:
        if col in df.columns:
            df[col] = safe_num(df[col])
    pivot = df.pivot_table(index="date", columns="name", values=["buy", "sell"], aggfunc="sum", fill_value=0)
    pivot.columns = ["_".join(map(str, c)).strip("_") for c in pivot.columns]
    out = pd.DataFrame({"日期": pd.to_datetime(pivot.index)})
    zero = pd.Series(0, index=pivot.index)

    def col(name: str) -> pd.Series:
        return pivot[name] if name in pivot.columns else zero

    foreign = shares_to_lots(col("buy_Foreign_Investor") - col("sell_Foreign_Investor"))
    trust = shares_to_lots(col("buy_Investment_Trust") - col("sell_Investment_Trust"))
    dealer_self = shares_to_lots(
        (col("buy_Dealer_self") if "buy_Dealer_self" in pivot.columns else col("buy_Dealer"))
        - (col("sell_Dealer_self") if "sell_Dealer_self" in pivot.columns else col("sell_Dealer"))
    )
    dealer_hedge = shares_to_lots(col("buy_Dealer_Hedging") - col("sell_Dealer_Hedging"))
    out["外資(張)"] = foreign.to_numpy()
    out["投信(張)"] = trust.to_numpy()
    out["自營商自行(張)"] = dealer_self.to_numpy()
    out["自營商避險(張)"] = dealer_hedge.to_numpy()
    out["三大法人合計(張)"] = out[["外資(張)", "投信(張)", "自營商自行(張)", "自營商避險(張)"]].sum(axis=1)
    return out.sort_values("日期").reset_index(drop=True)


def process_margin(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty or "date" not in raw.columns:
        return pd.DataFrame()
    df = raw.rename(columns={"date": "日期"}).copy()
    df["日期"] = pd.to_datetime(df["日期"])
    mapping = {
        "MarginPurchaseTodayBalance": "融資餘額(張)",
        "MarginPurchaseYesterdayBalance": "昨日融資餘額(張)",
        "ShortSaleTodayBalance": "融券餘額(張)",
        "ShortSaleYesterdayBalance": "昨日融券餘額(張)",
        "OffsetLoanAndShort": "資券相抵(張)",
    }
    for src, dst in mapping.items():
        df[dst] = safe_num(df[src]).round().astype(int) if src in df.columns else 0
    df["融資增減(張)"] = df["融資餘額(張)"] - df["昨日融資餘額(張)"]
    df["融券增減(張)"] = df["融券餘額(張)"] - df["昨日融券餘額(張)"]
    return df[["日期", "融資餘額(張)", "融資增減(張)", "融券餘額(張)", "融券增減(張)", "資券相抵(張)"]].sort_values("日期")


def process_day_trade(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty or "date" not in raw.columns:
        return pd.DataFrame()
    df = raw.rename(columns={"date": "日期"}).copy()
    df["日期"] = pd.to_datetime(df["日期"])
    vol_col = "DayTradingVolume" if "DayTradingVolume" in df.columns else "Volume"
    df["當沖量(張)"] = shares_to_lots(df[vol_col]) if vol_col in df.columns else 0
    return df[["日期", "當沖量(張)"]].sort_values("日期")


def clean_tdcc_level(value) -> int:
    text = str(value)
    if text.strip().isdigit():
        code = int(text.strip())
        if 1 <= code <= 15:
            return code
    nums = [int(x) for x in re.findall(r"\d+", text)]
    if not nums:
        return 0
    low = nums[0]
    if "999" in text or low < 1:
        return 1
    if low < 5:
        return 2
    if low < 10:
        return 3
    if low < 15:
        return 4
    if low < 20:
        return 5
    if low < 30:
        return 6
    if low < 40:
        return 7
    if low < 50:
        return 8
    if low < 100:
        return 9
    if low < 200:
        return 10
    if low < 400:
        return 11
    if low < 600:
        return 12
    if low < 800:
        return 13
    if low < 1000:
        return 14
    return 15


def process_tdcc(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty or "HoldingSharesLevel" not in raw.columns:
        return pd.DataFrame()
    df = raw.copy()
    df["日期"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["日期"])
    df = df[~df["HoldingSharesLevel"].astype(str).str.contains("差異|合計|總計", na=False)]
    df["級距碼"] = df["HoldingSharesLevel"].apply(clean_tdcc_level)
    df = df[df["級距碼"] > 0]
    volume_col = "HoldingShares" if "HoldingShares" in df.columns else "unit"
    df["張數"] = shares_to_lots(df[volume_col]) if volume_col in df.columns else 0
    df["人數"] = safe_num(df["people"]).astype(int) if "people" in df.columns else 0
    wide = df.pivot_table(index="日期", columns="級距碼", values="張數", aggfunc="sum", fill_value=0)
    out = pd.DataFrame({"日期": wide.index})
    out["總張數"] = wide.sum(axis=1).to_numpy()
    large_levels = [10, 11, 12, 13, 14, 15]
    out["100張以上(%)"] = (wide[[c for c in large_levels if c in wide.columns]].sum(axis=1) / wide.sum(axis=1).replace(0, np.nan) * 100).fillna(0).round(2).to_numpy()
    out["400張以上(%)"] = (wide[[c for c in [12, 13, 14, 15] if c in wide.columns]].sum(axis=1) / wide.sum(axis=1).replace(0, np.nan) * 100).fillna(0).round(2).to_numpy()
    out["1000張以上(%)"] = (wide[15] / wide.sum(axis=1).replace(0, np.nan) * 100).fillna(0).round(2).to_numpy() if 15 in wide.columns else 0
    out = out.sort_values("日期")
    out["400張以上週變動"] = out["400張以上(%)"].diff().round(2)
    return out.reset_index(drop=True)


def normalize_branch(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty or "date" not in raw.columns:
        return pd.DataFrame()
    df = raw.rename(columns={"buy_volume": "buy", "sell_volume": "sell"}).copy()
    required = {"date", "securities_trader", "buy", "sell"}
    if not required.issubset(df.columns):
        return pd.DataFrame()
    df["日期"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["日期"])
    df["分點"] = df["securities_trader"].astype(str).str.strip()
    df["買進股"] = safe_num(df["buy"]).clip(lower=0)
    df["賣出股"] = safe_num(df["sell"]).clip(lower=0)
    df["淨買股"] = df["買進股"] - df["賣出股"]
    df["買進(張)"] = shares_to_lots(df["買進股"])
    df["賣出(張)"] = shares_to_lots(df["賣出股"])
    df["淨買(張)"] = shares_to_lots(df["淨買股"])
    if "buy_price" in df.columns:
        df["買均價"] = safe_num(df["buy_price"])
    elif "price" in df.columns:
        df["買均價"] = safe_num(df["price"])
    else:
        df["買均價"] = np.nan
    return df[["日期", "分點", "買進股", "賣出股", "淨買股", "買進(張)", "賣出(張)", "淨買(張)", "買均價"]]


def top_branch_summary(branch: pd.DataFrame, top_n: int) -> tuple[pd.DataFrame, float, list[str]]:
    if branch.empty:
        return pd.DataFrame(), 0.0, []
    grouped = branch.groupby("分點", as_index=False).agg(
        買進股=("買進股", "sum"),
        賣出股=("賣出股", "sum"),
        淨買股=("淨買股", "sum"),
        買均價分子=("買進股", "sum"),
    )
    buy_price_map = (
        branch.assign(_amt=branch["買進股"] * branch["買均價"].fillna(0))
        .groupby("分點")
        .agg(買進金額=("_amt", "sum"), 買進股=("買進股", "sum"))
    )
    grouped = grouped.merge(buy_price_map, on="分點", how="left", suffixes=("", "_price"))
    grouped["買進(張)"] = shares_to_lots(grouped["買進股"])
    grouped["賣出(張)"] = shares_to_lots(grouped["賣出股"])
    grouped["淨買(張)"] = shares_to_lots(grouped["淨買股"])
    grouped["買均價"] = np.where(grouped["買進股_price"] > 0, grouped["買進金額"] / grouped["買進股_price"], np.nan)
    top = grouped.sort_values("淨買(張)", ascending=False).head(top_n).copy()
    top["買均價"] = top["買均價"].round(2)
    net_shares = top[top["淨買股"] > 0]["淨買股"].sum()
    cost = (
        (top[top["淨買股"] > 0]["買均價"] * top[top["淨買股"] > 0]["淨買股"]).sum() / net_shares
        if net_shares > 0
        else 0.0
    )
    names = top["分點"].tolist()
    return top[["分點", "買進(張)", "賣出(張)", "淨買(張)", "買均價"]], round(float(cost), 2), names


def make_kline_chart(df: pd.DataFrame, short_ma: int, mid_ma: int, long_ma: int):
    if df.empty:
        return None
    chart_df = df.copy()
    chart_df["漲"] = chart_df["收盤"] >= chart_df["開盤"]
    base = alt.Chart(chart_df).encode(x=alt.X("日期:T", title="日期"))
    wick = base.mark_rule().encode(
        y=alt.Y("最低:Q", title="價格"),
        y2="最高:Q",
        color=alt.condition("datum.漲", alt.value("#d32f2f"), alt.value("#2e7d32")),
    )
    body = base.mark_bar(size=5).encode(
        y="開盤:Q",
        y2="收盤:Q",
        color=alt.condition("datum.漲", alt.value("#d32f2f"), alt.value("#2e7d32")),
        tooltip=["日期:T", "開盤:Q", "最高:Q", "最低:Q", "收盤:Q", "成交量(張):Q"],
    )
    lines = []
    colors = {short_ma: "#1565c0", mid_ma: "#ef6c00", long_ma: "#6a1b9a"}
    for ma in [short_ma, mid_ma, long_ma]:
        lines.append(base.mark_line(size=1.6, color=colors[ma]).encode(y=f"MA{ma}:Q"))
    lr_lines = []
    for col, color in [("LR_Upper", "#8d6e63"), ("LR_Mid", "#455a64"), ("LR_Lower", "#8d6e63")]:
        if col in chart_df.columns and chart_df[col].notna().any():
            lr_lines.append(base.mark_line(size=1, strokeDash=[5, 4], color=color).encode(y=f"{col}:Q"))
    price_chart = wick + body
    for layer in lines + lr_lines:
        price_chart = price_chart + layer
    price_chart = price_chart.properties(height=470)
    volume_chart = base.mark_bar(color="#90a4ae").encode(
        y=alt.Y("成交量(張):Q", title="成交量(張)")
    ).properties(height=130)
    return alt.vconcat(price_chart, volume_chart).resolve_scale(x="shared")


def merge_daily_research(price, inst, margin, day_trade) -> pd.DataFrame:
    if price.empty:
        return pd.DataFrame()
    daily = price[["日期", "收盤", "漲跌", "成交量(張)", "乖離中線(%)"]].copy()
    for df in [inst, margin, day_trade]:
        if not df.empty:
            daily = daily.merge(df, on="日期", how="left")
    fill_cols = [c for c in daily.columns if c != "日期"]
    daily[fill_cols] = daily[fill_cols].fillna(0)
    return daily.sort_values("日期", ascending=False).reset_index(drop=True)


def build_research_result(
    stock_id: str,
    name: str,
    daily: pd.DataFrame,
    tdcc: pd.DataFrame,
    branch_top: pd.DataFrame,
    branch_cost: float,
    price_structure: dict,
    mid_ma: int,
) -> dict:
    latest = daily.iloc[0] if not daily.empty else pd.Series(dtype=object)
    close = float(latest.get("收盤", 0))
    ma_bias = float(latest.get("乖離中線(%)", 0))
    smart_net = int(branch_top["淨買(張)"].sum()) if not branch_top.empty else 0
    inst_net = int(latest.get("三大法人合計(張)", 0))
    margin_chg = int(latest.get("融資增減(張)", 0))
    day_trade = int(latest.get("當沖量(張)", 0))
    volume = int(latest.get("成交量(張)", 0))
    day_trade_ratio = (day_trade / volume * 100) if volume > 0 else 0
    defense_bias = ((close - branch_cost) / branch_cost * 100) if branch_cost > 0 else 0

    tdcc_latest = tdcc.iloc[-1] if not tdcc.empty else pd.Series(dtype=object)
    c_value = float(tdcc_latest.get("400張以上(%)", 0))
    c_flow = float(tdcc_latest.get("400張以上週變動", 0))

    warnings = []
    positives = []
    if smart_net > 0 and inst_net > 0:
        positives.append("主力分點與法人方向同為買超，短線買盤一致。")
    if smart_net < 0 and inst_net < 0:
        warnings.append("主力分點與法人同步賣超，籌碼面偏弱。")
    if margin_chg > max(300, smart_net * 0.6) and smart_net > 0:
        warnings.append("融資增幅相對主力買超偏高，需防假主力或高槓桿鎖碼。")
    if day_trade_ratio > 45:
        warnings.append(f"當沖占成交量 {day_trade_ratio:.1f}%，短線雜訊偏高。")
    if defense_bias < -3:
        warnings.append(f"收盤跌破主力成本估算 {defense_bias:.1f}%，防守線失守。")
    elif 0 <= defense_bias <= 5:
        positives.append("股價貼近主力成本區，具備觀察價值。")
    if c_value >= 40 and c_flow > 0:
        positives.append("集保大戶存量與週變動同向偏多。")
    if c_value < 25 and c_flow < 0:
        warnings.append("集保大戶存量偏低且續減，籌碼較鬆散。")

    signal = price_structure.get("訊號", "neutral")
    if signal == "bullish" and smart_net > 0:
        conclusion = "形態突破 / 主力點火，偏多追蹤"
        action = "技術型態與主力分點同步偏多，可列入強勢觀察名單，防守以主力成本與中期均線為主。"
    elif signal == "bearish" and smart_net < 0:
        conclusion = "形態轉弱 / 主力撤退，風險優先"
        action = "技術面與籌碼面同步轉弱，應先控風險，反彈不宜追高。"
    elif defense_bias < -5 and smart_net < 0:
        conclusion = "跌破防守 / 籌碼撤退，嚴禁摸底"
        action = "股價跌破主力成本且分點賣超，任何反彈都需先視為修正中的反抽。"
    elif close > 0 and ma_bias > 8 and smart_net < 0:
        conclusion = "通道過熱 / 逢高派發警訊"
        action = "股價偏離中線且主力轉賣，偏向高檔調節，追價風險升高。"
    elif smart_net > 0 and c_flow >= 0:
        conclusion = "籌碼偏多 / 等待價格確認"
        action = "籌碼端偏多，但仍需觀察價格是否站穩均線與突破壓力。"
    else:
        conclusion = "多空混合 / 保留觀察"
        action = "目前訊號未完全同向，適合納入觀察清單，等待價格或籌碼其中一方表態。"

    return {
        "股票": f"{stock_id} {name}".strip(),
        "收盤": close,
        f"中線乖離MA{mid_ma}(%)": ma_bias,
        "主力前排淨買(張)": smart_net,
        "法人合計(張)": inst_net,
        "融資增減(張)": margin_chg,
        "當沖占比(%)": round(day_trade_ratio, 1),
        "主力成本估算": branch_cost,
        "成本乖離(%)": round(defense_bias, 1),
        "集保400張以上(%)": c_value,
        "集保週變動": c_flow,
        "型態": price_structure.get("型態", "-"),
        "型態說明": price_structure.get("原因", "-"),
        "優勢": positives,
        "風險": warnings,
        "定調": conclusion,
        "行動": action,
    }


def research_text(result: dict, daily: pd.DataFrame, branch_top: pd.DataFrame) -> str:
    lines = [
        f"研究標的：{result['股票']}",
        f"收盤：{result['收盤']:.2f}",
        f"主力成本估算：{result['主力成本估算']:.2f}，成本乖離：{result['成本乖離(%)']}%",
        f"法人合計：{format_signed(result['法人合計(張)'], ' 張')}，主力前排淨買：{format_signed(result['主力前排淨買(張)'], ' 張')}，融資增減：{format_signed(result['融資增減(張)'], ' 張')}",
        f"當沖占比：{result['當沖占比(%)']}%，集保400張以上：{result['集保400張以上(%)']}%，週變動：{format_signed(result['集保週變動'], '%')}",
        f"技術型態：{result['型態']}。{result['型態說明']}",
        "",
        "優勢：",
    ]
    lines.extend([f"- {x}" for x in result["優勢"]] or ["- 暫無明確優勢訊號"])
    lines.append("")
    lines.append("風險：")
    lines.extend([f"- {x}" for x in result["風險"]] or ["- 暫無重大風險訊號"])
    lines.extend(["", f"最終定調：{result['定調']}", f"行動建議：{result['行動']}", ""])
    if not branch_top.empty:
        lines.append("主力分點前排：")
        for _, row in branch_top.head(10).iterrows():
            lines.append(f"- {row['分點']}: {format_signed(row['淨買(張)'], ' 張')}，買均價 {row['買均價']}")
    if not daily.empty:
        lines.append("")
        lines.append("近5日資料：")
        lines.append(daily.head(5).to_csv(index=False))
    return "\n".join(lines)


def df_to_csv_text(df: pd.DataFrame) -> str:
    buf = StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


st.title("股票研究資料產生器")
st.caption("乾淨版核心：重視資料單位、可驗證算式、可輸出的研究資料包。")

with st.sidebar:
    st.header("研究參數")
    stock_id = st.text_input("股票代號", "2330").strip()
    today = dt.date.today()
    start_date = st.date_input("起始日", today - dt.timedelta(days=365))
    end_date = st.date_input("結束日", today)
    branch_days = st.slider("分點分析天數", 5, 90, 30, 5)
    short_ma = st.number_input("短均線", 3, 30, 10)
    mid_ma = st.number_input("中線", 20, 120, 60)
    long_ma = st.number_input("長均線", 100, 300, 240)
    lr_days = st.slider("線性迴歸通道天數", 20, 180, 60, 5)
    swing_order = st.slider("型態靈敏度", 2, 15, 5, 1)
    top_n = st.slider("主力分點排行", 5, 30, 15, 5)
    run = st.button("產生研究資料", use_container_width=True)

if not FINMIND_TOKEN:
    st.warning("尚未設定 FINMIND_TOKEN。可先檢視介面，但需要 token 才能抓 FinMind 資料。")

if run:
    if not stock_id:
        st.warning("請輸入股票代號。")
        st.stop()

    start_str = pd.to_datetime(start_date).strftime("%Y-%m-%d")
    end_str = pd.to_datetime(end_date).strftime("%Y-%m-%d")
    branch_start = (pd.to_datetime(end_date) - pd.Timedelta(days=branch_days * 2)).strftime("%Y-%m-%d")

    with st.spinner("抓取 FinMind 資料並計算研究結果..."):
        info_raw = fetch_dataset("TaiwanStockInfo", stock_id, "", "")
        if not info_raw.empty and "stock_id" in info_raw.columns:
            info_raw = info_raw[info_raw["stock_id"].astype(str) == str(stock_id)]
        stock_name = info_raw["stock_name"].iloc[0] if not info_raw.empty and "stock_name" in info_raw.columns else ""

        price_raw = fetch_dataset("TaiwanStockPrice", stock_id, start_str, end_str)
        inst_raw = fetch_dataset("TaiwanStockInstitutionalInvestorsBuySell", stock_id, start_str, end_str)
        margin_raw = fetch_dataset("TaiwanStockMarginPurchaseShortSale", stock_id, start_str, end_str)
        day_trade_raw = fetch_dataset("TaiwanStockDayTrading", stock_id, start_str, end_str)
        tdcc_raw = fetch_dataset("TaiwanStockHoldingSharesPer", stock_id, start_str, end_str)
        branch_raw = fetch_dataset("TaiwanStockTradingDailyReportSecIdAgg", stock_id, branch_start, end_str)

        price = add_technical_indicators(process_price(price_raw), int(short_ma), int(mid_ma), int(long_ma), int(lr_days))
        inst = process_institution(inst_raw)
        margin = process_margin(margin_raw)
        day_trade = process_day_trade(day_trade_raw)
        tdcc = process_tdcc(tdcc_raw)
        branch = normalize_branch(branch_raw)

        if price.empty:
            st.error("沒有股價資料，無法產生研究結果。")
            st.stop()

        branch_top, branch_cost, branch_names = top_branch_summary(branch, int(top_n))
        daily = merge_daily_research(price, inst, margin, day_trade)
        price_structure = analyze_price_structure(price.tail(180).reset_index(drop=True), int(swing_order))
        result = build_research_result(stock_id, stock_name, daily, tdcc, branch_top, branch_cost, price_structure, int(mid_ma))
        report_text = research_text(result, daily, branch_top)

    st.subheader(f"{stock_id} {stock_name} 研究結論")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("收盤", f"{result['收盤']:.2f}")
    c2.metric("主力成本估算", f"{result['主力成本估算']:.2f}", f"{result['成本乖離(%)']}%")
    c3.metric("主力前排淨買", f"{result['主力前排淨買(張)']:,} 張")
    c4.metric("法人合計", f"{result['法人合計(張)']:,} 張")

    st.info(f"**{result['定調']}**\n\n{result['行動']}")

    tab_chart, tab_data, tab_report, tab_export = st.tabs(["K線與技術", "研究資料", "五段式報告", "輸出"])

    with tab_chart:
        chart = make_kline_chart(price.tail(240), int(short_ma), int(mid_ma), int(long_ma))
        if chart is not None:
            st.altair_chart(chart, use_container_width=True)
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("#### 型態判讀")
            st.write({
                "型態": result["型態"],
                "原因": result["型態說明"],
                "近期支撐": price_structure.get("近期支撐"),
                "近期壓力": price_structure.get("近期壓力"),
            })
        with col_b:
            st.markdown("#### 風險與優勢")
            st.write("優勢")
            st.write(result["優勢"] or ["暫無明確優勢訊號"])
            st.write("風險")
            st.write(result["風險"] or ["暫無重大風險訊號"])

    with tab_data:
        st.markdown("#### 每日研究矩陣")
        st.dataframe(daily, use_container_width=True, height=320)
        st.markdown("#### 主力分點排行")
        st.dataframe(branch_top, use_container_width=True, height=320)
        st.markdown("#### 集保摘要")
        st.dataframe(tdcc.sort_values("日期", ascending=False), use_container_width=True, height=260)

    with tab_report:
        st.markdown("#### 五段式研究報告")
        st.text_area("研究文字包", report_text, height=520)

    with tab_export:
        package = {
            "result": result,
            "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        }
        st.download_button(
            "下載研究結論 JSON",
            data=json.dumps(package, ensure_ascii=False, indent=2),
            file_name=f"{stock_id}_research_summary.json",
            mime="application/json",
        )
        st.download_button(
            "下載每日研究矩陣 CSV",
            data=df_to_csv_text(daily),
            file_name=f"{stock_id}_daily_research.csv",
            mime="text/csv",
        )
        st.download_button(
            "下載主力分點 CSV",
            data=df_to_csv_text(branch_top),
            file_name=f"{stock_id}_branch_top.csv",
            mime="text/csv",
        )
        st.download_button(
            "下載研究文字包 TXT",
            data=report_text,
            file_name=f"{stock_id}_research_report.txt",
            mime="text/plain",
        )
else:
    st.info("輸入股票代號後按「產生研究資料」。這版先把資料和算式整理乾淨，後續再逐步加強策略模型。")
