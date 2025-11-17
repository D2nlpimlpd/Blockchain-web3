import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
import time
import json
import altair as alt
from dotenv import load_dotenv
from web3 import Web3
from backend.controller import simulate_step
from backend.web3_api import w3

load_dotenv()

# == 初始化合约 ==
with open("backend/AlgoStableV2_abi.json") as f:
    abi = json.load(f)

try:
    STABLE_ADDR = w3.to_checksum_address(os.getenv("STABLE_ADDR"))
    ACCOUNT_ADDRESS = w3.to_checksum_address(os.getenv("ACCOUNT_ADDRESS"))
except Exception as e:
    st.error(f"⚠️ 地址格式错误，请检查 .env 文件中的地址: {e}")
    st.stop()

stable_contract = w3.eth.contract(address=STABLE_ADDR, abi=abi)

# === 检查链上连接状态 ===
try:
    block_number = w3.eth.block_number
    chain_ok = True
    chain_status = f"✅ 已连接 Sepolia 区块链（最新区块：{block_number}）"
except Exception:
    chain_ok = False
    chain_status = "⚠️ 无法连接区块链，将自动切换为本地模拟模式"

# === Streamlit 页面 ===
st.set_page_config(page_title="LUNA UST 链上崩盘模拟", layout="wide")
st.title("🪙 LUNA–UST 链上算法稳定币崩盘模拟器")

st.sidebar.header("📊 当前链上状态")
st.sidebar.write(chain_status)

# 尝试获取链上状态
try:
    price = stable_contract.functions.price().call() / 1e18
except Exception:
    price = 1.0

try:
    balance = stable_contract.functions.balanceOf(ACCOUNT_ADDRESS).call() / 1e18
except Exception:
    balance = 0.0

st.sidebar.write(f"合约地址： `{STABLE_ADDR}`")
st.sidebar.write(f"账户地址： `{ACCOUNT_ADDRESS}`")
st.sidebar.metric("UST 余额", f"{balance:,.2f} UST")
st.sidebar.metric("当前价格", f"{price:.4f} USD")

# === 模拟参数初始化 ===
state = {
    "ust_supply": 1_000_000,
    "luna_supply": 1_000_000,
    "peg_ust": 1_000_000,
    "peg_luna": 1_000_000,
    "ust_price": price,
    "luna_price": 100.0,
}
data = []

# === 模式选择 ===
st.markdown("---")
mode = st.selectbox(
    "请选择运行模式：",
    ["🧮 本地模拟（快速）", "🔗 链上模式（真实交易）"],
    index=0 if not chain_ok else 1
)
use_onchain = mode.startswith("🔗") and chain_ok

if not chain_ok and use_onchain:
    st.warning("⚠️ 链上连接不可用，已自动切换到本地模式。")
    use_onchain = False

st.write(f"当前运行模式：{'🔗 链上模式（真实交易）' if use_onchain else '🧮 本地模拟（仅本地计算）'}")

# === 模拟主逻辑 ===
if st.button("开始模拟"):
    st.info("模拟进行中，请稍等...")
    chart_area = st.empty()

    for step in range(300):  
        state = simulate_step(state, stable_contract, use_onchain=use_onchain)
        data.append({
            "Step": step,
            "UST Price": state["ust_price"],
            "LUNA Price": state["luna_price"],
        })
        df = pd.DataFrame(data)

        # === Altair 双图 ===
        luna_chart = (
            alt.Chart(df)
            .mark_line(color="#1f77b4", strokeWidth=2)
            .encode(
                x=alt.X("Step:Q", title="模拟步数"),
                y=alt.Y("LUNA Price:Q", title="LUNA Price (USD)", scale=alt.Scale(domain=(0, max(df['LUNA Price'].max()*1.1, 0.1)))),
                tooltip=["Step", "LUNA Price"]
            )
            .properties(width=400, height=300, title="LUNA 价格走势")
        )

        ust_chart = (
            alt.Chart(df)
            .mark_line(color="#d62728", strokeWidth=2)
            .encode(
                x=alt.X("Step:Q", title="模拟步数"),
                y=alt.Y("UST Price:Q", title="UST Price (USD)", scale=alt.Scale(domain=(0, 1.1))),
                tooltip=["Step", "UST Price"]
            )
            .properties(width=400, height=300, title="UST 价格走势")
        )

        # 左右并列展示，独立Y轴
        combined_chart = alt.hconcat(luna_chart, ust_chart).resolve_scale(y="independent")

        chart_area.altair_chart(combined_chart, use_container_width=True)
        time.sleep(0.4 if use_onchain else 0.1)

    st.success("✅ 模拟完成！")

st.caption("提示：左图为 LUNA 价格走势，右图为 UST 价格走势；链上模式下每步调用 setPrice()，速度较慢。")