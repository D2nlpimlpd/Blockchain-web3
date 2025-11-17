# frontend/app.py
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pandas as pd
import time
import json
from dotenv import load_dotenv

# Plotly
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from backend.controller import simulate_step
from backend.web3_api import w3

load_dotenv()

# ================= Web3 / Contract =================
with open("backend/AlgoStableV2_abi.json") as f:
    abi = json.load(f)


def _addr(x):
    try:
        return w3.to_checksum_address(x) if x else None
    except Exception:
        return None


STABLE_ADDR = _addr(os.getenv("STABLE_ADDR"))
ACCOUNT_ADDRESS = _addr(os.getenv("ACCOUNT_ADDRESS"))

try:
    stable_contract = (
        w3.eth.contract(address=STABLE_ADDR, abi=abi) if STABLE_ADDR else None
    )
    _ = w3.eth.block_number
    chain_ok = True
    chain_status = "✅ Web3 connection OK"
except Exception:
    chain_ok = False
    stable_contract = None
    chain_status = "⚠️ Cannot connect to blockchain, falling back to local simulation"

# ================= Page config =================
st.set_page_config(
    page_title="LUNA–UST Simulation (Historical-style)",
    layout="wide",
)
st.title("🪙 LUNA–UST Collapse Simulator ")

st.sidebar.header("📊 Status")
st.sidebar.write(chain_status)

# ================= Terra May 2022 preset (v4 params) =================
def terra_may_2022_preset() -> dict:
    state = {
        "ust_supply": 18_000_000_000.0,
        "luna_supply": 350_000_000.0,
        "ust_price": 1.0,
        "luna_price": 80.0,
        # AMM pool: initial marginal price ≈ CEX
        "pool_ust": 800_000_000.0,
        "pool_luna": 800_000_000.0 / 80.0,
        # LFG reserve
        "lfg_reserve_usd": 2_000_000_000.0,
        "lfg_reserve0": 2_000_000_000.0,
        "luna_price_hist": [80.0],
        # External shocks: moderate, mainly to trigger de-peg
        "ext_events": [
            {"step": 20, "type": "ust_sell", "usd": 250_000_000, "latency": 0},
            {"step": 28, "type": "ust_sell", "usd": 300_000_000, "latency": 0},
            {"step": 36, "type": "luna_sell", "usd": 200_000_000, "latency": 0},
            {"step": 48, "type": "ust_sell", "usd": 600_000_000, "latency": 0},
            {"step": 60, "type": "ust_sell", "usd": 900_000_000, "latency": 0},
            {"step": 80, "type": "luna_sell", "usd": 300_000_000, "latency": 0},
            {"step": 110, "type": "ust_sell", "usd": 1_500_000_000, "latency": 0},
        ],
        # v4 parameters (must be in sync with backend.model.default_params)
        "params": {
            "amm_fee": 0.003,
            "max_trade_mult": 8.0,
            # Redemption / expansion: conservative, slows LUNA supply explosion
            "redeem_alpha": 0.04,
            "max_redeem_usd_frac": 0.03,
            "max_luna_mint_frac_of_supply": 0.30,
            # Bank run (strength increases over time)
            "bankrun_low": 0.0,
            "bankrun_high": 0.06,
            "bankrun_t0": 150,
            "bankrun_tau": 45,
            "max_bankrun_frac": 0.04,
            # Delayed sell queue (LUNA -> CEX)
            "luna_cex_release_rate": 0.25,
            "arbitrage_to_cex_beta": 0.80,
            # CEX depth & impact limits
            "cex_depth_ust": 80_000_000.0,
            "cex_depth_luna": 80_000_000.0,
            "depth_halflife_steps": 800,
            "impact_coeff": 0.8,
            "max_log_up_ust": 0.12,
            "max_log_dn_ust": 0.18,
            "max_log_up_luna": 0.22,
            "max_log_dn_luna": 0.40,
            # Oracle delay
            "oracle_delay": 10,
            # LFG: intervenes on small/mid depegs, stops on deep depeg
            "lfg_trigger": 0.997,
            "lfg_per_step_usd": 400_000_000.0,
            "lfg_effectiveness": 0.35,
            "lfg_effect_decay": 0.6,
            "lfg_cutoff_depeg": 0.45,
            # LP withdrawal
            "pool_drain_base": 0.002,
            "pool_drain_slope": 0.020,
            # Hard bounds
            "ust_min": 1e-3,
            "ust_max": 1.02,
            "luna_min": 1e-8,
            "luna_max": 5e4,
        },
    }
    return state


state = terra_may_2022_preset()
data = []

# ================= Run mode =================
st.markdown("---")
mode = st.selectbox(
    "Run mode:",
    ["🧮 Local simulation (recommended)", "🔗 On-chain mode (requires contract/keys)"],
    index=0 if not chain_ok else 1,
)
use_onchain = mode.startswith("🔗") and chain_ok
if not chain_ok and use_onchain:
    st.warning("⚠️ Web3 is not available, switched back to local simulation.")
    use_onchain = False

# ================= Plot: 4×2 dashboard (smoothed) =================
def build_figure(df: pd.DataFrame) -> go.Figure:
    # --- Simple smoothing (rolling mean) ---
    def smooth(s, window=5):
        return s.rolling(window=window, min_periods=1, center=True).mean()

    fig = make_subplots(
        rows=4,
        cols=2,
        subplot_titles=(
            "💎 LUNA Spot Price (CEX)",
            "🟩 UST Spot Price (CEX)",
            "🔥 LUNA Mint / Burn / Total Supply",
            "💧 UST Mint / Burn / Total Supply",
            "🏛️ AMM vs CEX: LUNA Price (USD)",
            "🏦 LFG Reserve / Intervention & Price Spreads",
            "🧮 AMM Pool Balances (UST & LUNA)",
            "⚙️ AMM Constant Product k (relative) & UST Share",
        ),
        specs=[
            [{}, {}],
            [{"secondary_y": True}, {"secondary_y": True}],
            [{}, {"secondary_y": True}],
            [{"secondary_y": True}, {"secondary_y": True}],
        ],
        vertical_spacing=0.11,
        horizontal_spacing=0.08,
    )

    # ========== Row 1: prices (smoothed + spline) ==========
    fig.add_trace(
        go.Scatter(
            x=df["Step"],
            y=smooth(df["LUNA Price"], window=5),
            mode="lines",
            name="LUNA (CEX)",
            line=dict(color="#1f77b4", width=2),
            line_shape="spline",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=df["Step"],
            y=smooth(df["UST Price"], window=5),
            mode="lines",
            name="UST (CEX)",
            line=dict(color="#d62728", width=2),
            line_shape="spline",
        ),
        row=1,
        col=2,
    )

    # ========== Row 2: supply + mint/burn ==========
    # LUNA supply
    fig.add_trace(
        go.Scatter(
            x=df["Step"],
            y=df["LUNA Supply"],
            mode="lines",
            name="LUNA Supply",
            line=dict(color="#7f7f7f", width=2),
            line_shape="spline",
        ),
        row=2,
        col=1,
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=df["Step"],
            y=df["LUNA Minted"],
            name="LUNA Minted",
            marker_color="#2ca02c",
            opacity=0.6,
        ),
        row=2,
        col=1,
        secondary_y=True,
    )
    fig.add_trace(
        go.Bar(
            x=df["Step"],
            y=df["LUNA Burned"],
            name="LUNA Burned",
            marker_color="#d62728",
            opacity=0.6,
        ),
        row=2,
        col=1,
        secondary_y=True,
    )

    # UST supply
    fig.add_trace(
        go.Scatter(
            x=df["Step"],
            y=df["UST Supply"],
            mode="lines",
            name="UST Supply",
            line=dict(color="#7f7f7f", width=2),
            line_shape="spline",
        ),
        row=2,
        col=2,
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=df["Step"],
            y=df["UST Minted"],
            name="UST Minted",
            marker_color="#2ca02c",
            opacity=0.6,
        ),
        row=2,
        col=2,
        secondary_y=True,
    )
    fig.add_trace(
        go.Bar(
            x=df["Step"],
            y=df["UST Burned"],
            name="UST Burned",
            marker_color="#d62728",
            opacity=0.6,
        ),
        row=2,
        col=2,
        secondary_y=True,
    )

    # ========== Row 3: AMM vs CEX + LFG ==========
    # LUNA price CEX vs AMM (USD)
    fig.add_trace(
        go.Scatter(
            x=df["Step"],
            y=smooth(df["LUNA Price"], window=5),
            mode="lines",
            name="LUNA (CEX, USD)",
            line=dict(color="#1f77b4", width=2),
            line_shape="spline",
        ),
        row=3,
        col=1,
    )

    if "AMM LUNA Price (USD)" in df:
        fig.add_trace(
            go.Scatter(
                x=df["Step"],
                y=smooth(df["AMM LUNA Price (USD)"], window=5),
                mode="lines",
                name="LUNA (AMM, USD)",
                line=dict(color="#ff7f0e", width=2, dash="dot"),
                line_shape="spline",
            ),
            row=3,
            col=1,
        )

    # Spreads + LFG
    if "Spread UST" in df:
        fig.add_trace(
            go.Scatter(
                x=df["Step"],
                y=smooth(df["Spread UST"], window=5),
                mode="lines",
                name="UST spread (CEX - 1)",
                line=dict(color="#9467bd"),
                line_shape="spline",
            ),
            row=3,
            col=2,
            secondary_y=False,
        )
    if "Spread LUNA" in df:
        fig.add_trace(
            go.Scatter(
                x=df["Step"],
                y=smooth(df["Spread LUNA"], window=5),
                mode="lines",
                name="LUNA spread (CEX - AMM)",
                line=dict(color="#8c564b", dash="dot"),
                line_shape="spline",
            ),
            row=3,
            col=2,
            secondary_y=False,
        )
    if "LFG Reserve" in df:
        fig.add_trace(
            go.Scatter(
                x=df["Step"],
                y=df["LFG Reserve"],
                mode="lines",
                name="LFG Reserve (USD)",
                line=dict(color="#2ca02c", width=3),
                line_shape="spline",
            ),
            row=3,
            col=2,
            secondary_y=True,
        )
    if "LFG Spent" in df:
        fig.add_trace(
            go.Bar(
                x=df["Step"],
                y=df["LFG Spent"],
                name="LFG spent this step (USD)",
                marker_color="#17becf",
                opacity=0.5,
            ),
            row=3,
            col=2,
            secondary_y=True,
        )

    # ========== Row 4: pool balances + k / share / slippage ==========
    if "Pool UST" in df:
        fig.add_trace(
            go.Scatter(
                x=df["Step"],
                y=df["Pool UST"],
                mode="lines",
                name="Pool UST",
                line=dict(color="#1f9a4b"),
                line_shape="spline",
            ),
            row=4,
            col=1,
            secondary_y=False,
        )
    if "Pool LUNA" in df:
        fig.add_trace(
            go.Scatter(
                x=df["Step"],
                y=df["Pool LUNA"],
                mode="lines",
                name="Pool LUNA",
                line=dict(color="#e377c2", dash="dot"),
                line_shape="spline",
            ),
            row=4,
            col=1,
            secondary_y=True,
        )

    if "Pool K Rel" in df:
        fig.add_trace(
            go.Scatter(
                x=df["Step"],
                y=df["Pool K Rel"],
                mode="lines",
                name="k / k0",
                line=dict(color="#ff7f0e", width=2),
                line_shape="spline",
            ),
            row=4,
            col=2,
            secondary_y=True,
        )
    if "Pool UST Share" in df:
        fig.add_trace(
            go.Scatter(
                x=df["Step"],
                y=df["Pool UST Share"],
                mode="lines",
                name="UST share (0–1)",
                line=dict(color="#1f77b4"),
                line_shape="spline",
            ),
            row=4,
            col=2,
            secondary_y=False,
        )
    if "Slippage" in df:
        fig.add_trace(
            go.Bar(
                x=df["Step"],
                y=df["Slippage"],
                name="Slippage (this step)",
                marker_color="#d62728",
                opacity=0.35,
            ),
            row=4,
            col=2,
            secondary_y=False,
        )

    # ========== Axes & layout ==========
    for r in [1, 2, 3, 4]:
        fig.update_xaxes(title_text="Step", row=r, col=1)
        fig.update_xaxes(title_text="Step", row=r, col=2)

    fig.update_yaxes(title_text="USD", row=1, col=1)
    fig.update_yaxes(title_text="USD", row=1, col=2)
    fig.update_yaxes(title_text="Supply", row=2, col=1, secondary_y=False)
    fig.update_yaxes(title_text="Mint / Burn", row=2, col=1, secondary_y=True)
    fig.update_yaxes(title_text="Supply", row=2, col=2, secondary_y=False)
    fig.update_yaxes(title_text="Mint / Burn", row=2, col=2, secondary_y=True)
    fig.update_yaxes(title_text="USD", row=3, col=1)
    fig.update_yaxes(title_text="Spread (USD)", row=3, col=2, secondary_y=False)
    fig.update_yaxes(title_text="LFG (USD)", row=3, col=2, secondary_y=True)
    fig.update_yaxes(title_text="Pool UST", row=4, col=1, secondary_y=False)
    fig.update_yaxes(title_text="Pool LUNA", row=4, col=1, secondary_y=True)
    fig.update_yaxes(title_text="Share / Slippage", row=4, col=2, secondary_y=False)
    fig.update_yaxes(title_text="k (relative)", row=4, col=2, secondary_y=True)

    fig.update_layout(
        height=1280,
        showlegend=True,
        legend_tracegroupgap=8,
        margin=dict(l=20, r=20, t=60, b=20),
        template="plotly_white",
    )

    return fig


# ================= Simulation loop config =================
REDRAW_EVERY = 8   # redraw chart every N steps
REFRESH_MS = 120   # front-end sleep (ms)
CHART_HEIGHT = 1320

# ================= Run button =================
if st.button("Start simulation"):
    st.info(
        "🏃 Simulation running… In a few hundred steps: UST slowly de-pegs to a few cents, "
        "LUNA crashes and supply explodes."
    )

    st.markdown("---")
    top_l, top_r = st.columns(2)
    luna_txt = top_l.empty()
    ust_txt = top_r.empty()

    chart_box = st.container(height=CHART_HEIGHT, border=True)
    chart_ph = chart_box.empty()

    prev_luna_supply = state["luna_supply"]
    prev_ust_supply = state["ust_supply"]

    for step in range(1, 501):  # increase upper bound if you want longer runs
        contract = stable_contract if use_onchain else None
        state = simulate_step(state, contract, step=step, use_onchain=use_onchain)

        # Per-step changes
        luna_minted = max(0.0, state["luna_supply"] - prev_luna_supply)
        luna_burned = max(0.0, prev_luna_supply - state["luna_supply"])
        ust_minted = max(0.0, state["ust_supply"] - prev_ust_supply)
        ust_burned = max(0.0, prev_ust_supply - state["ust_supply"])

        prev_luna_supply = state["luna_supply"]
        prev_ust_supply = state["ust_supply"]

        # Record data
        data.append(
            {
                "Step": step,
                "UST Price": float(state.get("ust_price", 0.0)),
                "LUNA Price": float(state.get("luna_price", 0.0)),
                "LUNA Supply": float(state.get("luna_supply", 0.0)),
                "UST Supply": float(state.get("ust_supply", 0.0)),
                "LUNA Minted": float(luna_minted),
                "LUNA Burned": float(luna_burned),
                "UST Minted": float(ust_minted),
                "UST Burned": float(ust_burned),
                "AMM LUNA Price (USD)": state.get("amm_luna_price_usd", None),
                "AMM LUNA Price (UST)": state.get("amm_luna_price_ust", None),
                "Pool UST": state.get("pool_ust", None),
                "Pool LUNA": state.get("pool_luna", None),
                "Slippage": state.get("last_trade_slippage", 0.0),
                "LFG Reserve": state.get("lfg_reserve_usd", 0.0),
                "LFG Spent": state.get("lfg_spent_usd", 0.0),
                "Spread UST": state.get("spread_ust", 0.0),
                "Spread LUNA": state.get("spread_luna", 0.0),
                "Pool K": state.get("pool_k", None),
                "Pool K Rel": state.get("pool_k_rel", None),
                "Pool UST Share": state.get("pool_ust_share", None),
            }
        )
        df = pd.DataFrame(data)

        # Top-level price labels
        luna_txt.markdown(
            f"<div style='font-size:16px'>💎 LUNA price: "
            f"<b>${state['luna_price']:.6f}</b></div>",
            unsafe_allow_html=True,
        )
        ust_txt.markdown(
            f"<div style='font-size:16px'>🟩 UST price: "
            f"<b>${state['ust_price']:.6f}</b></div>",
            unsafe_allow_html=True,
        )

        # Throttled redraw
        if step % REDRAW_EVERY == 0 or step in (1, 500):
            fig = build_figure(df)
            chart_ph.plotly_chart(fig, use_container_width=True)

        time.sleep(REFRESH_MS / 1000.0)

    st.success("✅ Simulation finished!")

st.caption(
    "If you want to match specific historical anchor points "
    "(for example: UST ≈ 0.9 at step N, ≈ 0.3 at step M), "
    "tell me your targets and I can help tune a parameter set to fit them."
)