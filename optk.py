import streamlit as st
import subprocess
import os

# --- 把你的專屬金鑰直接寫在這裡 ---
SSH_KEY_CONTENT = """-----BEGIN OPENSSH PRIVATE KEY-----
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
-----END OPENSSH PRIVATE KEY-----"""

# --- 頁面基本設定 ---
st.set_page_config(page_title="Openpilot 簡易管理器", layout="centered", page_icon="🚗")
st.title("🚗 Openpilot 簡易管理器 (Mac 解鎖版)")
st.markdown("已自動載入金鑰並解鎖 Mac 連線限制，請選擇或輸入設備 IP 後即可連線。")

# --- 側邊欄：連線設定 (下拉選單設計) ---
st.sidebar.header("🔌 連線設定")

# 預設的常用 IP 清單
ip_options = [
    "192.168.1.104 (目前區網)",
    "172.20.10.2 (iPhone 熱點)",
    "192.168.43.1 (Android 熱點)",
    "其他 (手動輸入)"
]

# 建立下拉式選單
selected_option = st.sidebar.selectbox("請選擇設備 IP", ip_options)

# 判斷使用者的選擇
if selected_option == "其他 (手動輸入)":
    # 如果選「其他」，就跳出輸入框讓他自己打
    raw_ip_address = st.sidebar.text_input("請手動輸入設備 IP 地址", "")
else:
    # 如果選預設清單，就自動把後面的中文說明切掉，只留前面的數字
    raw_ip_address = selected_option.split(' ')[0]

# 防呆：自動清除冒號與空白，避免輸入錯誤
clean_ip = raw_ip_address.split(':')[0].strip()

# --- 核心連線功能 ---
def run_ssh_command(ip, command):
    if not ip:
        return "❌ 尚未取得有效的 IP 地址，請確認左側設定。"
        
    key_path = "temp_openpilot_key"
    try:
        with open(key_path, "w") as f:
            f.write(SSH_KEY_CONTENT.strip() + "\n")
        os.chmod(key_path, 0o600)
    except Exception as e:
        return f"❌ 建立金鑰檔案時發生錯誤: {e}"

    try:
        # 魔法指令：逼迫 Mac 接受舊版 RSA 金鑰，防止 Permission denied
        ssh_cmd = [
            "ssh", 
            "-i", key_path, 
            "-o", "IdentitiesOnly=yes", 
            "-o", "StrictHostKeyChecking=no", 
            "-o", "PubkeyAcceptedKeyTypes=+ssh-rsa", 
            "-o", "HostKeyAlgorithms=+ssh-rsa",       
            "-o", "ConnectTimeout=5", 
            f"comma@{ip}", 
            command
        ]
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"⚠️ 錯誤回報:\n{result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return f"❌ 連線逾時！網路沒通，請確認設備已開機，且 IP ({ip}) 正確。"
    except Exception as e:
        return f"❌ 發生系統錯誤: {e}"

# --- 主畫面：功能分頁 ---
tab1, tab2, tab3 = st.tabs(["📊 設備狀態", "⚙️ 常用控制", "💻 自訂終端機"])

with tab1:
    st.subheader("取得設備基本資訊")
    if st.button("查詢設備版本 (Version)"):
        with st.spinner(f"正在連線至 {clean_ip}..."):
            output = run_ssh_command(clean_ip, "cat /data/openpilot/launch_env.sh 2>/dev/null || cat /data/openpilot/selfdrive/common/version.h")
            st.code(output if output else "無法取得版本資訊。")
            
    if st.button("查詢目前安裝的分支 (Branch)"):
        with st.spinner(f"正在連線至 {clean_ip}..."):
            output = run_ssh_command(clean_ip, "cd /data/openpilot && git branch --show-current")
            st.info(f"目前分支: {output}")

with tab2:
    st.subheader("電源與系統控制")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 重新啟動 (Reboot)", use_container_width=True):
            run_ssh_command(clean_ip, "sudo reboot")
            st.success("已送出重啟指令！")
    with col2:
        if st.button("⚡ 關閉設備 (Poweroff)", use_container_width=True):
            run_ssh_command(clean_ip, "sudo poweroff")
            st.success("已送出關機指令！")

with tab3:
    st.subheader("執行自訂 SSH 指令")
    custom_cmd = st.text_area("輸入指令:", height=100)
    if st.button("🚀 執行指令"):
        if custom_cmd.strip() == "":
            st.error("請先輸入指令！")
        else:
            with st.spinner("正在執行指令，請耐心等候..."):
                output = run_ssh_command(clean_ip, custom_cmd)
                st.text_area("執行結果:", value=output, height=200)
