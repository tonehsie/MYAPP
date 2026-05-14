import streamlit as st
import subprocess

# --- 頁面基本設定 ---
st.set_page_config(page_title="Openpilot 簡易管理器", layout="centered", page_icon="🚗")
st.title("🚗 Openpilot 簡易管理器")
st.markdown("將你的 Mac 與設備連線至同一個 Wi-Fi，即可進行遠端控制。")

# --- 側邊欄：連線設定 ---
st.sidebar.header("🔌 連線設定")
ip_address = st.sidebar.text_input("設備 IP 地址", "192.168.43.1")
st.sidebar.markdown("*(如果是用手機熱點分享給設備，IP 通常會是 `192.168.43.1`)*")

# --- 核心連線功能 ---
def run_ssh_command(ip, command):
    """透過 Mac 系統內建的 SSH 執行遠端指令"""
    try:
        # 使用 subprocess 呼叫系統 ssh，加入參數避免第一次連線的 yes/no 詢問卡住
        ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5", f"comma@{ip}", command]
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=15)
        
        # 回傳執行結果或錯誤訊息
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"⚠️ 錯誤回報:\n{result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "❌ 連線逾時！請確認設備已開機，且與 Mac 在同一個 Wi-Fi 網域下。"
    except Exception as e:
        return f"❌ 發生系統錯誤: {e}"

# --- 主畫面：功能分頁 ---
tab1, tab2, tab3 = st.tabs(["📊 設備狀態", "⚙️ 常用控制", "💻 自訂終端機"])

# 分頁 1：設備狀態
with tab1:
    st.subheader("取得設備基本資訊")
    if st.button("查詢設備版本 (Version)"):
        with st.spinner("連線中..."):
            output = run_ssh_command(ip_address, "cat /data/openpilot/launch_env.sh 2>/dev/null || cat /data/openpilot/selfdrive/common/version.h")
            st.code(output if output else "無法取得版本資訊，請確認路徑。")
            
    if st.button("查詢目前安裝的分支 (Branch)"):
        with st.spinner("連線中..."):
            output = run_ssh_command(ip_address, "cd /data/openpilot && git branch --show-current")
            st.info(f"目前分支: {output}")

# 分頁 2：常用控制
with tab2:
    st.subheader("電源與系統控制")
    st.warning("執行重啟或關機後，連線將會中斷。")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 重新啟動 (Reboot)", use_container_width=True):
            run_ssh_command(ip_address, "sudo reboot")
            st.success("已送出重啟指令！設備將在幾秒後重新啟動。")
            
    with col2:
        if st.button("⚡ 關閉設備 (Poweroff)", use_container_width=True):
            run_ssh_command(ip_address, "sudo poweroff")
            st.success("已送出關機指令！")

# 分頁 3：自訂終端機 (給需要刷機或進階操作時使用)
with tab3:
    st.subheader("執行自訂 SSH 指令")
    st.markdown("在這裡可以貼上社群提供的 Fork 安裝碼（例如 `cd /data; rm -rf openpilot; git clone...`）")
    
    custom_cmd = st.text_area("輸入指令:", height=100)
    if st.button("🚀 執行指令"):
        if custom_cmd.strip() == "":
            st.error("請先輸入指令！")
        else:
            with st.spinner("正在執行指令，若指令較長（如刷機）請耐心等候..."):
                output = run_ssh_command(ip_address, custom_cmd)
                st.text_area("執行結果:", value=output, height=200)
