#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全息量化系統 V76.0 自動修復工具。

用法：
    python v76_repair_tool.py 原始檔.py 修正版.py
"""

from __future__ import annotations

import argparse
import ast
import re
import shutil
import textwrap
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str, required: bool = True) -> str:
    count = text.count(old)
    if count == 0:
        if required:
            raise RuntimeError(f"找不到要修正的程式片段：{label}")
        print(f"[略過] {label}：原始碼中未找到")
        return text
    if count > 1:
        print(f"[注意] {label}：找到 {count} 處，只替換第一處")
    return text.replace(old, new, 1)


def replace_all(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count == 0:
        print(f"[略過] {label}：原始碼中未找到")
        return text
    print(f"[修正] {label}：{count} 處")
    return text.replace(old, new)


def function_spans(source: str, function_name: str) -> list[tuple[int, int]]:
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    spans: list[tuple[int, int]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            start = offsets[node.lineno - 1]
            end = offsets[getattr(node, "end_lineno", node.lineno)]
            spans.append((start, end))
    return spans


def dedupe_function(source: str, function_name: str, keep: str = "first") -> str:
    spans = function_spans(source, function_name)
    if len(spans) <= 1:
        return source

    keep_index = 0 if keep == "first" else len(spans) - 1
    pieces: list[str] = []
    cursor = 0
    for index, (start, end) in enumerate(spans):
        pieces.append(source[cursor:start])
        if index == keep_index:
            pieces.append(source[start:end])
        else:
            pieces.append(
                f"\n# V76.0：已移除重複定義的 {function_name}()，避免後方版本覆蓋前方版本。\n"
            )
        cursor = end
    pieces.append(source[cursor:])
    print(f"[修正] {function_name}() 重複定義：保留 {keep}")
    return "".join(pieces)


def replace_function(source: str, function_name: str, new_code: str) -> str:
    spans = function_spans(source, function_name)
    if not spans:
        raise RuntimeError(f"找不到函式：{function_name}")
    if len(spans) > 1:
        raise RuntimeError(f"函式 {function_name} 仍有重複定義")

    start, end = spans[0]
    replacement = textwrap.dedent(new_code).strip() + "\n\n"
    print(f"[修正] 重寫函式：{function_name}()")
    return source[:start] + replacement + source[end:]


def insert_imports(source: str) -> str:
    additions: list[str] = []
    for module_line in ["import os\n", "import html as html_lib\n", "import logging\n"]:
        if module_line.strip() not in source:
            additions.append(module_line)

    if not additions:
        return source

    marker = "import streamlit as st\n"
    if marker not in source:
        raise RuntimeError("找不到 import streamlit as st")
    print("[修正] 新增 os/html/logging 匯入")
    return source.replace(marker, marker + "".join(additions), 1)


def patch_source(source: str) -> str:
    source = insert_imports(source)
    source = dedupe_function(source, "get_v50_intelligence", keep="first")

    secret_pattern = re.compile(
        r'FINMIND_TOKEN\s*=\s*"[^"]*"\s*\n'
        r'GITHUB_MANUAL_URL\s*=\s*"[^"]*"\s*',
        re.MULTILINE,
    )
    secret_replacement = '''LOGGER = logging.getLogger("v76")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def get_secret(name, default=""):
    # 先讀 Streamlit secrets，再讀環境變數。
    try:
        value = st.secrets.get(name, None)
        if value is not None:
            return str(value)
    except Exception:
        pass
    return str(os.getenv(name, default))

FINMIND_TOKEN = get_secret("FINMIND_TOKEN")
GITHUB_MANUAL_URL = get_secret(
    "GITHUB_MANUAL_URL",
    "https://raw.githubusercontent.com/tonehsie/stock/refs/heads/main/README.md",
)

if not FINMIND_TOKEN:
    st.warning("尚未設定 FINMIND_TOKEN。請在 .streamlit/secrets.toml 或環境變數中設定。")
'''
    source, count = secret_pattern.subn(secret_replacement, source, count=1)
    if count != 1:
        raise RuntimeError("找不到 FINMIND_TOKEN / GITHUB_MANUAL_URL 硬編碼區塊")
    print("[修正] Token 改用 Streamlit secrets / 環境變數")

    source = replace_once(
        source,
        'r = GENERIC_SESSION.get(f"https://api.web.finmindtrade.com/v2/user_info?token={token}", timeout=5)',
        'r = GENERIC_SESSION.get("https://api.web.finmindtrade.com/v2/user_info", params={"token": token}, timeout=5)',
        "FinMind 使用量 API 改用 params",
        required=False,
    )
    source = replace_once(
        source,
        'st.markdown(fetch_github_manual(GITHUB_MANUAL_URL), unsafe_allow_html=True)',
        'st.markdown(fetch_github_manual(GITHUB_MANUAL_URL))',
        "GitHub 指南停用 unsafe HTML",
        required=False,
    )

    old_retry = 'Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])'
    new_retry = '''Retry(
        total=4,
        connect=4,
        read=4,
        status=4,
        backoff_factor=0.6,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET"]),
        respect_retry_after_header=True,
        raise_on_status=False,
    )'''
    source = replace_all(source, old_retry, new_retry, "HTTP Retry 設定")

    cache_marker = "def cached_finmind_api_call(url, params_tuple):"
    cache_decorator = "@st.cache_data(ttl=900, max_entries=256, show_spinner=False)\n"
    if cache_decorator + cache_marker not in source:
        source = source.replace(cache_marker, cache_decorator + cache_marker, 1)
        print("[修正] FinMind 一般呼叫加入 15 分鐘快取")

    source = replace_all(
        source,
        "ThreadPoolExecutor(max_workers=100)",
        "ThreadPoolExecutor(max_workers=16)",
        "分點 API 併發數 100→16",
    )
    source = replace_once(
        source,
        '("TaiwanStockConvertibleBondDailyOverview", dates[0], None, None),',
        '("TaiwanStockConvertibleBondDailyOverview", dt_sd, None, None),',
        "可轉債行情改抓歷史區間",
        required=False,
    )
    source = replace_once(
        source,
        '''max_len = needed_days + 20
        if max_len > len(dates): max_len = len(dates)
        if max_len == 0: max_len = 1''',
        '''max_len = max(120, needed_days + 20)
        if max_len > len(dates):
            max_len = len(dates)
        if max_len == 0:
            max_len = 1''',
        "分點歷史至少抓 120 個交易日",
    )
    source = replace_once(
        source,
        'capital_str = f"{current_total_shares / 10000:.2f} 億"',
        'capital_str = f"{current_total_shares / 100000:.2f} 億股"',
        "股本顯示修正 10 倍誤差",
    )
    source = replace_all(
        source,
        "{alert_smart_pct*100:.1f}%",
        "{alert_smart_pct:.1f}%",
        "警報百分比顯示",
    )
    source = replace_once(
        source,
        "b_h1 = [h for h in highs if l1[2] < l[2] < h2[2]]",
        "b_h1 = [h for h in highs if l1[2] < h[2] < l2[2]]",
        "頭肩底未定義變數",
    )
    source = replace_once(
        source,
        "bt_vol = max(1, int(round(raw_vol / 1000))) if raw_vol > 10000 else int(raw_vol)",
        "bt_vol = max(1, int(round(raw_vol)))",
        "鉅額交易避免重複除以 1000",
    )
    source = replace_once(
        source,
        'st.success(f"V75.9 終極版已成功處理 {user_stock_id}。當前 RAM 使用狀態健康。")',
        'st.success(f"V76.0 修正版已完成 {user_stock_id} 的資料處理。")',
        "移除未量測的 RAM 健康宣稱",
        required=False,
    )
    source = replace_all(
        source,
        "您可以完全信任上方第一點與第二點的純量化籌碼判斷。",
        "可將上方籌碼結果作為輔助判斷，但仍需搭配價格、風險與資料完整性確認。",
        "降低過度確定的投資訊號敘述",
    )
    source = replace_all(
        source,
        "🎯 **依籌碼特徵破案！**",
        "🎯 **依籌碼特徵列出優先候選：**",
        "鉅額交易候選敘述",
    )

    source = replace_function(
        source,
        "get_dead_chip_info",
        r'''
def get_dead_chip_info(ds, dci, dd, sv, ce):
    # 取得死籌碼比例；允許使用者明確輸入 0。
    if dci is not None and str(dci).strip() != "":
        try:
            value = float(str(dci).replace("%", "").strip())
            return max(0.0, min(99.9, value)), "手動輸入"
        except (TypeError, ValueError):
            LOGGER.warning("死籌碼手動輸入無法解析：%r", dci)

    mk = str(ds)[:7].replace("/", "-")
    if dd and mk in dd:
        return float(dd[mk]), f"{ce}當月"

    if dd:
        try:
            latest_key = sorted(dd.keys(), reverse=True)[0]
            return float(dd[latest_key]), f"{ce}最新({latest_key})"
        except Exception:
            LOGGER.exception("死籌碼歷史資料解析失敗")

    if sv and sv > 0:
        return float(sv), ce
    return 0.0, "缺資料"
''',
    )

    source = replace_function(
        source,
        "clean_level_by_math",
        r'''
def clean_level_by_math(x):
    # 把 TDCC 級距代碼或股數區間轉成固定 15 級。
    raw = str(x).strip()
    s = re.sub(r"[,，\s]|\.0$", "", raw)

    if s in _LEVEL_CLEAN_CACHE:
        return _LEVEL_CLEAN_CACHE[s]

    if not s or s in {"合計", "總計", "差異數", "nan", "None", "<NA>"}:
        result = "合計"
    elif "以上" in s:
        result = "1000張以上"
    elif s.isdigit() and 1 <= int(s) <= 15:
        result = _LEVEL_MAP[int(s)]
    elif s == "99":
        result = "合計"
    else:
        nums = [int(n) for n in _num_re.findall(s)]
        if not nums:
            result = s
        else:
            upper = nums[-1]
            if upper <= 999:
                result = "1-999股"
            elif upper <= 5_000:
                result = "1-5張"
            elif upper <= 10_000:
                result = "5-10張"
            elif upper <= 15_000:
                result = "10-15張"
            elif upper <= 20_000:
                result = "15-20張"
            elif upper <= 30_000:
                result = "20-30張"
            elif upper <= 40_000:
                result = "30-40張"
            elif upper <= 50_000:
                result = "40-50張"
            elif upper <= 100_000:
                result = "50-100張"
            elif upper <= 200_000:
                result = "100-200張"
            elif upper <= 400_000:
                result = "200-400張"
            elif upper <= 600_000:
                result = "400-600張"
            elif upper <= 800_000:
                result = "600-800張"
            elif upper <= 1_000_000:
                result = "800-1000張"
            else:
                result = "1000張以上"

    _LEVEL_CLEAN_CACHE[s] = result
    return result
''',
    )

    source = replace_function(
        source,
        "process_day_trading",
        r'''
def process_day_trading(df):
    if not is_valid(df):
        return pd.DataFrame()

    df_out = df.copy()
    if "DayTradingVolume" in df_out.columns:
        vol_col = "DayTradingVolume"
    elif "Volume" in df_out.columns:
        vol_col = "Volume"
    else:
        vol_col = None

    if vol_col is not None:
        df_out["當沖總張數"] = (safe_to_num(df_out[vol_col]) / 1000).round().astype(int)
    else:
        df_out["當沖總張數"] = 0

    df_out = df_out.rename(columns={"date": "日期"})
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]
    if "日期" not in df_out.columns:
        return pd.DataFrame()

    return (
        df_out[["日期", "當沖總張數"]]
        .sort_values("日期", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )
''',
    )

    source = replace_function(
        source,
        "process_margin_and_lending",
        r'''
def process_margin_and_lending(df_margin_raw, df_lending_raw):
    if not is_valid(df_margin_raw):
        return pd.DataFrame()

    df_m = df_margin_raw.copy()
    numeric_cols = [
        "MarginPurchaseBuy", "MarginPurchaseSell",
        "MarginPurchaseCashRepayment", "MarginPurchaseTodayBalance",
        "MarginPurchaseYesterdayBalance", "ShortSaleBuy", "ShortSaleSell",
        "ShortSaleCashRepayment", "ShortSaleTodayBalance",
        "OffsetLoanAndShort", "ShortSaleYesterdayBalance",
    ]
    for col in numeric_cols:
        if col in df_m.columns:
            df_m[col] = safe_to_num(df_m[col]).round().astype(int)

    df_out = df_m.rename(columns={
        "date": "日期",
        "MarginPurchaseBuy": "融資買進(萬元)",
        "MarginPurchaseSell": "融資賣出(萬元)",
        "MarginPurchaseCashRepayment": "融資現償(萬元)",
        "MarginPurchaseTodayBalance": "融資餘額(萬元)",
        "ShortSaleBuy": "融券買進(張)",
        "ShortSaleSell": "融券賣出(張)",
        "ShortSaleTodayBalance": "融券餘額(張)",
        "OffsetLoanAndShort": "資券相抵(張)",
    })
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]
    if "日期" not in df_out.columns:
        return pd.DataFrame()

    if "融資餘額(萬元)" in df_out.columns and "MarginPurchaseYesterdayBalance" in df_out.columns:
        previous = safe_to_num(df_out["MarginPurchaseYesterdayBalance"]).round().astype(int)
        df_out["融資增減(萬元)"] = df_out["融資餘額(萬元)"] - previous

    if "融券餘額(張)" in df_out.columns and "ShortSaleYesterdayBalance" in df_out.columns:
        previous = safe_to_num(df_out["ShortSaleYesterdayBalance"]).round().astype(int)
        df_out["融券增減(張)"] = df_out["融券餘額(張)"] - previous

    if is_valid(df_lending_raw, ["date", "volume"]):
        lending = df_lending_raw[["date", "volume"]].copy()
        lending["volume"] = safe_to_num(lending["volume"])
        lending_daily = lending.groupby("date", as_index=False)["volume"].sum()
        lending_daily = lending_daily.rename(columns={"date": "日期"})
        lending_daily["本日借券成交(張)"] = (lending_daily["volume"] / 1000).round().astype(int)
        df_out = pd.merge(
            df_out,
            lending_daily[["日期", "本日借券成交(張)"]],
            on="日期",
            how="left",
            validate="many_to_one",
        )
        df_out["本日借券成交(張)"] = df_out["本日借券成交(張)"].fillna(0).astype(int)
    else:
        df_out["本日借券成交(張)"] = 0

    display_cols = [
        "日期", "融資買進(萬元)", "融資賣出(萬元)", "融資現償(萬元)",
        "融資餘額(萬元)", "融資增減(萬元)", "融券買進(張)",
        "融券賣出(張)", "融券餘額(張)", "融券增減(張)",
        "資券相抵(張)", "本日借券成交(張)",
    ]
    display_cols = [c for c in display_cols if c in df_out.columns]
    return df_out[display_cols].sort_values("日期", ascending=False).head(10).reset_index(drop=True)
''',
    )

    source = replace_function(
        source,
        "process_block_trading",
        r'''
def process_block_trading(df_block_raw, rank_dates):
    if not is_valid(df_block_raw, ["date"]):
        return pd.DataFrame()

    target_dates = list(rank_dates[:5])
    df_b = df_block_raw[df_block_raw["date"].isin(target_dates)].copy()
    if df_b.empty:
        return pd.DataFrame()

    df_b = df_b.rename(columns={
        "date": "日期", "trade_type": "交易類別", "price": "成交價(元)",
        "volume": "成交張數", "trading_money": "成交金額(萬元)",
    })
    if "成交價(元)" in df_b.columns:
        df_b["成交價(元)"] = safe_to_num(df_b["成交價(元)"], fill_val=np.nan)
    if "成交張數" in df_b.columns:
        df_b["成交張數"] = (safe_to_num(df_b["成交張數"]) / 1000).round().astype(int)
    if "成交金額(萬元)" in df_b.columns:
        df_b["成交金額(萬元)"] = (safe_to_num(df_b["成交金額(萬元)"]) / 10000).round().astype(int)

    display_cols = [c for c in ["日期", "交易類別", "成交價(元)", "成交張數", "成交金額(萬元)"] if c in df_b.columns]
    if not display_cols:
        return pd.DataFrame()

    sort_cols = ["日期"]
    ascending = [False]
    if "成交金額(萬元)" in df_b.columns:
        sort_cols.append("成交金額(萬元)")
        ascending.append(False)
    return df_b[display_cols].sort_values(sort_cols, ascending=ascending).reset_index(drop=True)
''',
    )

    source = replace_function(
        source,
        "process_linear_regression",
        r'''
def process_linear_regression(df_price, lr_days):
    try:
        if not is_valid(df_price, ["日期", "收盤價(元)"], 2):
            return pd.DataFrame()

        df_lr = df_price.head(int(lr_days)).sort_values("日期", ascending=True).copy()
        df_lr["收盤價(元)"] = pd.to_numeric(df_lr["收盤價(元)"], errors="coerce")
        df_lr = df_lr.dropna(subset=["收盤價(元)"]).reset_index(drop=True)
        if len(df_lr) < 2:
            return pd.DataFrame()

        y = df_lr["收盤價(元)"].to_numpy(dtype=float)
        x = np.arange(len(y), dtype=float)
        slope, intercept = np.polyfit(x, y, 1)
        y_pred = slope * x + intercept
        residual = y - y_pred
        std_err = float(np.std(residual, ddof=1)) if len(y) > 2 else float(np.std(residual))

        df_lr["LR_Mid"] = y_pred
        df_lr["LR_Upper"] = y_pred + 2.0 * std_err
        df_lr["LR_Lower"] = y_pred - 2.0 * std_err
        return df_lr[["日期", "LR_Mid", "LR_Upper", "LR_Lower"]]
    except Exception:
        LOGGER.exception("線性迴歸通道計算失敗")
        return pd.DataFrame()
''',
    )

    source = replace_function(
        source,
        "render_clean_html_table",
        r'''
def render_clean_html_table(df, title=""):
    if not is_valid(df):
        if title:
            safe_title = html_lib.escape(str(title))
            st.markdown(f"<div class='section-title'>{safe_title}</div>", unsafe_allow_html=True)
        st.warning("此區塊查無資料。")
        return

    text_keywords = {"日期", "分點", "標籤", "週期", "名稱", "姓名", "身份別", "條件", "措施", "診斷", "代號", "類別"}
    cols = df.columns.tolist()
    align_classes = ["text-left" if any(k in str(col) for k in text_keywords) else "text-right" for col in cols]

    html_parts = []
    if title:
        html_parts.append(f"<div class='section-title'>{html_lib.escape(str(title))}</div>")
    html_parts.append("<div class='table-container'><table><thead><tr>")
    html_parts.extend([f"<th>{html_lib.escape(str(col))}</th>" for col in cols])
    html_parts.append("</tr></thead><tbody>")

    for row in df.itertuples(index=False):
        html_parts.append("<tr>")
        for i, val in enumerate(row):
            display_val = "-"
            if pd.notna(val):
                raw = str(val).strip()
                if raw and raw.lower() != "nan":
                    safe = html_lib.escape(raw)
                    if "無本獲利" in raw:
                        display_val = f"<span class='profit-warning'>{safe}</span>"
                    elif "(虧)" in raw:
                        clean_loss = html_lib.escape(raw.replace("(虧)", "").strip())
                        display_val = f"<span class='loss-warning'>(虧) {clean_loss}</span>"
                    elif raw.startswith("+"):
                        display_val = f"<span class='highlight-red'>{safe}</span>"
                    elif raw.startswith("-") and len(raw) > 1 and raw[1].isdigit():
                        try:
                            number = float(raw.replace(",", ""))
                            formatted = f"{number:,.2f}" if "." in raw else f"{int(number):,}"
                            display_val = f"<span class='highlight-green'>{formatted}</span>"
                        except ValueError:
                            display_val = f"<span class='highlight-green'>{safe}</span>"
                    elif "%" in raw:
                        display_val = safe
                    else:
                        try:
                            number = float(raw.replace(",", ""))
                            display_val = f"{number:,.2f}" if "." in raw else f"{int(number):,}"
                        except ValueError:
                            display_val = safe
            html_parts.append(f"<td class='{align_classes[i]}'>{display_val}</td>")
        html_parts.append("</tr>")

    html_parts.append("</tbody></table></div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)
''',
    )

    source = replace_once(
        source,
        '''def process_v30_daily_tracking(df_branch_raw, intel_tags, df_price, df_branch_diff, actual_dates, fire_thresh, period_days=5):
    if not is_valid(df_branch_raw) or len(actual_dates) < period_days: return pd.DataFrame(), pd.DataFrame()
    out, audit_smart_money = [], []''',
        '''def process_v30_daily_tracking(df_branch_raw, intel_tags, df_price, df_branch_diff, actual_dates, fire_thresh, period_days=5):
    if not is_valid(df_branch_raw) or not actual_dates:
        return pd.DataFrame(), pd.DataFrame()
    period_days = min(int(period_days), len(actual_dates))
    out, audit_smart_money = [], []''',
        "日追蹤資料不足時改用可用天數",
        required=False,
    )

    old_cb_block = '''        is_cbas_arb = False
        if is_valid(df_cbas, ['未償還餘額'], 2):
            try:
                cb_curr = float(df_cbas.iloc[0]['未償還餘額'])
                cb_prev = float(df_cbas.iloc[1]['未償還餘額'])
                if cb_curr < cb_prev and today_smart_net < -50:
                    is_cbas_arb = True
            except: pass'''
    new_cb_block = '''        is_cbas_arb = False
        if is_valid(df_cbas, ["可轉債代號", "日期", "未償還餘額"], 2):
            try:
                for _, cb_group in df_cbas.groupby("可轉債代號"):
                    cb_group = cb_group.sort_values("日期", ascending=False)
                    balances = pd.to_numeric(cb_group["未償還餘額"], errors="coerce").dropna()
                    if len(balances) >= 2 and balances.iloc[0] < balances.iloc[1] and today_smart_net < -50:
                        is_cbas_arb = True
                        break
            except Exception:
                LOGGER.exception("可轉債套利判斷失敗")'''
    source = replace_once(source, old_cb_block, new_cb_block, "可轉債套利改為同債券依日期比較", required=False)

    source = replace_once(
        source,
        '''        return {}
    except Exception:
        return {}

def render_clean_html_table''',
        '''        return {}
    except Exception:
        LOGGER.exception("幾何形態辨識失敗")
        return {}

def render_clean_html_table''',
        "幾何辨識增加錯誤紀錄",
        required=False,
    )
    source = replace_once(
        source,
        '''    except:
        return pd.DataFrame()

def fetch_heavy_data_sync_with_progress''',
        '''    except Exception:
        LOGGER.exception("FinMind 資料集讀取失敗：%s", ds)
        return pd.DataFrame()

def fetch_heavy_data_sync_with_progress''',
        "FinMind 一般資料讀取增加錯誤紀錄",
        required=False,
    )

    source = source.replace("V75.9", "V76.0")
    source = source.replace("V75.8", "V76.0")

    ast.parse(source)
    return source


def main() -> None:
    parser = argparse.ArgumentParser(description="修正全息量化系統 V75.9 原始碼")
    parser.add_argument("input", type=Path, help="原始 .py 檔")
    parser.add_argument("output", type=Path, nargs="?", help="輸出的 V76.0 .py 檔")
    args = parser.parse_args()

    input_path = args.input.expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"找不到原始檔：{input_path}")

    output_path = args.output.expanduser().resolve() if args.output else input_path.with_name(input_path.stem + "_v76_fixed.py")
    source = input_path.read_text(encoding="utf-8")

    backup_path = input_path.with_suffix(input_path.suffix + ".bak")
    if not backup_path.exists():
        shutil.copy2(input_path, backup_path)
        print(f"[備份] {backup_path}")

    fixed = patch_source(source)
    output_path.write_text(fixed, encoding="utf-8", newline="\n")
    ast.parse(output_path.read_text(encoding="utf-8"))

    print(f"[完成] 已輸出：{output_path}")
    print("[提醒] 請立即撤銷曾經公開的 FinMind/GitHub Token，並設定新的 secrets。")


if __name__ == "__main__":
    main()
