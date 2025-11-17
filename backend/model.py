# backend/model.py
import math
import random
from typing import List, Dict, Tuple

# ---------- 工具 ----------

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def bounded_impact_asym(price: float, net_usd: float, depth_usd: float,
                        coeff: float, max_up: float, max_dn: float) -> float:
    """
    不对称、有界价格冲击（下跌更快、上涨受限）
    p' = p * exp( ±max_* * tanh(coeff*flow/depth) )
    """
    if price <= 0 or depth_usd <= 0:
        return max(price, 1e-12)
    x = coeff * (net_usd / depth_usd)
    if x >= 0:
        log_move = max_up * math.tanh(x)
    else:
        log_move = -max_dn * math.tanh(-x)
    return max(price * math.exp(log_move), 1e-12)

def cpmm_swap_x_for_y(x_res: float, y_res: float, dx: float, fee: float,
                      max_trade_mult: float) -> Tuple[float, float, float, float, float]:
    """
    常乘积 AMM：X->Y，含手续费与单笔上限
    返回 (dy_out, new_x, new_y, effective_price, slippage_pct)
    """
    if dx <= 0 or x_res <= 0 or y_res <= 0:
        return 0.0, max(x_res, 1e-12), max(y_res, 1e-12), 0.0, 0.0
    dx_eff = min(dx * (1 - fee), max_trade_mult * x_res)
    k = x_res * y_res
    new_x = x_res + dx_eff
    new_y = k / new_x
    dy_out = max(y_res - new_y, 0.0)

    pre_marginal = y_res / x_res
    eff_price = dy_out / dx if dx > 0 else 0.0
    slip = 0.0 if pre_marginal <= 0 else 1 - (eff_price / pre_marginal)
    return dy_out, max(new_x, 1e-12), max(new_y, 1e-12), max(eff_price, 0.0), max(slip, 0.0)

# ---------- 默认参数（v4 更保守） ----------

def default_params() -> Dict:
    return {
        # AMM
        "amm_fee": 0.003,
        "max_trade_mult": 8.0,

        # 赎回 / 增发：整体减半，放慢 LUNA 膨胀
        "redeem_alpha": 0.04,
        "max_redeem_usd_frac": 0.03,
        "max_luna_mint_frac_of_supply": 0.30,

        # 银行挤兑：随着时间才变猛
        "bankrun_low": 0.0,
        "bankrun_high": 0.06,
        "bankrun_t0": 150,   # 中点在 150 步
        "bankrun_tau": 45,
        "max_bankrun_frac": 0.04,

        # 抛压延迟队列（LUNA -> CEX）
        "luna_cex_release_rate": 0.25,   # 每步释放 25% 排队 LUNA
        "arbitrage_to_cex_beta": 0.80,   # 80% 铸出 LUNA 排队去 CEX，其余打 AMM

        # CEX 深度：更深 + 更慢衰减 + 更小单步跌幅
        "cex_depth_ust": 80_000_000.0,
        "cex_depth_luna": 80_000_000.0,
        "depth_halflife_steps": 800,     # 时间半衰期：800 步
        "impact_coeff": 0.8,
        "max_log_up_ust": 0.12,  # UST 单步上涨极限 ≈ +13%
        "max_log_dn_ust": 0.18,  # UST 单步下跌极限 ≈ -16%
        "max_log_up_luna": 0.22,
        "max_log_dn_luna": 0.40,

        # 预言机延迟
        "oracle_delay": 10,

        # LFG：前 100 多步会明显用钱；深度脱锚才会停
        "lfg_trigger": 0.997,
        "lfg_per_step_usd": 400_000_000.0,
        "lfg_effectiveness": 0.35,
        "lfg_effect_decay": 0.6,   # 储备越少效能越差
        "lfg_cutoff_depeg": 0.45,  # UST 跌破 0.55 以后基本不救

        # AMM 撤池（脱锚越深撤得越快）
        "pool_drain_base": 0.002,
        "pool_drain_slope": 0.020,

        # 硬边界
        "ust_min": 1e-3, "ust_max": 1.02,
        "luna_min": 1e-8, "luna_max": 5e4,
    }

def default_ext_events() -> list:
    return []

# ---------- 主循环 ----------

def compute_new_state(state: Dict, step: int = 1) -> Dict:
    P = {**default_params(), **(state.get("params") or {})}

    # 取参
    fee = float(P["amm_fee"]); max_trade_mult = float(P["max_trade_mult"])
    alpha = float(P["redeem_alpha"]); max_frac = float(P["max_redeem_usd_frac"])
    max_luna_mint_frac = float(P["max_luna_mint_frac_of_supply"])

    bank_low = float(P["bankrun_low"]); bank_high = float(P["bankrun_high"])
    t0 = float(P["bankrun_t0"]); tau = float(P["bankrun_tau"])
    bank_max = float(P["max_bankrun_frac"])

    beta_cex = float(P["arbitrage_to_cex_beta"])
    rel_rate = float(P["luna_cex_release_rate"])

    depth_ust0 = float(P["cex_depth_ust"]); depth_luna0 = float(P["cex_depth_luna"])
    halflife = max(1.0, float(P["depth_halflife_steps"]))
    coeff = float(P["impact_coeff"])
    up_u, dn_u = float(P["max_log_up_ust"]), float(P["max_log_dn_ust"])
    up_l, dn_l = float(P["max_log_up_luna"]), float(P["max_log_dn_luna"])

    oracle_delay = int(P["oracle_delay"])

    lfg_trigger = float(P["lfg_trigger"])
    lfg_step = float(P["lfg_per_step_usd"])
    lfg_eff = float(P["lfg_effectiveness"])
    lfg_decay = float(P["lfg_effect_decay"])
    lfg_cutoff = float(P["lfg_cutoff_depeg"])

    drain_base = float(P["pool_drain_base"]); drain_slope = float(P["pool_drain_slope"])

    ust_min = float(P["ust_min"]); ust_max = float(P["ust_max"])
    luna_min = float(P["luna_min"]); luna_max = float(P["luna_max"])

    # 状态
    ust_price = float(state["ust_price"]); luna_price = float(state["luna_price"])
    ust_supply = float(state["ust_supply"]); luna_supply = float(state["luna_supply"])
    pool_ust = float(state.get("pool_ust", 5_000_000.0))
    pool_luna = float(state.get("pool_luna", max(5_000_000.0 / max(luna_price, 1e-8), 1.0)))

    lfg_reserve = float(state.get("lfg_reserve_usd", 0.0))
    lfg_reserve0 = float(state.get("lfg_reserve0", max(lfg_reserve, 1.0)))

    # 抛压延迟队列（LUNA 数量）
    pending_luna = float(state.get("pending_luna_cex", 0.0))

    # k0
    pool_k0 = state.get("pool_k0")
    if pool_k0 is None:
        pool_k0 = pool_ust * pool_luna

    # 预言机
    hist = state.get("luna_price_hist") or [luna_price]
    hist.append(luna_price)
    if len(hist) > 1024:
        hist = hist[-1024:]
    oracle_luna_price = hist[-(oracle_delay + 1)] if len(hist) > oracle_delay else luna_price

    # 外部事件
    ext_events = state.get("ext_events") or default_ext_events()
    ust_net_flow_usd = 0.0; luna_net_flow_usd = 0.0
    for ev in ext_events:
        if step == int(ev.get("step", -1)) + int(ev.get("latency", 0)):
            usd = float(ev.get("usd", 0.0)); typ = ev.get("type")
            if   typ == "ust_sell":  ust_net_flow_usd  -= usd
            elif typ == "ust_buy":   ust_net_flow_usd  += usd
            elif typ == "luna_sell": luna_net_flow_usd -= usd
            elif typ == "luna_buy":  luna_net_flow_usd += usd

    # 噪声
    ust_price *= 1 + random.uniform(-0.001, 0.001)
    luna_price *= 1 + random.uniform(-0.006, 0.006)

    # 有效深度（时间衰减 + 脱锚衰减）
    time_decay = 0.5 ** (step / halflife)
    depeg_now = clamp(1.0 - ust_price, 0.0, 1.0)
    depeg_decay = 0.7 + 0.3 * math.exp(-depeg_now / 0.15)  # 小脱锚时深度更高
    depth_ust = max(1e5, depth_ust0 * time_decay * depeg_decay)
    depth_luna = max(1e5, depth_luna0 * time_decay * depeg_decay)

    # 银行挤兑强度（随时间拉升的 sigmoid）
    bank_alpha = bank_low + (bank_high - bank_low) * (
        1.0 / (1.0 + math.exp(-(step - t0) / max(tau, 1e-6)))
    )
    if ust_price < 1.0:
        bank_usd = clamp(bank_alpha * depeg_now * ust_supply, 0.0, bank_max * ust_supply)
        ust_price = bounded_impact_asym(ust_price, -bank_usd, depth_ust, coeff, up_u, dn_u)

    # 赎回/增发
    lfg_spent = 0.0; last_slip = 0.0
    max_step_usd = max_frac * ust_supply

    if ust_price < 1.0:
        redeem_usd = clamp(alpha * depeg_now * ust_supply, 0.0, max_step_usd)
        if redeem_usd > 0.0 and oracle_luna_price > 0.0:
            ust_supply -= redeem_usd
            minted_luna = min(redeem_usd / oracle_luna_price,
                              max_luna_mint_frac * max(luna_supply, 1.0))
            luna_supply += minted_luna

            # 一部分打 AMM
            dx_amm = (1 - beta_cex) * minted_luna
            if dx_amm > 0:
                dx_amm = min(dx_amm, pool_luna * 0.95)
                _, new_luna, new_ust, _, slip = cpmm_swap_x_for_y(
                    pool_luna, pool_ust, dx_amm, fee=fee, max_trade_mult=max_trade_mult
                )
                pool_luna, pool_ust = new_luna, new_ust
                last_slip = slip

            # 其余排队去 CEX
            pending_luna += max(minted_luna - dx_amm, 0.0)

    elif ust_price > 1.0:
        overpeg = clamp(ust_price - 1.0, 0.0, 1.0)
        mint_usd = clamp(alpha * overpeg * ust_supply, 0.0, 0.4 * max_step_usd)
        if mint_usd > 0.0 and oracle_luna_price > 0.0:
            burn_luna = min(mint_usd / oracle_luna_price, luna_supply * 0.06)
            luna_supply -= burn_luna
            ust_supply += mint_usd
            dx = min(mint_usd, pool_ust * 0.95)
            _, new_ust, new_luna, _, slip = cpmm_swap_x_for_y(
                pool_ust, pool_luna, dx, fee=fee, max_trade_mult=max_trade_mult
            )
            pool_ust, pool_luna = new_ust, new_luna
            last_slip = slip

    # LFG：小〜中等脱锚时出手力度大；深度脱锚停止
    if ust_price < lfg_trigger and lfg_reserve > 0.0:
        depeg = depeg_now
        if depeg < lfg_cutoff:
            # depeg 越大，front_mult 越大（但封顶）
            front_mult = 1.0 + 3.0 * (depeg / 0.25) ** 1.2
            front_mult = clamp(front_mult, 1.0, 4.0)
            spend = min(lfg_step * front_mult, lfg_reserve)
            if spend > 0:
                lfg_reserve -= spend
                lfg_spent = spend
                eff = lfg_eff * ((lfg_reserve / lfg_reserve0) ** lfg_decay)
                ust_price = bounded_impact_asym(
                    ust_price, eff * spend, depth_ust, coeff, up_u, dn_u
                )

    # CEX 抛压队列释放
    if pending_luna > 0:
        sell_qty = rel_rate * pending_luna
        pending_luna -= sell_qty
        luna_price = bounded_impact_asym(
            luna_price, -(sell_qty * luna_price), depth_luna, coeff, up_l, dn_l
        )

    # 外部事件
    if ust_net_flow_usd:
        ust_price = bounded_impact_asym(ust_price, ust_net_flow_usd, depth_ust, coeff, up_u, dn_u)
    if luna_net_flow_usd:
        luna_price = bounded_impact_asym(luna_price, luna_net_flow_usd, depth_luna, coeff, up_l, dn_l)

    # 撤池：UST < 1 时逐步撤流动性
    if ust_price < 1.0:
        drain = clamp(drain_base + drain_slope * depeg_now, 0.0, 0.25)
        pool_ust *= (1 - drain); pool_luna *= (1 - drain)

    # 硬边界
    ust_price = clamp(ust_price, ust_min, ust_max)
    luna_price = clamp(luna_price, luna_min, luna_max)

    # 指标
    amm_luna_price_ust = pool_ust / pool_luna if pool_luna > 0 else float("inf")
    amm_luna_price_usd = amm_luna_price_ust * ust_price
    spread_ust = ust_price - 1.0
    spread_luna = luna_price - amm_luna_price_usd

    pool_k = pool_ust * pool_luna
    pool_k_rel = (pool_k / pool_k0) if pool_k0 > 0 else 1.0
    total_ust_equiv = pool_ust + pool_luna * amm_luna_price_ust
    pool_ust_share = (pool_ust / total_ust_equiv) if total_ust_equiv > 0 else 0.5

    return {
        "ust_price": ust_price, "luna_price": luna_price,
        "ust_supply": max(ust_supply, 0.0), "luna_supply": max(luna_supply, 0.0),

        "pool_ust": pool_ust, "pool_luna": pool_luna, "pool_k0": pool_k0,
        "lfg_reserve_usd": lfg_reserve, "lfg_reserve0": lfg_reserve0,
        "luna_price_hist": hist,
        "pending_luna_cex": max(pending_luna, 0.0),

        "amm_luna_price_ust": amm_luna_price_ust,
        "amm_luna_price_usd": amm_luna_price_usd,
        "last_trade_slippage": last_slip,
        "lfg_spent_usd": lfg_spent,
        "spread_ust": spread_ust, "spread_luna": spread_luna,
        "pool_k": pool_k, "pool_k_rel": pool_k_rel, "pool_ust_share": pool_ust_share,

        "params": P, "ext_events": ext_events,
    }