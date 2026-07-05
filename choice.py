import concurrent.futures
import datetime
import html
import os
import re

import numpy as np
import pandas as pd
import requests
import streamlit as st
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 頁面與基礎設定
# ==========================================
st.set_page_config(layout="wide", page_title="全息量化系統 (動態門檻雷達)", initial_sidebar_state="expanded")


def get_secret_value(key, default=""):
    try:
        value = st.secrets.get(key)
    except Exception:
        value = None
    return value or os.getenv(key, default)


FINMIND_TOKEN = get_secret_value("FINMIND_TOKEN")

CSS = """
<style>
.table-container { overflow: auto; max-height: 700px; width: 100%; margin-bottom: 25px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding-bottom: 10px; }
.table-container table { width: 100% !important; border-collapse: separate !important; border-spacing: 0; font-size: 15px !important; font-family: sans-serif; background-color: #fff; }
.table-container th, .table-container td { white-space: nowrap !important; padding: 12px 15px !important; border-bottom: 1px solid #dee2e6; border-right: 1px solid #dee2e6; vertical-align: middle; text-align: center; }
.table-container th { border-top: 1px solid #dee2e6; background-color: #f1f3f5 !important; color: #333 !important; font-weight: 700 !important; position: sticky; top: 0; z-index: 3; }
.table-container th:first-child, .table-container td:first-child { position: sticky; left: 0; background-color: #f8f9fa; z-index: 4; font-weight: bold; border-left: 1px solid #dee2e6; }
.info-box { background-color: #f8f9fa; padding: 15px 20px; border-radius: 8px; margin-bottom: 25px; border-left: 6px solid #1e3a8a; font-size: 1.1rem; font-weight: bold; color: #1e3a8a; }
.highlight-red { color: #d32f2f; font-weight: bold; }
.highlight-green { color: #2e7d32; font-weight: bold; }
.threshold-badge { background-color: #e3f2fd; color: #1e3a8a; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 13px;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ==========================================
# 核心連線引擎
# ==========================================
@st.cache_resource(max_entries=3)
def get_finmind_session():
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0"}
    if FINMIND_TOKEN:
        headers["Authorization"] = f"Bearer {FINMIND_TOKEN}"
    session.headers.update(headers)

    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=30, pool_maxsize=30)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


FM_SESSION = get_finmind_session()


@st.cache_data(ttl=1800, show_spinner=False)
def cached_finmind_api_call(url, params_tuple):
    try:
        response = FM_SESSION.get(url, params=dict(params_tuple), timeout=20)
        response.raise_for_status()
        payload = response.json()
        return payload.get("data", [])
    except Exception as exc:
        return {"error": str(exc), "params": dict(params_tuple)}


def normalize_api_result(result):
    if isinstance(result, dict) and "error" in result:
        return pd.DataFrame(), result["error"]
    return pd.DataFrame(result), None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_stock_info():
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {"dataset": "TaiwanStockInfo", "start_date": "2000-01-01"}
    df, _ = normalize_api_result(cached_finmind_api_call(url, tuple(sorted(params.items()))))
    if not df.empty and "stock_id" in df.columns:
        df = df[df["industry_category"].fillna("") != ""]
        mask = df["stock_id"].astype(str).str.fullmatch(r"\d{4}")
        return df[mask].drop_duplicates("stock_id")
    return pd.DataFrame()


def fetch_single_tdcc(stock_id, date_str):
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        "dataset": "TaiwanStockHoldingSharesPer",
        "data_id": stock_id,
        "start_date": date_str,
        "end_date": date_str,
    }
    df, error = normalize_api_result(cached_finmind_api_call(url, tuple(sorted(params.items()))))
    return df, error


def render_clean_html_table(df):
    if df.empty:
        return

    cols = df.columns.tolist()
    html_parts = ["<div class='table-container'><table><thead><tr>"]
    html_parts.extend([f"<th>{html.escape(str(c))}</th>" for c in cols])
    html_parts.append("</tr></thead><tbody>")

    for row in df.itertuples(index=False):
        html_parts.append("<tr>")
        for val in row:
            value = str(val).strip()
            safe_value = html.escape(value)
            if value.startswith("+"):
                safe_value = f"<span class='highlight-red'>{safe_value}</span>"
            elif value.startswith("-") and len(value) > 1 and value[1].isdigit():
                safe_value = f"<span class='highlight-green'>{safe_value}</span>"
            elif "張" in value and len(value) <= 8:
                safe_value = f"<span class='threshold-badge'>{safe_value}</span>"
            html_parts.append(f"<td>{safe_value}</td>")
        html_parts.append("</tr>")
    html_parts.append("</tbody></table></div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def parse_level_to_floor_lots(value):
    text = str(value).replace(",", "").strip()
    if not text:
        return 0

    if text.isdigit():
        level = int(text)
        level_map = {
            10: 100,
            11: 200,
            12: 400,
            13: 600,
            14: 800,
        }
        if level in level_map:
            return level_map[level]
        if level >= 15:
            return 1000
        return 0

    numbers = [int(n) for n in re.findall(r"\d+", text)]
    if not numbers:
        return 0

    lots = numbers[0] // 1000
    if lots >= 1000:
        return 1000
    if lots >= 800:
        return 800
    if lots >= 600:
        return 600
    if lots >= 400:
        return 400
    if lots >= 200:
        return 200
    if lots >= 100:
        return 100
    return 0


def calc_dynamic_smart_pct(df_sub, val_col):
    total_shares = df_sub.groupby("stock_id")[val_col].sum() / 1000
    total_shares = total_shares[total_shares > 0]
    if total_shares.empty:
        return pd.DataFrame(columns=["Total_Shares", "Smart_Pct", "Dynamic_CT"])

    levels = np.array([100, 200, 400, 600, 800, 1000])
    raw_threshold = np.clip(total_shares * 0.01, 100, 1000)
    diffs = np.abs(raw_threshold.to_numpy()[:, None] - levels)
    ct_series = pd.Series(levels[diffs.argmin(axis=1)], index=total_shares.index)

    df_sub = df_sub[df_sub["stock_id"].isin(total_shares.index)].copy()
    df_sub["ct"] = df_sub["stock_id"].map(ct_series)

    smart_mask = df_sub["floor_lots"] >= df_sub["ct"]
    smart_shares = df_sub[smart_mask].groupby("stock_id")[val_col].sum() / 1000
    smart_pct = (smart_shares / total_shares * 100).fillna(0)

    return pd.DataFrame({
        "Total_Shares": total_shares,
        "Smart_Pct": smart_pct,
        "Dynamic_CT": ct_series,
    })


# ==========================================
# 介面與參數
# ==========================================
st.sidebar.header("雷達掃描參數")

if not FINMIND_TOKEN:
    st.sidebar.warning("尚未設定 FINMIND_TOKEN，公開額度可能很快用完。")

df_info = fetch_stock_info()
industry_list = (
    ["全市場暴力掃描 (需較長時間)"] + sorted(df_info["industry_category"].unique().tolist())
    if not df_info.empty
    else ["全市場暴力掃描 (需較長時間)"]
)
scan_mode = st.sidebar.selectbox("掃描範圍", industry_list, index=0)

capital_limit = st.sidebar.number_input("股本上限 (億)", min_value=1, max_value=200, value=50, step=5)

st.sidebar.divider()
st.sidebar.markdown("### 系統自動計算：大戶精算門檻")
st.sidebar.caption("系統將自動套用 V75.9 邏輯，依據每檔股票總發行量的 1% (界於100~1000張) 自動捕捉最適合的大戶級距。您不需手動設定。")

diff_threshold = st.sidebar.slider("單週大戶增加門檻 (%)", 0.1, 10.0, 0.3, 0.1)

st.sidebar.divider()
run_btn = st.sidebar.button("啟動多執行緒雷達掃描", use_container_width=True)

st.title("全息量化系統 (V76.9 動態精算門檻雷達)")
st.caption("已全面掛載級距辨識與動態股本計算引擎。系統會為每一檔中小型股自動分配最佳的「大戶門檻」。")

if run_btn:
    if df_info.empty:
        st.error("無法取得台股代號清單，請確認 FINMIND_TOKEN 或稍後再試。")
        st.stop()

    with st.spinner("定位集保結算日..."):
        params_tsmc = {
            "dataset": "TaiwanStockHoldingSharesPer",
            "data_id": "2330",
            "start_date": (datetime.date.today() - datetime.timedelta(days=45)).strftime("%Y-%m-%d"),
        }
        df_tsmc, tsmc_error = normalize_api_result(
            cached_finmind_api_call("https://api.finmindtrade.com/api/v4/data", tuple(sorted(params_tsmc.items())))
        )
        if tsmc_error:
            st.error(f"集保日期取得失敗：{tsmc_error}")
            st.stop()
        if df_tsmc.empty or "date" not in df_tsmc.columns or len(df_tsmc["date"].unique()) < 2:
            st.error("集保日期取得失敗，FinMind 回傳資料不足。")
            st.stop()
        tdcc_dates = sorted(df_tsmc["date"].unique(), reverse=True)
        latest_date, prev_date = tdcc_dates[0], tdcc_dates[1]
        st.markdown(
            f"<div class='info-box'>比對區間：<b>{html.escape(str(latest_date))}</b> vs <b>{html.escape(str(prev_date))}</b></div>",
            unsafe_allow_html=True,
        )

    target_stocks = (
        df_info["stock_id"].tolist()
        if "全市場" in scan_mode
        else df_info[df_info["industry_category"] == scan_mode]["stock_id"].tolist()
    )
    total_stocks = len(target_stocks)

    if total_stocks == 0:
        st.warning("目前篩選條件沒有可掃描的股票。")
        st.stop()

    st.info(f"鎖定【{scan_mode}】板塊，共計 {total_stocks} 檔個股。啟動多管線併發抓取...")

    prog_bar = st.progress(0.0)
    status_text = st.empty()

    all_results = []
    completed = 0
    error_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        future_to_stock = {}
        for sid in target_stocks:
            future_to_stock[executor.submit(fetch_single_tdcc, sid, latest_date)] = ("latest", sid)
            future_to_stock[executor.submit(fetch_single_tdcc, sid, prev_date)] = ("prev", sid)

        total_requests = max(len(future_to_stock), 1)
        for future in concurrent.futures.as_completed(future_to_stock):
            req_type, sid = future_to_stock[future]
            try:
                res, error = future.result()
            except Exception:
                res, error = pd.DataFrame(), "thread error"

            if error:
                error_count += 1
            elif not res.empty:
                res["period"] = req_type
                all_results.append(res)

            completed += 1
            prog_bar.progress(min(1.0, completed / total_requests))
            status_text.text(f"資料下載中... ({completed} / {total_requests})")

    prog_bar.empty()
    status_text.empty()

    if not all_results:
        st.error("額度耗盡或無資料回傳，請確認 FINMIND_TOKEN 與 FinMind API 狀態。")
        st.stop()

    df_all = pd.concat(all_results, ignore_index=True)
    stocks_with_data = df_all["stock_id"].nunique() if "stock_id" in df_all.columns else 0
    if error_count:
        st.warning(f"資料庫建置完成，但有 {error_count} 筆請求失敗；已用成功資料繼續運算。")
    else:
        st.success(f"資料庫建置完成！成功對齊 {stocks_with_data} 檔個股數據。")

    with st.spinner("引擎運算中：套用個股動態門檻精算籌碼流向..."):
        if "stock_id" not in df_all.columns or "HoldingSharesLevel" not in df_all.columns:
            st.error("FinMind 回傳欄位不完整，無法計算持股級距。")
            st.stop()

        val_col = "unit" if "unit" in df_all.columns else "HoldingShares"
        if val_col not in df_all.columns:
            st.error("FinMind 回傳資料缺少 unit / HoldingShares 欄位，無法計算股數。")
            st.stop()

        df_all[val_col] = pd.to_numeric(df_all[val_col], errors="coerce").fillna(0)
        df_all["floor_lots"] = df_all["HoldingSharesLevel"].apply(parse_level_to_floor_lots)

        df_l = calc_dynamic_smart_pct(df_all[df_all["period"] == "latest"].copy(), val_col)
        df_p = calc_dynamic_smart_pct(df_all[df_all["period"] == "prev"].copy(), val_col)

        if df_l.empty or df_p.empty:
            st.warning("可用資料不足，無法完成本次比較。")
            st.stop()

        df_scan = df_l.join(df_p, lsuffix="_latest", rsuffix="_prev").dropna()
        df_scan = df_scan[df_scan["Total_Shares_latest"] <= (capital_limit * 10000)]
        df_scan["Diff_Pct"] = df_scan["Smart_Pct_latest"] - df_scan["Smart_Pct_prev"]
        df_scan = df_scan[df_scan["Diff_Pct"] >= diff_threshold].sort_values("Diff_Pct", ascending=False)

        if df_scan.empty:
            st.warning(f"掃描結束！在過濾股本後，本次區間的確沒有個股大戶增加超過 {diff_threshold}%。")
        else:
            stock_names = df_info.set_index("stock_id")["stock_name"].to_dict()
            out_data = []
            for sid, row in df_scan.iterrows():
                out_data.append({
                    "代號": sid,
                    "名稱": stock_names.get(str(sid), ""),
                    "預估股本(億)": f"{row['Total_Shares_latest'] / 10000:.2f}",
                    "系統精算大戶門檻": f"{int(row['Dynamic_CT_latest'])} 張",
                    "上週大戶(%)": f"{row['Smart_Pct_prev']:.2f}%",
                    "最新大戶(%)": f"{row['Smart_Pct_latest']:.2f}%",
                    "大戶增減(%)": f"+{row['Diff_Pct']:.2f}%" if row["Diff_Pct"] > 0 else f"{row['Diff_Pct']:.2f}%",
                })
            st.balloons()
            render_clean_html_table(pd.DataFrame(out_data))
